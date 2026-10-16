"""Software Architect Agent for EventAI.

Responsibilities:
- Inspects project files (Tool).
- Evaluates architectural design and best practices (LLM).
- Outputs structured architecture decision drafts or change requests.
- Emits execution traces for observability.
"""

import argparse
import json
import time
import uuid
from pathlib import Path
from typing import Any, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError

from src.llm.factory import get_chat_model
from src.observability.tracing import (
    append_trace,
    estimate_cost_credits,
    usage_from_message,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


class ArchitectureViolation(BaseModel):
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    recommendation: str


class ArchitectureReviewResult(BaseModel):
    status: Literal["approved", "changes_requested", "unparseable"]
    architectural_summary: str
    violations: list[ArchitectureViolation] = Field(default_factory=list)


class ArchitectState(TypedDict, total=False):
    target_file: str
    file_content: str
    result: dict[str, Any]
    error: str


def read_workspace_file(relative_path: str) -> str:
    """TOOL: Read a file from the repository safely."""
    requested = (REPO_ROOT / relative_path).resolve()
    try:
        requested.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError("Security violation: Path escapes repository root") from exc

    if not requested.is_file():
        raise FileNotFoundError(f"Target file not found: {relative_path}")
    return requested.read_text(encoding="utf-8")


def _extract_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join([item if isinstance(item, str) else item.get("text", "") for item in content])
    return str(content)


def _parse_llm_json(text: str) -> ArchitectureReviewResult:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].lstrip()

    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]

    try:
        return ArchitectureReviewResult.model_validate(json.loads(cleaned))
    except (json.JSONDecodeError, ValidationError):
        return ArchitectureReviewResult(
            status="unparseable",
            architectural_summary="Failed to parse LLM output.",
            violations=[],
        )


def build_architect_graph(llm: Any | None = None):
    llm = llm or get_chat_model()

    def inspect_code(state: ArchitectState) -> ArchitectState:
        try:
            # Tool invocation
            content = read_workspace_file(state["target_file"])
            return {"file_content": content}
        except Exception as exc:
            return {"error": str(exc)}

    def route_inspection(state: ArchitectState):
        return END if state.get("error") else "evaluate_architecture"

    def evaluate_architecture(state: ArchitectState) -> ArchitectState:
        system = SystemMessage(
            content=(
                "You are the Software Architect of EventAI. Evaluate the provided source code "
                "for architectural integrity, separation of concerns, and hardcoded dependencies. "
                "Return ONLY valid JSON with keys: 'status' (approved or changes_requested), "
                "'architectural_summary', and 'violations' (list of objects with 'severity', "
                "'description', 'recommendation')."
            )
        )
        human = HumanMessage(
            content=(
                f"Perform an architectural review on: {state['target_file']}\n\n"
                f"SOURCE CODE:\n{state['file_content']}"
            )
        )

        response = llm.invoke([system, human])
        result = _parse_llm_json(_extract_text(response))
        result_dict = result.model_dump()
        result_dict["_usage"] = usage_from_message(response)

        return {"result": result_dict}

    builder = StateGraph(ArchitectState)
    builder.add_node("inspect_code", inspect_code)
    builder.add_node("evaluate_architecture", evaluate_architecture)

    builder.add_edge(START, "inspect_code")
    builder.add_conditional_edges("inspect_code", route_inspection, ["evaluate_architecture", END])
    builder.add_edge("evaluate_architecture", END)

    return builder.compile()


def run_architect_agent(
        target_file: str,
        *,
        task_id: str = "ARCH-REVIEW-01",
        llm: Any | None = None,
        trace_file: str | None = None,
) -> ArchitectureReviewResult:
    run_id = str(uuid.uuid4())
    started = time.perf_counter()

    graph = build_architect_graph(llm=llm)
    state = graph.invoke({"target_file": target_file})
    duration = time.perf_counter() - started
    model_name = getattr(llm, "model", None) or getattr(llm, "model_name", None) or "qwen3:4b"

    trace_log = {
        "run_id": run_id,
        "task_id": task_id,
        "agent": "software-architect-agent",
        "model": model_name,
        "tools": ["read_workspace_file"],
        "duration_seconds": round(duration, 4),
    }

    if state.get("error"):
        trace_log.update({"status": "error", "error": state["error"]})
        append_trace(trace_log, trace_file)
        raise RuntimeError(state["error"])

    raw = dict(state["result"])
    input_tokens, output_tokens = raw.pop("_usage", (None, None))
    result = ArchitectureReviewResult.model_validate(raw)

    trace_log.update({
        "status": "success",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_credits": estimate_cost_credits(
            duration_seconds=duration, input_tokens=input_tokens, output_tokens=output_tokens
        ),
    })
    append_trace(trace_log, trace_file)

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="File to review")
    args = parser.parse_args()

    result = run_architect_agent(args.file)
    print(result.model_dump_json(indent=2))