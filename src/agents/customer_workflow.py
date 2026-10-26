"""Customer delivery workflow (Session 3): Factory -> separate product checkout.

    PO agent ──stories──▶ Web implementer ──file + hash──▶ QA agent (product check) ──▶ Human gate
                               ▲                                │ red                     │ changes_requested
                               └──────── feedback ◀─────────────┴─────────────────────────┘
                                       at most cfg.max_correction_rounds (<= 2), then escalate_to_human

* Hand-over only via LangGraph state (structured dicts), one task_id + workflow_id.
* Implementer may only write inside cfg.allowed_write_paths of the product checkout.
* QA runs the product's own tests inside the product checkout.
* A human decides about a concrete artifact hash; an agent "approved" is a recommendation only.
* Evidence per run: runs/<project>/<run_id>/ (manifest.json, trace.jsonl, requirements/,
  implementation-N.json, qa-round-N.json, review-N.json). Nothing shared is overwritten.

Run:
    python -m src.agents.customer_workflow --project projects/website-01.json --reviewer Fatih
After reviewing and committing the product change:
    python -m src.agents.customer_workflow --record-result RUN_ID --project projects/website-01.json
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from src.app.settings import get_settings
from src.factory.project import FACTORY_ROOT, ProjectConfig, git_state, load_project
from src.models.task import EngineeringTask
from src.observability.tracing import append_trace

Decision = Literal["approved", "changes_requested", "escalate_to_human"]
AC_TESTS = {"AC-01": "ac01", "AC-02": "ac02", "AC-04": "ac04"}


class RunContext(BaseModel):
    run_id: str
    workflow_id: str
    task_id: str
    reviewer: str = Field(min_length=1)
    run_dir: str
    trace_file: str


class HumanDecision(BaseModel):
    task_id: str
    workflow_id: str
    run_id: str
    round: int
    reviewer: str = Field(min_length=1)
    decision: Decision
    comment: str = ""
    visually_checked: bool = False
    reviewed_file: str
    reviewed_artifact_sha256: str | None
    tested_source_commit: str | None
    agent_recommendation: Decision
    identity_assurance: str = "self_declared_course_review"
    decided_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CustomerState(TypedDict, total=False):
    requirements: dict[str, Any]
    implementation: dict[str, Any]
    qa: dict[str, Any]
    round: int
    feedback: str | None
    history: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    recommendation: str
    errors: list[str]
    steps: list[str]


PoFn = Callable[[ProjectConfig, RunContext], dict[str, Any]]
ImplFn = Callable[[ProjectConfig, RunContext, list[dict[str, Any]], str | None], dict[str, Any]]
QaFn = Callable[[ProjectConfig, RunContext], dict[str, Any]]
DecideFn = Callable[[ProjectConfig, RunContext, dict[str, Any]], HumanDecision]


# --------------------------------------------------------------------------- #
# Default steps (real agents)
# --------------------------------------------------------------------------- #
def po_step(cfg: ProjectConfig, ctx: RunContext) -> dict[str, Any]:
    from src.agents.product_owner import run_po_task

    task = EngineeringTask(task_id=ctx.task_id, workflow_id=ctx.workflow_id, task_type="requirements",
                           description=f"Derive user stories for customer task {cfg.task_id} ({cfg.customer})",
                           assigned_role="product_owner_requirements", input_files=[cfg.brief],
                           metadata={"project_id": cfg.project_id})
    return run_po_task(task, trace_file=ctx.trace_file, output_dir=Path(ctx.run_dir) / "requirements").model_dump()


def implement_step(cfg: ProjectConfig, ctx: RunContext, stories: list[dict[str, Any]], feedback: str | None) -> dict[str, Any]:
    from src.agents.web_implementer import ROLE, run_implementer

    task = EngineeringTask(task_id=ctx.task_id, workflow_id=ctx.workflow_id, task_type="implementation",
                           description=f"Fill {cfg.target_file} for {cfg.task_id}", assigned_role=ROLE,
                           input_files=[cfg.brief], metadata={"project_id": cfg.project_id})
    return run_implementer(task, cfg, stories=stories, feedback=feedback, trace_file=ctx.trace_file).model_dump()


def qa_step(cfg: ProjectConfig, ctx: RunContext) -> dict[str, Any]:
    from src.agents.qa_agent import run_pytest, run_qa_agent
    from src.llm.factory import get_chat_model

    task = EngineeringTask(task_id=ctx.task_id, workflow_id=ctx.workflow_id, task_type="product_check",
                           description=f"Product check for {cfg.task_id} in {cfg.product_repo}",
                           assigned_role="qa_test_engineer", input_files=cfg.product_test_paths,
                           metadata={"project_id": cfg.project_id})
    report = run_qa_agent(
        task,
        llm=get_chat_model(reasoning=False, json_mode=True),
        pytest_runner=lambda paths: run_pytest(paths, repo_root=cfg.product_path),
        trace_file=ctx.trace_file,
    )
    return report.model_dump()


def cli_decision(cfg: ProjectConfig, ctx: RunContext, state: dict[str, Any]) -> HumanDecision:
    impl, qa = state.get("implementation", {}), state.get("qa", {})
    print("\n" + "=" * 60 + "\nHUMAN GATE")
    print(f"Task {ctx.task_id} | run {ctx.run_id} | round {state.get('round', 0)}")
    print(f"Agent recommendation: {state['recommendation']}")
    if state.get("errors"):
        print(f"Errors: {state['errors']}")
    print(f"Implementation: {impl.get('status')}  file: {cfg.product_path / cfg.target_file}")
    print(f"Artifact sha256: {impl.get('artifact_sha256')}")
    if qa:
        run = qa.get("test_run", {})
        print(f"QA: {qa.get('verdict')} - {run.get('passed')} passed / {run.get('failed')} failed - {qa.get('summary')}")
    print(f"\nBitte im Browser prüfen:  python3 -m http.server 8000 --directory {cfg.product_path / 'site'}")
    print("-> http://localhost:8000  (Inhalte N-01/N-02/N-03, Link 'Anfrage stellen', Übungshinweis)")
    checked = input("Inhalte und Kontaktlink im Browser geprüft? [j/n]: ").strip().lower() == "j"
    choice = ""
    while choice not in {"approved", "changes_requested", "escalate_to_human"}:
        choice = input("Decision [approved / changes_requested / escalate_to_human]: ").strip()
    comment = ""
    while choice != "approved" and not comment:
        comment = input("Begründung (Pflicht bei Ablehnung/Eskalation): ").strip()
    if choice == "approved":
        comment = input("Kommentar (optional): ").strip()
    return make_decision(cfg, ctx, state, choice, comment, visually_checked=checked)


def make_decision(cfg: ProjectConfig, ctx: RunContext, state: dict[str, Any], decision: str,
                  comment: str = "", *, visually_checked: bool = False) -> HumanDecision:
    return HumanDecision(
        task_id=ctx.task_id, workflow_id=ctx.workflow_id, run_id=ctx.run_id,
        round=state.get("round", 0), reviewer=ctx.reviewer, decision=decision, comment=comment,
        visually_checked=visually_checked, reviewed_file=cfg.target_file,
        reviewed_artifact_sha256=state.get("implementation", {}).get("artifact_sha256"),
        tested_source_commit=state.get("_input_commit"), agent_recommendation=state["recommendation"],
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def qa_feedback(qa: dict[str, Any]) -> str:
    run = qa.get("test_run", {})
    lines = [f"Product check: {qa.get('verdict')} ({run.get('failed', 0)} failed). {qa.get('summary', '')}"]
    lines += [f"- failed: {t}" for t in run.get("failed_tests", [])]
    lines += [f"- {f.get('severity')}: {f.get('test')}: {f.get('description')}" for f in qa.get("findings", [])]
    tail = run.get("output_tail", "")
    asserts = [l.strip() for l in tail.splitlines() if l.strip().startswith(("E ", "AssertionError"))]
    lines += [f"  {a}" for a in asserts[:12]]
    return "\n".join(lines)


def criteria_status(qa: dict[str, Any] | None) -> dict[str, str]:
    """Map AC ids to the product check result (automated evidence only, not acceptance)."""
    if not qa:
        return {ac: "not_checked" for ac in AC_TESTS}
    failed = " ".join(qa.get("test_run", {}).get("failed_tests", []))
    green = qa.get("verdict") == "approved"
    return {ac: ("failed" if key in failed else "passed" if green or qa.get("test_run", {}).get("passed") else "unknown")
            for ac, key in AC_TESTS.items()}


def recommend(state: CustomerState, max_rounds: int) -> Decision:
    if state.get("errors"):
        return "escalate_to_human"
    if state.get("requirements", {}).get("status") in ("needs_clarification", "unparseable"):
        return "escalate_to_human"
    if state.get("implementation", {}).get("status") != "success":
        return "escalate_to_human"
    verdict = state.get("qa", {}).get("verdict")
    if verdict == "approved":
        return "approved"
    if verdict == "escalate_to_human" or state.get("round", 0) >= max_rounds:
        return "escalate_to_human"
    return "changes_requested"


def _dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Graph
# --------------------------------------------------------------------------- #
def build_graph(cfg: ProjectConfig, ctx: RunContext, *, po: PoFn, implement: ImplFn, qa: QaFn, decide: DecideFn,
                input_commit: str | None):
    run_dir = Path(ctx.run_dir)
    max_rounds = cfg.max_correction_rounds

    def guarded(name: str, state: CustomerState, fn: Callable[[], dict[str, Any]]) -> CustomerState:
        steps = [*state.get("steps", []), name]
        try:
            return {name: fn(), "steps": steps}
        except Exception as exc:  # agent failure -> human gate, never crash
            return {"errors": [*state.get("errors", []), f"{name}: {type(exc).__name__}: {exc}"], "steps": steps}

    def requirements(state: CustomerState) -> CustomerState:
        return guarded("requirements", state, lambda: po(cfg, ctx))

    def implementation(state: CustomerState) -> CustomerState:
        stories = state.get("requirements", {}).get("user_stories", [])
        out = guarded("implementation", state, lambda: implement(cfg, ctx, stories, state.get("feedback")))
        if "implementation" in out:
            _dump(run_dir / f"implementation-{state.get('round', 0)}.json", out["implementation"])
        return out

    def quality(state: CustomerState) -> CustomerState:
        out = guarded("qa", state, lambda: qa(cfg, ctx))
        if "qa" in out:
            _dump(run_dir / f"qa-round-{state.get('round', 0)}.json", out["qa"])
            out["history"] = [*state.get("history", []), {
                "round": state.get("round", 0),
                "artifact_sha256": state.get("implementation", {}).get("artifact_sha256"),
                "qa_verdict": out["qa"].get("verdict"),
                "tests_passed": out["qa"].get("test_run", {}).get("passed"),
                "tests_failed": out["qa"].get("test_run", {}).get("failed"),
            }]
        return out

    def correct_after_qa(state: CustomerState) -> CustomerState:
        return {"round": state.get("round", 0) + 1, "feedback": qa_feedback(state["qa"]),
                "steps": [*state.get("steps", []), "auto_correction"]}

    def human_gate(state: CustomerState) -> CustomerState:
        rec = recommend(state, max_rounds)
        decision = decide(cfg, ctx, {**state, "recommendation": rec, "_input_commit": input_commit})
        record = decision.model_dump()
        _dump(run_dir / f"review-{state.get('round', 0)}.json", record)
        update: CustomerState = {"recommendation": rec, "decisions": [*state.get("decisions", []), record],
                                 "steps": [*state.get("steps", []), "human_gate"]}
        if decision.decision == "changes_requested" and state.get("round", 0) < max_rounds:
            update["round"] = state.get("round", 0) + 1
            update["feedback"] = f"Human reviewer {decision.reviewer}: {decision.comment}"
        return update

    def after(node_next: str):
        return lambda s: "human_gate" if s.get("errors") else node_next

    def after_implementation(state: CustomerState) -> str:
        if state.get("errors") or state.get("implementation", {}).get("status") != "success":
            return "human_gate"
        return "qa"

    def after_qa(state: CustomerState) -> str:
        if state.get("errors"):
            return "human_gate"
        if state["qa"].get("verdict") == "changes_requested" and state.get("round", 0) < max_rounds:
            return "correct_after_qa"
        return "human_gate"

    def after_gate(state: CustomerState) -> str:
        last = state["decisions"][-1]
        if last["decision"] == "changes_requested" and last["round"] < state.get("round", 0):
            return "implementation"
        return END

    g = StateGraph(CustomerState)
    g.add_node("requirements", requirements)
    g.add_node("implementation", implementation)
    g.add_node("qa", quality)
    g.add_node("correct_after_qa", correct_after_qa)
    g.add_node("human_gate", human_gate)
    g.add_edge(START, "requirements")
    g.add_conditional_edges("requirements", after("implementation"), ["implementation", "human_gate"])
    g.add_conditional_edges("implementation", after_implementation, ["qa", "human_gate"])
    g.add_conditional_edges("qa", after_qa, ["correct_after_qa", "human_gate"])
    g.add_edge("correct_after_qa", "implementation")
    g.add_conditional_edges("human_gate", after_gate, ["implementation", END])
    return g.compile()


def run_customer_workflow(
    cfg: ProjectConfig,
    reviewer: str,
    *,
    po: PoFn = po_step,
    implement: ImplFn = implement_step,
    qa: QaFn = qa_step,
    decide: DecideFn = cli_decision,
    factory_root: Path = FACTORY_ROOT,
) -> tuple[CustomerState, Path]:
    run_id = str(uuid.uuid4())
    run_dir = factory_root / cfg.runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    ctx = RunContext(run_id=run_id, workflow_id=run_id, task_id=cfg.task_id, reviewer=reviewer,
                     run_dir=str(run_dir), trace_file=str(run_dir / "trace.jsonl"))
    settings = get_settings()

    # Fix input commits BEFORE any agent touches the product checkout.
    factory_git, product_git = git_state(factory_root), git_state(cfg.product_path)
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.perf_counter()

    graph = build_graph(cfg, ctx, po=po, implement=implement, qa=qa, decide=decide,
                        input_commit=product_git["commit"])
    state: CustomerState = graph.invoke({"round": 0, "errors": [], "steps": [], "history": [], "decisions": []},
                                        {"recursion_limit": 40})
    duration = round(time.perf_counter() - started, 4)

    final = state["decisions"][-1] if state.get("decisions") else {}
    trace_lines = [json.loads(l) for l in Path(ctx.trace_file).read_text(encoding="utf-8").splitlines()] \
        if Path(ctx.trace_file).exists() else []
    agent_records = [r for r in trace_lines if r.get("agent") != "customer-workflow"]
    manifest = {
        "run_id": run_id,
        "workflow_id": ctx.workflow_id,
        "project_id": cfg.project_id,
        "customer": cfg.customer,
        "customer_task_id": cfg.task_id,
        "issue": cfg.issue,
        "product_repo": cfg.product_repo,
        "product_path": str(cfg.product_path),
        "factory_input_commit": factory_git["commit"],
        "factory_dirty_at_start": factory_git["dirty"],
        "product_input_commit": product_git["commit"],
        "product_dirty_at_start": product_git["dirty"],
        "product_result_commit": None,  # filled by --record-result after the human commit
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "llm_settings": {"temperature": settings.llm_temperature, "json_mode": True, "reasoning": False,
                         "max_output_tokens_implementer": 2048},
        "agents": ["product-owner-agent", "web-implementer-agent", "qa-agent"],
        "steps": state.get("steps", []),
        "correction_rounds": state.get("round", 0),
        "max_correction_rounds": cfg.max_correction_rounds,
        "history": state.get("history", []),
        "errors": state.get("errors", []),
        "target_file": cfg.target_file,
        "final_artifact_sha256": state.get("implementation", {}).get("artifact_sha256"),
        "criteria_product_check": criteria_status(state.get("qa")),
        "agent_recommendation": state.get("recommendation"),
        "human_decision": final.get("decision"),
        "reviewer": final.get("reviewer"),
        "decided_at_utc": final.get("decided_at_utc"),
        "agent_calls": sum(r.get("calls", 0) or 0 for r in agent_records),
        "agent_credits": round(sum(r.get("estimated_cost_credits", 0) or 0 for r in agent_records), 4),
        "token_usage_complete": all(r.get("token_usage_complete") for r in agent_records if r.get("calls")),
        "started_at_utc": started_at,
        "duration_seconds_incl_human_wait": duration,
        "trace_file": "trace.jsonl",
        "manual_interventions": [],
    }
    _dump(run_dir / "manifest.json", manifest)
    append_trace({"run_id": run_id, "workflow_id": run_id, "task_id": cfg.task_id, "project_id": cfg.project_id,
                  "agent": "customer-workflow", "role": "agent_engineer", "calls": 0,
                  "status": "error" if state.get("errors") else "success", "steps": state.get("steps", []),
                  "recommendation": state.get("recommendation"), "human_decision": final.get("decision"),
                  "duration_seconds": duration}, ctx.trace_file)
    return state, run_dir


def record_result(cfg: ProjectConfig, run_id: str, *, note: str | None = None,
                  factory_root: Path = FACTORY_ROOT) -> dict[str, Any]:
    """After the human committed the product change: link the result commit to the run."""
    path = factory_root / cfg.runs_dir / run_id / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    product = git_state(cfg.product_path)
    manifest["product_result_commit"] = product["commit"]
    manifest["product_dirty_at_record"] = product["dirty"]
    if note:
        manifest["manual_interventions"].append({"at_utc": datetime.now(timezone.utc).isoformat(), "note": note})
    _dump(path, manifest)
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description="Customer workflow: PO -> implementer -> QA -> human gate")
    p.add_argument("--project", default="projects/website-01.json")
    p.add_argument("--product-path", default=None, help="Override the product checkout location")
    p.add_argument("--reviewer", help="Accountable human for the gate")
    p.add_argument("--record-result", metavar="RUN_ID", help="Link the product result commit to a finished run")
    p.add_argument("--note", default=None, help="Manual intervention note (with --record-result)")
    a = p.parse_args()
    cfg = load_project(a.project, product_path=a.product_path)
    if a.record_result:
        print(json.dumps(record_result(cfg, a.record_result, note=a.note), indent=2, ensure_ascii=False))
        return
    if not a.reviewer:
        p.error("--reviewer is required")
    state, run_dir = run_customer_workflow(cfg, a.reviewer)
    print(json.dumps({k: state.get(k) for k in ("steps", "errors", "recommendation", "round")}, indent=2))
    print(f"Evidence: {run_dir}")


if __name__ == "__main__":
    main()
