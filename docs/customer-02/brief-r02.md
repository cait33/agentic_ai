# HansePack – Factory brief R-02 (reference task, experiment only)

Reference task **R-02** from the Session 7 task sheet (`task sheets/session-06-08/Task_Sheet_Session_07_en.md`, section 4).
Project config: `projects/quotation-02-r02.json` · Task ID `R-02`.
**Experiment, not a customer requirement.** Runs only on an isolated copy of product Q-BASE; the result is never merged
into the customer candidate. The same brief is used unchanged for the S7 baseline (F-BASE) and the S8 repeat (F-NEW).

## Task (R-02, verbatim)

> Add `calculation_note` to exported quotation JSON with fixed text `Net amounts; shipping shown separately.`.
> Preserve display, money values and error handling. Add a test for the field; all existing business tests must still pass.

## Context in the product checkout `client-02-quotation`

- The export is `quote_to_json(quote: dict) -> str` in `quotation/export.py`. It already exists and works:
  it returns `json.dumps(data, ensure_ascii=False, indent=2)` with the keys `currency`, `rule_version`, `lines`,
  `goods_net_cents`, `shipping_cents`, `total_cents`; every line has `sku`, `quantity`, `unit_price_cents`,
  `list_amount_cents`, `discount_percent`, `discount_cents`, `net_cents`.
- `quote` is the dict returned by `quotation.pricing.calculate_quote(items, rule_version)` (already validated and calculated).
- The web UI (`quotation/web.py`) shows and downloads exactly the text returned by `quote_to_json`.
- Product tests: `tests/` (`python -m pytest tests -q`), currently 153 passed.

## Rules

1. The new key is `calculation_note` with exactly the text `Net amounts; shipping shown separately.` (same text for every quote).
2. Keep every existing key, value and line unchanged; do not recalculate, round or convert money values (integer cents stay integer cents).
3. Keep the function name and signature `quote_to_json(quote)`; deterministic output; standard library `json` and `typing` only.
4. Do not change the calculation, validation or error handling (`quotation/pricing.py`) or the web UI.
5. Do not change or delete existing tests or the customer fixtures.

## Checks (by the team, not by the agent)

`python -m pytest tests -q` in the product checkout, plus the team's independent R-02 acceptance checks
(`tests/r02/test_r02_acceptance.py` in the Factory repository, identical in S7 and S8)