"""Web Implementer agent: writes customer content into the product checkout.

Role:    backend_api_engineer (Factory capability "web-implementer-agent")
Input:   EngineeringTask (input_files = [customer brief]), ProjectConfig,
         PO user stories (structured handover) and optional feedback from QA / reviewer
LLM:     one call via the provider factory, JSON output validated with Pydantic
Tools:   read_product_file   - reads a file of the product checkout
         write_product_slots - replaces ONLY the content between
                               <!-- AGENT:<slot> --> ... <!-- /AGENT:<slot> --> markers
                               of a file inside the allowed product area
Guards:  - path must stay inside product checkout AND allowed_write_paths
         - unknown slots, <script>, event handlers, javascript: and external URLs are rejected
         - unparseable LLM output writes nothing (status "unparseable")
         - only slots that have markers in the target file are written; an empty slot
           value in the LLM output means "leave unchanged" (never wipes existing content)
Trace:   one JSONL record per run (run_id, workflow_id, task_id, agent, role, model,
         tools, calls, tokens, duration, artifact hash, credits)
"""

from __future__ import annotations

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

AGENT_NAME = "web-implementer-agent"
ROLE = "backend_api_engineer"
SLOTS = ("nav", "header", "services", "audiences", "approach", "contact", "footer")
MAX_OUTPUT_TOKENS = 3072
_SLOT_RE = re.compile(r"(<!-- AGENT:(\w+) -->)(.*?)(<!-- /AGENT:\2 -->)", re.DOTALL)
_FORBIDDEN = [
    (re.compile(r"<\s*script", re.I), "<script> is not allowed"),
    (re.compile(r"\son\w+\s*=", re.I), "inline event handlers are not allowed"),
    (re.compile(r"javascript:", re.I), "javascript: URLs are not allowed"),
    (re.compile(r"(src|href)\s*=\s*[\"']?\s*(https?:)?//", re.I), "external resources are not allowed"),
    (re.compile(r"<!--\s*/?AGENT:", re.I), "slot content must not contain AGENT markers"),
    (re.compile(r"<\s*/?\s*nav\b", re.I), "slot content must not contain <nav> (the team owns the <nav> element)"),
]


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class ImplementerOutput(BaseModel):
    """What the LLM must return (also used as Ollama JSON schema)."""

    status: Literal["success", "needs_clarification"]
    nav_html: str = ""
    header_html: str = ""
    services_html: str = ""
    audiences_html: str = ""
    approach_html: str = ""
    contact_html: str = ""
    footer_html: str = ""
    notes: str = ""


class ImplementationResult(BaseModel):
    status: Literal["success", "needs_clarification", "unparseable", "rejected"]
    target_file: str
    artifact_sha256: str | None = None
    slots_written: list[str] = Field(default_factory=list)
    slots_unchanged: list[str] = Field(default_factory=list)
    notes: str = ""
    error: str | None = None


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_product_file(cfg: ProjectConfig, relative_path: str) -> str:
    """TOOL: read a UTF-8 file from the allowed area of the product checkout."""
    target = cfg.product_file(relative_path)
    if not target.is_file():
        raise FileNotFoundError(f"Product file not found: {relative_path}")
    return target.read_text(encoding="utf-8")


def current_slots(html: str) -> dict[str, str]:
    return {m.group(2): m.group(3).strip() for m in _SLOT_RE.finditer(html)}


def validate_slot_content(name: str, content: str) -> None:
    if name not in SLOTS:
        raise ValueError(f"Unknown slot: {name!r}")
    for pattern, reason in _FORBIDDEN:
        if pattern.search(content):
            raise ValueError(f"Slot {name!r}: {reason}")


def write_product_slots(cfg: ProjectConfig, relative_path: str, slots: dict[str, str]) -> str:
    """TOOL: replace the content between AGENT markers; everything else stays untouched.

    Returns the sha256 of the written file.
    """
    target = cfg.product_file(relative_path)
    html = target.read_text(encoding="utf-8")
    existing = set(current_slots(html))
    for name, content in slots.items():
        validate_slot_content(name, content)
        if name not in existing:
            raise ValueError(f"Slot {name!r} has no markers in {relative_path}")

    def replace(match: re.Match[str]) -> str:
        name = match.group(2)
        if name not in slots:
            return match.group(0)
        indent = "\n    "
        body = indent.join(line for line in slots[name].strip().splitlines())
        return f"{match.group(1)}{indent}{body}\n    {match.group(4)}"

    target.write_text(_SLOT_RE.sub(replace, html), encoding="utf-8")
    return sha256_file(target)


