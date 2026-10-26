"""DevOps Engineer Agent for EventAI.

Responsibilities:
- Reads infrastructure files like docker-compose.yml (Tool).
- Validates structural requirements deterministically.
- Outputs structured configuration findings.
"""

import argparse
import time
import uuid
from pathlib import Path
from pydantic import BaseModel, Field

from src.models.task import EngineeringTask
from src.observability.tracing import append_trace, estimate_cost_credits

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE = "devops_engineer"


class DevOpsReport(BaseModel):
    status: str
    infrastructure_ok: bool
    findings: list[str] = Field(default_factory=list)


def read_infra_file(filename: str) -> str:
    """TOOL: Read an infrastructure file safely from root."""
    target = (REPO_ROOT / filename).resolve()
    try:
        target.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError("Security violation: Path escapes repository root") from exc

    if not target.exists():
        raise FileNotFoundError(f"Infra file not found: {filename}")
    return target.read_text(encoding="utf-8")


def run_devops_agent(task: EngineeringTask, trace_file: str | None = None) -> DevOpsReport:
    if task.assigned_role != ROLE:
        raise ValueError(f"DevOps agent only accepts tasks for role {ROLE!r}")

    run_id = str(uuid.uuid4())
    started = time.perf_counter()
    findings = []
    infra_ok = True

    try:
        # Check Docker setup
        compose_content = read_infra_file("docker-compose.yml")
        if "postgres" not in compose_content:
            findings.append("Missing PostgreSQL configuration in docker-compose.yml")
            infra_ok = False
        else:
            findings.append("PostgreSQL configuration verified.")

        report = DevOpsReport(
            status="success",
            infrastructure_ok=infra_ok,
            findings=findings
        )
        error = None
    except Exception as exc:
        error = str(exc)

    duration = time.perf_counter() - started

    trace_log = {
        "run_id": run_id,
        "workflow_id": task.workflow_id,
        "task_id": task.task_id,
        "agent": "devops-auditor-agent",
        "role": ROLE,
        "model": "config-linter",
        "tools": ["read_infra_file"],
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
    parser.add_argument("--task-id", default="DEVOPS-AUDIT-01")
    args = parser.parse_args()

    task = EngineeringTask(
        task_id=args.task_id,
        task_type="infrastructure_audit",
        description="Verify docker-compose.yml structure.",
        assigned_role=ROLE,
    )
    print(run_devops_agent(task).model_dump_json(indent=2))