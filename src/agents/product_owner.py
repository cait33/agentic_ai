"""Product Owner Agent

Responsibilities:
- Creating requirements from a brief
- Use the requirements and brief to create user stories.
- Use the brief and user stories to create acceptance criteria.
- Using user stories and brief to calculate backlog value for each story.
- Validate when and if requirements are met.

Tools:
- Reads project files.
- Write to only the requirements, user stories, acceptance criteria and backlog files.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path
from typing import Any, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError

from src.app.settings import get_settings
from src.llm.factory import get_chat_model
from src.observability.tracing import (
    append_trace,
    estimate_cost_credits,
    usage_from_message,
)

from enum import Enum

class FileChoice(Enum):
    REQUIREMENTS = "requirements"
    USER_STORIES = "user_stories"
    ACCEPTANCE_CRITERIA = "acceptance_criteria"
    BACKLOG = "backlog"

REPO_ROOT = Path(__file__).resolve().parents[1]


class Finding(BaseModel):
    severity: Literal["low", "medium", "high"]
    description: str

class AcceptanceCriteria(BaseModel):
    description: str

class UserStory(BaseModel):
    id: str
    description: str
    Acceptance_criteria: list[AcceptanceCriteria] = Field(default_factory=list)
    backlog_value: int = Field(description="Business value score for the backlog")

class Requirement(BaseModel):
    id: str
    description: str
    is_met: bool = Field(description="Validation if requirement is met")

class ProductOwnerResult(BaseModel):
    status: Literal["success", "needs_clarification", "unparseable"]
    summary: str
    requirements: list[Requirement] = Field(default_factory = list)
    user_stories: list[UserStory]=Field(default_factory=list)

class POState(TypedDict, total=False):
    input_path: str
    file_content: str
    content_to_write: str
    file_to_write: FileChoice
    result: dict[str, Any]
    error: str


def read_repository_text_file(relative_path: str) -> str:
    """Read a UTF-8 file while preventing access outside the repository. (Tool from file_review_agent)"""
    requested = (REPO_ROOT / relative_path).resolve()
    try:
        requested.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError("Path escapes repository root") from exc

    if not requested.is_file():
        raise FileNotFoundError(relative_path)
    return requested.read_text(encoding="utf-8")


def write_repository_text_file(file_choice: FileChoice, content: str) -> bool:
    """Write to one of the following (UTF-8) files: requirements, user stories, acceptance criteria and backlog files. (Tool)"""
    requested_path = (REPO_ROOT / 'src/app/requirements' ).resolve()
    if not requested_path.is_dir():
        requested_path.mkdir()
    requested_file = (requested_path / file_choice.value).resolve()
    requested_file.touch(exist_ok=True)
    if requested_file.write_text(content) != None:
        return True
    else:
        return False


def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return str(content)


def _parse_result(text: str) -> ProductOwnerResult:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].lstrip()

    # Be tolerant of a short explanation around the JSON object.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]

    try:
        return ProductOwnerResult.model_validate(json.loads(cleaned))
    except (json.JSONDecodeError, ValidationError):
        return ProductOwnerResult(
            status="unparseable",
            summary=text[:1000],
            findings=[],
        )


def build_graph(llm: Any | None = None, *, trace_context: dict[str, Any] | None = None):
    llm = llm if llm is not None else get_chat_model()
    trace_context = trace_context if trace_context is not None else {"tools": [], "calls": 0}

    def read_file(state: POState) -> POState:
        trace_context["tools"].append("read_repository_text_file")
        try:
            return {
                "file_content": read_repository_text_file(state["input_path"])
            }
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def route_after_read(state: POState):
        return END if state.get("error") else "process_requirements"

    def write_file(state: POState) -> POState:
        trace_context["tools"].append("read_repository_text_file")
        try:
            return {
                "content_to_write": write_repository_text_file(state["file_to_write"])
            }
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def route_after_write(state:POState):
        return END if state.get("error") else "process_requirements"
    
    def process_requirements(state: POState) -> POState:
        system = SystemMessage(
            content=(
                "You are an expert Product Owner Agent. Your responsibilities are:\n"
                "- Create requirements from a provided brief.\n"
                "- Use the requirements and brief to create user stories.\n"
                "- Use the brief and user stories to create acceptance criteria.\n"
                "- Calculate backlog value for each story.\n"
                "- Validate when and if requirements are met.\n\n"
                "Return ONLY valid JSON with keys: 'status' (success or needs_clarification), "
                "'summary', 'requirements' (list of objects with id, description, and is_met), "
                "and 'user_stories' (list of objects with id, description, acceptance_criteria, and backlog_value)."
            )
        )   
        human = HumanMessage(
            content=(
                f"Act as the Product Owner. Read the following project brief from {state['input_path']} "
                "and generate the structured requirements, user stories, acceptance criteria, and backlog values.\n\n"
                f"PROJECT BRIEF CONTENT:\n{state['file_content']}"
            )
        )
        trace_context["calls"] += 1
        response = llm.invoke([system, human])
        trace_context["input_tokens"], trace_context["output_tokens"] = usage_from_message(response)
        result = _parse_result(_message_text(response))
        result_dict = result.model_dump()
        result_dict["_usage"] = usage_from_message(response)
        return {"result": result_dict}

    builder = StateGraph(POState)
    builder.add_node("read_file", read_file)
    builder.add_node("write_file", write_file)
    builder.add_node("process_requirements", process_requirements)
    builder.add_edge(START, "read_file")
    builder.add_conditional_edges("read_file", route_after_read, ["process_requirements", END])
    builder.add_edge("process_requirements", END)
    builder.add_edge(START, "write_file")
    builder.add_conditional_edges("write_file", route_after_write, ["process_requirements", END])
    builder.add_edge("process_requirements", END)
    return builder.compile()


def run_process_requirements(
    input_path: str,
    *,
    task_id: str = "PO-DEMO",
    llm: Any | None = None,
    trace_file: str | None = None,
) -> ProductOwnerResult:
    settings = get_settings()
    run_id = str(uuid.uuid4())
    started = time.perf_counter()
    context: dict[str, Any] = {
        "tools": [], "calls": 0, "input_tokens": None, "output_tokens": None,
    }
    record: dict[str, Any] = {
        "run_id": run_id,
        "workflow_id": run_id,
        "task_id": task_id,
        "agent": "product-owner-agent",
        "role": "product-owner",
        "provider": settings.llm_provider if llm is None else "injected",
        "model": settings.llm_model if llm is None else (
            getattr(llm, "model", None) or getattr(llm, "model_name", None)
            or type(llm).__name__
        ),
        "status": "error",
    }
    try:
        graph = build_graph(llm, trace_context=context)
        state = graph.invoke({"input_path": input_path}, {"recursion_limit": 10})
        if state.get("error"):
            raise RuntimeError(state["error"])
        raw = dict(state["result"])
        raw.pop("_usage", None)
        result = ProductOwnerResult.model_validate(raw)
        record["result_status"] = result.status 
        record["status"] = "invalid_output" if result.status == "unparseable" else "success"
        return result
    except (Exception, KeyboardInterrupt) as exc:
        record["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "error"
        # Do not persist provider exception text: it may contain credentials/URLs.
        record["error_type"] = type(exc).__name__
        raise
    finally:
        duration = time.perf_counter() - started
        append_trace(
            {
                **record,
                **context,
                "duration_seconds": round(duration, 4),
                "estimated_cost_credits": estimate_cost_credits(
                    duration_seconds=duration,
                    input_tokens=context["input_tokens"],
                    output_tokens=context["output_tokens"],
                    calls=context["calls"],
                ),
                "token_usage_complete": context["input_tokens"] is not None
                and context["output_tokens"] is not None,
            },
            trace_file,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Repository-relative file path")
    parser.add_argument("--task-id", default="STARTER-DEMO")
    args = parser.parse_args()

    result = run_process_requirements(args.input, task_id=args.task_id)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
