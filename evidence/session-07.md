# Session 07 - 23/11/2026

Complete the HansePack quotation calculator for the original HP-V1 rules (HP-AC01–HP-AC07), show that the Factory blocks an incorrect delivery after an intentionally injected discount fault, and preserve an R-02 baseline measurement for the Factory improvement in Session 8.

## Tasks/Responsibilities

| Task | Person | What |
| ---- | ----- | ---- |
| 1 | Daniil| Customer task E06/E09/E10 (input validation + CLI) through the Factory: `--verify-only` run `fd84928a-9334-4377-adb2-ddcf46c82f9b` (`released`), `quotation/pricing.py` (`c8d80e3`), human decision (`Daniil`, `approved`) |
| 1 | Caitlin | Web UI attempts through the Factory: runs `7272cdc6` (web_slots, no target file) and `fbc26776` (python_module, write outside `quotation/` refused) – both `not_released`, branch `createWebsite2Run`; UI template `5d3ab42` (later replaced) |
| 1 | Fatih | Customer task "JSON export" through the Factory: export stub + config `projects/quotation-02-export.json` + brief `brief-t7-export.md` (product PR #10, Factory PR #62), real run `d9c8a2eb` (1 correction round after human feedback, `released`), result product PR #12 (`3ef8387`), evidence Factory PR #63 |
| 1 | Fatih | Small web UI `quotation/web.py` (human-written, standard library `http.server`) + `tests/test_web.py` + README start command (product PR #10) |
| 1 | Francisco | Human gate of the export run: round 0 `changes_requested` with concrete feedback, round 1 `approved` incl. UI/export review |
| 2 | Fatih | Product checks for all Q01–Q14 / E01–E10 (line values + totals) + JSON export contract test `tests/test_export.py` (product PR #9, `cb4c821`) |
| 2 | Fatih | Candidate checks 153 passed, fresh checkout without the Factory, Factory tests 54 passed (separately), UI review organised (done by Francisco at the gate) |
| 3 | Fatih + Francisco | Factory gate tests for passed / blocked / corrected states with mocked LLM `tests/factory/test_fault_gate.py` (Factory PR #59, written by Fatih, reviewed + merged by Francisco) |
| 3 | Fatih + Francisco | Controlled discount fault on product branch `t7/injected-discount-fault`: fault run `991c4f06` (`not_released`) + correction run `bcae3e2c` (`released`), evidence Factory PR #60 |
| 3 | Francisco | Human reviewer at the gate: fault run `changes_requested` 12:19 UTC, correction run `approved` 12:20 UTC (pair session with Fatih) |
| 4 | Rafael (+ Francisco) | Tags Q-BASE / F-BASE, R-02 setup PR (review + merge Rafael), R-02 baseline run 01b79f0c on an isolated Q-BASE copy (run operation, gate + rework Francisco), bottleneck + hypothesis for S8 |

Only existing roles (`organization/roles.yaml`) were used; no new agents or roles.
Merged without a second review: Factory PR #58 (self-merged by Daniil), product PR #9 (merged by Fatih); direct pushes to `main`: Factory `df169ef`, `04b6e2b` (evidence skeleton), product `c8d80e3` (validation + CLI), `5d3ab42` (UI template); merged by the author: product PRs #11, #12, Factory PRs #61, #63 (Fatih). Reviewed by a second person: Factory PRs #59, #60, #62 and product PR #10 (written by Fatih, merged by Francisco); the export result (#12) was reviewed by Francisco at the gate before the merge.


## Repositories and commits

| | Repository | From | To |
|---|---|---|---|
| Factory | https://github.com/cait33/agentic_ai | `3269bdd` (end of S6) | TODO (merge commit of the final S7 evidence PR) |
| HansePack product | https://github.com/franciscotbatista99/client-02-quotation | `910ec24` (end of S6) | `3ef8387` (release candidate HP-AC01–07) |
| Nordwerk product (frozen) | https://github.com/franciscotbatista99/client-01-website | tag `v1.0` → `f1575ad` | unchanged |

Release candidate = Q-BASE: tag [`Q-BASE`](https://github.com/franciscotbatista99/client-02-quotation/tree/Q-BASE) → product `3ef8387`. F-BASE: tag [`F-BASE`](https://github.com/cait33/agentic_ai/tree/F-BASE) → Factory `9a6e0ca` (merge of the R-02 setup PR, no change under `src/`).


## 1. Calculation scope completed, small UI built

- Starting point: the S6 agent code (`910ec24`) already gets all Q01–Q14 right. E06 (duplicate SKU), E09 (`True` as quantity) and E10 (quantity 10 001) are not rejected yet, and there is no web UI and no JSON export.
- Customer issue: #2 (scope, open questions, assumptions; S7 scope E06/E09/E10, web UI, JSON export)
- **Validation E06/E09/E10** (Daniil, product `c8d80e3`): duplicate SKUs, `bool` quantities and quantities outside 1–10 000 are rejected with `QuoteError` (`type(quantity) is not int`), 1–3 lines; CLI `python -m quotation.pricing '<json>'`. Product checks after the change: 97 passed / 1 skipped (export not yet there). E06/E09/E10 validation and CLI main() added by hand in c8d80e3, then verified via --verify-only run fd84928a-9334-4377-adb2-ddcf46c82f9b..
- **Web UI** `quotation/web.py` – **human-written** (Fatih), standard library `http.server`, no runtime dependencies:
  - start: `python -m quotation.web` → http://127.0.0.1:8000 (documented in the README)
  - 1–3 lines (article + quantity), "Berechnen", table with all line values and totals, "JSON herunterladen", net notice "Nettobeträge – Lehrprojekt, kein verbindliches Angebot"
  - no validation in the page: every entered value goes unchanged to `calculate_quote`; invalid input comes back as HTTP 422 with the Python error text and no quote
  - `POST /api/quote` returns exactly `quote_to_json(calculate_quote(...))`; the page renders the table from that text and the download saves the same text → display and export cannot differ
  - Earlier Factory attempts for the UI (Caitlin) failed and stay visible as failed runs: `7272cdc6` (web_slots, target file missing) and `fbc26776` (python_module, write to `site/index.html` refused) – branch `createWebsite2Run`, TODO merge
- **JSON export** `quotation/export.py` – **written by the Factory agent** (run below): `quote_to_json(quote)` copies the customer fields unchanged (per line SKU, quantity, unit price, list amount, discount %, discount, line net; goods net, shipping, total, currency, `rule_version`), integer cents, `json.dumps(…, ensure_ascii=False, indent=2)`.

### Factory run: input validation E06/E09/E10

Task given to the Factory: reject duplicate SKUs (E06), Boolean quantities (E09) and quantities > 10 000 (E10) in quotation/pricing.py with QuoteError. No silent type coercion or SKU aggregation is allowed, and Q01–Q14 must stay correct. Results are checked by the team's product tests, not by the agent.

|                |                                                                                                                                                                                                                                                                  |
|----------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Run            | fd84928a-9334-4377-adb2-ddcf46c82f9b (--verify-only, raw data runs/quotation-02/fd84928a-9334-4377-adb2-ddcf46c82f9b)                                                                                                                                            |
| Project / task | quotation-02 / CUST-002, customer issue #2                                                                                                                                                                                                                |
| Inputs         | product commit c8d80e3 (quotation/pricing.py with E06/E09/E10 validation + CLI main()), Factory createWebsite2Run / projects/quotation-02.json, brief docs/customer-02/brief-t7.md|
| Human gate     | Daniil, approved, review hint: diff + pytest + E06/E09/E10; comment: "All changes to client repo done successfully."|
| Result         | released (QA: 97 passed / 0 failed, 1 skipped export), product result commit c8d80e3, artifact sha256 15fbbaa9b7b64bcf66221cc3d12edf9d7bf1fdb13124e3677272cc0734ebe315|
| Manual product work (counts as human work)        | Added strict checks for E06 (duplicate SKU & 1 <= len(items) <= 3), E09 (type(quantity) is int rejecting bool), E10 (1 <= quantity <= 10000), non-dict item guard, and CLI main() in quotation/pricing.py (c8d80e3).|

### Factory run: JSON export (S7 customer task)

Task given to the Factory (brief `docs/customer-02/brief-t7-export.md`): implement `quote_to_json` in `quotation/export.py` according to rule 7 / HP-AC06 of the client briefing – values copied unchanged, integer cents, deterministic, standard library only. Results are checked by the team's product tests (`tests/test_export.py`, `tests/test_web.py`), not by the agent.

| | |
|---|---|
| Run | `d9c8a2eb-425f-49a5-9d28-7021149979d9` (raw data `runs/quotation-02-export/d9c8a2eb…`, Factory PR #63) |
| Project / task | `quotation-02-export` (same Factory, own config + runs area) / `CUST-002`, customer issue #2 |
| Inputs | product `f322fd0` (stub + UI + tests, `git status` clean), Factory `14828df`, brief `brief-t7-export.md` |
| Model / settings | Ollama qwen3:4b, temperature 0, JSON mode, reasoning off, implementer max. 3072 output tokens |
| Structured handover | PO agent → user stories (`requirements/*.json`, PO cache miss → stored) → backend-api-agent → `implementation-N.json` (file + sha256) → QA agent (real pytest in the product checkout) → `qa-round-N.json` → gate `review-N.json` → human feedback → implementer |
| Round 0 | agent wrote `export.py` (`310446b5…`) but **without `import json`** and without the contract docstring → product checks 109 passed / **44 failed** (`NameError`) → QA `escalate_to_human` (its LLM assessment was unparseable, so no automatic correction) |
| Human intervention | Francisco at the gate, round 0: `changes_requested`, 12:49 UTC: "NameError: name 'json' is not defined – add 'import json' and keep 'from typing import Any' at the top; keep the module docstring (contract) unchanged. The json.dumps logic itself is correct." |
| Round 1 (correction) | implementer with this feedback → `c462738f…` → **153 passed / 0 failed** → QA `approved` |
| Correction rounds | 1 of max. 2 |
| Human gate | Francisco, `approved`, 12:53 UTC (13:53 local): "Diff ok (import json added, contract docstring kept); 153 passed. UI review: HP-BOX 50 + HP-TAPE 10 = 17075 ct, display = downloaded JSON; qty 0 -> error, no quote; net notice visible." |
| Result | `released`, product result commit `3ef8387` (PR #12, agent output committed unchanged), artifact sha256 `c462738f…`; HP_AC01–HP_AC06 passed |
| Agent contribution | `quotation/export.py` (new implementation, 40 lines) |
| LLM calls / agent credits | 4 LLM calls (PO 1, implementer 2, QA 1) / **5.60 credits** (PO 1.31, implementer 1.31 + 1.31, QA 1.65 + 0.02) |
| Duration | agent time ≈ 140 s; workflow incl. human wait 424 s |
| Manual product work (counts as human work) | export stub (interface only), web UI `quotation/web.py`, `tests/test_web.py`, README, removal of the unused `site/` template and a committed `.DS_Store` (product PRs #10, #11) |

Notes: `factory_dirty_at_start: true` (untracked local files on the operator's machine, no tracked Factory change); like the S6 run, round 0 failed on a missing import – see bottleneck below.


## 2. Customer-provided results tested

| Check | Expected (customer values) | Automated test | Result |
|---|---|---|---|
| Q01–Q14 line values (HP-V1) | List amount, discount %, discount and line net, with tier boundaries 49/50/99/100. Rounding cases: Q04 1237.5 → 1238, Q13 3187.5 → 3188, Q14 662.5 → 663 (HALF_UP). | `test_hp_ac03_lines_match_customer_values[Q01–Q14]` | ✅ 14/14 |
| Q01–Q14 totals (HP-V1) | goods net, shipping, total; Q06 shipping after discount (45 000 → 1200), Q07 at threshold (50 000 → 0) | `test_hp_ac03_totals_*` | ✅ 14/14 |
| E01–E10 | Rejected in Python with `QuoteError` and no quote. Input is not modified, types are not coerced and SKUs are not aggregated. | `test_hp_ac04_*[E01–E10]`, `test_hp_ac04_duplicate_sku_is_not_aggregated`, `test_hp_ac04_no_silent_type_coercion` | ✅ 10/10 + extra checks |
| JSON export | required fields, integer cents, rule version, export = calculation | `tests/test_export.py` (`test_hp_ac06_*`), `tests/test_web.py` (`test_hp_ac06_displayed_text_is_exactly_the_export`) | ✅ |
| Independence | no Factory/LLM/network imports, no lookup of reference answers, fixtures unchanged | `test_hp_ac01_*` + `tests/test_fixtures.py` | ✅ |
| Factory | gate passed/blocked, loop limit, project separation | Factory `python -m pytest` | ✅ 54 passed ([`factory-pytest.txt`](session-07/factory-pytest.txt)) |

- Product test command: `cd client-02-quotation && python -m pytest` (expected values only from `fixtures/HansePack_Referenzfaelle.json`, never from the agent)
- Factory test command: `python -m pytest` in the Factory repo, run separately
- Product check results:
  - Before the Factory run (`66f9c5e`, after product PR #9): 89 passed / 8 failed / 1 skipped. The 8 failures are E06, E09 and E10, including the no-aggregation and no-coercion checks. The skipped test is the export test, because `quotation/export.py` was not implemented yet.
    After c8d80e3 / --verify-only fd84928a-9334-4377-adb2-ddcf46c82f9b: 97 passed / 0 failed / 1 skipped (all Q01–Q14 and E01–E10 green; 1 skipped test is test_export.py before quotation/export.py is present).
  - In the export run: round 0 109/44, round 1 153/0.
  - Final candidate `3ef8387`: **153 passed** ([`product-pytest.txt`](session-07/product-pytest.txt), Fatih, 13:54).
- Expected values unchanged; no differences between implementation and customer values on the candidate, no escalation to the instructor needed.
- Human UI review: **Francisco**, 13:51–13:53 local, product `c462738f…` = candidate `3ef8387` (during the gate of run `d9c8a2eb`, recorded in `review-1.json`).
  - Multi-line quotation: HP-BOX × 50 + HP-TAPE × 10 (Q12) → total 17 075 cent shown.
  - JSON downloaded and compared with the display: identical.
  - Invalid quantity 0 → error "Quantity must be an integer between 1 and 10000 (got 0)."; no quotation shown.
  - Net notice visible.
  - Automated complement: `tests/test_web.py` (27 tests); browser check with Playwright before the run (Q12 display 17 075 ct = download `total_cents` 17 075, quantity 0 → error, table hidden).

**Fresh checkout:** Fatih, 13:54 local:
- clone of `3ef8387`, with `git status` clean;
- no installation needed except `pytest` (standard library only);
- `python -m pytest` → 153 passed;
- UI starts with `python -m quotation.web` (port 8031 in the check): page with net notice, `POST /api/quote` Q12 → `"total_cents": 17075`, quantity 0 → error;
- no Factory, LLM or database needed.

Record: [`evidence/session-07/fresh-checkout.txt`](session-07/fresh-checkout.txt).


## 3. Controlled business fault injected

Fault injected on an isolated copy of the candidate: the 5 % discount starts **above 50** instead of **from 50**. Exactly one condition was changed in `quotation/pricing.py` (`quantity <= 49` → `quantity <= 50`); customer expectations and tests are unchanged.

| | |
|---|---|
| Isolated state | product branch `t7/injected-discount-fault` in a separate checkout `~/hp-fault` (fresh clone of `main` = `5d3ab42`, pricing as validated in `c8d80e3`), fault commit `851a7d2`; Factory `02f25ed`, config `projects/quotation-02.json` unchanged, product path overridden with `--product-path ~/hp-fault`; `git status` clean at both runs |
| Expected effect | Q03 total 13 700 instead of 13 075 cent. Q12 contains HP-BOX × 50, so it gives 17 700 instead of 17 075. Checked before the run on `851a7d2` with the product tests: exactly 6 tests red (`test_hp_ac02_lines/totals[Q03]`, `test_hp_ac03_lines/totals[Q03]`, `test_hp_ac03_lines/totals[Q12]`), 91 passed, 1 skipped (export) |
| Fault run | `991c4f06-502f-4b45-b294-93397d5bd07b` (Factory `--verify-only`: QA agent runs the product checks, then human gate). QA: **91 passed / 6 failed** → `changes_requested`. The gate printed "RELEASE BLOCKERS (Stand kann NICHT freigegeben werden)" and **did not offer "approved"** (only `changes_requested` / `escalate_to_human`). Result **`not_released`**, blockers: human decision `changes_requested` + "product check not green: failed=6, tests=[…Q03…, …Q12…]" |
| Correction | by hand (Fatih, watched by Francisco): the one changed line reverted, commit `aa40d63` |
| Correction run | `bcae3e2c-f183-4efb-80f1-43f6c468747e`: QA **97 passed / 0 failed** (1 skipped: export) → `approved` → **`released`**; artifact sha256 `a9124cae…` **identical** to `quotation/pricing.py` on product `main` |
| Human gate | Francisco: fault run `changes_requested`, 12:19 UTC (13:19 local), "Injected discount fault: Q03 13700 instead of 13075 – not released"; correction run `approved`, 12:20 UTC (13:20 local), "Correction verified: Q03 13075 again, all Q01-Q14 / E01-E10 green" |
| Model / costs | Ollama qwen3:4b; fault run 1 LLM call (QA failure assessment, 1565 in / 528 out tokens, 53 s) = 1.58 credits; correction run 0 LLM calls = 0.01 credits |
| Delivered? | No – the fault state was never merged into `main`, tagged or released; the branch stays only as evidence |

- Factory gate tests (mocked LLM, real pytest tool on a temporary product checkout with the unchanged customer fixtures): `tests/factory/test_fault_gate.py`, Factory PR #59 – **6 passed** ([`fault-gate-pytest.txt`](session-07/fault-gate-pytest.txt)); whole Factory suite 54 passed.
  - Passed state: correct code → green check + human approval → `released`.
  - Blocked state: injected fault → QA `changes_requested` in all 3 rounds (2 correction rounds = loop limit) → escalation → **`not_released` even if the human chooses "approved"**, blocker names Q03.
  - Correction: fault in round 0 → QA feedback naming Q03 handed to the implementer → corrected round 1 → `released`.
  - A green state without human approval stays `not_released`; a file changed after QA is blocked by the hash check.
  - Counter-check: with the QA blocker disabled in `release_blockers`, the blocked-state test fails – the tests detect an ineffective gate.
  - The loop-limit and project-separation tests still pass.
- Mock tests show the workflow logic, not real LLM use; the real runs are `991c4f06` and `bcae3e2c` above.

## 4. R-02 baseline before improvement

Task R-02 (verbatim, task sheet S7 section 4, Factory brief [`docs/customer-02/brief-r02.md`](../docs/customer-02/brief-r02.md)): add `calculation_note` to exported quotation JSON with fixed text `Net amounts; shipping shown separately.`. Preserve display, money values and error handling. Add a test for the field; all existing business tests must still pass. **Experiment only – never merged into the customer candidate.**

**Setup (fixed before the run, identical in S8):**

- Config [`projects/quotation-02-r02.json`](../projects/quotation-02-r02.json): same Factory, implementer `python_module` → `quotation/export.py`, product tests `tests/`, max. 2 correction rounds, own runs area `runs/quotation-02-r02/`. **PO cache off** (`reuse_po_output: false`), so no run reuses an earlier run's output.
- Independent acceptance checks [`tests/r02/test_r02_acceptance.py`](../tests/r02/test_r02_acceptance.py) are in the Factory repo, outside the agent's write area, and are evaluated with [`tests/r02/check_r02.py`](../tests/r02/check_r02.py):

| ID | Criterion |
|---|---|
| R02-1 | `calculation_note` present with the exact text for Q01–Q14 |
| R02-2 | all other export values = calculation = customer values HP-V1, integer cents |
| R02-3 | no other new fields, existing key order kept |
| R02-4 | error handling unchanged: E01–E10 → `QuoteError`; web API quantity 0 → 422, no quote |
| R02-5 | display unchanged: `pricing.py`, `web.py`, `catalog.py` unchanged vs Q-BASE; UI serves Q12 = 17 075 ct incl. note |
| R02-6 | existing tests and customer fixtures unchanged vs Q-BASE |
| R02-7 | product has its own passing test for `calculation_note` |
| R02-8 | all product business tests pass (`python -m pytest tests`, Q-BASE: 153) |

| | Run 1 |
|---|---|
| Q-BASE / F-BASE | product `3ef8387` (tag `Q-BASE`) / Factory `9a6e0ca` (tag `F-BASE`) |
| Isolated copy / branch | `git worktree` of Q-BASE at `C:\Users\Utilizador\hp-r02-run1`, branch [`r02/baseline-run1`](https://github.com/franciscotbatista99/client-02-quotation/tree/r02/baseline-run1) (pushed, not merged); `product_dirty_at_start: false`, `factory_dirty_at_start: false` |
| Model / settings | Ollama `qwen3:4b`, temperature 0.0, JSON mode, reasoning off, implementer max. 3072 output tokens |
| Run ID | `01b79f0c-b798-4060-9b63-e226723bb758` (raw data `runs/quotation-02-r02/01b79f0c-b798-4060-9b63-e226723bb758/`), started 14:56:57 local |
| Rounds / QA | round 0: 153 passed / 0 failed → QA `approved` (0 LLM calls); 0 correction rounds |
| Gate | Francisco, `approved`, 15:06:11 local (14:06:11 UTC), comment: "Diff ok: calculation_note added at the end with exact text, all other fields unchanged; 153 passed. Finding: agent also deleted the module docstring (not requested, no functional effect). No product test for the field (implementer can only write quotation/) -> human rework after the run." → `released` |
| Agent output commit | `aa19aaf` – `quotation/export.py` +2/−12: `calculation_note` added as last key; module docstring deleted (not requested) |
| R-02 criteria on agent output | R02-1…R02-6 passed, **R02-7 failed** (no product test for the field), R02-8 passed (153) – [report](session-07/r02/run1-agent-output-checkfix.txt) |
| Human rework | `4fda164`: `tests/test_r02_calculation_note.py` (9 lines), ≈ 5 min (15:21–15:26 local), by Francisco → all R02-1…R02-8 passed, 62/62 acceptance checks + 154 product tests – [report](session-07/r02/run1-after-rework.txt) |
| Agent time / LLM calls / credits | 177.4 s (PO 87.7 s, implementer 47.1 s, QA 42.6 s) / 2 calls (PO 813 in / 383 out, implementer 1697 in / 326 out tokens) / **3.85 credits** |
| Human review / rework | gate wait ≈ 376 s (≈ 6 min: diff, tests, decision) / rework ≈ 5 min |
| Result | Full run, `released` by the human gate. **R-02 not complete from the Factory alone (R02-7)**; complete after ≈ 5 min human rework. |
| Run 2 | not done (time) |

Evaluation note: the first evaluation ([`run1-agent-output.txt`](session-07/r02/run1-agent-output.txt)) also showed R02-5 and R02-6 red. The cause was in the check, not in the product. The check compared sha256 values of LF files, but the Windows worktree has CRLF line endings (`core.autocrlf`); the agent diff touched only `export.py`. The check was fixed after the run (CRLF normalised before hashing, criteria unchanged, commit `4ab9c1b`), and the same agent output was evaluated again → [`run1-agent-output-checkfix.txt`](session-07/r02/run1-agent-output-checkfix.txt). Both reports are kept; S8 uses the fixed check for both variants.

## Cost

Factory development and the R-02 experiment are recorded separately from customer delivery.

| Category | Who | Quantity                                                  | Credits |
| -------- | --- |-----------------------------------------------------------|---------|
| Customer delivery `CUST-002`: Factory task E06/E09/E10 validation, CLI `main()`, `--verify-only` gate & cleanup (`c8d80e3`, `fd84928a-9334-4377-adb2-ddcf46c82f9b`) | Daniil | 1.5 h                                                     | 150.00  |
| Customer delivery `CUST-002`: attempting web UI + JSON export | Caitlin | 0.75 h                                                    | 75.0    |
| Customer delivery `CUST-002`: product checks Q01–Q14 / E01–E10 + export test (product PR #9) | Fatih | 0.25 h                                                    | 25.00   |
| Customer delivery `CUST-002`: web UI (human-written), export stub, UI tests, README, export task config + brief (product PR #10, Factory PR #62) | Fatih | 0.4 h                                                     | 40.00   |
| Customer delivery `CUST-002`: export run operation, result PR #12, record-result, candidate checks, fresh checkout (Factory PR #63) | Fatih | 0.2 h                                                     | 20.00   |
| Customer delivery `CUST-002`: time tracking, plan, this index | Rafael | TODO h                                                    | TODO    |
| Review `CUST-002`: human UI/export review | TODO | TODO h                                                    | TODO    |
| Review `CUST-002`: human gate (task run, fault run, correction run) | Francisco | TODO h                                                    | TODO    |
| Factory development `FACTORY-S7`: gate tests passed/blocked (mocked LLM, PR #59) | Fatih | 0.25 h                                                    | 25.00   |
| Factory development `FACTORY-S7`: gate tests passed/blocked (mocked LLM) | Francisco | TODO h                                                    | TODO    |
| Factory development `FACTORY-S7`: fault case (fault branch, fault + correction runs, PR #60) | Fatih | 0.2 h                                                     | 20.00   |
| Factory development `FACTORY-S7`: fault case (fault branch, fault + correction runs) | Francisco | TODO h                                                    | TODO    |
| R-02 baseline (separate): review + merge of setup PR, F-BASE tag, time tracking, evidence | Rafael | 0.5 h | 50.00 |
| R-02 baseline (separate): Q-BASE tag, setup PR, worktree, run operation, gate review, rework, evaluation | Francisco | 1.5 h | 150.00 |
| Agents `CUST-002`: export run `d9c8a2eb` (incl. failed round 0) | – | 4 LLM calls                                               | 5.60    |
| Agents `CUST-002`: failed UI runs `7272cdc6` + `fbc26776` (Caitlin, branch `createWebsite2Run`) | – | 1 LLM call                                                | 1.81    |
| Agents `CUST-002`: validation `c8d80e3` | – | unknown (no run evidence)                                 | unknown |
| Agents `FACTORY-S7`: fault run `991c4f06` + correction run `bcae3e2c` | – | 1 LLM call                                                | 1.59    |
| Agents R-02: run 01b79f0c (1 full run, no failed runs) | – | 2 LLM calls | 3.85 |
| Agents: test runs not in the repository | – | unknown                                                   | unknown |
| CI | – | TODO (none – Actions disabled / N runs incl. failed runs) | TODO    |

Unknown values are marked `unknown`, not 0.

### Plan

| Session | Planned scope | Budget (credits) |
|---|---|---|
| S7 | HP-AC03 (Q01–Q14), HP-AC04 (E01–E10), HP-AC05 web UI, HP-AC06 JSON export, HP-AC07 release candidate | 1600 (team planning from S6: 5 people × ≈ 3 h = 1500 + ≈ 25 agent runs à ≈ 4 credits) · **actual TODO** |
| S8 (reserve) | CR-02 / HP-V2 shipping rule (HP-AC08), HP-AC09 release, Factory change + R-02 repeat | 600 reserve |

Budgets are a team planning proposal, not agreed with the instructor yet.

Actual S7 effort (from `costs/usage.csv`): **TODO h human + TODO agent credits + TODO CI = TODO credits** (`CUST-002` TODO, `FACTORY-S7` TODO, R-02 TODO).
Plan deviations: R-02 was planned for 13:30–14:15. Setup and tags ran ≈ 14:05–14:55, the run 14:57–15:06, evaluation and rework until ≈ 15:30 – after the 15:00 deadline. The R-02 check was fixed after the run (CRLF, see section 4). Second R-02 run not done (time). Further deviations: TODO.

## Bottleneck and hypothesis

- **Observed bottleneck (R-02 baseline `01b79f0c`):** the Factory's check is blind to task-specific requirements, and the implementer cannot deliver tests.
  - QA was green (153/0, 0 LLM calls) and recommended `approved`, but R-02 was not complete: there was no product test for the field (R02-7 failed).
  - The agent also deleted the module docstring without being asked. No check detected it.
  - Both problems were found only by the human: gate review ≈ 6 min, rework ≈ 5 min.
  - Cause in the code: the `python_module` implementer writes exactly one file inside `quotation/` (`_product_target` in `src/agents/backend_api_engineer.py`), and QA only runs the product tests that already exist (`tests/test_export.py` deliberately ignores extra fields).
- Not chosen: the missing import in round 0 (S6 `6b975659`, S7 `d9c8a2eb`). It did not occur in R-02, because `export.py` already had its imports, so R-02 cannot measure it.
- **Small Factory change planned for S8 (F-NEW, exactly one):** *structured test task*. The `python_module` implementer may return, in its structured JSON output, **one new test file** under `tests/`. Only new files are allowed: existing tests cannot be changed or deleted. The same AST safety checks apply, through a new config field `allowed_test_paths`. QA runs the new test together with the existing tests, so a red task test leads to automatic correction feedback. Same model, settings, brief, Q-BASE and acceptance checks.
- **Hypothesis / measure:** with F-NEW, R02-7 on the agent output changes from *failed* (baseline) to *passed*, and human rework drops from ≈ 5 min to 0, with R02-1…R02-6/R02-8 unchanged. Agent credits per run rise by at most ≈ 20 % (3.85 → ≤ 4.6).
  - Measured with `tests/r02/check_r02.py` (criteria on agent output, correction rounds, calls/seconds/credits) plus human review/rework minutes.
  - Comparison: F-BASE `9a6e0ca` vs. F-NEW, same Q-BASE `3ef8387` and `qwen3:4b`.
  - One pair is a preliminary observation only.
- The baseline was recorded on F-BASE `9a6e0ca` before any change; F-NEW is implemented only afterwards, on its own branch.

## Next steps (max. 3)

1. S8 customer change CR-02 / HP-V2 through the Factory: shipping 1500 cent below 40 000 cent goods net after discount, free from exactly 40 000. Regression of all Q01–Q14 under HP-V2 and E01–E10 (line values and discounts unchanged), human review of Q06/Q10/Q11, versioned release (HP-AC08, HP-AC09).
2. S8 Factory experiment: implement exactly one small change (F-NEW) for the bottleneck above. Repeat R-02 from a fresh isolated copy of the same HP-V1 Q-BASE, with the same model, settings and checks and no reuse of baseline output, patches or caches. Compare with this baseline and decide keep / adapt / revert.
3. S8 handover and economic review: hand over startup, tests and rule description to the customer; reconcile S6–S8 cost totals; show with evidence what was reused from Nordwerk, what stayed customer-specific and which Factory investment we keep for a third customer.