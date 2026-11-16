"""Session 6: project separation Nordwerk <-> HansePack (deterministic, no LLM).

A HansePack task runs through the same customer workflow while a Nordwerk checkout
exists next to it. Agents are mocked; all checkouts are temporary git repos (tmp_path),
no real product data is touched. Runs in the standard `python -m pytest`.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from src.agents import customer_workflow as cw
from src.factory.project import FACTORY_ROOT, ProjectConfig, load_project

STUB = 'class QuoteError(ValueError):\n    pass\n\n\ndef calculate_quote(items, rule_version="HP-V1"):\n    raise NotImplementedError\n'
AGENT_CODE = 'class QuoteError(ValueError):\n    pass\n\n\ndef calculate_quote(items, rule_version="HP-V1"):\n    return {"total_cents": 0}\n'


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def make_repo(root: Path, files: dict[str, str]) -> Path:
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(content, encoding="utf-8")
    git(root, "init", "-q")
    git(root, "-c", "user.name=test", "-c", "user.email=test@example.invalid", "add", ".")
    git(root, "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-q", "-m", "init")
    return root


def snapshot(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.parts}


@pytest.fixture
def nordwerk(tmp_path) -> Path:
    return make_repo(tmp_path / "client-01-website", {
        "site/index.html": "<!doctype html><html lang='de'><title>Nordwerk Industrie-Service</title></html>\n",
        "site/en.html": "<!doctype html><html lang='en'><title>Nordwerk Industrie-Service</title></html>\n",
        "tests/test_site.py": "def test_ac01_name():\n    assert True\n",
    })


@pytest.fixture
def hansepack(tmp_path) -> Path:
    return make_repo(tmp_path / "client-02-quotation", {
        "quotation/__init__.py": "",
        "quotation/pricing.py": STUB,
        "fixtures/HansePack_Katalog.json": '{"products": []}\n',
        "tests/test_reference_cases.py": "def test_hp_ac02_q01():\n    assert True\n",
    })


@pytest.fixture
def nordwerk_cfg(nordwerk) -> ProjectConfig:
    # the real shipped Nordwerk config, only pointed at the temporary checkout
    return load_project(FACTORY_ROOT / "projects" / "website-01.json", product_path=nordwerk)


@pytest.fixture
def hansepack_cfg(hansepack) -> ProjectConfig:
    return ProjectConfig(
        project_id="hansepack-test", customer="HansePack (fiktiv)", product_repo="example/client-02-quotation",
        product_path=hansepack, task_id="HP-T6", brief="docs/customer-02/brief-t6.md",
        target_file="quotation/pricing.py", allowed_write_paths=["quotation/"],
        product_test_paths=["tests"], runs_dir="runs/hansepack-test", reuse_po_output=False,
    )


def fake_po(cfg, ctx):
    return {"status": "success", "summary": "s", "requirements": [],
            "user_stories": [{"id": "US1", "description": "HP-BOX x 50 quote", "acceptance_criteria": [], "backlog_value": 90}]}


def fake_implement(cfg, ctx, stories, feedback):
    target = cfg.product_file(cfg.target_file)  # the Factory's write guard
    target.write_text(AGENT_CODE, encoding="utf-8")
    return {"status": "success", "target_file": cfg.target_file,
            "artifact_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}


def fake_qa(cfg, ctx):
    return {"task_id": ctx.task_id, "verdict": "approved", "summary": "green", "findings": [],
            "test_run": {"exit_code": 0, "passed": 1, "failed": 0, "failed_tests": [], "output_tail": ""}}


def approve(cfg, ctx, state):
    return cw.make_decision(cfg, ctx, state, "approved", visually_checked=True)


def test_hansepack_run_changes_no_nordwerk_file(nordwerk, nordwerk_cfg, hansepack, hansepack_cfg, tmp_path) -> None:
    before, head = snapshot(nordwerk), git(nordwerk, "rev-parse", "HEAD")
    factory = tmp_path / "factory"

    state, run_dir = cw.run_customer_workflow(hansepack_cfg, "Fatih", po=fake_po, implement=fake_implement,
                                              qa=fake_qa, decide=approve, factory_root=factory)

    assert state["decisions"][-1]["release_status"] == "released"
    # Nordwerk: identical files, same commit, clean working tree
    assert snapshot(nordwerk) == before
    assert git(nordwerk, "rev-parse", "HEAD") == head
    assert git(nordwerk, "status", "--porcelain") == ""
    # HansePack: only the configured target file changed
    assert git(hansepack, "status", "--porcelain").split() == ["M", "quotation/pricing.py"]
    # evidence only in the HansePack runs area, nothing under the Nordwerk runs area
    assert run_dir.parent == factory / "runs" / "hansepack-test"
    assert not (factory / nordwerk_cfg.runs_dir).exists()
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["project_id"] == "hansepack-test" and manifest["product_path"] == str(hansepack)


@pytest.mark.parametrize("path", [
    "site/index.html",                       # Nordwerk target name inside the HansePack checkout
    "../client-01-website/site/index.html",  # escape into the Nordwerk checkout
    "tests/test_reference_cases.py",         # product checks are not agent-writable
    "fixtures/HansePack_Katalog.json",       # customer fixtures are not agent-writable
])
def test_hansepack_config_cannot_write_outside_its_area(hansepack_cfg, path) -> None:
    with pytest.raises(PermissionError):
        hansepack_cfg.product_file(path)


def test_hansepack_config_cannot_write_absolute_nordwerk_path(hansepack_cfg, nordwerk) -> None:
    with pytest.raises(PermissionError):
        hansepack_cfg.product_file(str(nordwerk / "site" / "index.html"))


def test_shipped_project_configs_are_separated() -> None:
    configs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((FACTORY_ROOT / "projects").glob("*.json"))]
    runs_dirs = [c["runs_dir"] for c in configs]
    assert len(runs_dirs) == len(set(runs_dirs)), "every project needs its own runs_dir"
    for c in configs:
        if c["project_id"].startswith("hansepack"):
            assert not c["runs_dir"].startswith("runs/website"), c["project_id"]
            assert "client-01-website" not in c["product_path"], c["project_id"]
            assert not any(p.strip("/") == "site" for p in c["allowed_write_paths"]), c["project_id"]
