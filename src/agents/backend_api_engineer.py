"""Backend / API Engineer Agent for EventAI.

Responsibilities:
- Reads FastAPI application files (Tool: scan_api_endpoints).
- Analyzes API contracts and endpoints deterministically.
- Implements deterministic Python modules inside customer product checkouts
  under quotation/ via EventAI's provider factory (Tool: write_python_module).
- Outputs structured API route reports and verified Python artifacts.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError

from src.app.settings import get_settings
from src.factory.project import FACTORY_ROOT, ProjectConfig
from src.llm.factory import get_chat_model
from src.models.task import EngineeringTask
from src.observability.tracing import append_trace, estimate_cost_credits, usage_from_message

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
    "urllib3",
    "aiohttp",
    "http",
    "ftplib",
    "smtplib",
    "telnetlib",
    "importlib",
    "pickle",
    "shelve",
    "marshal",
    "ctypes",
    "cffi",
    "shutil",
    "os",
    "sys",
    "pathlib",
    "tempfile",
    "glob",
    "random",
    "secrets",
    "uuid",
    "time",
    "threading",
    "multiprocessing",
    "asyncio",
    "builtins",
    "inspect",
    "src",
    "openai",
    "anthropic",
    "langchain",
    "langchain_core",
    "langchain_ollama",
    "langchain_openai",
    "langchain_anthropic",
    "langgraph",
    "ollama",
    "litellm",
    "google",
    "cohere",
    "groq",
    "mistralai",
    "together",
    "fireworks",
    "huggingface_hub",
    "transformers",
}

BLOCKED_CALLS = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
    "input",
    "breakpoint",
    "getattr",
    "setattr",
    "delattr",
    "globals",
    "locals",
    "vars",
}

BLOCKED_METHODS = {
    "write_text",
    "write_bytes",
    "unlink",
    "rmdir",
    "mkdir",
    "rename",
    "replace",
    "system",
    "popen",
    "spawn",
    "run",
    "Popen",
    "call",
    "check_output",
    "check_call",
}

BACKEND_IMPLEMENTER_PROMPT = """You are the Backend / API Engineer Agent for EventAI (role: backend_api_engineer).

Your core responsibility is maintaining and extending backend Python codebases. Alongside analyzing FastAPI contracts and API routes, you implement production-grade, deterministic Python modules, service functions, data schemas, and business calculations that preserve the existing module contract.

UNIVERSAL BACKEND ENGINEERING RULES:
1. Write clean, self-contained Python 3.10+ code with full type annotations and docstrings.
2. Preserve all existing public classes, exceptions, and function signatures from the target stub file exactly.
3. All business logic must be 100% deterministic. Never generate code that calls an LLM, external API, network socket, filesystem writer, or random generator at runtime.
4. Only import from safe Python standard library modules (such as `decimal`, `math`, `typing`, `dataclasses`, `collections`) or the product's own modules documented in the stub (such as `quotation.catalog`). Never import Factory (`src.*`), LLM SDKs, `os`, `sys`, `subprocess`, or networking packages.
5. When implementing pricing, quantities, discounts, shipping, taxes, or financial calculations:
   - Follow the money representation specified in the stub/brief (e.g., integer cents or `decimal.Decimal`—never `float`).
   - Enforce strict guard clauses at the start of functions to reject invalid inputs (such as `quantity <= 0`, empty item lists, or unknown SKUs) by raising the stub's domain error class (e.g., `QuoteError` / `ValueError`).
6. If QA or human reviewer feedback is provided, fix every reported issue while keeping the stub contract intact.

