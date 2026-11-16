"""Customer project addressing for the Factory (Session 3, extended Session 6).

A project config (projects/<project_id>.json) tells the Factory WHICH customer
product it works on, WHERE the separate product checkout lives and WHICH task
it delivers. Agents, policies and tools stay in the Factory; product files are
only written inside the configured product checkout and allowed paths.

Override the checkout location without editing the config:
    PRODUCT_PATH=/path/to/client-02-quotation python -m src.agents.customer_workflow ...
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

FACTORY_ROOT = Path(__file__).resolve().parents[2]


class ProjectConfig(BaseModel):
    project_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    customer: str = ""
    product_repo: str = Field(min_length=1)
    product_path: Path
    task_id: str = Field(min_length=1)
    issue: str | None = None
    brief: str = Field(min_length=1, description="Factory-relative path of the customer brief")
    implementer: Literal["web_slots", "python_module"] = Field(
        default="web_slots",
        description="Generic implementer capability mode: 'web_slots' (HTML) or 'python_module' (Python code)",
    )
    target_file: str = "site/index.html"
    allowed_write_paths: list[str] = Field(default_factory=lambda: ["site/"], min_length=1)
    product_test_paths: list[str] = Field(default_factory=lambda: ["tests"], min_length=1)
    ac_test_pattern: str | None = Field(
        default=None,
        description="Optional regex with 2 groups (full_test_name, criterion_key), defaults to test_acNN_*",
    )
    review_hint: str | None = Field(
        default=None,
        description="Optional human-gate inspection command/instructions shown instead of the default web preview hint",
    )
    runs_dir: str = Field(min_length=1)
    max_correction_rounds: int = Field(default=2, ge=0, le=2)
    reuse_po_output: bool = Field(default=True, description="F-NEW: reuse PO result if brief/prompt/model unchanged")

    @field_validator("allowed_write_paths")
    @classmethod
    def _normalise_dirs(cls, value: list[str]) -> list[str]:
        out = []
        for item in value:
            item = item.strip().strip("/")
            if not item or ".." in Path(item).parts or Path(item).is_absolute():
                raise ValueError(f"Invalid allowed write path: {item!r}")
            out.append(item + "/")
        return out

    def product_file(self, relative_path: str) -> Path:
        """Resolve a product-relative path and enforce the allowed write area."""
        root = self.product_path.resolve()
        target = (root / relative_path).resolve()
        try:
            rel = target.relative_to(root).as_posix()
        except ValueError as exc:
            raise PermissionError(f"Path escapes the product checkout: {relative_path}") from exc
        if not any(rel.startswith(prefix) for prefix in self.allowed_write_paths):
            raise PermissionError(
                f"Path {relative_path!r} is outside the allowed product area {self.allowed_write_paths}"
            )
        return target


def load_project(config_path: str | Path, *, product_path: str | Path | None = None) -> ProjectConfig:
    """Load a project config. Relative product paths are resolved against the Factory root."""
    path = Path(config_path)
    if not path.is_absolute():
        path = FACTORY_ROOT / path
    data = json.loads(path.read_text(encoding="utf-8"))
    override = product_path or os.environ.get("PRODUCT_PATH")
    if override:
        data["product_path"] = str(override)
    product = Path(data["product_path"]).expanduser()
    if not product.is_absolute():
        product = (FACTORY_ROOT / product).resolve()
    data["product_path"] = product
    cfg = ProjectConfig.model_validate(data)

    if not cfg.product_path.is_dir():
        raise FileNotFoundError(f"Product checkout not found: {cfg.product_path}")
    if (cfg.product_path.resolve() == FACTORY_ROOT) or FACTORY_ROOT in cfg.product_path.resolve().parents:
        raise ValueError("Product checkout must be separate from the Factory repository")
    cfg.product_file(cfg.target_file)  # target must be inside the allowed area
    if not (FACTORY_ROOT / cfg.brief).is_file():
        raise FileNotFoundError(f"Customer brief not found: {cfg.brief}")
    return cfg


def git_state(repo: Path) -> dict[str, object]:
    """Commit + dirty flag of a checkout; None values if it is not a git repo."""
    def git(*args: str) -> str | None:
        try:
            proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return proc.stdout.strip() if proc.returncode == 0 else None

    commit = git("rev-parse", "HEAD")
    status = git("status", "--porcelain")
    return {"commit": commit, "dirty": None if status is None else bool(status)}