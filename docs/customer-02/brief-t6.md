# HP-T6 – HansePack quotation calculator: calculation core (Session 6)

Source: HansePack client brief v1.0 (8 November 2026), `task sheets/session-06-08/Client_Brief_HansePack_en.md`.
Customer issue: client-02-quotation #2. Fictional company, course project.
Product repo: `client-02-quotation` (separate from the Nordwerk website; nothing of Nordwerk is touched).

## Task for Session 6

Implement the deterministic Python calculation of a quotation in **`quotation/pricing.py`** (the only file the Factory writes).
Today the customer checks three cases; the other rules below must not be contradicted (completed in Session 7):

| Case | Input | Expected (integer cents, rule version HP-V1) |
|---|---|---|
| Q01 | HP-BOX × 1 | line: list 250, discount 0 % / 0, net 250; goods net 250, shipping 1200, total 1450 |
| Q03 | HP-BOX × 50 | line: list 12500, discount 5 % / 625, net 11875; goods net 11875, shipping 1200, total 13075 |
| E01 | HP-BOX × 0 | `QuoteError` with an understandable message, **no** quotation |

Not part of this task: web UI, JSON download, shipping rule HP-V2, tests, any file outside `quotation/pricing.py`.

## Interface (binding – keep the contract of the existing stub)

- `quotation/pricing.py` already exists as a stub. Keep its docstring contract: signature, result keys, `QuoteError`. Replace the stub body with the implementation.
- `class QuoteError(ValueError)`: raised for every invalid input; `str(error)` is an understandable message.
- `calculate_quote(items: list[dict], rule_version: str = "HP-V1") -> dict` (do not change the signature)
  - `items` example: `[{"sku": "HP-BOX", "quantity": 50}]`
  - only `rule_version="HP-V1"` exists in S6/S7; any other value raises `QuoteError`
  - returns `{"currency": "EUR", "rule_version": "HP-V1", "lines": [...], "goods_net_cents": int, "shipping_cents": int, "total_cents": int}`
  - each line: `{"sku", "quantity", "unit_price_cents", "list_amount_cents", "discount_percent", "discount_cents", "net_cents"}`, lines in input order
  - all money values are Python `int` (integer cents) – no float, no Decimal in the result
  - never modify the `items` passed in; never return a partial quotation for invalid input
- Prices: `from quotation.catalog import load_catalog` – returns `{sku: unit_price_cents}`. `quotation/catalog.py` is human-written: use it, do not change it, do not copy prices into the code.
- Optional reproducible call: `main(argv=None) -> int` and `if __name__ == "__main__": raise SystemExit(main())`; `python -m quotation.pricing '{"items": [{"sku": "HP-BOX", "quantity": 50}]}'` prints the result as JSON and returns 0; on an error it prints `Fehler: <message>` to stderr and returns 2.
- Standard library only. Do not import `src`, langchain, langgraph, ollama, openai, requests, httpx, urllib or socket.
- Do not write customer case IDs (the Q- and E- numbers above) or the names of the reference file or its fields into the code; the product tests reject that.

## Business rules (customer brief)

1. A quotation contains 1–3 lines. Each SKU occurs at most once. Quantities are integers from 1 to 10,000. Unknown items, duplicate SKUs, empty lists, missing values, strings instead of numbers, fractional and Boolean quantities are invalid. Do not silently coerce, round or aggregate invalid input. (In Python `True` is an `int` – check `bool` first.)
2. Per line, list amount = quantity × unit price. The quantity discount applies to the **entire list amount of that line**: 1–49 units 0 %, 50–99 units 5 %, 100+ units 10 %.
3. Round each line's discount to whole cents with ROUND_HALF_UP: `discount_cents = (list_amount_cents * discount_percent + 50) // 100`. Line net = list amount − discount.
4. Goods net = sum of line nets. Shipping (HP-V1): 1200 cents if goods net < 50000 cents, otherwise 0 – threshold inclusive, evaluated after discount. Total = goods net + shipping.
5. Net amounts only, no VAT.