OUTPUT FORMAT:
Reply ONLY with one JSON object containing the keys `status` ("success" or "needs_clarification"), `code`, `entrypoint_name`, and `notes`."""


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class BackendReport(BaseModel):
    status: str
    endpoints_found: int | None = None
    routes: list[str] = Field(default_factory=list)
    code: str | None = None
    entrypoint_name: str | None = None
    written_path: str | None = None
    error: str | None = None


class PythonImplementerOutput(BaseModel):
    """What the LLM must return (also used as Ollama JSON schema)."""

    status: Literal["success", "needs_clarification"] = "success"
    code: str = Field(default="", description="Complete, runnable Python source code.")
    entrypoint_name: str = Field(
        default="calculate_quote",
        description="Primary function, class, or router implemented.",
    )
    verification_tests: str = Field(
        default="",
        description="Optional notes/assertions (never executed in the Factory).",
    )
    notes: str = ""


# Backwards-compatible alias
CodeArtifact = PythonImplementerOutput


class ImplementationResult(BaseModel):
    """Result returned to `customer_workflow.py` (mirrors `web_implementer.ImplementationResult`)."""

    status: Literal["success", "needs_clarification", "unparseable", "rejected"]
    target_file: str
    artifact_sha256: str | None = None
    entrypoint_name: str | None = None
    notes: str = ""
    error: str | None = None


# --------------------------------------------------------------------------- #
# Static AST & Contract Guards
# --------------------------------------------------------------------------- #
def _validate_ast_safety(source: str, label: str = "generated code") -> ast.Module:
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
            if isinstance(node.func, ast.Attribute) and node.func.attr in BLOCKED_METHODS:
                raise ValueError(f"Blocked method call in {label}: {node.func.attr!r}")

    return tree


def _validate_stub_contract(tree: ast.Module, stub_source: str | None) -> None:
    """Verify that required classes and function signatures from the stub are preserved."""
    if not stub_source:
        return

    stub_tree = ast.parse(stub_source)
    gen_classes = {
        node.name: node for node in tree.body if isinstance(node, ast.ClassDef)
    }
    gen_funcs = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }

    for node in stub_tree.body:
        if isinstance(node, ast.ClassDef):
            if node.name not in gen_classes:
                raise ValueError(f"Contract violation: missing required class {node.name!r}")
            stub_bases = {b.id for b in node.bases if isinstance(b, ast.Name)}
            if "ValueError" in stub_bases:
                gen_bases = {b.id for b in gen_classes[node.name].bases if isinstance(b, ast.Name)}
                if "ValueError" not in gen_bases:
                    raise ValueError(
                        f"Contract violation: class {node.name!r} must inherit from ValueError"
                    )

        elif isinstance(node, ast.FunctionDef):
            if node.name not in gen_funcs:
                raise ValueError(f"Contract violation: missing required function {node.name!r}")
            gen_fn = gen_funcs[node.name]
            stub_pos = [a.arg for a in node.args.posonlyargs] + [a.arg for a in node.args.args]
            gen_pos = [a.arg for a in gen_fn.args.posonlyargs] + [a.arg for a in gen_fn.args.args]
            if len(gen_pos) < len(stub_pos):
                raise ValueError(
                    f"Contract violation: function {node.name!r} expected parameters {stub_pos}, got {gen_pos}"
                )
            if len(gen_fn.args.defaults) < len(node.args.defaults):
                raise ValueError(
                    f"Contract violation: function {node.name!r} missing default parameter values"
                )
            # Reject an unimplemented stub that still raises NotImplementedError at top level
            for stmt in gen_fn.body:
                if isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Call):
                    if isinstance(stmt.exc.func, ast.Name) and stmt.exc.func.id == "NotImplementedError":
                        raise ValueError(
                            f"Contract violation: function {node.name!r} still raises NotImplementedError"
                        )


def _validate_python_module(source: str, stub_source: str | None = None) -> None:
    """Run static syntax, safety, and stub-contract checks without executing code."""
    if not source.strip():
        raise ValueError("Generated Python source code is empty")
    tree = _validate_ast_safety(source, label="generated code")
    _validate_stub_contract(tree, stub_source)


# --------------------------------------------------------------------------- #
# Product Checkout File Tools
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _product_target(cfg: ProjectConfig, relative_path: str) -> Path:
    """Resolve a product-relative path via `cfg.product_file` and enforce `quotation/`."""
    target = cfg.product_file(relative_path)
    rel = target.relative_to(cfg.product_path.resolve()).as_posix()
    if not rel.startswith("quotation/"):
        raise PermissionError(
            f"Python implementer may only write inside 'quotation/', got {relative_path!r}"
        )
    return target


def read_product_file(cfg: ProjectConfig, relative_path: str) -> str:
    """TOOL: Read a UTF-8 file from the allowed `quotation/` area of the product checkout."""
    target = _product_target(cfg, relative_path)
    if not target.is_file():
        raise FileNotFoundError(f"Product file not found: {relative_path}")
    return target.read_text(encoding="utf-8")


def write_python_module(cfg: ProjectConfig, relative_path: str, code: str) -> str:
    """TOOL: Write validated Python code into `quotation/` and return its sha256."""
    target = _product_target(cfg, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(code.rstrip() + "\n", encoding="utf-8")
    return sha256_file(target)


# --------------------------------------------------------------------------- #
# LLM Helpers
# --------------------------------------------------------------------------- #
def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, list):
        content = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return str(content)


def parse_output(text: str) -> PythonImplementerOutput | None:
    text = _THINK_RE.sub("", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return PythonImplementerOutput.model_validate(json.loads(text[start:end + 1]))
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
            "format": PythonImplementerOutput.model_json_schema(),
            "num_predict": max(llm.num_predict or 0, MAX_OUTPUT_TOKENS),
        })
    return llm


def build_implementer_messages(
    *,
    brief: str,
    stub_code: str,
    target_file: str,
    stories: list[dict[str, Any]],
    feedback: str | None,
    extra_context: str = "",
) -> list[Any]:
    parts = [
        "CUSTOMER BRIEF:\n" + brief,
        "USER STORIES FROM PRODUCT OWNER (structured handover):\n"
        + json.dumps(stories, ensure_ascii=False, indent=1),
        f"TARGET FILE ({target_file}) CURRENT STUB:\n```python\n{stub_code}\n```",
    ]
    if extra_context:
        parts.append("ADDITIONAL CONTEXT:\n" + extra_context)
    if feedback:
        parts.append(
            "FEEDBACK FROM QA / HUMAN REVIEWER - fix exactly these problems:\n" + feedback
        )
    return [SystemMessage(content=BACKEND_IMPLEMENTER_PROMPT), HumanMessage(content="\n\n".join(parts))]


# --------------------------------------------------------------------------- #
# Standalone Factory Tools & Entry Point
# --------------------------------------------------------------------------- #
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
    return [line.strip() for line in lines if line.strip().startswith(("@app.", "@router."))]


def implement_python_code(
    task: EngineeringTask,
    llm: Any,
    ctx: dict[str, Any],
    *,
    stub_code: str | None = None,
) -> tuple[PythonImplementerOutput | None, str | None]:
    """TOOL: Generate and statically validate deterministic Python code."""
    context_blocks: list[str] = []
    for filepath in task.input_files:
        target = _resolve_repo_path(filepath)
        content = target.read_text(encoding="utf-8")
        lang = "json" if target.suffix == ".json" else "python"
        context_blocks.append(f"### File: {filepath}\n```{lang}\n{content}\n```")
    context_text = "\n\n".join(context_blocks) if context_blocks else "No reference files provided."

    parts = [
        f"TASK ID: {task.task_id}",
        f"TASK TYPE: {task.task_type}",
        f"DESCRIPTION:\n{task.description}",
        f"REPOSITORY CONTEXT:\n{context_text}",
    ]
    if stub_code:
        parts.append(f"TARGET STUB:\n```python\n{stub_code}\n```")

    chat_model = _prepare_llm(llm)
    messages: list[Any] = [
        SystemMessage(content=BACKEND_IMPLEMENTER_PROMPT),
        HumanMessage(content="\n\n".join(parts)),
    ]

    ctx["calls"] += 1
    response = chat_model.invoke(messages)
    in_tokens, out_tokens = usage_from_message(response)
    if in_tokens is not None:
        ctx["input_tokens"] = (ctx["input_tokens"] or 0) + in_tokens
    if out_tokens is not None:
        ctx["output_tokens"] = (ctx["output_tokens"] or 0) + out_tokens

    artifact = parse_output(_message_text(response))
    if artifact is None:
        return None, "LLM output is not valid PythonImplementerOutput JSON"

    _validate_python_module(artifact.code, stub_source=stub_code)
    return artifact, None


def run_backend_agent(
    task: EngineeringTask,
    llm: Any | None = None,
    trace_file: str | None = None,
) -> BackendReport:
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
            try:
                artifact, parse_error = implement_python_code(task, active_llm, ctx)
            except (ValueError, SyntaxError) as exc:
                report = BackendReport(status="rejected", error=str(exc))
            else:
                if artifact is None:
                    report = BackendReport(status="unparseable", error=parse_error)
                else:
                    report = BackendReport(
                        status="success",
                        code=artifact.code,
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


# --------------------------------------------------------------------------- #
# Customer Workflow Entry Point
# --------------------------------------------------------------------------- #
def run_python_implementer(
    task: EngineeringTask,
    cfg: ProjectConfig,
    *,
    stories: list[dict[str, Any]] | None = None,
    feedback: str | None = None,
    llm: Any | None = None,
    trace_file: str | None = None,
) -> ImplementationResult:
    """Customer-workflow entry point: implements a Python module in `cfg.target_file`."""
    if task.assigned_role != ROLE:
        raise ValueError(f"Python implementer only accepts tasks for role {ROLE!r}")
    if not task.input_files:
        raise ValueError("Implementer task needs the customer brief in input_files")

    settings = get_settings()
    run_id = str(uuid.uuid4())
    started = time.perf_counter()
    ctx: dict[str, Any] = {"tools": [], "calls": 0, "input_tokens": None, "output_tokens": None}
    record: dict[str, Any] = {
        "run_id": run_id,
        "workflow_id": task.workflow_id,
        "task_id": task.task_id,
        "project_id": cfg.project_id,
        "agent": AGENT_NAME,
        "role": ROLE,
        "provider": settings.llm_provider if llm is None else "injected",
        "model": settings.llm_model if llm is None else (
            getattr(llm, "model", None) or getattr(llm, "model_name", None) or type(llm).__name__
        ),
        "target_file": cfg.target_file,
        "had_feedback": bool(feedback),
        "status": "error",
    }

    try:
        ctx["tools"].append("read_product_file")
        stub_code = read_product_file(cfg, cfg.target_file)

        brief_path = Path(task.input_files[0])
        if not brief_path.is_absolute():
            brief_path = (FACTORY_ROOT / brief_path).resolve()
            brief_path.relative_to(FACTORY_ROOT)
        brief = brief_path.read_text(encoding="utf-8")

        extra_blocks: list[str] = []
        catalog_path = cfg.product_path / "quotation" / "catalog.py"
        if catalog_path.is_file():
            extra_blocks.append(
                f"### Product module: quotation/catalog.py\n```python\n{catalog_path.read_text(encoding='utf-8')}\n```"
            )
        for extra_file in task.input_files[1:]:
            extra_target = _resolve_repo_path(extra_file)
            extra_blocks.append(f"### File: {extra_file}\n```\n{extra_target.read_text(encoding='utf-8')}\n```")

        chat_model = _prepare_llm(llm or get_chat_model(reasoning=False, json_mode=True))
        messages = build_implementer_messages(
            brief=brief,
            stub_code=stub_code,
            target_file=cfg.target_file,
            stories=stories or [],
            feedback=feedback,
            extra_context="\n\n".join(extra_blocks),
        )

        ctx["calls"] += 1
        response = chat_model.invoke(messages)
        ctx["input_tokens"], ctx["output_tokens"] = usage_from_message(response)

        output = parse_output(_message_text(response))
        if output is None:
            result = ImplementationResult(
                status="unparseable",
                target_file=cfg.target_file,
                error="LLM output is not valid PythonImplementerOutput JSON",
            )
        elif output.status == "needs_clarification":
            result = ImplementationResult(
                status="needs_clarification",
                target_file=cfg.target_file,
                notes=output.notes,
            )
        else:
            try:
                _validate_python_module(output.code, stub_source=stub_code)
                ctx["tools"].append("write_python_module")
                digest = write_python_module(cfg, cfg.target_file, output.code)
                result = ImplementationResult(
                    status="success",
                    target_file=cfg.target_file,
                    artifact_sha256=digest,
                    entrypoint_name=output.entrypoint_name,
                    notes=output.notes,
                )
            except (ValueError, SyntaxError, PermissionError) as exc:
                result = ImplementationResult(
                    status="rejected",
                    target_file=cfg.target_file,
                    error=str(exc),
                )

        record["result_status"] = result.status
        record["artifact_sha256"] = result.artifact_sha256
        record["status"] = "success" if result.status == "success" else "invalid_output"
        return result
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
    parser.add_argument("--file", default=None)
    parser.add_argument("--task-type", default="api_analysis")
    parser.add_argument("--description", default="Extract API routes from the application.")
    args = parser.parse_args()

    if args.file:
        input_files = [args.file]
    elif args.task_type == "api_analysis":
        input_files = ["src/app/main.py"]
    else:
        input_files = [
            "task sheets/session-06-08/HansePack_Katalog.json",
            "task sheets/session-06-08/HansePack_Referenzfaelle.json",
        ]

    task = EngineeringTask(
        task_id=args.task_id,
        task_type=args.task_type,
        description=args.description,
        assigned_role=ROLE,
        input_files=input_files,
    )
    print(run_backend_agent(task).model_dump_json(indent=2, exclude_none=True))