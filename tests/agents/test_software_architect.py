import json
from pathlib import Path
import pytest
from langchain_core.messages import AIMessage

from src.agents.software_architect import (
    ArchitectureReviewResult,
    build_architect_graph,
    read_workspace_file,
    run_architect_agent,
)


class MockArchitectLLM:
    """Simulates LLM response returning structured architecture review JSON."""

    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "status": "changes_requested",
                    "architectural_summary": "Architecture review completed: violations detected.",
                    "violations": [
                        {
                            "severity": "high",
                            "description": "Direct tight coupling found.",
                            "recommendation": "Decouple using an interface or dependency injection.",
                        }
                    ],
                }
            )
        )


# 1. Test: Tool access is restricted
def test_tool_access_restricted_outside_repo() -> None:
    with pytest.raises(ValueError, match="Security violation"):
        read_workspace_file("../../etc/passwd")


# 2. Test: Invalid input is rejected
def test_invalid_input_file_rejected() -> None:
    with pytest.raises(RuntimeError, match="Target file not found"):
        run_architect_agent(
            "non_existent_file.py",
            task_id="TEST-FAIL-01",
            llm=MockArchitectLLM(),
        )


# 3. Test: Output conforms to Pydantic schema
def test_output_conforms_to_pydantic_schema(tmp_path: Path) -> None:
    trace_file = tmp_path / "test-trace.jsonl"
    result = run_architect_agent(
        "src/app/main.py",
        task_id="TEST-SCHEMA-01",
        llm=MockArchitectLLM(),
        trace_file=str(trace_file),
    )

    # Validate instance and schema fields
    assert isinstance(result, ArchitectureReviewResult)
    assert result.status == "changes_requested"
    assert len(result.violations) == 1
    assert result.violations[0].severity == "high"
    assert "Direct tight coupling" in result.violations[0].description


# 4. Test: The workflow terminates properly
def test_workflow_terminates() -> None:
    graph = build_architect_graph(llm=MockArchitectLLM())
    final_state = graph.invoke({"target_file": "src/app/main.py"})

    assert "result" in final_state
    assert final_state["result"]["status"] == "changes_requested"
    assert "error" not in final_state


# 5. Test: Expected artifact(trace log) is generated
def test_expected_trace_artifact_generated(tmp_path: Path) -> None:
    trace_file = tmp_path / "test-trace.jsonl"
    run_architect_agent(
        "src/app/main.py",
        task_id="TEST-TRACE-01",
        llm=MockArchitectLLM(),
        trace_file=str(trace_file),
    )

    assert trace_file.exists(), "Trace log file was not created"
    lines = trace_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    trace_data = json.loads(lines[0])
    assert trace_data["task_id"] == "TEST-TRACE-01"
    assert trace_data["agent"] == "software-architect-agent"
    assert trace_data["status"] == "success"
    assert "read_workspace_file" in trace_data["tools"]
    assert "duration_seconds" in trace_data