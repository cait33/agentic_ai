"""Both agents accept the same EngineeringTask (Session 2, task 3)."""

import json

import pytest
from langchain_core.messages import AIMessage

from src.agents.qa_agent import PytestRun, run_qa_agent
from src.agents.software_architect import ArchitectureReviewResult, run_architect_task
from src.models.task import EngineeringTask


class ArchitectFakeLLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {"status": "approved", "architectural_summary": "Clean structure.", "violations": []}
            )
        )


def green_runner(paths):
    return PytestRun(exit_code=0, passed=3)


def test_both_agents_accept_engineering_task(tmp_path) -> None:
    arch_task = EngineeringTask(
        task_id="TASK-42",
        task_type="architecture_review",
        description="Review the FastAPI entry point.",
        assigned_role="software_architect",
        input_files=["src/app/main.py"],
        workflow_id="WF-42",
    )
    qa_task = arch_task.model_copy(
        update={
            "task_type": "qa_review",
            "assigned_role": "qa_test_engineer",
            "input_files": ["tests/starter"],
        }
    )

    arch_result = run_architect_task(arch_task, llm=ArchitectFakeLLM(), trace_file=str(tmp_path / "a.jsonl"))
    qa_report = run_qa_agent(qa_task, llm=ArchitectFakeLLM(), pytest_runner=green_runner,
                             trace_file=str(tmp_path / "q.jsonl"))

    assert isinstance(arch_result, ArchitectureReviewResult)
    assert arch_result.status == "approved"
    assert qa_report.verdict == "approved"
    # Same task_id links both agents' work and traces.
    assert qa_report.task_id == arch_task.task_id
    arch_trace = json.loads((tmp_path / "a.jsonl").read_text().splitlines()[-1])
    qa_trace = json.loads((tmp_path / "q.jsonl").read_text().splitlines()[-1])
    assert arch_trace["task_id"] == qa_trace["task_id"] == "TASK-42"


def test_architect_rejects_task_for_other_role() -> None:
    task = EngineeringTask(
        task_id="TASK-43",
        task_type="qa_review",
        description="Wrong role.",
        assigned_role="qa_test_engineer",
        input_files=["src/app/main.py"],
    )
    with pytest.raises(ValueError, match="software_architect"):
        run_architect_task(task, llm=ArchitectFakeLLM())


def test_architect_rejects_task_without_file() -> None:
    task = EngineeringTask(
        task_id="TASK-44",
        task_type="architecture_review",
        description="No file.",
        assigned_role="software_architect",
    )
    with pytest.raises(ValueError, match="input_files"):
        run_architect_task(task, llm=ArchitectFakeLLM())
