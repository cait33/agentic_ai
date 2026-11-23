"""Session 7, task 3: the Factory gate holds back a business fault and releases the corrected state.

The product checkout is a temporary copy with the UNCHANGED customer fixtures (from task sheets/session-06-08)
and a product check that loads the customer's expected values. The QA agent runs the REAL pytest tool in that
checkout; only the LLM calls (implementer, QA failure assessment) are mocked. The injected fault is the one of
the task sheet: the 5 % discount starts above 50 instead of from 50 -> Q03 total 13700 instead of 13075.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from src.agents import customer_workflow as cw
from src.agents.qa_agent import run_pytest, run_qa_agent
from src.factory.project import FACTORY_ROOT, ProjectConfig
from src.models.task import EngineeringTask

CUSTOMER_FILES = FACTORY_ROOT / "task sheets" / "session-06-08"
REFERENCE = json.loads((CUSTOMER_FILES / "HansePack_Referenzfaelle.json").read_text(encoding="utf-8"))

PRICING = '''from quotation.catalog import load_catalog


class QuoteError(ValueError):
    pass


def _rate(quantity):
    return 10 if quantity >= 100 else 5 if {five_percent_condition} else 0


def calculate_quote(items, rule_version="HP-V1"):
    if not items:
        raise QuoteError("at least one line is required")
    prices = load_catalog()
    lines = []
    for item in items:
        quantity = item["quantity"]
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 10000:
            raise QuoteError("quantity must be a whole number between 1 and 10000")
        list_amount = quantity * prices[item["sku"]]
        rate = _rate(quantity)
        discount = (list_amount * rate + 50) // 100
        lines.append({{"sku": item["sku"], "quantity": quantity, "unit_price_cents": prices[item["sku"]],
                      "list_amount_cents": list_amount, "discount_percent": rate,
                      "discount_cents": discount, "net_cents": list_amount - discount}})
    goods = sum(line["net_cents"] for line in lines)
    shipping = 1200 if goods < 50000 else 0
    return {{"currency": "EUR", "rule_version": rule_version, "lines": lines,
            "goods_net_cents": goods, "shipping_cents": shipping, "total_cents": goods + shipping}}
'''
CORRECT = PRICING.format(five_percent_condition="quantity >= 50")
FAULTY = PRICING.format(five_percent_condition="quantity > 50")  # injected fault: 5 % only ABOVE 50

PRODUCT_CHECK = '''import json
from pathlib import Path

import pytest

from quotation.pricing import calculate_quote

REF = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "HansePack_Referenzfaelle.json").read_text(encoding="utf-8"))
CASES = {c["id"]: c for c in REF["valid_cases"]}


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_hp_ac03_totals_match_customer_values(case_id):
    quote = calculate_quote(CASES[case_id]["input"]["items"])
    expected = CASES[case_id]["expected"]["HP-V1"]
    assert {k: quote[k] for k in expected} == expected
'''


class FakeLLM:
    """Stands in for the QA agent's failure assessment (the verdict itself comes from pytest)."""

    def invoke(self, messages):
        return AIMessage(content=json.dumps({"summary": "Customer reference values do not match.", "findings": [
            {"severity": "high", "test": "test_hp_ac03_totals_match_customer_values", "description": "wrong total"}]}))


@pytest.fixture
def product(tmp_path) -> Path:
    root = tmp_path / "client-02-quotation"
    (root / "quotation").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "fixtures").mkdir()
    for name in ("HansePack_Katalog.json", "HansePack_Referenzfaelle.json"):
        shutil.copyfile(CUSTOMER_FILES / name, root / "fixtures" / name)  # unchanged customer files
    (root / "quotation" / "__init__.py").write_text("", encoding="utf-8")
    (root / "quotation" / "catalog.py").write_text(
        "import json\nfrom pathlib import Path\n\n\ndef load_catalog():\n"
        "    data = json.loads((Path(__file__).resolve().parents[1] / 'fixtures' / 'HansePack_Katalog.json')"
        ".read_text(encoding='utf-8'))\n"
        "    return {p['sku']: int(p['unit_price_cents']) for p in data['products']}\n", encoding="utf-8")
    (root / "quotation" / "pricing.py").write_text("def calculate_quote(items, rule_version='HP-V1'):\n"
                                                    "    raise NotImplementedError\n", encoding="utf-8")
    (root / "tests" / "test_customer_values.py").write_text(PRODUCT_CHECK, encoding="utf-8")
    (root / "pytest.ini").write_text("[pytest]\npythonpath = .\ntestpaths = tests\n", encoding="utf-8")
    return root


@pytest.fixture
def cfg(product) -> ProjectConfig:
    return ProjectConfig(
        project_id="quotation-gate-test", product_repo="example/client-02-quotation", product_path=product,
        task_id="HP-T7-FAULT", brief="docs/customer-02/brief-t6.md", implementer="python_module",
        target_file="quotation/pricing.py", allowed_write_paths=["quotation/"], product_test_paths=["tests"],
        ac_test_pattern=r"def (test_(hp_ac\d{2})\w*)", runs_dir="runs/quotation-gate-test",
        reuse_po_output=False, max_correction_rounds=2,
    )


