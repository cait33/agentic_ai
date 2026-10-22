"""Data & RAG Engineer Agent for EventAI.

Responsibilities:
- Reads SQL migration files (Tool).
- Analyzes PostgreSQL and vector schema changes.
- Outputs structured schema analysis.
"""

import argparse
import time
import uuid
from pathlib import Path
from pydantic import BaseModel, Field

from src.models.task import EngineeringTask
from src.observability.tracing import append_trace, estimate_cost_credits

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE = "data_rag_engineer"


class DataSchemaReport(BaseModel):
    status: str
    vector_extension_enabled: bool
    tables_created: list[str] = Field(default_factory=list)


def scan_sql_schema(filepath: str) -> tuple[bool, list[str]]:
    """TOOL: Read SQL file and extract schema definitions."""
    target = (REPO_ROOT / filepath).resolve()
    try:
        target.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError("Security violation: Path escapes repository root") from exc

    if not target.exists():
        raise FileNotFoundError(f"SQL file not found: {filepath}")

    content = target.read_text(encoding="utf-8").upper()
    vector_enabled = "CREATE EXTENSION" in content and "VECTOR" in content

    lines = content.splitlines()
    tables = [
        line.split("TABLE")[1].strip().split()[0]
        for line in lines if line.strip().startswith("CREATE TABLE")
    ]
    return vector_enabled, tables


def run_data_agent(task: EngineeringTask, trace_file: str | None = None) -> DataSchemaReport:
    if task.assigned_role != ROLE:
        raise ValueError(f"Agent only accepts tasks for role {ROLE!r}")

    run_id = str(uuid.uuid4())
    started = time.perf_counter()

    try:
        source_file = task.input_files[0] if task.input_files else "db/migrations/001_work_items.sql"
        vector_enabled, tables = scan_sql_schema(source_file)
        report = DataSchemaReport(
            status="success",
            vector_extension_enabled=vector_enabled,
            tables_created=tables
        )
        error = None
    except Exception as exc:
        error = str(exc)

    duration = time.perf_counter() - started

    trace_log = {
        "run_id": run_id,
        "workflow_id": task.workflow_id,
        "task_id": task.task_id,
        "agent": "data-rag-agent",
        "role": ROLE,
        "model": "schema-inspector",
        "tools": ["scan_sql_schema"],
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
    parser.add_argument("--task-id", default="DATA-AUDIT-01")
    parser.add_argument("--file", default="db/migrations/001_work_items.sql")
    args = parser.parse_args()

    task = EngineeringTask(
        task_id=args.task_id,
        task_type="schema_analysis",
        description="Verify database migrations.",
        assigned_role=ROLE,
        input_files=[args.file]
    )
    print(run_data_agent(task).model_dump_json(indent=2))