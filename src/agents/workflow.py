"""EventAI agent-to-agent workflow with human gate (Session 2, tasks 4 + 5).

    [PO agent, if a brief is given] -> Architect agent -> QA agent -> Human gate

* Hand-over happens only through the LangGraph state (no copy & paste).
* All agents receive the shared EngineeringTask (src/models/task.py) with one
  task_id and one workflow_id.
* If any agent fails, the workflow skips the remaining agents and goes straight
  to the human gate with recommendation "escalate_to_human".
* The human gate records WHO decided WHAT for WHICH task/artifact and WHEN.
  An LLM "approved" is only a recommendation, never the human decision.
* No loops: every node runs at most once, recursion_limit=20.

The requirements (product owner) step is optional and injectable, so the
workflow runs with the two existing agents today and the PO agent can be
plugged in with one argument later.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from src.models.task import EngineeringTask
from src.observability.tracing import append_trace

Decision = Literal["approved", "changes_requested", "escalate_to_human"]
StepFn = Callable[["WorkflowInput", dict[str, Any]], dict[str, Any]]
DecisionFn = Callable[[dict[str, Any]], "HumanDecision"]

DEFAULT_DECISIONS_DIR = "evidence/session-02/decisions"


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class WorkflowInput(BaseModel):
    task_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    source_file: str = Field(min_length=1, description="File the architect reviews")
    test_paths: list[str] = Field(min_length=1, description="Paths below tests/ for the QA agent")
    reviewer: str = Field(min_length=1, description="Accountable human for the gate")
    brief_file: str | None = Field(default=None, description="Project brief for the PO agent (optional)")
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class HumanDecision(BaseModel):
    task_id: str
    workflow_id: str
    reviewer: str = Field(min_length=1)
    decision: Decision
    comment: str = ""
    reviewed_artifacts: list[str]
    agent_recommendation: Decision
    decided_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WorkflowState(TypedDict, total=False):
    input: dict[str, Any]
    requirements: dict[str, Any]
    architecture: dict[str, Any]
    qa: dict[str, Any]
    errors: list[str]
    steps: list[str]
    recommendation: str
    human_decision: dict[str, Any]


# --------------------------------------------------------------------------- #
# Default agent adapters (real agents)
# --------------------------------------------------------------------------- #
def architect_step(wf: WorkflowInput, state: dict[str, Any], *, llm: Any = None, trace_file: str | None = None) -> dict[str, Any]:
    from src.agents.software_architect import run_architect_task

    task = EngineeringTask(
        task_id=wf.task_id,
        workflow_id=wf.workflow_id,
        task_type="architecture_review",
        description=wf.description,
        assigned_role="software_architect",
        input_files=[wf.source_file],
    )
    return run_architect_task(task, llm=llm, trace_file=trace_file).model_dump()


def qa_step(wf: WorkflowInput, state: dict[str, Any], *, llm: Any = None, trace_file: str | None = None,
            pytest_runner: Any = None) -> dict[str, Any]:
    from src.agents.qa_agent import run_qa_agent

    task = EngineeringTask(
        task_id=wf.task_id,
        workflow_id=wf.workflow_id,
        task_type="qa_review",
        description=wf.description,
        assigned_role="qa_test_engineer",
        input_files=wf.test_paths,
    )
    report = run_qa_agent(task, llm=llm, pytest_runner=pytest_runner, trace_file=trace_file)
    return report.model_dump()


def po_step(wf: WorkflowInput, state: dict[str, Any], *, llm: Any = None, trace_file: str | None = None) -> dict[str, Any]:
    """Product owner agent: turns the project brief into requirements and user stories."""
    from src.agents.product_owner import run_po_task

    if not wf.brief_file:
        raise ValueError("PO step needs brief_file")
    task = EngineeringTask(
        task_id=wf.task_id,
        workflow_id=wf.workflow_id,
        task_type="requirements",
        description=wf.description,
        assigned_role="product_owner_requirements",
        input_files=[wf.brief_file],
    )
    return run_po_task(task, llm=llm, trace_file=trace_file).model_dump()


def cli_decision(state: dict[str, Any]) -> HumanDecision:
    """Ask the reviewer in the terminal."""
    wf = WorkflowInput.model_validate(state["input"])
    print("\n=== HUMAN GATE ===")
    print(f"Task: {wf.task_id} - {wf.description}")
    print(f"Agent recommendation: {state['recommendation']}")
    if state.get("errors"):
        print(f"Errors: {state['errors']}")
    if state.get("architecture"):
        print(f"Architecture: {state['architecture'].get('status')} - {state['architecture'].get('architectural_summary')}")
    if state.get("qa"):
        print(f"QA: {state['qa'].get('verdict')} - {state['qa'].get('summary')}")
    choice = ""
    while choice not in {"approved", "changes_requested", "escalate_to_human"}:
        choice = input("Decision [approved / changes_requested / escalate_to_human]: ").strip()
    comment = input("Comment (optional): ").strip()
    return _make_decision(state, wf.reviewer, choice, comment)


def _make_decision(state: dict[str, Any], reviewer: str, decision: str, comment: str = "") -> HumanDecision:
    wf = WorkflowInput.model_validate(state["input"])
    return HumanDecision(
        task_id=wf.task_id,
        workflow_id=wf.workflow_id,
        reviewer=reviewer,
        decision=decision,
        comment=comment,
        reviewed_artifacts=[wf.source_file, *wf.test_paths],
        agent_recommendation=state["recommendation"],
    )


# --------------------------------------------------------------------------- #
# Graph
# --------------------------------------------------------------------------- #
def _recommend(state: WorkflowState) -> Decision:
    if state.get("errors"):
        return "escalate_to_human"
    arch = state.get("architecture", {}).get("status")
    qa = state.get("qa", {}).get("verdict")
    if qa == "escalate_to_human" or arch == "unparseable":
        return "escalate_to_human"
    if arch == "approved" and qa == "approved":
        return "approved"
    return "changes_requested"


def build_workflow(
    *,
    architect: StepFn,
    qa: StepFn,
    decide: DecisionFn,
    requirements: StepFn | None = None,
):
    def make_node(name: str, fn: StepFn):
        def node(state: WorkflowState) -> WorkflowState:
            wf = WorkflowInput.model_validate(state["input"])
            steps = [*state.get("steps", []), name]
            try:
                return {name: fn(wf, dict(state)), "steps": steps}
            except Exception as exc:  # any agent failure -> escalate, never crash the workflow
                return {"errors": [*state.get("errors", []), f"{name}: {type(exc).__name__}"], "steps": steps}
        return node

    def route(next_node: str):
        def _route(state: WorkflowState) -> str:
            return "human_gate" if state.get("errors") else next_node
        return _route

    def human_gate(state: WorkflowState) -> WorkflowState:
        state = {**state, "recommendation": _recommend(state)}
        decision = decide(dict(state))
        return {
            "recommendation": state["recommendation"],
            "human_decision": decision.model_dump(),
            "steps": [*state.get("steps", []), "human_gate"],
        }

    g = StateGraph(WorkflowState)
    g.add_node("architecture", make_node("architecture", architect))
    g.add_node("qa", make_node("qa", qa))
    g.add_node("human_gate", human_gate)

    if requirements is not None:
        g.add_node("requirements", make_node("requirements", requirements))
        g.add_edge(START, "requirements")
        g.add_conditional_edges("requirements", route("architecture"), ["architecture", "human_gate"])
    else:
        g.add_edge(START, "architecture")
    g.add_conditional_edges("architecture", route("qa"), ["qa", "human_gate"])
    g.add_edge("qa", "human_gate")
    g.add_edge("human_gate", END)
    return g.compile()


def run_workflow(
    wf: WorkflowInput,
    *,
    architect: StepFn = architect_step,
    qa: StepFn = qa_step,
    decide: DecisionFn = cli_decision,
    requirements: StepFn | None = None,
    trace_file: str | None = None,
    decisions_dir: str = DEFAULT_DECISIONS_DIR,
) -> WorkflowState:
    started = time.perf_counter()
    if requirements is None and wf.brief_file:
        requirements = po_step  # PO agent runs first whenever a brief is given
    graph = build_workflow(architect=architect, qa=qa, decide=decide, requirements=requirements)
    state: WorkflowState = graph.invoke({"input": wf.model_dump(), "errors": [], "steps": []}, {"recursion_limit": 20})

    # Persist the human decision as a reviewable artifact.
    out = Path(decisions_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{wf.workflow_id}.json").write_text(json.dumps(state["human_decision"], indent=2), encoding="utf-8")

    append_trace(
        {
            "run_id": wf.workflow_id,
            "workflow_id": wf.workflow_id,
            "task_id": wf.task_id,
            "agent": "eventai-workflow",
            "role": "agent_engineer",
            "status": "error" if state.get("errors") else "success",
            "steps": state.get("steps", []),
            "errors": state.get("errors", []),
            "recommendation": state.get("recommendation"),
            "human_decision": state["human_decision"]["decision"],
            "reviewer": state["human_decision"]["reviewer"],
            "duration_seconds": round(time.perf_counter() - started, 4),
        },
        trace_file,
    )
    return state


def main() -> None:
    p = argparse.ArgumentParser(description="EventAI workflow: architect -> QA -> human gate")
    p.add_argument("--task-id", default="WF-TASK-01")
    p.add_argument("--description", default="Review the API entry point and run the agent tests.")
    p.add_argument("--source", default="src/app/main.py")
    p.add_argument("--tests", nargs="+", default=["tests/agents"])
    p.add_argument("--reviewer", required=True)
    p.add_argument("--brief", default=None, help="Project brief for the PO agent (optional)")
    a = p.parse_args()
    wf = WorkflowInput(task_id=a.task_id, description=a.description, source_file=a.source,
                       test_paths=a.tests, reviewer=a.reviewer, brief_file=a.brief)
    state = run_workflow(wf)
    print(json.dumps({k: state.get(k) for k in ("steps", "errors", "recommendation", "human_decision")}, indent=2))


if __name__ == "__main__":
    main()
