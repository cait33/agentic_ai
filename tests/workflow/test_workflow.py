"""Workflow tests (Session 2, task 6): success, failure, structure, termination.

All agents are replaced by fakes, so no LLM or real pytest run is needed.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from src.agents.workflow import HumanDecision, WorkflowInput, _make_decision, run_workflow


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
def make_input(**overrides) -> WorkflowInput:
    data = {
        "task_id": "WF-TEST-001",
        "description": "Review main.py and run the agent tests.",
        "source_file": "src/app/main.py",
        "test_paths": ["tests/agents"],
        "reviewer": "Fatih",
        "workflow_id": "WF-1",
    }
    data.update(overrides)
    return WorkflowInput(**data)


def arch_ok(wf, state):
    return {"status": "approved", "architectural_summary": "Fine.", "violations": []}


def arch_changes(wf, state):
    return {"status": "changes_requested", "architectural_summary": "Coupling.", "violations": []}


def arch_crash(wf, state):
    raise RuntimeError("model unavailable")


class QASpy:
    """QA fake that records what it received from the previous agent."""

    def __init__(self, verdict="approved"):
        self.verdict = verdict
        self.calls = 0
        self.seen_architecture = None

    def __call__(self, wf, state):
        self.calls += 1
        self.seen_architecture = state.get("architecture")
        return {"task_id": wf.task_id, "verdict": self.verdict, "summary": "QA done."}


def human(decision="approved", reviewer="Fatih"):
    def decide(state):
        return _make_decision(state, reviewer, decision, "checked in review")
    return decide


def run(tmp_path, **kwargs):
    defaults = dict(
        architect=arch_ok,
        qa=QASpy(),
        decide=human(),
        trace_file=str(tmp_path / "wf.jsonl"),
        decisions_dir=str(tmp_path / "decisions"),
    )
    defaults.update(kwargs)
    return run_workflow(make_input(), **defaults)


# --------------------------------------------------------------------------- #
# Success
# --------------------------------------------------------------------------- #
def test_success_runs_all_agents_and_reaches_human_gate(tmp_path) -> None:
    state = run(tmp_path)

    assert state["steps"] == ["architecture", "qa", "human_gate"]
    assert state["errors"] == []
    assert state["recommendation"] == "approved"
    assert state["human_decision"]["decision"] == "approved"


def test_handover_happens_through_state(tmp_path) -> None:
    qa = QASpy()
    run(tmp_path, qa=qa)

    assert qa.seen_architecture == arch_ok(None, None)


def test_optional_requirements_step_runs_first(tmp_path) -> None:
    def po(wf, state):
        return {"user_story": "As a user I want ...", "acceptance_criteria": ["works"]}

    qa = QASpy()
    state = run(tmp_path, requirements=po, qa=qa)

    assert state["steps"] == ["requirements", "architecture", "qa", "human_gate"]
    assert state["requirements"]["user_story"].startswith("As a user")


# --------------------------------------------------------------------------- #
# Failure / escalation
# --------------------------------------------------------------------------- #
def test_agent_failure_skips_rest_and_escalates(tmp_path) -> None:
    qa = QASpy()
    state = run(tmp_path, architect=arch_crash, qa=qa, decide=human("escalate_to_human"))

    assert qa.calls == 0, "QA must not run after the architect failed"
    assert state["steps"] == ["architecture", "human_gate"]
    assert state["errors"] == ["architecture: RuntimeError"]
    assert state["recommendation"] == "escalate_to_human"


def test_changes_requested_by_an_agent_is_recommended(tmp_path) -> None:
    state = run(tmp_path, architect=arch_changes, decide=human("changes_requested"))
    assert state["recommendation"] == "changes_requested"


def test_human_can_overrule_agent_recommendation(tmp_path) -> None:
    state = run(tmp_path, architect=arch_changes, decide=human("approved"))

    assert state["recommendation"] == "changes_requested"
    assert state["human_decision"]["decision"] == "approved"
    assert state["human_decision"]["agent_recommendation"] == "changes_requested"


def test_invalid_human_decision_is_rejected(tmp_path) -> None:
    with pytest.raises(ValidationError):
        run(tmp_path, decide=human("looks_good"))


def test_input_without_reviewer_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_input(reviewer="")


# --------------------------------------------------------------------------- #
# Structure: decision artifact + workflow trace
# --------------------------------------------------------------------------- #
def test_human_decision_is_persisted_with_who_what_when(tmp_path) -> None:
    run(tmp_path)
    saved = json.loads((tmp_path / "decisions" / "WF-1.json").read_text(encoding="utf-8"))

    decision = HumanDecision.model_validate(saved)
    assert decision.reviewer == "Fatih"
    assert decision.task_id == "WF-TEST-001"
    assert decision.decision == "approved"
    assert decision.decided_at
    assert "src/app/main.py" in decision.reviewed_artifacts


def test_workflow_trace_links_task_and_decision(tmp_path) -> None:
    run(tmp_path)
    trace = json.loads((tmp_path / "wf.jsonl").read_text(encoding="utf-8").splitlines()[-1])

    assert trace["workflow_id"] == "WF-1"
    assert trace["task_id"] == "WF-TEST-001"
    assert trace["steps"] == ["architecture", "qa", "human_gate"]
    assert trace["human_decision"] == "approved"
    assert trace["reviewer"] == "Fatih"


# --------------------------------------------------------------------------- #
# Termination
# --------------------------------------------------------------------------- #
def test_each_agent_runs_exactly_once(tmp_path) -> None:
    qa = QASpy(verdict="changes_requested")
    state = run(tmp_path, qa=qa, decide=human("changes_requested"))

    assert qa.calls == 1
    assert state["steps"].count("human_gate") == 1