# --------------------------------------------------------------------------- #
# LLM
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT = (
    "You are the web implementer of a software factory. You fill HTML slots of a static, "
    "German-language company website. Use the REQUIRED TEXTS exactly, character by character "
    "(including punctuation and the en dash). Do not invent services, customers, logos, "
    "certifications, numbers or promises. No <script>, no inline styles, no event handlers, "
    "no external URLs, no images.\n"
    "Use exactly this markup per slot:\n"
    "- nav_html (goes INSIDE the team's existing <nav>, do not output <nav> yourself): "
    "<ul><li><a href=\"#leistungen\">Leistungen</a></li><li><a href=\"#zielgruppen\">Zielgruppen</a></li>"
    "<li><a href=\"#arbeitsweise\">Arbeitsweise</a></li><li><a href=\"#kontakt\">Kontakt</a></li></ul>\n"
    "- header_html: <h1>COMPANY NAME</h1> followed by <p class=\"claim\">MAIN CLAIM</p>\n"
    "- services_html: one <article class=\"service\"><h3>SERVICE NAME</h3><p>SERVICE TEXT</p></article> "
    "per service in scope\n"
    "- audiences_html: <ul><li>TARGET GROUP</li>...</ul> with each target group as its own <li>\n"
    "- approach_html: <p>WORKING METHOD TEXT</p>\n"
    "- contact_html: <p>short neutral German sentence</p> and "
    "<a class=\"contact-link\" href=\"MAILTO TARGET\">LINK TEXT</a>\n"
    "- footer_html: <p class=\"notice\">EXERCISE NOTICE</p>\n"
    "Only fill slots listed under AVAILABLE SLOTS. If a slot needs no change, return an empty string "
    "for it (it stays as it is). If you change a slot, return its COMPLETE new content, keeping every "
    "existing item that is still required.\n"
    "Reply ONLY with one JSON object with the keys status, nav_html, header_html, services_html, "
    "audiences_html, approach_html, contact_html, footer_html, notes. "
    "If the brief is not a website brief, return status \"needs_clarification\" with the reason in notes."
)


def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, list):
        content = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return str(content)


def parse_output(text: str) -> ImplementerOutput | None:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return ImplementerOutput.model_validate(json.loads(text[start:end + 1]))
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
            "format": ImplementerOutput.model_json_schema(),
            "num_predict": max(llm.num_predict or 0, MAX_OUTPUT_TOKENS),
        })
    return llm


def build_messages(brief: str, stories: list[dict[str, Any]], slots: dict[str, str], feedback: str | None) -> list[Any]:
    parts = [
        "CUSTOMER BRIEF (contains the REQUIRED TEXTS and the scope of today):\n" + brief,
        "USER STORIES FROM PRODUCT OWNER (structured handover):\n" + json.dumps(stories, ensure_ascii=False, indent=1),
        "AVAILABLE SLOTS: " + ", ".join(slots),
        "CURRENT SLOT CONTENT:\n" + json.dumps(slots, ensure_ascii=False, indent=1),
    ]
    if feedback:
        parts.append("FEEDBACK FROM QA / HUMAN REVIEWER - fix exactly these problems:\n" + feedback)
    return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content="\n\n".join(parts))]


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def run_implementer(
    task: EngineeringTask,
    cfg: ProjectConfig,
    *,
    stories: list[dict[str, Any]] | None = None,
    feedback: str | None = None,
    llm: Any | None = None,
    trace_file: str | None = None,
) -> ImplementationResult:
    if task.assigned_role != ROLE:
        raise ValueError(f"Web implementer only accepts tasks for role {ROLE!r}")
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
        brief = (FACTORY_ROOT / task.input_files[0]).read_text(encoding="utf-8")
        ctx["tools"].append("read_product_file")
        slots_before = current_slots(read_product_file(cfg, cfg.target_file))
        slots_before = {name: slots_before[name] for name in SLOTS if name in slots_before}
        if not slots_before:
            raise ValueError(f"Target file has no AGENT markers for any of: {list(SLOTS)}")

        model = _prepare_llm(llm or get_chat_model(reasoning=False, json_mode=True))
        ctx["calls"] += 1
        response = model.invoke(build_messages(brief, stories or [], slots_before, feedback))
        ctx["input_tokens"], ctx["output_tokens"] = usage_from_message(response)

        output = parse_output(_message_text(response))
        if output is None:
            result = ImplementationResult(status="unparseable", target_file=cfg.target_file,
                                          error="LLM output is not valid ImplementerOutput JSON")
        elif output.status == "needs_clarification":
            result = ImplementationResult(status="needs_clarification", target_file=cfg.target_file, notes=output.notes)
        else:
            proposed = {name: getattr(output, f"{name}_html").strip() for name in slots_before}
            slots = {name: html for name, html in proposed.items() if html}
            unchanged = [name for name in slots_before if name not in slots]
            try:
                if not slots:
                    raise ValueError("LLM output changes no slot")
                ctx["tools"].append("write_product_slots")
                digest = write_product_slots(cfg, cfg.target_file, slots)
                result = ImplementationResult(status="success", target_file=cfg.target_file,
                                              artifact_sha256=digest, slots_written=list(slots),
                                              slots_unchanged=unchanged, notes=output.notes)
            except (ValueError, PermissionError) as exc:
                result = ImplementationResult(status="rejected", target_file=cfg.target_file, error=str(exc))

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
        append_trace({
            **record, **ctx,
            "duration_seconds": round(duration, 4),
            "estimated_cost_credits": estimate_cost_credits(
                duration_seconds=duration, input_tokens=ctx["input_tokens"],
                output_tokens=ctx["output_tokens"], calls=ctx["calls"],
            ),
            "token_usage_complete": ctx["input_tokens"] is not None and ctx["output_tokens"] is not None,
        }, trace_file)
