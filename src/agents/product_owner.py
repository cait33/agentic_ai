"""Product Owner Agent

Role: product_owner_requirements

Responsibilities:
- Create requirements from a project brief.
- Use the requirements and brief to create user stories.
- Create acceptance criteria for each user story.
- Calculate a backlog value for each story.
- Validate whether requirements are met.

Tools:
- read_repository_text_file: reads the brief (only inside the repository)
- write_repository_text_file: writes requirements / user stories / acceptance
  criteria / backlog as JSON into the output directory (default docs/requirements/<task_id>/)

Guards:
- At most one LLM call; for Ollama: structured JSON output (schema), no reasoning,
  max 1536 output tokens; unparseable output -> status "unparseable", nothing is written.
- Output is tolerant of typical small-model deviations (criteria as strings,
  missing is_met / backlog_value, <think> blocks).
"""

from __future__ import annotations

import argparse
import json
import re
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError, field_validator

from src.app.settings import get_settings
from src.llm.factory import get_chat_model
from src.models.task import EngineeringTask
from src.observability.tracing import (
    append_trace,
    estimate_cost_credits,
    usage_from_message,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = "docs/requirements"
AGENT_NAME = "product-owner-agent"
ROLE = "product_owner_requirements"


class FileChoice(Enum):
    REQUIREMENTS = "requirements.json"
    USER_STORIES = "user_stories.json"
    ACCEPTANCE_CRITERIA = "acceptance_criteria.json"
    BACKLOG = "backlog.json"


def take_latest_error(current: Optional[str], new: Optional[str]) -> Optional[str]:
    """Reducer that retains the latest error string in LangGraph state."""
    return new if new is not None else current


# --------------------------------------------------------------------------- #
# Result models (tolerant of small-model output)
# --------------------------------------------------------------------------- #
class AcceptanceCriteria(BaseModel):
    description: str


class UserStory(BaseModel):
    id: str
    description: str
    acceptance_criteria: list[AcceptanceCriteria] = Field(default_factory=list)
    backlog_value: int = Field(default=0, ge=0, description="Business value score for the backlog")

    @field_validator("acceptance_criteria", mode="before")
    @classmethod
    def criteria_as_objects(cls, value: Any) -> Any:
        # Models often return ["text", ...] instead of [{"description": "text"}, ...]
        if isinstance(value, list):
            return [{"description": v} if isinstance(v, str) else v for v in value]
        return value

    @field_validator("backlog_value", mode="before")
    @classmethod
    def round_value(cls, value: Any) -> Any:
        if isinstance(value, float):
            return round(value)
        return value


class Requirement(BaseModel):
    id: str
    description: str
    is_met: bool = Field(default=False, description="Validation if requirement is met")


class ProductOwnerResult(BaseModel):
    status: Literal["success", "needs_clarification", "unparseable"]
    summary: str
    requirements: list[Requirement] = Field(default_factory=list)
    user_stories: list[UserStory] = Field(default_factory=list)


class POState(TypedDict, total=False):
    input_path: str
    file_content: str
    result: dict[str, Any]
    written_files: list[str]
    error: Annotated[Optional[str], take_latest_error]


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
def _inside_repo(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError("Path escapes repository root") from exc
    return resolved


def read_repository_text_file(relative_path: str) -> str:
    """TOOL: read a UTF-8 file, only inside the repository."""
    requested = _inside_repo(REPO_ROOT / relative_path)
    if not requested.is_file():
        raise FileNotFoundError(f"File not found: {relative_path}")
    return requested.read_text(encoding="utf-8")


def write_repository_text_file(file_choice: FileChoice, content: str, output_dir: Path) -> Path:
    """TOOL: write one of the four allowed PO artefacts into output_dir."""
    if not isinstance(file_choice, FileChoice):
        raise ValueError("Only requirements, user stories, acceptance criteria and backlog may be written")
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / file_choice.value
    target.write_text(content, encoding="utf-8")
    return target


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(i if isinstance(i, str) else str(i.get("text", "")) for i in content)
    return str(content)


def _parse_result(text: str) -> ProductOwnerResult:
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        return ProductOwnerResult.model_validate(json.loads(cleaned))
    except (json.JSONDecodeError, ValidationError) as exc:
        return ProductOwnerResult(status="unparseable", summary=f"Invalid JSON from model: {type(exc).__name__}")



# Output contract for the model. qwen3 keeps "thinking" in plain text even with
# reasoning disabled, so for Ollama we use structured output: the JSON schema
# below is passed as `format`, and the model can only emit JSON of this shape.
PO_MAX_OUTPUT_TOKENS = 1536


class _LLMUserStory(BaseModel):
    id: str
    description: str
    acceptance_criteria: list[str]
    backlog_value: int


class _LLMOutput(BaseModel):
    status: Literal["success", "needs_clarification"]
    summary: str
    requirements: list[Requirement]
    user_stories: list[_LLMUserStory]


def _prepare_llm(llm: Any) -> Any:
    try:
        from langchain_ollama import ChatOllama
    except ImportError:  # pragma: no cover
        return llm
    if isinstance(llm, ChatOllama):
        return llm.model_copy(
            update={
                "reasoning": False,
                "format": _LLMOutput.model_json_schema(),
                "num_predict": max(llm.num_predict or 0, PO_MAX_OUTPUT_TOKENS),
            }
        )
    return llm


# --------------------------------------------------------------------------- #
# Graph
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT = (
    "You are the Product Owner of EventAI. From a project brief you create requirements, "
    "user stories, acceptance criteria and a backlog value (0-100) per story.\n"
    "Reply ONLY with one compact JSON object, no other text. Keep it short: "
    "at most 4 requirements and at most 4 user stories, at most 2 short acceptance criteria each.\n"
    "If the text is not a project brief (e.g. source code), return status 'needs_clarification', "
    "the reason in 'summary' and empty lists.\n"
    'Format: {"status": "success", "summary": "...", '
    '"requirements": [{"id": "R1", "description": "...", "is_met": false}], '
    '"user_stories": [{"id": "US1", "description": "As a ... I want ... so that ...", '
    '"acceptance_criteria": ["..."], "backlog_value": 80}]}'
)


def build_graph(
    llm: Any | None = None,
    *,
    trace_context: dict[str, Any] | None = None,
    output_dir: Path | None = None,
):
    llm = llm if llm is not None else _prepare_llm(get_chat_model())
    ctx = trace_context if trace_context is not None else {"tools": [], "calls": 0}
    out_dir = output_dir or (REPO_ROOT / DEFAULT_OUTPUT_DIR)

    def read_file(state: POState) -> POState:
        ctx["tools"].append("read_repository_text_file")
        try:
            return {"file_content": read_repository_text_file(state["input_path"])}
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def process_requirements(state: POState) -> POState:
        human = HumanMessage(
            content=f"PROJECT BRIEF ({state['input_path']}):\n{state['file_content']}\n\n/no_think"
        )
        ctx["calls"] += 1
        response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), human])
        ctx["input_tokens"], ctx["output_tokens"] = usage_from_message(response)
        return {"result": _parse_result(_message_text(response)).model_dump()}

    def write_files(state: POState) -> POState:
        ctx["tools"].append("write_repository_text_file")
        result = ProductOwnerResult.model_validate(state["result"])
        stories = [s.model_dump() for s in result.user_stories]
        artefacts = {
            FileChoice.REQUIREMENTS: [r.model_dump() for r in result.requirements],
            FileChoice.USER_STORIES: stories,
            FileChoice.ACCEPTANCE_CRITERIA: {s["id"]: s["acceptance_criteria"] for s in stories},
            FileChoice.BACKLOG: sorted(
                ({"id": s["id"], "backlog_value": s["backlog_value"]} for s in stories),
                key=lambda s: s["backlog_value"],
                reverse=True,
            ),
        }
        try:
            written = [
                str(write_repository_text_file(choice, json.dumps(data, indent=2, ensure_ascii=False), out_dir))
                for choice, data in artefacts.items()
            ]
            return {"written_files": written}
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def route_after_read(state: POState) -> str:
        return END if state.get("error") else "process_requirements"

    def route_after_process(state: POState) -> str:
        return "write_files" if state["result"]["status"] == "success" else END

    builder = StateGraph(POState)
    builder.add_node("read_file", read_file)
    builder.add_node("process_requirements", process_requirements)
    builder.add_node("write_files", write_files)
    builder.add_edge(START, "read_file")
    builder.add_conditional_edges("read_file", route_after_read, ["process_requirements", END])
    builder.add_conditional_edges("process_requirements", route_after_process, ["write_files", END])
    builder.add_edge("write_files", END)
    return builder.compile()


