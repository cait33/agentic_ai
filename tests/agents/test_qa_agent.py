"""Tests for the QA agent (src/agents/qa_agent.py). Owner: Fatih.

The LLM is always faked. The pytest tool is faked in most tests; two tests run
the real tool against a tiny throw-away test suite in tmp_path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from src.models.task import EngineeringTask
from src.agents.qa_agent import (
    PytestRun,
    QAReport,
    build_qa_graph,
    parse_pytest_output,
    run_pytest,
    run_qa_agent,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
class FakeLLM:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return AIMessage(content=self.content)


GOOD_ASSESSMENT = json.dumps(
    {
        "summary": "The health endpoint returns the wrong status.",
        "findings": [
            {"severity": "high", "test": "tests/test_api.py::test_health", "description": "Expected 200, got 500."}
        ],
    }
)


def make_task(**overrides) -> EngineeringTask:
    data = {
        "task_id": "TEST-QA-001",
        "task_type": "qa_review",
        "description": "Check the API tests.",
        "assigned_role": "qa_test_engineer",
        "input_files": ["tests/starter"],
    }
    data.update(overrides)
    return EngineeringTask(**data)


def green_runner(paths):
    return PytestRun(exit_code=0, passed=5, skipped=1)


def red_runner(paths):
    return PytestRun(
        exit_code=1,
        passed=3,
        failed=1,
        failed_tests=["tests/test_api.py::test_health"],
        output_tail="FAILED tests/test_api.py::test_health - assert 500 == 200",
    )


def timeout_runner(paths):
    return PytestRun(exit_code=-1, timed_out=True)


def last_trace(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8").splitlines()[-1])


# --------------------------------------------------------------------------- #
# Input validation
# --------------------------------------------------------------------------- #
def test_task_without_test_paths_is_rejected(tmp_path) -> None:
    with pytest.raises(ValueError, match="at least one test path"):
        run_qa_agent(
            make_task(input_files=[]),
            llm=FakeLLM(GOOD_ASSESSMENT),
            pytest_runner=green_runner,
            trace_file=str(tmp_path / "t.jsonl"),
        )


def test_agent_rejects_task_for_other_role(tmp_path) -> None:
    with pytest.raises(ValueError, match="qa_test_engineer"):
        run_qa_agent(
            make_task(assigned_role="software_architect"),
            llm=FakeLLM(GOOD_ASSESSMENT),
            pytest_runner=green_runner,
            trace_file=str(tmp_path / "t.jsonl"),
        )


# --------------------------------------------------------------------------- #
# Tool: real pytest run + path restriction
# --------------------------------------------------------------------------- #
def _write_suite(root: Path) -> None:
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        "def test_ok():\n    assert 1 + 1 == 2\n\n"
        "def test_broken():\n    assert 1 + 1 == 3\n",
        encoding="utf-8",
    )


def test_real_tool_counts_passed_and_failed(tmp_path) -> None:
    _write_suite(tmp_path)
    run = run_pytest(["tests/test_sample.py"], repo_root=tmp_path, timeout_seconds=60)

    assert run.passed == 1
    assert run.failed == 1
    assert run.exit_code == 1
    assert not run.green
    assert any("test_broken" in t for t in run.failed_tests)


@pytest.mark.parametrize("path", ["../outside", "src/app/main.py", "/etc"])
def test_tool_only_allows_paths_below_tests(path, tmp_path) -> None:
    _write_suite(tmp_path)
    with pytest.raises(ValueError, match="inside tests/"):
        run_pytest([path], repo_root=tmp_path)


def test_parse_pytest_summary_line() -> None:
    out = "FAILED tests/a.py::test_x - boom\n2 failed, 7 passed, 1 skipped, 1 error in 0.42s\n"
    run = parse_pytest_output(out, exit_code=1)
    assert (run.passed, run.failed, run.skipped, run.errors) == (7, 2, 1, 1)
    assert run.failed_tests == ["tests/a.py::test_x"]


# --------------------------------------------------------------------------- #
# Success case: green tests -> approved, no LLM call (cost saving)
# --------------------------------------------------------------------------- #
def test_green_tests_are_approved_without_llm_call(tmp_path) -> None:
    llm = FakeLLM(GOOD_ASSESSMENT)
    report = run_qa_agent(make_task(), llm=llm, pytest_runner=green_runner, trace_file=str(tmp_path / "t.jsonl"))

    assert isinstance(report, QAReport)
    assert report.verdict == "approved"
    assert report.test_run.passed == 5
    assert report.requires_human_approval is True
    assert llm.calls == 0


# --------------------------------------------------------------------------- #
# Failing tests -> changes_requested with LLM findings
# --------------------------------------------------------------------------- #
def test_red_tests_request_changes_with_findings(tmp_path) -> None:
    llm = FakeLLM(GOOD_ASSESSMENT)
    report = run_qa_agent(make_task(), llm=llm, pytest_runner=red_runner, trace_file=str(tmp_path / "t.jsonl"))

    assert report.verdict == "changes_requested"
    assert report.findings[0].severity == "high"
    assert llm.calls == 1


def test_llm_cannot_approve_failing_tests(tmp_path) -> None:
    sneaky = FakeLLM(json.dumps({"summary": "Looks fine, approve it!", "findings": [], "verdict": "approved"}))
    report = run_qa_agent(make_task(), llm=sneaky, pytest_runner=red_runner, trace_file=str(tmp_path / "t.jsonl"))

    assert report.verdict == "changes_requested"


# --------------------------------------------------------------------------- #
# Error / escalation cases
# --------------------------------------------------------------------------- #
def test_unparseable_llm_output_escalates_to_human(tmp_path) -> None:
    report = run_qa_agent(
        make_task(), llm=FakeLLM("no json here"), pytest_runner=red_runner, trace_file=str(tmp_path / "t.jsonl")
    )
    assert report.verdict == "escalate_to_human"


def test_timeout_escalates_without_llm_call(tmp_path) -> None:
    llm = FakeLLM(GOOD_ASSESSMENT)
    trace = tmp_path / "t.jsonl"
    report = run_qa_agent(make_task(), llm=llm, pytest_runner=timeout_runner, trace_file=str(trace))

    assert report.verdict == "escalate_to_human"
    assert llm.calls == 0
    assert last_trace(trace)["status"] == "escalated"


def test_missing_test_path_raises_and_traces_error(tmp_path) -> None:
    llm = FakeLLM(GOOD_ASSESSMENT)
    trace = tmp_path / "t.jsonl"
    with pytest.raises(RuntimeError, match="not found"):
        run_qa_agent(make_task(input_files=["tests/does_not_exist.py"]), llm=llm, trace_file=str(trace))

    record = last_trace(trace)
    assert record["status"] == "error"
    assert record["calls"] == 0
    assert llm.calls == 0


# --------------------------------------------------------------------------- #
# Trace evidence
# --------------------------------------------------------------------------- #
def test_trace_contains_required_fields(tmp_path) -> None:
    trace = tmp_path / "t.jsonl"
    run_qa_agent(
        make_task(workflow_id="WF-42"),
        llm=FakeLLM(GOOD_ASSESSMENT),
        pytest_runner=red_runner,
        trace_file=str(trace),
    )
    record = last_trace(trace)

    for field in ("run_id", "workflow_id", "task_id", "agent", "role", "model",
                  "duration_seconds", "status", "tools", "calls", "estimated_cost_credits"):
        assert field in record, f"missing trace field: {field}"
    assert record["workflow_id"] == "WF-42"
    assert record["agent"] == "qa-agent"
    assert record["role"] == "qa_test_engineer"
    assert record["tools"] == ["run_pytest"]
    assert record["calls"] == 1
    assert record["result_status"] == "changes_requested"


# --------------------------------------------------------------------------- #
# Termination
# --------------------------------------------------------------------------- #
def test_graph_terminates_with_report() -> None:
    graph = build_qa_graph(FakeLLM(GOOD_ASSESSMENT), pytest_runner=red_runner)
    state = graph.invoke({"task": make_task().model_dump()}, {"recursion_limit": 10})

    assert "report" in state
    assert "error" not in state
