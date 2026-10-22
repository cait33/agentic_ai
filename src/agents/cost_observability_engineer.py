"""Cost & Observability Agent for EventAI.

Responsibilities:
- Reads trace logs (Tool).
- Analyzes total cost and token consumption (Deterministically/Pydantic).
- Outputs a structured summary.
- Emits execution traces for observability.
"""

import argparse
import json
import time
import uuid
from pathlib import Path
from pydantic import BaseModel

from src.models.task import EngineeringTask
from src.observability.tracing import append_trace, estimate_cost_credits

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE = "cost_observability_engineer"


class CostReport(BaseModel):
    status: str
    total_runs_analyzed: int
    total_estimated_credits: float
    summary: str


def read_trace_logs() -> list[dict]:
    """TOOL: Read and parse the local JSONL trace logs."""
    log_file = REPO_ROOT / "logs" / "agent-runs.jsonl"
    if not log_file.exists():
        return []

    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def run_cost_agent(task: EngineeringTask, trace_file: str | None = None) -> CostReport:
    """Executes the cost observability analysis."""
    if task.assigned_role != ROLE:
        raise ValueError(f"Cost agent only accepts tasks for role {ROLE!r}")

    run_id = str(uuid.uuid4())
    started = time.perf_counter()

    try:
        # Tool execution
        logs = read_trace_logs()

        # Analysis
        total_credits = sum(log.get("estimated_cost_credits", 0.0) for log in logs)
        report = CostReport(
            status="success",
            total_runs_analyzed=len(logs),
            total_estimated_credits=round(total_credits, 4),
            summary=f"Analyzed {len(logs)} trace(s) totaling {round(total_credits, 2)} credits."
        )
        error = None
    except Exception as exc:
        error = str(exc)

    duration = time.perf_counter() - started

    trace_log = {
        "run_id": run_id,
        "workflow_id": task.workflow_id,
        "task_id": task.task_id,
        "agent": "cost-observability-agent",
        "role": ROLE,
        "model": "trace-aggregator",
        "tools": ["read_trace_logs"],
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
    parser.add_argument("--task-id", default="COST-AUDIT-01")
    args = parser.parse_args()

    task = EngineeringTask(
        task_id=args.task_id,
        task_type="cost_audit",
        description="Calculate total system cost from trace logs.",
        assigned_role=ROLE,
    )
    print(run_cost_agent(task).model_dump_json(indent=2))