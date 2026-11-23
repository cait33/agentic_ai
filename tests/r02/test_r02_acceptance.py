"""R-02 independent acceptance checks (binding for the S7 baseline AND the S8 repeat – do not change).

Written by the team before the R-02 baseline run, kept in the Factory repo (not in the product), so no agent can
change the binding criteria. Agents may add their own product tests; these checks stay the same.

R-02: Add `calculation_note` to exported quotation JSON with fixed text `Net amounts; shipping shown separately.`.
      Preserve display, money values and error handling. Add a test for the field; all existing business tests
      must still pass.

Run (normally via tests/r02/check_r02.py):
    R02_PRODUCT_PATH=/path/to/isolated/copy python -m pytest tests/r02/test_r02_acceptance.py -q -rA
Skipped when R02_PRODUCT_PATH is not set (keeps the normal Factory test suite independent of the experiment).

Criteria (IDs used in the evidence):
    R02-1  calculation_note present with the exact text, for all Q01–Q14
    R02-2  all other export fields/values unchanged = calculation = customer values (HP-V1), integer cents
    R02-3  no other new top-level or line fields
    R02-4  error handling unchanged: E01–E10 still rejected with QuoteError, web API answers 422 and no quote
    R02-5  display unchanged: quotation/web.py and quotation/pricing.py byte-identical to Q-BASE, page still served
    R02-6  existing business tests and customer fixtures unchanged (byte-identical to Q-BASE)
    R02-7  the product contains its own passing test for calculation_note (pytest -k calculation_note)
    (R02-8 "all existing business tests pass" is checked by check_r02.py with the product's own pytest run.)
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

PRODUCT = os.environ.get("R02_PRODUCT_PATH")
pytestmark = pytest.mark.skipif(not PRODUCT, reason="R02_PRODUCT_PATH not set (R-02 experiment checks only)")

NOTE = "Net amounts; shipping shown separately."
Q_BASE_COMMIT = "3ef83876d663b4ffb7222655c54fe7e4271973c2"
TOP_FIELDS = ["currency", "rule_version", "lines", "goods_net_cents", "shipping_cents", "total_cents"]
LINE_FIELDS = ["sku", "quantity", "unit_price_cents", "list_amount_cents",
               "discount_percent", "discount_cents", "net_cents"]
TOTAL_FIELDS = ["currency", "rule_version", "goods_net_cents", "shipping_cents", "total_cents"]

# sha256 of the files at Q-BASE (3ef8387) that R-02 must not change.
UNCHANGED_AT_Q_BASE = {
    "quotation/pricing.py": "a9124caeafb1c1514fdff0afda65f5a4ba94409fe344bdb8427d2cb8bf99ebb6",
    "quotation/web.py": "b24b7207d3a212ab36ec5e65c1f835430da6c189891977ad3c4e3d4875513905",
    "quotation/catalog.py": "7b98df5eb0bb9693f99fc84e6361c648e8fe6d2bbb4d6a2a8a7899900629ce39",
    "tests/test_export.py": "79d2188d8044d0d1453ec4bb92fcd1d0a369502393dfe133fef56df994a758f8",
    "tests/test_fixtures.py": "5aa7f30728c215962db9bf4745647d3c7c752bd6ccddd1942862da40fc394d59",
    "tests/test_reference_cases.py": "a2e2862d71d9ebdc8e26ba7dc95f48c5b13c22a47e80b1ee959d96a6f0cd02f1",
    "tests/test_web.py": "c5c49e7605605bdbe051be537f6bd51957d59f37a7c1bb58a24a59d1b84772f2",
    "fixtures/HansePack_Katalog.json": "70f0e1a7389b136828a794c79df130762d7638d9f63b373a7fd43e16607f953a",
    "fixtures/HansePack_Referenzfaelle.json": "7deb994e5debd82019062574ecfb1e445c4bd474e98b33fb532668ae00dc839a",
    "fixtures/SHA256SUMS": "64b86226e26c1ba9fd47fa6e81e542e8f76f152126b3d61e87df6faff2c964f0",
}

ROOT = Path(PRODUCT).expanduser().resolve() if PRODUCT else Path(".")
if PRODUCT and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _sha(rel: str) -> str:
    """sha256 with CRLF normalised to LF (Windows checkouts with core.autocrlf convert text files)."""
    return hashlib.sha256((ROOT / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()

def _reference() -> dict:
    return json.loads((ROOT / "fixtures" / "HansePack_Referenzfaelle.json").read_text(encoding="utf-8"))


VALID = {c["id"]: c for c in _reference()["valid_cases"]} if PRODUCT else {f"Q{n:02d}": None for n in range(1, 15)}
INVALID = {c["id"]: c for c in _reference()["invalid_cases"]} if PRODUCT else {f"E{n:02d}": None for n in range(1, 11)}


def _exported(case_id: str) -> tuple[dict, dict]:
    from quotation.export import quote_to_json
    from quotation.pricing import calculate_quote

    quote = calculate_quote(VALID[case_id]["input"]["items"], rule_version="HP-V1")
    return quote, json.loads(quote_to_json(quote))


# R02-1 ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("case_id", sorted(VALID))
def test_r02_1_calculation_note_exact_text(case_id):
    _, data = _exported(case_id)
    assert data.get("calculation_note") == NOTE


# R02-2 ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("case_id", sorted(VALID))
def test_r02_2_values_unchanged(case_id):
    quote, data = _exported(case_id)
    assert {f: data[f] for f in TOTAL_FIELDS} == {f: quote[f] for f in TOTAL_FIELDS}
    assert {f: data[f] for f in TOTAL_FIELDS} == VALID[case_id]["expected"]["HP-V1"]
    assert [{f: line[f] for f in LINE_FIELDS} for line in data["lines"]] == VALID[case_id]["expected_lines"]
    money = [data["goods_net_cents"], data["shipping_cents"], data["total_cents"]]
    for line in data["lines"]:
        money += [line["unit_price_cents"], line["list_amount_cents"], line["discount_cents"], line["net_cents"]]
    assert all(type(v) is int for v in money)


# R02-3 ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("case_id", sorted(VALID))
def test_r02_3_no_other_new_fields(case_id):
    _, data = _exported(case_id)
    assert set(data) == set(TOP_FIELDS) | {"calculation_note"}
    assert [k for k in data if k != "calculation_note"] == TOP_FIELDS  # existing order kept
    assert all(list(line) == LINE_FIELDS for line in data["lines"])


# R02-4 ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("case_id", sorted(INVALID))
def test_r02_4_error_handling_unchanged(case_id):
    from quotation.pricing import QuoteError, calculate_quote

    with pytest.raises(QuoteError):
        calculate_quote(INVALID[case_id]["input"]["items"], rule_version="HP-V1")


@pytest.fixture(scope="module")
def base_url():
    from quotation.web import make_server

    server = make_server(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _post(url: str, body: object) -> tuple[int, str]:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status, res.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode("utf-8")


def test_r02_4_web_api_invalid_quantity_is_error_without_quote(base_url):
    status, text = _post(base_url + "/api/quote", {"items": [{"sku": "HP-BOX", "quantity": 0}]})
    assert status == 422
    assert "calculation_note" not in text and "total_cents" not in text


# R02-5 ---------------------------------------------------------------------------------------------------------
def test_r02_5_display_and_calculation_code_unchanged(base_url):
    for rel in ("quotation/pricing.py", "quotation/web.py", "quotation/catalog.py"):
        assert _sha(rel) == UNCHANGED_AT_Q_BASE[rel], rel
    with urllib.request.urlopen(base_url + "/", timeout=5) as res:
        assert res.status == 200
    status, text = _post(base_url + "/api/quote", {"items": [{"sku": "HP-BOX", "quantity": 50},
                                                             {"sku": "HP-TAPE", "quantity": 10}]})
    assert status == 200
    data = json.loads(text)
    assert data["total_cents"] == 17075 and data["calculation_note"] == NOTE


# R02-6 ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("rel", sorted(r for r in UNCHANGED_AT_Q_BASE if r.startswith(("tests/", "fixtures/"))))
def test_r02_6_existing_tests_and_fixtures_unchanged(rel):
    assert _sha(rel) == UNCHANGED_AT_Q_BASE[rel]


# R02-7 ---------------------------------------------------------------------------------------------------------
def test_r02_7_product_has_own_passing_test_for_the_field():
    own = [p for p in sorted((ROOT / "tests").rglob("test_*.py")) if "calculation_note" in p.read_text(encoding="utf-8")]
    assert own, "no product test mentions calculation_note"
    proc = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-k", "calculation_note", "-p", "no:cacheprovider"],
                          cwd=ROOT, capture_output=True, text=True, timeout=300)
    # returncode 5 = no test selected
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]