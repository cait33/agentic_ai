"""Backend / API Engineer Agent for EventAI.

Responsibilities:
- Reads FastAPI application files (Tool).
- Analyzes API contracts and endpoints deterministically.
- Outputs structured API routes.
"""

import argparse
import json
import os
import time
from typing import Any
import uuid
import re
import ast
from pathlib import Path
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError
from src.app.settings import get_settings
from src.llm.factory import get_chat_model
from src.models.task import EngineeringTask
from src.observability.tracing import append_trace, estimate_cost_credits, usage_from_message

from src.models.task import EngineeringTask
from src.observability.tracing import append_trace, estimate_cost_credits

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_NAME = "backend-api-agent"
ROLE = "backend_api_engineer"

MAX_OUTPUT_TOKENS = 3072
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

BLOCKED_MODULES = {
    "subprocess",
    "socket",
    "requests",
    "httpx",
    "urllib",
    "importlib",
    "pickle",
    "ctypes",
    "shutil",
    "os",
    "sys",
    "random",
}

BLOCKED_CALLS = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
    "input",
    "breakpoint",
}

BACKEND_IMPLEMENTER_PROMPT = """You are the Backend / API Engineer Agent for EventAI (role: backend_api_engineer).

Your core responsibility is maintaining and extending EventAI's backend codebase. Alongside analyzing FastAPI contracts and API routes, you implement production-grade, deterministic Python modules, service functions, data schemas, and business calculations that integrate cleanly with EventAI's existing FastAPI and Pydantic architecture.

UNIVERSAL BACKEND ENGINEERING RULES:
1. Retain your backend architectural standards: write clean, self-contained Python 3.10+ code with full type annotations and docstrings.
2. All business logic must be 100% deterministic. Never generate code that calls an LLM, external API, or random generator at runtime to determine values or prices.
3. Only import from the Python standard library or internal/third-party packages already present in the provided repository context files.
4. Provide `verification_tests` using plain Python `assert` statements and `try / except` blocks (do not import `pytest` or `unittest`).
5. When implementing pricing, quantities, discounts, shipping, taxes, or financial calculations:
  - Use `decimal.Decimal` (initialized from strings, e.g., `Decimal("19.99")`) or integer cents—never `float`.
  - Enforce strict guard clauses at the start of functions to reject invalid inputs (such as `quantity <= 0` or unknown SKUs) by raising `ValueError`.
  - Include assertions in `verification_tests` covering valid boundary cases and expected `ValueError` rejections.

OUTPUT FORMAT:
Reply ONLY with one JSON object containing the keys `code`, `entrypoint_name`, and `verification_tests`."""


class BackendReport(BaseModel):
    status: str
    endpoints_found: int | None = None
    routes: list[str] = Field(default_factory=list)
    code: str | None = None
    entrypoint_name: str | None = None
    written_path: str | None = None
    error: str | None = None
    

class CodeArtifact(BaseModel):
    code: str = Field(description="Complete, runnable Python source code.")
    entrypoint_name: str = Field(description="Primary function, class, or router implemented.")
    verification_tests: str = Field(description="Plain Python assertions verifying edge cases and errors.")
    
class CodeToolResult(BaseModel):
    artifact: CodeArtifact
    written_path: str | None = None
    calls: int
    input_tokens: int
    output_tokens: int
    