def po(cfg_, ctx):
    return {"status": "success", "summary": "s", "requirements": [],
            "user_stories": [{"id": "US1", "description": "Quote with quantity tiers", "acceptance_criteria": [],
                              "backlog_value": 90}]}


def implementer(*versions: str):
    """Mocked implementer: writes the given code versions round by round (last one repeats)."""
    seen: list[str | None] = []

    def implement(cfg_, ctx, stories, feedback):
        seen.append(feedback)
        code = versions[min(len(seen) - 1, len(versions) - 1)]
        target = cfg_.product_file(cfg_.target_file)
        target.write_text(code, encoding="utf-8")
        return {"status": "success", "target_file": cfg_.target_file,
                "artifact_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}

    implement.feedback = seen
    return implement


def qa(cfg_, ctx):
    """Real QA agent + real pytest tool in the product checkout; only the LLM assessment is mocked."""
    task = EngineeringTask(task_id=ctx.task_id, workflow_id=ctx.workflow_id, task_type="product_check",
                           description="Product check", assigned_role="qa_test_engineer",
                           input_files=cfg_.product_test_paths)
    return run_qa_agent(task, llm=FakeLLM(), pytest_runner=lambda paths: run_pytest(paths, repo_root=cfg_.product_path),
                        trace_file=ctx.trace_file).model_dump()


def human(decision: str):
    return lambda cfg_, ctx, state: cw.make_decision(cfg_, ctx, state, decision, "gate test", visually_checked=True)


def run(cfg, implement, decision, tmp_path):
    state, run_dir = cw.run_customer_workflow(cfg, "Francisco", po=po, implement=implement, qa=qa,
                                              decide=human(decision), factory_root=tmp_path / "factory")
    return state, json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))


def test_customer_reference_values_are_the_ones_of_the_task_sheet() -> None:
    q03 = {c["id"]: c for c in REFERENCE["valid_cases"]}["Q03"]
    assert q03["input"]["items"] == [{"sku": "HP-BOX", "quantity": 50}]
    assert q03["expected"]["HP-V1"]["total_cents"] == 13075


def test_correct_candidate_passes_and_is_released(cfg, tmp_path) -> None:
    state, manifest = run(cfg, implementer(CORRECT), "approved", tmp_path)
    assert manifest["history"][-1]["tests_failed"] == 0
    assert manifest["correction_rounds"] == 0
    assert manifest["release_status"] == "released" and manifest["release_blockers"] == []


def test_injected_discount_fault_is_held_back_even_if_a_human_approves(cfg, tmp_path) -> None:
    state, manifest = run(cfg, implementer(FAULTY), "approved", tmp_path)
    # unchanged customer checks fail in every round -> correction rounds up to the limit
    assert [h["qa_verdict"] for h in manifest["history"]] == ["changes_requested"] * 3
    assert manifest["correction_rounds"] == cfg.max_correction_rounds
    assert manifest["agent_recommendation"] == "escalate_to_human"
    # the gate keeps the faulty state back although the human clicked "approved"
    assert manifest["release_status"] == "not_released"
    assert any("product check not green" in b and "Q03" in b for b in manifest["release_blockers"])
    assert manifest["criteria_product_check"]["HP_AC03"] == "failed"


def test_fault_triggers_correction_and_corrected_version_is_released(cfg, tmp_path) -> None:
    implement = implementer(FAULTY, CORRECT)
    state, manifest = run(cfg, implement, "approved", tmp_path)
    assert [h["qa_verdict"] for h in manifest["history"]] == ["changes_requested", "approved"]
    assert manifest["history"][0]["tests_failed"] >= 1 and manifest["history"][1]["tests_failed"] == 0
    assert manifest["correction_rounds"] == 1
    # the QA result (failing customer case) was handed back to the implementer
    assert implement.feedback[0] is None and "Q03" in implement.feedback[1]
    assert manifest["release_status"] == "released"


def test_human_rejection_keeps_a_green_state_unreleased(cfg, tmp_path) -> None:
    state, manifest = run(cfg, implementer(CORRECT), "escalate_to_human", tmp_path)
    assert manifest["history"][-1]["tests_failed"] == 0
    assert manifest["release_status"] == "not_released"
    assert manifest["release_blockers"][0] == "human decision: escalate_to_human"


def test_artifact_changed_after_qa_blocks_release(cfg, tmp_path) -> None:
    def tamper(cfg_, ctx, state):
        (cfg_.product_path / cfg_.target_file).write_text(FAULTY, encoding="utf-8")  # change after QA
        return cw.make_decision(cfg_, ctx, state, "approved", visually_checked=True)

    state, run_dir = cw.run_customer_workflow(cfg, "Francisco", po=po, implement=implementer(CORRECT), qa=qa,
                                              decide=tamper, factory_root=tmp_path / "factory")
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["release_status"] == "not_released"
    assert any("hash mismatch" in b for b in manifest["release_blockers"])
