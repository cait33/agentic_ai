"""QA & Test Engineer agent for EventAI.

Role: qa_test_engineer (accountable human: Fatih)

Input:   EngineeringTask (src/models/task.py, assigned_role="qa_test_engineer", input_files = test paths)
Tool:    run_pytest  - runs pytest in a subprocess, only on paths below tests/
LLM:     only called when tests fail, to explain the failures (saves calls/cost)
Output:  QAReport    - verdict, summary, findings, raw test numbers
Guards:  - the LLM can never turn failing tests into "approved"
         - pytest timeout / unparseable LLM output -> escalate_to_human
         - at most one LLM call per run, LangGraph recursion_limit=10
Trace:   one JSONL record per run (run_id, workflow_id, task_id, agent, role,
         model, provider, tools, calls, tokens, duration, status, credits)

The verdict is a recommendation. Merging still requires a human decision
(see organization/company.md).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError

from src.app.settings import get_settings
from src.models.task import EngineeringTask
from src.llm.factory import get_chat_model
from src.observability.tracing import (
    append_trace,
    estimate_cost_credits,
    usage_from_message,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_NAME = "qa-agent"
ROLE = "qa_test_engineer"
TOOL_NAME = "run_pytest"
DEFAULT_TIMEOUT_SECONDS = 120
MAX_OUTPUT_CHARS_FOR_LLM = 4000


# --------------------------------------------------------------------------- #
# Result models
# --------------------------------------------------------------------------- #
class PytestRun(BaseModel):
    exit_code: int
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    failed_tests: list[str] = Field(default_factory=list)
    timed_out: bool = False
    output_tail: str = ""

    @property
    def green(self) -> bool:
        return (
            not self.timed_out
            and self.exit_code == 0
            and self.failed == 0
            and self.errors == 0
        )


class QAFinding(BaseModel):
    severity: Literal["low", "medium", "high"]
    test: str
    description: str


class QAReport(BaseModel):
    task_id: str
    verdict: Literal["approved", "changes_requested", "escalate_to_human"]
    summary: str
    findings: list[QAFinding] = Field(default_factory=list)
    test_run: PytestRun
    requires_human_approval: bool = True


class _LLMAssessment(BaseModel):
    summary: str
    findings: list[QAFinding] = Field(default_factory=list)


class QAState(TypedDict, total=False):
    task: dict[str, Any]
    test_run: dict[str, Any]
    report: dict[str, Any]
    error: str


# --------------------------------------------------------------------------- #
# Tool
# --------------------------------------------------------------------------- #
_COUNT_RE = re.compile(r"(\d+) (passed|failed|errors?|skipped)")


def _resolve_test_path(path: str, repo_root: Path) -> Path:
    tests_root = (repo_root / "tests").resolve()
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(tests_root)
    except ValueError as exc:
        raise ValueError(f"Test path must be inside tests/: {path}") from exc
    if not resolved.exists():
        raise FileNotFoundError(f"Test path not found: {path}")
    return resolved


def parse_pytest_output(output: str, exit_code: int) -> PytestRun:
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    summary_lines = [l for l in output.splitlines() if " in " in l and _COUNT_RE.search(l)]
    if summary_lines:
        for number, kind in _COUNT_RE.findall(summary_lines[-1]):
            key = "errors" if kind.startswith("error") else kind
            counts[key] = int(number)
    failed_tests = [
        line.split(" ", 1)[1].split(" - ", 1)[0].strip()
        for line in output.splitlines()
        if line.startswith(("FAILED ", "ERROR "))
    ]
    return PytestRun(
        exit_code=exit_code,
        failed_tests=failed_tests,
        output_tail=output[-MAX_OUTPUT_CHARS_FOR_LLM:],
        **counts,
    )


def run_pytest(
    test_paths: list[str],
    *,
    repo_root: Path = REPO_ROOT,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> PytestRun:
    """TOOL: run pytest on paths below tests/ and return structured numbers."""
    if not test_paths:
        raise ValueError("No test paths given")
    resolved = [str(_resolve_test_path(p, repo_root)) for p in test_paths]

    cmd = [sys.executable, "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider", *resolved]
    try:
        proc = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout if isinstance(exc.stdout, str) else ""
        return PytestRun(exit_code=-1, timed_out=True, output_tail=partial[-MAX_OUTPUT_CHARS_FOR_LLM:])

    return parse_pytest_output(proc.stdout + proc.stderr, proc.returncode)


# --------------------------------------------------------------------------- #
# LLM helpers
# --------------------------------------------------------------------------- #
def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(i if isinstance(i, str) else i.get("text", "") for i in content)
    return str(content)


def _parse_assessment(text: str) -> _LLMAssessment | None:
    cleaned = text.strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return _LLMAssessment.model_validate(json.loads(cleaned[start : end + 1]))
    except (json.JSONDecodeError, ValidationError):
        return None


# --------------------------------------------------------------------------- #
# Graph
# --------------------------------------------------------------------------- #
PytestRunner = Callable[[list[str]], PytestRun]


def build_qa_graph(
    llm: Any | None = None,
    *,
    pytest_runner: PytestRunner | None = None,
    trace_context: dict[str, Any] | None = None,
):
    runner = pytest_runner or run_pytest
    ctx = trace_context if trace_context is not None else {}
    ctx.setdefault("tools", [])
    ctx.setdefault("calls", 0)
    ctx.setdefault("input_tokens", None)
    ctx.setdefault("output_tokens", None)

    def run_tests(state: QAState) -> QAState:
        task = EngineeringTask.model_validate(state["task"])
        ctx["tools"].append(TOOL_NAME)
        try:
            return {"test_run": runner(task.input_files).model_dump()}
        except (ValueError, FileNotFoundError) as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def route_after_tests(state: QAState) -> str:
        if state.get("error"):
            return END
        run = PytestRun.model_validate(state["test_run"])
        if run.timed_out:
            return "escalate"
        return "approve" if run.green else "assess_failures"

    def approve(state: QAState) -> QAState:
        run = PytestRun.model_validate(state["test_run"])
        report = QAReport(
            task_id=state["task"]["task_id"],
            verdict="approved",
            summary=f"All tests passed ({run.passed} passed, {run.skipped} skipped).",
            test_run=run,
        )
        return {"report": report.model_dump()}

    def escalate(state: QAState) -> QAState:
        run = PytestRun.model_validate(state["test_run"])
        report = QAReport(
            task_id=state["task"]["task_id"],
            verdict="escalate_to_human",
            summary=state.get("report", {}).get("summary")
            or "Test run timed out; a human has to check the test suite.",
            test_run=run,
        )
        return {"report": report.model_dump()}

    def assess_failures(state: QAState) -> QAState:
        run = PytestRun.model_validate(state["test_run"])
        model = llm or get_chat_model()
        system = SystemMessage(
            content=(
                "You are the QA engineer of EventAI. Explain failing pytest results. "
                "Return ONLY valid JSON with keys 'summary' (string) and 'findings' "
                "(list of objects with 'severity' (low|medium|high), 'test', 'description')."
            )
        )
        human = HumanMessage(
            content=(
                f"Task: {state['task']['description']}\n"
                f"Failed tests: {', '.join(run.failed_tests) or 'unknown'}\n\n"
                f"PYTEST OUTPUT (tail):\n{run.output_tail}"
            )
        )
        ctx["calls"] += 1
        response = model.invoke([system, human])
        in_tok, out_tok = usage_from_message(response)
        ctx["input_tokens"], ctx["output_tokens"] = in_tok, out_tok

        assessment = _parse_assessment(_message_text(response))
        if assessment is None:
            report = QAReport(
                task_id=state["task"]["task_id"],
                verdict="escalate_to_human",
                summary="Tests failed and the LLM assessment was unparseable.",
                test_run=run,
            )
        else:
            # Guardrail: failing tests are always changes_requested, whatever the LLM says.
            report = QAReport(
                task_id=state["task"]["task_id"],
                verdict="changes_requested",
                summary=assessment.summary,
                findings=assessment.findings,
                test_run=run,
            )
        return {"report": report.model_dump()}

    builder = StateGraph(QAState)
    builder.add_node("run_tests", run_tests)
    builder.add_node("approve", approve)
    builder.add_node("escalate", escalate)
    builder.add_node("assess_failures", assess_failures)
    builder.add_edge(START, "run_tests")
    builder.add_conditional_edges(
        "run_tests", route_after_tests, ["approve", "escalate", "assess_failures", END]
    )
    builder.add_edge("approve", END)
    builder.add_edge("escalate", END)
    builder.add_edge("assess_failures", END)
    return builder.compile()


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def run_qa_agent(
    task: EngineeringTask,
    *,
    llm: Any | None = None,
    pytest_runner: PytestRunner | None = None,
    trace_file: str | None = None,
) -> QAReport:
    if task.assigned_role != ROLE:
        raise ValueError(f"QA agent only accepts tasks for role {ROLE!r}")
    if not task.input_files:
        raise ValueError("QA task needs at least one test path in input_files")

    settings = get_settings()
    run_id = str(uuid.uuid4())
    started = time.perf_counter()
    context: dict[str, Any] = {"tools": [], "calls": 0, "input_tokens": None, "output_tokens": None}
    record: dict[str, Any] = {
        "run_id": run_id,
        "workflow_id": task.workflow_id,
        "task_id": task.task_id,
        "agent": AGENT_NAME,
        "role": ROLE,
        "provider": settings.llm_provider if llm is None else "injected",
        "model": settings.llm_model if llm is None else (
            getattr(llm, "model", None) or getattr(llm, "model_name", None) or type(llm).__name__
        ),
        "status": "error",
    }
    try:
        graph = build_qa_graph(llm, pytest_runner=pytest_runner, trace_context=context)
        state = graph.invoke({"task": task.model_dump()}, {"recursion_limit": 10})
        if state.get("error"):
            raise RuntimeError(state["error"])
        report = QAReport.model_validate(state["report"])
        record["result_status"] = report.verdict
        record["tests_passed"] = report.test_run.passed
        record["tests_failed"] = report.test_run.failed + report.test_run.errors
        record["status"] = "escalated" if report.verdict == "escalate_to_human" else "success"
        return report
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


def main() -> None:
    parser = argparse.ArgumentParser(description="EventAI QA agent")
    parser.add_argument("--tests", nargs="+", default=["tests/agents"], help="Test paths below tests/")
    parser.add_argument("--task-id", default="QA-RUN-01")
    parser.add_argument("--description", default="Run the agent test suite and report the result.")
    args = parser.parse_args()

    task = EngineeringTask(
        task_id=args.task_id,
        task_type="qa_review",
        description=args.description,
        assigned_role=ROLE,
        input_files=args.tests,
    )
    print(run_qa_agent(task).model_dump_json(indent=2))


if __name__ == "__main__":
    main()