def _validate_ast_safety(source: str, label: str = "generated code") -> None:
    """Parse Python source into an AST and reject unsafe or non-deterministic constructs."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise SyntaxError(f"Syntax error in {label}: {exc}") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                if root_pkg in BLOCKED_MODULES:
                    raise ValueError(f"Blocked import in {label}: {alias.name!r}")

        elif isinstance(node, ast.ImportFrom) and node.module:
            root_pkg = node.module.split(".")[0]
            if root_pkg in BLOCKED_MODULES:
                raise ValueError(f"Blocked import in {label}: {node.module!r}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in BLOCKED_CALLS:
                raise ValueError(f"Blocked builtin call in {label}: {node.func.id!r}")
            if isinstance(node.func, ast.Attribute) and node.func.attr in {
                "write_text",
                "write_bytes",
                "unlink",
                "rmdir",
                "system",
                "popen",
            }:
                raise ValueError(f"Blocked method call in {label}: {node.func.attr!r}")


def _run_verification_tests(code: str, verification_tests: str) -> None:
    """Validate and execute generated assertions against the implementation in isolation."""
    _validate_ast_safety(code, label="generated code")
    _validate_ast_safety(verification_tests, label="verification tests")

    namespace: dict[str, object] = {"__name__": "__verification__"}
    combined_source = f"{code}\n\n{verification_tests}"
    exec(compile(combined_source, "<generated_verification>", "exec"), namespace)


def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, list):
        content = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return str(content)


def parse_output(text: str) -> CodeArtifact | None:
    text = _THINK_RE.sub("", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return CodeArtifact.model_validate(json.loads(text[start:end + 1]))
    except (json.JSONDecodeError, ValidationError):
        return None


def _prepare_llm(llm: Any) -> Any:
    try:
        from langchain_ollama import ChatOllama
    except ImportError:  # pragma: no cover
        return llm
    if isinstance(llm, ChatOllama):
        return llm.model_copy(update={
            "reasoning": False,
            "format": CodeArtifact.model_json_schema(),
            "num_predict": max(llm.num_predict or 0, MAX_OUTPUT_TOKENS),
        })
    return llm


def build_messages(task: EngineeringTask, context_text: str) -> list[Any]:
    parts = [
        f"TASK ID: {task.task_id}",
        f"TASK TYPE: {task.task_type}",
        f"DESCRIPTION:\n{task.description}",
        f"REPOSITORY CONTEXT:\n{context_text}",
    ]
    return [SystemMessage(content=BACKEND_IMPLEMENTER_PROMPT), HumanMessage(content="\n\n".join(parts))]


def _resolve_repo_path(filepath: str) -> Path:
    """Resolve a path relative to REPO_ROOT and block directory traversal."""
    target = (REPO_ROOT / filepath).resolve()
    try:
        target.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError(f"Security violation: Path escapes repository root: {filepath}") from exc
    if not target.exists():
        raise FileNotFoundError(f"Source file not found: {filepath}")
    return target


def scan_api_endpoints(filepath: str) -> list[str]:
    """TOOL: Read python file and extract FastAPI routes."""
    target = _resolve_repo_path(filepath)

    lines = target.read_text(encoding="utf-8").splitlines()
    routes = [line.strip() for line in lines if line.strip().startswith(("@app.", "@router."))]
    
    return routes


def implement_python_code(task: EngineeringTask, llm: Any, ctx: dict[str, Any]) -> tuple[CodeArtifact | None, str | None]:
    """TOOL: Generate, AST-validate, and verify deterministic Python code."""
    context_blocks: list[str] = []
    for filepath in task.input_files:
        target = _resolve_repo_path(filepath)
        # TODO adapt for json files
        content = target.read_text(encoding="utf-8")
        context_blocks.append(f"### File: {filepath}\n```python\n{content}\n```")
    context_text = "\n\n".join(context_blocks) if context_blocks else "No reference files provided."
    
    chat_model = _prepare_llm(llm)
    messages = build_messages(task, context_text)
    
    last_error: Exception | None = None

    for _attempt in range(2):
        ctx["calls"] += 1
        response = chat_model.invoke(messages)
        in_tokens, out_tokens = usage_from_message(response)
        response = llm.beta.chat.completions.parse(
            messages=messages,
            response_format=CodeArtifact,
            temperature=0.0,
        )

        if in_tokens is not None:
            ctx["input_tokens"] = (ctx["input_tokens"] or 0) + in_tokens
        if out_tokens is not None:
            ctx["output_tokens"] = (ctx["output_tokens"] or 0) + out_tokens

        raw_text = _message_text(response)
        artifact = parse_output(raw_text)
        
        if artifact is None:
            last_error = RuntimeError("Model returned an empty CodeArtifact.")
            continue
        
        try:
            _run_verification_tests(artifact)
            return artifact, None
        except Exception as exc:
            last_error = exc
            messages.append(response)
            messages.append(
                HumanMessage(
                    content=(
                        f"Verification failed with {last_error}\n"
                        "Fix the implementation or verification tests and reply ONLY with the corrected JSON object."
                    )
                )
            )

    raise ValueError(f"Code implementation failed validation: {last_error}")
    


def run_backend_agent(task: EngineeringTask, llm: Any | None = None, trace_file: str | None = None) -> BackendReport:
    if task.assigned_role != ROLE:
        raise ValueError(f"Agent only accepts tasks for role {ROLE!r}")

    settings = get_settings()
    run_id = str(uuid.uuid4())
    started = time.perf_counter()
    is_static = task.task_type == "api_analysis"

    ctx: dict[str, Any] = {
        "tools": [],
        "calls": 0,
        "input_tokens": None,
        "output_tokens": None,
    }
    record: dict[str, Any] = {
        "run_id": run_id,
        "workflow_id": task.workflow_id,
        "task_id": task.task_id,
        "agent": AGENT_NAME,
        "role": ROLE,
        "provider": "static" if is_static else (settings.llm_provider if llm is None else "injected"),
        "model": (
            "static-analysis"
            if is_static
            else (
                settings.llm_model
                if llm is None
                else (getattr(llm, "model", None) or getattr(llm, "model_name", None) or type(llm).__name__)
            )
        ),
        "status": "error",
    }

    try:
        if is_static:
            ctx["tools"].append("scan_api_endpoints")
            source_file = task.input_files[0] if task.input_files else "src/app/main.py"
            routes = scan_api_endpoints(source_file)
            report = BackendReport(
                status="success",
                endpoints_found=len(routes),
                routes=routes,
            )
        else:
            ctx["tools"].append("implement_python_code")
            active_llm = llm or get_chat_model(reasoning=False, json_mode=True)
            artifact, parse_error = implement_python_code(task, active_llm, ctx)
            if artifact is None:
                report = BackendReport(status="unparseable", error=parse_error)
            else:
                report = BackendReport(
                    status="success",
                    generated_code=artifact.code,
                    entrypoint_name=artifact.entrypoint_name,
                )
        record["result_status"] = report.status
        record["status"] = "success" if report.status == "success" else "invalid_output"
        return report
    except (Exception, KeyboardInterrupt) as exc:
        record["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "error"
        record["error_type"] = type(exc).__name__
        raise
    finally:
        duration = time.perf_counter() - started
        append_trace(
            {
                **record,
                **ctx,
                "duration_seconds": round(duration, 4),
                "estimated_cost_credits": estimate_cost_credits(
                    duration_seconds=duration,
                    input_tokens=ctx["input_tokens"],
                    output_tokens=ctx["output_tokens"],
                    calls=ctx["calls"],
                ),
                "token_usage_complete": ctx["input_tokens"] is not None and ctx["output_tokens"] is not None,
            },
            trace_file,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="BACKEND-AUDIT-01")
    parser.add_argument("--task-type", default="api_analysis")
    args = parser.parse_args()

    if args.file:
        input_files = [args.file]
    elif args.task_type == "api_analysis":
        input_files = ["src/app/main.py"]
    else:
        input_files = ["task sheets\session-06-08\HansePack_Katalog.json", "task sheets\session-06-08/HansePack_Referenzfaelle.json"]

    task = EngineeringTask(
        task_id=args.task_id,
        task_type="api_analysis",
        description="Extract API routes from the application.",
        assigned_role=ROLE,
        input_files=input_files
    )
    print(run_backend_agent(task).model_dump_json(indent=2, exclude_none=True))