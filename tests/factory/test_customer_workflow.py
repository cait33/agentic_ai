"""Factory tests for Session 3: project addressing, product write guard,
structured handover PO -> implementer -> QA and the correction loop limit.

Mock LLMs only (deterministic logic). The real model run is evidenced separately
under runs/website-01/<run_id>/.
All product writes happen in a temporary product checkout (tmp_path).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from src.agents import customer_workflow as cw
from src.agents.web_implementer import ROLE, current_slots, run_implementer, write_product_slots
from src.factory.project import ProjectConfig, load_project
from src.models.task import EngineeringTask

SKELETON = """<!doctype html>
<html lang="de"><head><title>Nordwerk Industrie-Service</title></head><body>
<header><!-- AGENT:header -->
<!-- /AGENT:header --></header>
<main><!-- AGENT:services -->
<!-- /AGENT:services -->
<!-- AGENT:contact -->
<!-- /AGENT:contact --></main>
<footer><!-- AGENT:footer -->
<!-- /AGENT:footer --></footer>
</body></html>
"""

GOOD = {
    "status": "success",
    "header_html": '<h1>Nordwerk Industrie-Service</h1>\n<p class="claim">Praktische Unterstützung für Ihren technischen Betrieb.</p>',
    "services_html": '<article class="service"><h3>Wartungsplanung</h3><p>Wir strukturieren Wartungsaufgaben und dokumentieren Zuständigkeiten für kleine technische Betriebe.</p></article>',
    "contact_html": '<a class="contact-link" href="mailto:kontakt@nordwerk.example">Anfrage stellen</a>',
    "footer_html": '<p class="notice">Fiktives Unternehmen – Lehrprojekt der HAW Hamburg. Keine realen Angebote oder Kontaktaufnahme.</p>',
    "notes": "",
}
STORIES = [{"id": "US1", "description": "Als Interessent will ich den Firmennamen sehen", "acceptance_criteria": [], "backlog_value": 90}]


class FakeLLM:
    def __init__(self, *contents: str) -> None:
        self.contents = list(contents)
        self.prompts: list[str] = []

    def invoke(self, messages):
        self.prompts.append("\n".join(str(m.content) for m in messages))
        return AIMessage(content=self.contents.pop(0) if len(self.contents) > 1 else self.contents[0])


@pytest.fixture
def product(tmp_path) -> Path:
    root = tmp_path / "client-01-website"
    (root / "site").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "site" / "index.html").write_text(SKELETON, encoding="utf-8")
    (root / "README.md").write_text("product readme", encoding="utf-8")
    return root


@pytest.fixture
def cfg(product, tmp_path) -> ProjectConfig:
    config = tmp_path / "website-test.json"
    config.write_text(json.dumps({
        "project_id": "website-test", "product_repo": "example/client-01-website",
        "product_path": str(product), "task_id": "CUST-TEST", "brief": "docs/customer-01/brief.md",
        "target_file": "site/index.html", "allowed_write_paths": ["site/"],
        "product_test_paths": ["tests"], "runs_dir": "runs/website-test", "max_correction_rounds": 2,
    }), encoding="utf-8")
    return load_project(config)


def impl_task(workflow_id: str = "WF-T") -> EngineeringTask:
    return EngineeringTask(task_id="CUST-TEST", workflow_id=workflow_id, task_type="implementation",
                           description="fill site", assigned_role=ROLE, input_files=["docs/customer-01/brief.md"])


# Project addressing ------------------------------------------------------------
def test_shipped_project_config_is_valid(product) -> None:
    cfg = load_project("projects/website-01.json", product_path=product)
    assert cfg.project_id == "website-01"
    assert cfg.task_id == "CUST-001"
    assert cfg.product_path == product.resolve()
    assert cfg.max_correction_rounds <= 2


def test_missing_product_checkout_is_rejected(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="Product checkout"):
        load_project("projects/website-01.json", product_path=tmp_path / "nope")


def test_product_checkout_inside_factory_is_rejected() -> None:
    with pytest.raises(ValueError, match="separate"):
        load_project("projects/website-01.json", product_path="src")


# Write guard (only in the temporary product checkout) ----------------------------
@pytest.mark.parametrize("path", ["../escape.html", "README.md", "tests/test_site.py", "/etc/passwd"])
def test_writes_outside_allowed_area_are_rejected(cfg, product, path) -> None:
    with pytest.raises(PermissionError):
        write_product_slots(cfg, path, {"header": "<h1>x</h1>"})
    assert (product / "README.md").read_text(encoding="utf-8") == "product readme"


@pytest.mark.parametrize("content", [
    "<script>alert(1)</script>", '<nav><a href="#kontakt">x</a></nav>', '<a href="https://evil.example">x</a>',
    '<a href="javascript:alert(1)">x</a>', '<p onclick="x()">x</p>', "<!-- /AGENT:header -->",
])
def test_unsafe_slot_content_is_rejected(cfg, content) -> None:
    with pytest.raises(ValueError):
        write_product_slots(cfg, "site/index.html", {"header": content})


def test_unknown_slot_is_rejected(cfg) -> None:
    with pytest.raises(ValueError, match="Unknown slot"):
        write_product_slots(cfg, "site/index.html", {"navigation": "<nav></nav>"})


def test_slot_write_keeps_structure_and_is_repeatable(cfg, product) -> None:
    write_product_slots(cfg, "site/index.html", {"header": "<h1>A</h1>"})
    write_product_slots(cfg, "site/index.html", {"header": "<h1>B</h1>"})
    html = (product / "site" / "index.html").read_text(encoding="utf-8")
    assert current_slots(html)["header"] == "<h1>B</h1>"
    assert html.count("<!-- AGENT:header -->") == 1 and '<html lang="de">' in html


# Implementer agent -----------------------------------------------------------------
def test_implementer_writes_product_file_and_uses_po_handover(cfg, product, tmp_path) -> None:
    llm = FakeLLM(json.dumps(GOOD))
    result = run_implementer(impl_task(), cfg, stories=STORIES, llm=llm, trace_file=str(tmp_path / "t.jsonl"))
    assert result.status == "success" and result.artifact_sha256
    html = (product / "site" / "index.html").read_text(encoding="utf-8")
    assert "mailto:kontakt@nordwerk.example" in html and "<h1>Nordwerk Industrie-Service</h1>" in html
    assert "US1" in llm.prompts[0]  # PO stories reached the implementer
    trace = json.loads((tmp_path / "t.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert trace["agent"] == "web-implementer-agent" and trace["calls"] == 1
    assert trace["artifact_sha256"] == result.artifact_sha256


def test_unparseable_implementer_output_writes_nothing(cfg, product, tmp_path) -> None:
    before = (product / "site" / "index.html").read_text(encoding="utf-8")
    result = run_implementer(impl_task(), cfg, llm=FakeLLM("Hier ist Ihre Website!"), trace_file=str(tmp_path / "t.jsonl"))
    assert result.status == "unparseable"
    assert (product / "site" / "index.html").read_text(encoding="utf-8") == before


def test_implementer_output_with_external_link_is_rejected(cfg, product, tmp_path) -> None:
    bad = {**GOOD, "contact_html": '<a href="https://nordwerk.de">Anfrage stellen</a>'}
    result = run_implementer(impl_task(), cfg, llm=FakeLLM(json.dumps(bad)), trace_file=str(tmp_path / "t.jsonl"))
    assert result.status == "rejected"
    assert "nordwerk.de" not in (product / "site" / "index.html").read_text(encoding="utf-8")


# Workflow: handover, gate, loop limit ---------------------------------------------------
def fake_po(cfg, ctx):
    return {"status": "success", "summary": "s", "requirements": [], "user_stories": STORIES}


def make_impl(llm):
    def implement(cfg, ctx, stories, feedback):
        return run_implementer(impl_task(ctx.workflow_id), cfg, stories=stories, feedback=feedback,
                               llm=llm, trace_file=ctx.trace_file).model_dump()
    return implement


def make_qa(*verdicts):
    calls = []

    def qa(cfg, ctx):
        verdict = verdicts[min(len(calls), len(verdicts) - 1)]
        calls.append(verdict)
        failed = 0 if verdict == "approved" else 1
        return {"task_id": ctx.task_id, "verdict": verdict, "summary": verdict, "findings": [],
                "test_run": {"exit_code": failed, "passed": 7 - failed, "failed": failed,
                             "failed_tests": [] if not failed else ["tests/test_site.py::test_ac04_contact_link_targets_mailto"],
                             "output_tail": "E   AssertionError: Kontaktlink muss auf mailto:kontakt@nordwerk.example zeigen"}}
    qa.calls = calls
    return qa


def decider(*decisions):
    seen = []

    def decide(cfg, ctx, state):
        choice = decisions[min(len(seen), len(decisions) - 1)]
        seen.append(state)
        return cw.make_decision(cfg, ctx, state, choice, comment="Link prüfen", visually_checked=True)
    decide.seen = seen
    return decide


def run(cfg, tmp_path, llm, qa, decide):
    return cw.run_customer_workflow(cfg, "Fatih", po=fake_po, implement=make_impl(llm), qa=qa,
                                    decide=decide, factory_root=tmp_path / "factory")


def test_happy_path_human_approves_concrete_artifact(cfg, product, tmp_path) -> None:
    state, run_dir = run(cfg, tmp_path, FakeLLM(json.dumps(GOOD)), make_qa("approved"), decider("approved"))
    assert state["steps"] == ["requirements", "implementation", "qa", "human_gate"]
    review = json.loads((run_dir / "review-0.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    from src.agents.web_implementer import sha256_file
    assert review["reviewer"] == "Fatih" and review["decision"] == "approved" and review["visually_checked"]
    assert review["reviewed_artifact_sha256"] == sha256_file(product / "site" / "index.html")
    assert manifest["run_id"] == run_dir.name and manifest["human_decision"] == "approved"
    assert manifest["final_artifact_sha256"] == review["reviewed_artifact_sha256"]
    assert {"product_input_commit", "factory_input_commit", "llm_model", "criteria_product_check"} <= set(manifest)


def test_red_product_check_triggers_auto_correction_with_qa_feedback(cfg, tmp_path) -> None:
    llm = FakeLLM(json.dumps(GOOD))
    state, _ = run(cfg, tmp_path, llm, make_qa("changes_requested", "approved"), decider("approved"))
    assert state["steps"].count("implementation") == 2 and state["round"] == 1
    assert "Kontaktlink muss auf mailto" in llm.prompts[1]  # QA findings handed back to implementer
    assert state["recommendation"] == "approved"


def test_loop_limit_escalates_after_two_corrections(cfg, tmp_path) -> None:
    qa = make_qa("changes_requested")
    decide = decider("changes_requested")
    state, run_dir = run(cfg, tmp_path, FakeLLM(json.dumps(GOOD)), qa, decide)
    assert state["steps"].count("implementation") == 3  # initial + 2 corrections
    assert state["round"] == 2
    assert state["recommendation"] == "escalate_to_human"
    assert len(decide.seen) == 1  # human sees the escalated state once, no further loop
    assert json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))["correction_rounds"] == 2


def test_human_rejection_feeds_comment_back_to_implementer(cfg, tmp_path) -> None:
    llm = FakeLLM(json.dumps(GOOD))
    state, run_dir = run(cfg, tmp_path, llm, make_qa("approved"), decider("changes_requested", "approved"))
    assert [d["decision"] for d in state["decisions"]] == ["changes_requested", "approved"]
    assert "Human reviewer Fatih: Link prüfen" in llm.prompts[1]
    assert (run_dir / "review-0.json").exists() and (run_dir / "review-1.json").exists()


def test_agent_failure_goes_to_gate_and_is_not_approved(cfg, tmp_path) -> None:
    state, _ = run(cfg, tmp_path, FakeLLM("kein json"), make_qa("approved"), decider("escalate_to_human"))
    assert "qa" not in state["steps"]
    assert state["recommendation"] == "escalate_to_human"


# --------------------------------------------------------------------------- #
# Session 4: seven slots, keep-unchanged rule, release gate, AC mapping
# --------------------------------------------------------------------------- #
SKELETON_T4 = """<!doctype html>
<html lang="de"><head><title>Nordwerk Industrie-Service</title></head><body>
<header><!-- AGENT:header -->
<h1>Nordwerk Industrie-Service</h1>
<!-- /AGENT:header -->
<nav aria-label="Hauptnavigation"><!-- AGENT:nav -->
<!-- /AGENT:nav --></nav></header>
<main><section id="leistungen"><!-- AGENT:services -->
<article class="service"><h3>Wartungsplanung</h3><p>alt</p></article>
<!-- /AGENT:services --></section>
<section id="zielgruppen"><!-- AGENT:audiences -->
<!-- /AGENT:audiences --></section>
<section id="arbeitsweise"><!-- AGENT:approach -->
<!-- /AGENT:approach --></section>
<section id="kontakt"><!-- AGENT:contact -->
<a class="contact-link" href="mailto:kontakt@nordwerk.example">Anfrage stellen</a>
<!-- /AGENT:contact --></section></main>
<footer><!-- AGENT:footer -->
<!-- /AGENT:footer --></footer>
</body></html>
"""

T4_OUTPUT = {
    "status": "success",
    "nav_html": '<ul><li><a href="#leistungen">Leistungen</a></li><li><a href="#kontakt">Kontakt</a></li></ul>',
    "audiences_html": '<ul><li>Kleine Produktionsbetriebe</li><li>Technische Serviceunternehmen</li></ul>',
    "approach_html": "<p>Ein fester Ansprechpartner, ein gemeinsam vereinbarter Leistungsumfang und nachvollziehbare Ergebnisse.</p>",
    "header_html": "", "services_html": "", "contact_html": "", "footer_html": "", "notes": "",
}


@pytest.fixture
def product_t4(product) -> Path:
    (product / "site" / "index.html").write_text(SKELETON_T4, encoding="utf-8")
    return product


def test_implementer_fills_new_t4_slots(cfg, product_t4, tmp_path) -> None:
    result = run_implementer(impl_task(), cfg, llm=FakeLLM(json.dumps(T4_OUTPUT)), trace_file=str(tmp_path / "t.jsonl"))
    assert result.status == "success"
    slots = current_slots((product_t4 / "site" / "index.html").read_text(encoding="utf-8"))
    assert 'href="#kontakt"' in slots["nav"]
    assert "Technische Serviceunternehmen" in slots["audiences"]
    assert slots["approach"].startswith("<p>Ein fester Ansprechpartner")
    assert set(result.slots_written) == {"nav", "audiences", "approach"}


def test_empty_slot_value_keeps_existing_content(cfg, product_t4, tmp_path) -> None:
    run_implementer(impl_task(), cfg, llm=FakeLLM(json.dumps(T4_OUTPUT)), trace_file=str(tmp_path / "t.jsonl"))
    slots = current_slots((product_t4 / "site" / "index.html").read_text(encoding="utf-8"))
    assert slots["header"] == "<h1>Nordwerk Industrie-Service</h1>"
    assert "mailto:kontakt@nordwerk.example" in slots["contact"]
    assert "Wartungsplanung" in slots["services"]


def test_output_without_any_change_is_rejected(cfg, product_t4, tmp_path) -> None:
    empty = {k: ("success" if k == "status" else "") for k in T4_OUTPUT}
    result = run_implementer(impl_task(), cfg, llm=FakeLLM(json.dumps(empty)), trace_file=str(tmp_path / "t.jsonl"))
    assert result.status == "rejected"


def test_prompt_only_offers_slots_present_in_file(cfg, product, tmp_path) -> None:
    llm = FakeLLM(json.dumps(GOOD))
    run_implementer(impl_task(), cfg, llm=llm, trace_file=str(tmp_path / "t.jsonl"))  # 4-slot T3 skeleton
    assert "AVAILABLE SLOTS: header, services, contact, footer" in llm.prompts[0]


# Release gate ------------------------------------------------------------------------
def test_green_check_and_human_approval_is_released(cfg, tmp_path) -> None:
    state, run_dir = run(cfg, tmp_path, FakeLLM(json.dumps(GOOD)), make_qa("approved"), decider("approved"))
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["release_status"] == "released" and manifest["release_blockers"] == []


def test_red_check_is_never_released_even_if_human_types_approved(cfg, tmp_path) -> None:
    cfg_no_loop = cfg.model_copy(update={"max_correction_rounds": 0})
    state, run_dir = run(cfg_no_loop, tmp_path, FakeLLM(json.dumps(GOOD)), make_qa("changes_requested"), decider("approved"))
    review = json.loads((run_dir / "review-0.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert review["decision"] == "approved"  # what the human typed is kept ...
    assert review["release_status"] == "not_released"  # ... but the state is not released
    assert any("product check not green" in b for b in review["release_blockers"])
    assert manifest["release_status"] == "not_released"
    assert manifest["criteria_product_check"]["AC-04"] in {"no_test", "failed"}


def test_artifact_changed_after_qa_is_not_released(cfg, product, tmp_path) -> None:
    def tamper_then_approve(cfg_, ctx, state):
        index = product / "site" / "index.html"
        index.write_text(index.read_text(encoding="utf-8").replace("kontakt@nordwerk.example", "info@falsch.example"),
                         encoding="utf-8")
        return cw.make_decision(cfg_, ctx, state, "approved", visually_checked=True)
    _, run_dir = run(cfg, tmp_path, FakeLLM(json.dumps(GOOD)), make_qa("approved"), tamper_then_approve)
    review = json.loads((run_dir / "review-0.json").read_text(encoding="utf-8"))
    assert review["release_status"] == "not_released"
    assert any("hash mismatch" in b for b in review["release_blockers"])


def test_escalated_run_is_not_released(cfg, tmp_path) -> None:
    _, run_dir = run(cfg, tmp_path, FakeLLM("kein json"), make_qa("approved"), decider("escalate_to_human"))
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["release_status"] == "not_released"
    assert manifest["agent_recommendation"] == "escalate_to_human"


# AC mapping by product test names ------------------------------------------------------
def test_criteria_status_uses_product_test_names(cfg, product) -> None:
    (product / "tests" / "test_site.py").write_text(
        "def test_ac01_name(): pass\ndef test_ac04_mailto(): pass\n", encoding="utf-8")
    ac_tests = cw.product_ac_tests(cfg)
    qa = {"verdict": "changes_requested", "test_run": {"failed": 1, "errors": 0,
          "failed_tests": ["tests/test_site.py::test_ac04_mailto"]}}
    status = cw.criteria_status(qa, ac_tests)
    assert status["AC-01"] == "passed"
    assert status["AC-04"] == "failed"
    assert status["AC-06"] == "no_test"
