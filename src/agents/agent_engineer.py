"""Agent Engineer Agent for EventAI.

Responsibilities:
- Reads workflow implementation files (Tool).
- Validates LangGraph node and edge configurations.
- Outputs structured LangGraph topology info.
"""

import argparse
import time
import uuid
from pathlib import Path
from pydantic import BaseModel, Field

from src.models.task import EngineeringTask
from src.observability.tracing import append_trace, estimate_cost_credits

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE = "agent_engineer"


class LangGraphReport(BaseModel):
    status: str
    nodes_found: int
    has_human_gate: bool


def analyze_langgraph_nodes(filepath: str) -> tuple[int, bool]:
    """TOOL: Read python file and extract LangGraph structure."""
    target = (REPO_ROOT / filepath).resolve()
    try:
        target.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError("Security violation: Path escapes repository root") from exc

    if not target.exists():
        raise FileNotFoundError(f"Workflow file not found: {filepath}")

    content = target.read_text(encoding="utf-8")
    nodes = content.count(".add_node(")
    has_human = "human_gate" in content or "HumanDecision" in content

    return nodes, has_human


def run_agent_engineer(task: EngineeringTask, trace_file: str | None = None) -> LangGraphReport:
    if task.assigned_role != ROLE:
        raise ValueError(f"Agent only accepts tasks for role {ROLE!r}")

    run_id = str(uuid.uuid4())
    started = time.perf_counter()

    try:
        source_file = task.input_files[0] if task.input_files else "src/agents/workflow.py"
        nodes, has_human = analyze_langgraph_nodes(source_file)
        report = LangGraphReport(
            status="success",
            nodes_found=nodes,
            has_human_gate=has_human
        )
        error = None
    except Exception as exc:
        error = str(exc)

    duration = time.perf_counter() - started

    trace_log = {
        "run_id": run_id,
        "workflow_id": task.workflow_id,
        "task_id": task.task_id,
        "agent": "agent-engineer-agent",
        "role": ROLE,
        "model": "topology-analyzer",
        "tools": ["analyze_langgraph_nodes"],
        "calls": 0,
        "input_tokens": None,
        "output_tokens": None,
        "duration_seconds": round(duration, 4),
        "status": "error" if error else "success",
        "estimated_cost_credits": estimate_cost_credits(
            duration_seconds=duration,
            input_tokens=None,
            output_tokens=None,
            calls=0,
        ),
    }

    if error:
        trace_log["error"] = error
        append_trace(trace_log, trace_file)
        raise RuntimeError(error)

    append_trace(trace_log, trace_file)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="LANGGRAPH-AUDIT-01")
    parser.add_argument("--file", default="src/agents/workflow.py")
    args = parser.parse_args()

    task = EngineeringTask(
        task_id=args.task_id,
        task_type="workflow_analysis",
        description="Verify LangGraph topology.",
        assigned_role=ROLE,
        input_files=[args.file]
    )
    print(run_agent_engineer(task).model_dump_json(indent=2))