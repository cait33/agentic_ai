"""Backend / API Engineer Agent for EventAI.

Responsibilities:
- Reads FastAPI application files (Tool).
- Analyzes API contracts and endpoints deterministically.
- Outputs structured API routes.
"""

import argparse
import time
import uuid
from pathlib import Path
from pydantic import BaseModel, Field

from src.models.task import EngineeringTask
from src.observability.tracing import append_trace, estimate_cost_credits

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE = "backend_api_engineer"


class BackendReport(BaseModel):
    status: str
    endpoints_found: int
    routes: list[str] = Field(default_factory=list)


def scan_api_endpoints(filepath: str) -> list[str]:
    """TOOL: Read python file and extract FastAPI routes."""
    target = (REPO_ROOT / filepath).resolve()
    try:
        target.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError("Security violation: Path escapes repository root") from exc

    if not target.exists():
        raise FileNotFoundError(f"Source file not found: {filepath}")

    lines = target.read_text(encoding="utf-8").splitlines()
    routes = [line.strip() for line in lines if line.strip().startswith(("@app.", "@router."))]
    return routes


def run_backend_agent(task: EngineeringTask, trace_file: str | None = None) -> BackendReport:
    if task.assigned_role != ROLE:
        raise ValueError(f"Agent only accepts tasks for role {ROLE!r}")

    run_id = str(uuid.uuid4())
    started = time.perf_counter()
    routes = []

    try:
        source_file = task.input_files[0] if task.input_files else "src/app/main.py"
        routes = scan_api_endpoints(source_file)
        report = BackendReport(status="success", endpoints_found=len(routes), routes=routes)
        error = None
    except Exception as exc:
        error = str(exc)

    duration = time.perf_counter() - started

    trace_log = {
        "run_id": run_id,
        "workflow_id": task.workflow_id,
        "task_id": task.task_id,
        "agent": "backend-api-agent",
        "role": ROLE,
        "model": "static-analysis",
        "tools": ["scan_api_endpoints"],
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
    parser.add_argument("--task-id", default="BACKEND-AUDIT-01")
    parser.add_argument("--file", default="src/app/main.py")
    args = parser.parse_args()

    task = EngineeringTask(
        task_id=args.task_id,
        task_type="api_analysis",
        description="Extract API routes from the application.",
        assigned_role=ROLE,
        input_files=[args.file]
    )
    print(run_backend_agent(task).model_dump_json(indent=2))