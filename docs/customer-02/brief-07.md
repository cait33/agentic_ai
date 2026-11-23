# HP-T7 – HansePack quotation calculator: full HP-V1 validation & CLI (Session 7)

Source: HansePack client brief v1.0 (8 November 2026), `task sheets/session-06-08/Client_Brief_HansePack_en.md`.
Customer issue: client-02-quotation (Session 7 task). Fictional company, course project.
Product repo: `client-02-quotation` (separate from the Nordwerk website; nothing of Nordwerk is touched).

## Task for Session 7

Complete the deterministic Python calculation and strict input validation in **`quotation/pricing.py`** (the only file the Factory writes in this run) so that **all 14 valid reference cases** and **all 10 invalid input cases** pass under rule version `HP-V1`, and include the reproducible CLI entry point.

| Requirement | Expected behavior (integer cents, rule version HP-V1) |
|---|---|
| All valid cases (14 cases) | Exact line values (`unit_price_cents`, `list_amount_cents`, `discount_percent`, `discount_cents`, `net_cents`) and totals (`goods_net_cents`, `shipping_cents`, `total_cents`) for 1–3 lines, tier boundaries (49/50, 99/100), ROUND_HALF_UP, and shipping threshold at 50,000 cents |
| All invalid cases (10 cases) | Raise `QuoteError` with a non-empty understandable message and produce **no** quotation: empty/non-list `items`, > 3 lines, missing/non-dict item fields, unknown/empty SKU, duplicate SKUs, quantity <= 0, quantity > 10,000, non-integer quantity (`bool`, `float`, `str`, `None`), unsupported `rule_version` |
| CLI entry point | `python -m quotation.pricing '{"items": [{"sku": "HP-BOX", "quantity": 50}]}'` prints JSON to stdout (exit 0) or `Fehler: <message>` to stderr (exit 2) |

Not part of this Factory task: web UI, JSON export module (`quotation/export.py`), shipping rule HP-V2 (deferred to Session 8), tests, any file outside `quotation/pricing.py`.

## Interface (binding – keep the existing contract)

- `quotation/pricing.py` already exists. Keep its public contract: signatures, result keys, `QuoteError`.
- `class QuoteError(ValueError)`: raised for every invalid input; `str(error)` is an understandable message.
- `calculate_quote(items: list[dict[str, Any]], rule_version: str = "HP-V1") -> dict[str, Any]` (do not change the signature)
    - `items` example: `[{"sku": "HP-BOX", "quantity": 50}]`
    - only `rule_version="HP-V1"` exists in S6/S7; any other value raises `QuoteError`
    - returns `{"currency": "EUR", "rule_version": "HP-V1", "lines": [...], "goods_net_cents": int, "shipping_cents": int, "total_cents": int}`
    - each line: `{"sku", "quantity", "unit_price_cents", "list_amount_cents", "discount_percent", "discount_cents", "net_cents"}`, lines in input order
    - all money values are Python `int` (integer cents) – no float, no Decimal in the result
    - never modify the `items` passed in; never return a partial quotation for invalid input
- Prices: `from quotation.catalog import load_catalog` – returns `{sku: unit_price_cents}`. `quotation/catalog.py` is human-written: use it, do not change it, do not copy prices into the code.
- Reproducible CLI entry point: `main(argv: list[str] | None = None) -> int` and `if __name__ == "__main__": raise SystemExit(main())`. Parses a single JSON argument (`{"items": [...], "rule_version": "HP-V1"}` or a raw JSON list `[...]`), calls `calculate_quote`, prints formatted JSON to stdout and returns `0`; on `QuoteError`, invalid JSON, or missing/extra CLI arguments prints `Fehler: <message>` to `sys.stderr` and returns `2`.
- Standard library only (`json`, `sys`, `typing`). Do not import `src`, langchain, langgraph, ollama, openai, requests, httpx, urllib or socket.
- Do not write customer case IDs (like Q01..Q14 or E01..E10) or the names of the reference file or its fields into the code; the product tests reject that.

## Business rules (customer brief)

1. `items` must be a `list` containing 1 to 3 lines (`1 <= len(items) <= 3`). Reject non-lists, empty lists, or more than 3 lines with `QuoteError`.
2. Each line must be a `dict` containing `"sku"` and `"quantity"` (reject missing keys or `None`).
3. `sku` must be a non-empty `str` present in `load_catalog()`. Each SKU may occur at most once per quotation – reject duplicate SKUs with `QuoteError` (never merge/aggregate).
4. `quantity` must be a strict integer from 1 to 10,000: check `type(quantity) is int` (in Python `isinstance(True, int)` is `True` – booleans `True`/`False`, floats like `1.5`, strings like `"50"`, and `None` must all raise `QuoteError`) and `1 <= quantity <= 10000`. Do not silently coerce or round invalid input.
5. Per line, list amount = quantity × unit price. The quantity discount applies to the **entire list amount of that line**: 1–49 units 0 %, 50–99 units 5 %, 100+ units 10 %.
6. Round each line's discount to whole cents with ROUND_HALF_UP: `discount_cents = (list_amount_cents * discount_percent + 50) // 100`. Line net = list amount − discount.
7. Goods net = sum of line nets. Shipping (HP-V1): 1200 cents if goods net < 50000 cents, otherwise 0 – threshold inclusive, evaluated after discount. Total = goods net + shipping.
8. Net amounts only, no VAT.