"""Tests for the Product Owner agent (fake LLM, temp output dir)."""

from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage

from src.agents.product_owner import (
    FileChoice,
    ProductOwnerResult,
    _parse_result,
    read_repository_text_file,
    run_po_task,
    run_process_requirements,
    write_repository_text_file,
)
from src.models.task import EngineeringTask

BRIEF = "tests/briefs/work-items.md"

GOOD = {
    "status": "success",
    "summary": "Work item management",
    "requirements": [{"id": "R1", "description": "Store work items in PostgreSQL", "is_met": False}],
    "user_stories": [
        {"id": "US1", "description": "As a user I want to create work items", "acceptance_criteria": ["POST returns 201"], "backlog_value": 90},
        {"id": "US2", "description": "As a user I want to delete work items", "acceptance_criteria": ["DELETE returns 204"], "backlog_value": 40},
    ],
}


class FakeLLM:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return AIMessage(content=self.content)


def run(tmp_path, content, input_path=BRIEF):
    llm = FakeLLM(content)
    result = run_process_requirements(
        input_path, task_id="TEST-PO-1", llm=llm,
        trace_file=str(tmp_path / "t.jsonl"), output_dir=tmp_path / "out",
    )
    return result, llm


def last_trace(tmp_path) -> dict:
    return json.loads((tmp_path / "t.jsonl").read_text(encoding="utf-8").splitlines()[-1])


# Tools ---------------------------------------------------------------------
def test_read_tool_rejects_paths_outside_repo() -> None:
    with pytest.raises(ValueError, match="escapes"):
        read_repository_text_file("../../etc/passwd")


def test_write_tool_only_accepts_po_artefacts(tmp_path) -> None:
    with pytest.raises(ValueError):
        write_repository_text_file("evil.py", "x", tmp_path)  # type: ignore[arg-type]
    path = write_repository_text_file(FileChoice.BACKLOG, "[]", tmp_path)
    assert path.name == "backlog.json"


# Success ---------------------------------------------------------------------
def test_success_returns_structured_result_and_writes_files(tmp_path) -> None:
    result, llm = run(tmp_path, json.dumps(GOOD))

    assert isinstance(result, ProductOwnerResult)
    assert result.status == "success"
    assert result.user_stories[0].acceptance_criteria[0].description == "POST returns 201"
    assert llm.calls == 1
    out = tmp_path / "out"
    assert {p.name for p in out.iterdir()} == {f.value for f in FileChoice}
    backlog = json.loads((out / "backlog.json").read_text())
    assert [b["id"] for b in backlog] == ["US1", "US2"]  # sorted by value


def test_tolerates_think_block_and_missing_optional_fields() -> None:
    text = '<think>{maybe}</think>{"status": "success", "summary": "s", ' \
           '"requirements": [{"id": "R1", "description": "d"}], ' \
           '"user_stories": [{"id": "US1", "description": "d", "backlog_value": 7.6}]}'
    result = _parse_result(text)
    assert result.status == "success"
    assert result.requirements[0].is_met is False
    assert result.user_stories[0].backlog_value == 8


# Failure cases -----------------------------------------------------------------
def test_unparseable_output_writes_nothing(tmp_path) -> None:
    result, _ = run(tmp_path, "Sorry, here are some ideas ...")

    assert result.status == "unparseable"
    assert not (tmp_path / "out").exists()
    assert last_trace(tmp_path)["status"] == "invalid_output"


def test_needs_clarification_writes_nothing(tmp_path) -> None:
    result, _ = run(tmp_path, json.dumps({"status": "needs_clarification", "summary": "Not a brief"}))
    assert result.status == "needs_clarification"
    assert not (tmp_path / "out").exists()


def test_missing_brief_raises_without_llm_call(tmp_path) -> None:
    llm = FakeLLM(json.dumps(GOOD))
    with pytest.raises(RuntimeError, match="not found"):
        run_process_requirements("docs/does-not-exist.md", llm=llm,
                                 trace_file=str(tmp_path / "t.jsonl"), output_dir=tmp_path / "out")
    assert llm.calls == 0
    assert last_trace(tmp_path)["status"] == "error"


# Trace + shared task model -------------------------------------------------------
def test_trace_has_required_fields(tmp_path) -> None:
    run(tmp_path, json.dumps(GOOD))
    trace = last_trace(tmp_path)
    for field in ("run_id", "workflow_id", "task_id", "agent", "role", "model", "status", "tools", "calls", "duration_seconds"):
        assert field in trace
    assert trace["role"] == "product_owner_requirements"
    assert trace["tools"] == ["read_repository_text_file", "write_repository_text_file"]


def test_po_accepts_engineering_task(tmp_path) -> None:
    task = EngineeringTask(task_id="TASK-PO", task_type="requirements", description="Derive stories",
                           assigned_role="product_owner_requirements", input_files=[BRIEF], workflow_id="WF-PO")
    result = run_po_task(task, llm=FakeLLM(json.dumps(GOOD)), trace_file=str(tmp_path / "t.jsonl"),
                         output_dir=tmp_path / "out")
    assert result.status == "success"
    assert last_trace(tmp_path)["workflow_id"] == "WF-PO"


def test_po_rejects_task_for_other_role(tmp_path) -> None:
    task = EngineeringTask(task_id="T", task_type="x", description="d", assigned_role="qa_test_engineer", input_files=[BRIEF])
    with pytest.raises(ValueError, match="product_owner_requirements"):
        run_po_task(task, llm=FakeLLM("{}"))
