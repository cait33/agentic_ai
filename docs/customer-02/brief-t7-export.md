# HansePack – Factory brief Session 7: JSON export (customer task)

Customer: HansePack Handelsgesellschaft (fictional) · Project config: `projects/quotation-02-export.json` · Task ID `CUST-002`
Source: client briefing `task sheets/session-06-08/Kundenbriefing_HansePack_de.md`, rule 7 and HP-AC06.

## Task for this run

Implement `quote_to_json(quote)` in **`quotation/export.py`** of the product checkout `client-02-quotation`.
Only this file is written. Keep the module docstring, the function name and its signature exactly.

## What the customer requires (rule 7, HP-AC06)

The JSON download of a quotation contains, per line: SKU, quantity, unit price, list amount, discount rate,
discount amount and line net – and in total: goods net, shipping, total, currency and rule version.
Money values in the export are **integer cents**. The export matches the visible calculation exactly.

## Interface

- Input `quote`: the dict returned by `quotation.pricing.calculate_quote(items, rule_version)`. It is already
  validated and calculated. Keys: `currency`, `rule_version`, `lines`, `goods_net_cents`, `shipping_cents`,
  `total_cents`; every element of `lines` has `sku`, `quantity`, `unit_price_cents`, `list_amount_cents`,
  `discount_percent`, `discount_cents`, `net_cents`.
- Output: a JSON **text** (`str`) built with the standard library `json` module:
  `json.dumps(data, ensure_ascii=False, indent=2)`, where `data` has exactly the keys
  `currency`, `rule_version`, `lines`, `goods_net_cents`, `shipping_cents`, `total_cents` (in this order) and every
  line exactly the seven line keys above (in this order).

## Rules

1. Copy the values unchanged from `quote`. Do **not** recalculate, round, convert to float or euro, or add money fields.
2. Deterministic: the same quote always gives the same text. No timestamp, no random quote number.
3. Standard library `json` and `typing` only. No file access, no network, no LLM, no imports from the Factory.
4. Do not hard-code customer case IDs or expected values.

## Checks (by the team, not by the agent)

`python -m pytest tests -q` in `client-02-quotation`; relevant: `tests/test_export.py` (export = calculation =
customer values for Q01–Q14, integer cents, rule version) and `tests/test_web.py` (the web UI shows and downloads
exactly this text). All existing business tests must stay green.