# --------------------------------------------------------------------------- #
# Entry points
# --------------------------------------------------------------------------- #
def run_process_requirements(
    input_path: str,
    *,
    task_id: str = "PO-DEMO",
    workflow_id: str | None = None,
    llm: Any | None = None,
    trace_file: str | None = None,
    output_dir: str | Path | None = None,
) -> ProductOwnerResult:
    settings = get_settings()
    run_id = str(uuid.uuid4())
    started = time.perf_counter()
    context: dict[str, Any] = {"tools": [], "calls": 0, "input_tokens": None, "output_tokens": None}
    record: dict[str, Any] = {
        "run_id": run_id,
        "workflow_id": workflow_id or run_id,
        "task_id": task_id,
        "agent": AGENT_NAME,
        "role": ROLE,
        "provider": settings.llm_provider if llm is None else "injected",
        "model": settings.llm_model if llm is None else (
            getattr(llm, "model", None) or getattr(llm, "model_name", None) or type(llm).__name__
        ),
        "status": "error",
    }
    out_dir = Path(output_dir) if output_dir else REPO_ROOT / DEFAULT_OUTPUT_DIR / task_id
    try:
        graph = build_graph(llm, trace_context=context, output_dir=out_dir)
        state = graph.invoke({"input_path": input_path}, {"recursion_limit": 10})
        if state.get("error"):
            raise RuntimeError(state["error"])
        result = ProductOwnerResult.model_validate(state["result"])
        record["result_status"] = result.status
        record["written_files"] = state.get("written_files", [])
        record["status"] = "invalid_output" if result.status == "unparseable" else "success"
        return result
    except (Exception, KeyboardInterrupt) as exc:
        record["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "error"
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


def run_po_task(
    task: EngineeringTask,
    *,
    llm: Any | None = None,
    trace_file: str | None = None,
    output_dir: str | Path | None = None,
) -> ProductOwnerResult:
    """Shared-task-model entry point: first input file is the project brief."""
    if task.assigned_role != ROLE:
        raise ValueError(f"PO agent only accepts tasks for role {ROLE!r}")
    if not task.input_files:
        raise ValueError("PO task needs a brief in input_files")
    return run_process_requirements(
        task.input_files[0],
        task_id=task.task_id,
        workflow_id=task.workflow_id,
        llm=llm,
        trace_file=trace_file,
        output_dir=output_dir,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Repository-relative path to the project brief")
    parser.add_argument("--task-id", default="PO-DEMO")
    args = parser.parse_args()
    result = run_process_requirements(args.input, task_id=args.task_id)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
