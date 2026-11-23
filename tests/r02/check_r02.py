"""R-02 evaluation runner (same for the S7 baseline and the S8 repeat).

Runs, against an isolated R-02 product copy:
  1. git state of the copy (commit, branch, dirty, files changed since Q-BASE)
  2. the product's own business tests      (R02-8: all existing business tests still pass)
  3. the independent acceptance checks     (experiments/r02/test_r02_acceptance.py, R02-1 … R02-7)
  4. optional: agent figures of a Factory run (calls, tokens, time, credits) from runs/quotation-02-r02/<run_id>/
and writes one plain-text report (raw output included) for evidence/.

Usage (from the Factory root; works on Windows, macOS and Linux):
    python experiments/r02/check_r02.py --product ../hp-r02-run1 --label agent-output \
        --run-id <RUN_ID> --out evidence/session-07/r02/run1-agent-output.txt
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

FACTORY = Path(__file__).resolve().parents[2]
ACCEPTANCE = Path(__file__).resolve().parent / "test_r02_acceptance.py"
Q_BASE_COMMIT = "3ef83876d663b4ffb7222655c54fe7e4271973c2"
RUNS_DIR = FACTORY / "runs" / "quotation-02-r02"


def sh(args: list[str], cwd: Path, env: dict | None = None, timeout: int = 600) -> tuple[int, str]:
    proc = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, (proc.stdout + proc.stderr)


def git(product: Path, *args: str) -> str:
    return sh(["git", *args], product)[1].strip()


def counts(output: str) -> dict[str, int]:
    tail = output.strip().splitlines()[-1] if output.strip() else ""
    return {k: int(n) for n, k in re.findall(r"(\d+) (passed|failed|skipped|error|errors)", tail)}


def agent_figures(run_id: str) -> tuple[dict, list[str]]:
    run_dir = RUNS_DIR / run_id
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    trace = [json.loads(l) for l in (run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    agents = [r for r in trace if r.get("agent") != "customer-workflow"]
    agent_seconds = round(sum(r.get("duration_seconds") or 0 for r in agents), 1)
    rows = []
    day = manifest["started_at_utc"][:10]
    for r in agents:
        tokens = f"{r.get('input_tokens')} in / {r.get('output_tokens')} out tokens" if r.get("calls") else "0 LLM calls"
        detail = r.get("verdict") or r.get("result_status") or r.get("status")
        rows.append(f'{day},R-02,agent,{r.get("agent")},{r.get("duration_seconds")},seconds,'
                    f'{r.get("estimated_cost_credits")},"[agent] R-02 baseline run {run_id[:8]}: {detail} ({tokens})"')
    summary = {
        "run_id": run_id,
        "factory_input_commit": manifest.get("factory_input_commit"),
        "factory_dirty_at_start": manifest.get("factory_dirty_at_start"),
        "product_input_commit": manifest.get("product_input_commit"),
        "product_dirty_at_start": manifest.get("product_dirty_at_start"),
        "product_result_commit": manifest.get("product_result_commit"),
        "llm": f'{manifest.get("llm_provider")} {manifest.get("llm_model")} {manifest.get("llm_settings")}',
        "po_cache": manifest.get("po_cache"),
        "steps": manifest.get("steps"),
        "history": manifest.get("history"),
        "correction_rounds": manifest.get("correction_rounds"),
        "release_status": manifest.get("release_status"),
        "release_blockers": manifest.get("release_blockers"),
        "human_decision": manifest.get("human_decision"),
        "reviewer": manifest.get("reviewer"),
        "decided_at_utc": manifest.get("decided_at_utc"),
        "agent_calls": manifest.get("agent_calls"),
        "agent_credits": manifest.get("agent_credits"),
        "agent_seconds": agent_seconds,
        "duration_seconds_incl_human_wait": manifest.get("duration_seconds_incl_human_wait"),
        "human_wait_seconds_approx": round((manifest.get("duration_seconds_incl_human_wait") or 0) - agent_seconds, 1),
    }
    return summary, rows


def main() -> int:
    p = argparse.ArgumentParser(description="R-02 evaluation (identical for F-BASE and F-NEW)")
    p.add_argument("--product", required=True, help="isolated R-02 product copy")
    p.add_argument("--label", required=True, help="e.g. agent-output | after-rework")
    p.add_argument("--run-id", default=None, help="Factory run id (adds agent figures + usage.csv rows)")
    p.add_argument("--out", required=True, help="report file, e.g. evidence/session-07/r02/run1-agent-output.txt")
    a = p.parse_args()

    product = Path(a.product).expanduser().resolve()
    out = Path(a.out)
    out = out if out.is_absolute() else FACTORY / out
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"# R-02 evaluation – {a.label}", f"checked_at_utc: {datetime.now(timezone.utc).isoformat()}",
             f"python: {sys.version.split()[0]}", f"factory_commit: {git(FACTORY, 'rev-parse', 'HEAD')}",
             f"factory_dirty: {bool(git(FACTORY, 'status', '--porcelain'))}",
             f"product_path: {product}", f"product_commit: {git(product, 'rev-parse', 'HEAD')}",
             f"product_branch: {git(product, 'branch', '--show-current')}",
             f"q_base: {Q_BASE_COMMIT}",
             f"product_git_status_porcelain: {git(product, 'status', '--porcelain') or '(clean)'}",
             "files changed since Q-BASE (committed + working tree):",
             git(product, "diff", "--stat", Q_BASE_COMMIT) or "(none)", ""]

    rc_prod, out_prod = sh([sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"], product)
    env = {**os.environ, "R02_PRODUCT_PATH": str(product)}
    rc_acc, out_acc = sh([sys.executable, "-m", "pytest", str(ACCEPTANCE), "-q", "-rA", "-p", "no:cacheprovider"],
                         FACTORY, env=env)

    crit: dict[str, str] = {}
    for cid in range(1, 8):
        tag = f"test_r02_{cid}_"
        passed = [l for l in out_acc.splitlines() if l.startswith("PASSED") and tag in l]
        failed = [l for l in out_acc.splitlines() if l.startswith(("FAILED", "ERROR")) and tag in l]
        crit[f"R02-{cid}"] = "failed" if failed else ("passed" if passed else "not_run")
    crit["R02-8"] = "passed" if rc_prod == 0 else "failed"

    summary = {
        "label": a.label,
        "product_tests": {"returncode": rc_prod, **counts(out_prod)},
        "acceptance_tests": {"returncode": rc_acc, **counts(out_acc)},
        "criteria": crit,
        "r02_complete": all(v == "passed" for v in crit.values()),
    }
    usage_rows: list[str] = []
    if a.run_id:
        summary["factory_run"], usage_rows = agent_figures(a.run_id)

    lines += ["## Summary", json.dumps(summary, indent=2, ensure_ascii=False), ""]
    if usage_rows:
        lines += ["## usage.csv rows (agent records of the run, paste into costs/usage.csv)", *usage_rows, ""]
    lines += ["## Product tests (python -m pytest tests -q)", out_prod.strip()[-6000:], "",
              "## R-02 acceptance checks (experiments/r02/test_r02_acceptance.py)", out_acc.strip()[-12000:], ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if usage_rows:
        print("\n".join(usage_rows))
    print(f"\nReport: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())