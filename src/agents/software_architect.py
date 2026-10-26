"""Software Architect Agent for EventAI.

Responsibilities:
- Inspects project files (Tool).
- Evaluates architectural design and best practices (LLM).
- Outputs structured architecture decision drafts or change requests.
- Emits execution traces for observability with task and workflow context.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError

from src.llm.factory import get_chat_model
from src.models.task import EngineeringTask
from src.observability.tracing import (
    append_trace,
    estimate_cost_credits,
    usage_from_message,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHITECT_MAX_OUTPUT_TOKENS = 1536


class ArchitectureViolation(BaseModel):
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    recommendation: str


class ArchitectureReviewResult(BaseModel):
    status: Literal["approved", "changes_requested", "unparseable"]
    architectural_summary: str
    violations: list[ArchitectureViolation] = Field(default_factory=list)


# Schema für Ollama structured output
class _LLMArchitectOutput(BaseModel):
    status: Literal["approved", "changes_requested"]
    architectural_summary: str
    violations: list[ArchitectureViolation] = Field(default_factory=list)


def _prepare_llm(llm: Any) -> Any:
    """Forces structured JSON output on Ollama to prevent truncated reasoning."""
    try:
        from langchain_ollama import ChatOllama
    except ImportError:  # pragma: no cover
        return llm
    if isinstance(llm, ChatOllama):
        return llm.model_copy(
            update={
                "reasoning": False,
                "format": _LLMArchitectOutput.model_json_schema(),
                "num_predict": max(llm.num_predict or 0, ARCHITECT_MAX_OUTPUT_TOKENS),
            }
        )
    return llm


class ArchitectState(TypedDict, total=False):
    task: EngineeringTask
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
    # Entfernt evtl. verbliebene Denk-Blöcke
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
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
    llm = llm if llm is not None else _prepare_llm(get_chat_model())

    def inspect_code(state: ArchitectState) -> ArchitectState:
        try:
            target = state.get("target_file")
            if not target and state.get("task") and state["task"].input_files:
                target = state["task"].input_files[0]
            if not target:
                raise ValueError("No target file specified in task or state.")

            content = read_workspace_file(target)
            return {"target_file": target, "file_content": content}
        except Exception as exc:
            return {"error": str(exc)}

    def route_inspection(state: ArchitectState):
        return END if state.get("error") else "evaluate_architecture"

    def evaluate_architecture(state: ArchitectState) -> ArchitectState:
        system = SystemMessage(
            content=(
                "You are the Software Architect of EventAI. Evaluate the source code for architectural integrity, "
                "separation of concerns, and dependency management. Keep it concise. "
                "Reply ONLY with a compact valid JSON object matching the requested schema."
            )
        )
        human = HumanMessage(
            content=(
                f"Perform an architectural review on: {state.get('target_file')}\n\n"
                f"SOURCE CODE:\n{state.get('file_content', '')}\n\n/no_think"
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
        target: str | EngineeringTask,
        *,
        task_id: str = "ARCH-REVIEW-01",
        llm: Any | None = None,
        trace_file: str | None = None,
) -> ArchitectureReviewResult:
    if isinstance(target, EngineeringTask):
        task = target
        target_file = task.input_files[0] if task.input_files else ""
        actual_task_id = task.task_id
        workflow_id = task.workflow_id
    else:
        target_file = target
        actual_task_id = task_id
        task = EngineeringTask(
            task_id=actual_task_id,
            task_type="architecture_review",
            description=f"Architecture review of {target_file}",
            assigned_role="software_architect",
            input_files=[target_file] if target_file else [],
        )
        workflow_id = task.workflow_id

    run_id = str(uuid.uuid4())
    started = time.perf_counter()

    graph = build_architect_graph(llm=llm)
    state = graph.invoke({"task": task, "target_file": target_file})
    duration = time.perf_counter() - started
    model_name = getattr(llm, "model", None) or getattr(llm, "model_name", None) or "qwen3:4b"

    trace_log = {
        "run_id": run_id,
        "workflow_id": workflow_id,
        "task_id": actual_task_id,
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

    trace_status = "invalid_output" if result.status == "unparseable" else "success"

    trace_log.update({
        "status": trace_status,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_credits": estimate_cost_credits(
            duration_seconds=duration, input_tokens=input_tokens, output_tokens=output_tokens
        ),
    })
    append_trace(trace_log, trace_file)

    return result


ARCHITECT_ROLE = "software_architect"


def run_architect_task(
        task: EngineeringTask,
        *,
        llm: Any | None = None,
        trace_file: str | None = None,
) -> ArchitectureReviewResult:
    if task.assigned_role != ARCHITECT_ROLE:
        raise ValueError(f"Architect agent only accepts tasks for role {ARCHITECT_ROLE!r}")
    if not task.input_files:
        raise ValueError("Architect task needs a file to review in input_files")

    return run_architect_agent(
        task,
        llm=llm,
        trace_file=trace_file,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="File to review")
    args = parser.parse_args()

    result = run_architect_agent(args.file)
    print(result.model_dump_json(indent=2))