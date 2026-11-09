"""F-NEW (Session 5): reuse the Product Owner output when its inputs are unchanged.

Hypothesis from Session 4: the PO agent dominates agent runtime (S3 68 %, S4 53 %,
R-01 baseline 41 %) although the brief already states the content verbatim. If the PO
result is reused when brief, PO prompt and model settings are identical, agent time per
run drops without losing check quality.

Cache key = sha256 over: brief text, PO system prompt, provider, model, temperature,
cache format version. Any change to one of them is a cache miss.

Only successful PO results are cached. The cache is Factory runtime state
(`state/po-cache/<project_id>/<key>.json`, not versioned); every hit or miss is recorded
in the run trace and manifest, and the reused requirements are copied into the run
directory so each run stays self-contained evidence.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

from src.app.settings import get_settings
from src.observability.tracing import append_trace, estimate_cost_credits

CACHE_FORMAT = "po-cache-v1"


def cache_key(brief_text: str, system_prompt: str, *, provider: str, model: str, temperature: float) -> str:
    material = json.dumps({
        "format": CACHE_FORMAT, "brief": brief_text, "system_prompt": system_prompt,
        "provider": provider, "model": model, "temperature": temperature,
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def cache_dir(factory_root: Path, project_id: str) -> Path:
    return factory_root / "state" / "po-cache" / project_id


def _write_requirements(run_dir: Path, result: dict[str, Any]) -> None:
    out = run_dir / "requirements"
    out.mkdir(parents=True, exist_ok=True)
    stories = result.get("user_stories", [])
    files = {
        "requirements.json": result.get("requirements", []),
        "user_stories.json": stories,
        "acceptance_criteria.json": {s.get("id"): s.get("acceptance_criteria", []) for s in stories},
        "backlog.json": sorted(({"id": s.get("id"), "backlog_value": s.get("backlog_value")} for s in stories),
                               key=lambda s: -(s["backlog_value"] or 0)),
    }
    for name, data in files.items():
        (out / name).write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def with_po_cache(po: Callable, cfg: Any, factory_root: Path, info: dict[str, Any],
                  *, brief_root: Path | None = None) -> Callable:
    """Wrap a PO step so identical inputs reuse the stored result instead of calling the LLM."""
    from src.agents.product_owner import SYSTEM_PROMPT

    settings = get_settings()
    brief_text = ((brief_root or factory_root) / cfg.brief).read_text(encoding="utf-8")
    key = cache_key(brief_text, SYSTEM_PROMPT, provider=settings.llm_provider, model=settings.llm_model,
                    temperature=settings.llm_temperature)
    path = cache_dir(factory_root, cfg.project_id) / f"{key}.json"
    info.update({"enabled": True, "key": key, "hit": False, "cache_file": str(path.relative_to(factory_root))})

    def cached(cfg_, ctx) -> dict[str, Any]:
        if path.is_file():
            started = time.perf_counter()
            stored = json.loads(path.read_text(encoding="utf-8"))
            result = stored["result"]
            _write_requirements(Path(ctx.run_dir), result)
            info.update({"hit": True, "source_run_id": stored.get("source_run_id")})
            duration = time.perf_counter() - started
            append_trace({
                "run_id": ctx.run_id, "workflow_id": ctx.workflow_id, "task_id": ctx.task_id,
                "project_id": cfg_.project_id, "agent": "product-owner-agent", "role": "product_owner_requirements",
                "status": "success", "result_status": result.get("status"), "po_cache": "hit", "cache_key": key,
                "source_run_id": stored.get("source_run_id"), "tools": ["po_cache_read"], "calls": 0,
                "input_tokens": 0, "output_tokens": 0, "token_usage_complete": True,
                "duration_seconds": round(duration, 4),
                "estimated_cost_credits": estimate_cost_credits(duration_seconds=duration, input_tokens=0,
                                                                output_tokens=0, calls=0),
            }, ctx.trace_file)
            return result
        result = po(cfg_, ctx)
        if result.get("status") == "success":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"key": key, "source_run_id": ctx.run_id, "result": result},
                                       indent=2, ensure_ascii=False, default=str), encoding="utf-8")
            info["stored"] = True
        return result

    return cached
