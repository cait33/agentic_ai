# Session 06 - 16/11/2026

Switch the existing Factory to a second customer (HansePack, customer project 02) and deliver a small, correctly calculating quotation case (Q01, Q03, E01) in a new, separate product repository – without changing the Nordwerk product.

## Tasks/Responsibilities

| Task | Person | What |
| ---- | ------ | ---- |
| 1 | Francisco | Created product repo `client-02-quotation`; customer fixtures with checksums, provenance checks `tests/test_fixtures.py`, README start/test commands (product PR #4); Factory brief `docs/customer-02/brief-t6.md` + completed `projects/quotation-02.json` (Factory PR #52); task ID `CUST-002` |
| 1 | Rafael | First project config `projects/quotation-02.json` (completed by Francisco), planning, issue definitions with Francisco |
| 1 | Fatih | Nordwerk `v1.0` frozen and checked (fresh checkout, tests, startup; Factory PR #50) |
| 1 | Daniil | Product planning: created functional product issues for `client-02-quotation` covering catalog validation, quotation calculation, web UI & export, and CR-02 shipping rules |
| 2 | Daniil | Factory adaptation: extended `ProjectConfig` with `implementer`, `ac_test_pattern`, and `review_hint` fields |
| 2 | Daniil | Factory adaptation: added dynamic dispatcher logic and generic review hints in `customer_workflow.py` |
| 2 | Caitlin | Factory adaptation: generic Python module implementer `run_python_implementer` for role `backend_api_engineer` (branch `generic_code_implementer`, merged 14:43); review of the first version by Fatih (bug list 13:15) |
| 2 | Daniil + Caitlin | Real Factory run `6b975659` on `quotation-02` (1 correction round, released), result commit `910ec24`, run evidence (Factory PR #55) |
| 2 | Francisco | Human reviewer at the gate: approved 13:46 UTC (14:46 local) |
| 3 | Fatih | Final checks on the result: product 17 passed, Factory 48 passed (`evidence/session-06/product-pytest.txt`, `factory-pytest.txt`) |
| 3 | Fatih | Product checks Q01/Q03/E01 + interface stub `quotation/pricing.py` (product PR #1), catalogue loader `quotation/catalog.py` (product PR #3), Factory project separation test (Factory PR #48) |
| 4 | Rafael | Time tracking, plan S6/S7 + reserve S8, this index |
| 4 | Fatih | Index skeleton (PR #51), completion with run data, own costs |

Only existing roles (`organization/roles.yaml`) were used; no new agents or roles. The Python implementer runs under the existing role `backend_api_engineer`.
Merged without a second review: Factory PRs #49, #54, #55 (self-merged by Daniil), branch `generic_code_implementer` (merged by Caitlin without PR); direct pushes to `main`: Factory `69fa757`, `787e069` (project config), product `910ec24` (agent result, pushed by Daniil without PR). Reviewed by a second person: Factory PR #52 (Francisco's brief, merged by Rafael), product PR #4 (Francisco's fixtures, merged by Rafael).


## Repositories and commits

| | Repository | From | To |
|---|---|---|---|
| Factory | https://github.com/cait33/agentic_ai | `c0338aa` (end of S5) | merge commit of the final S6 evidence PR (`main`) |
| HansePack product (new) | https://github.com/franciscotbatista99/client-02-quotation | `585341d` (initial commit) | `910ec24` (agent result, Factory run `6b975659`) |
| Nordwerk product (frozen) | https://github.com/franciscotbatista99/client-01-website | tag `v1.0` → `f1575ad` | unchanged |

Course materials S6–S8 synced into the Factory from `MARS-Group-HAW/agentic_ai` `course/session-03` (`f66013c`) via PR #47.


## 1. Order clarified, product repo created, Factory switched

- Customer issue: #2 (today's scope Q01/Q03/E01, open questions, explicit assumptions, responsibility)
- Customer fixtures: `fixtures/HansePack_Katalog.json` (sha256 `70f0e1a7…`), `fixtures/HansePack_Referenzfaelle.json` (sha256 `7deb994e…`), unchanged from the course repo; checked by `tests/test_fixtures.py` and `test_hp_ac01_fixtures_unchanged`
- Product start/test: README (Francisco); `python -m pytest tests -q`; reproducible call: `python -c "from quotation.pricing import calculate_quote; print(calculate_quote([{'sku': 'HP-BOX', 'quantity': 50}]))"` (web UI follows in S7)
- Project config: `projects/quotation-02.json` – own `project_id`, product checkout `../client-02-quotation`, `target_file` `quotation/pricing.py`, `allowed_write_paths` `["quotation/"]`, `runs_dir` `runs/quotation-02`, `implementer` `python_module`, `ac_test_pattern` `test_hp_acNN_*`, `review_hint` with the expected Q01/Q03/E01 values, task ID `CUST-002`
- Factory brief: `docs/customer-02/brief-t6.md` (Francisco): today's scope, interface, use of `catalog.py`, HP-V1 rules (discount, ROUND_HALF_UP, shipping, validation), no case IDs / LLM / network in the product

**Nordwerk frozen:** fresh checkout of tag `v1.0` (`f1575ad`), `git status` clean, 44 passed, `index.html` + `en.html` start via `python3 -m http.server` (Fatih, 12:10) – [`evidence/session-06/nordwerk-v1.0-check.txt`](session-06/nordwerk-v1.0-check.txt).

### Reuse vs. adaptation

| Component | Reused unchanged | Adapted for HansePack |
|---|---|---|
| LangGraph customer workflow (PO → implementer → QA → gate, max. 2 correction rounds) | ✅ | dispatcher by `cfg.implementer` (PR #49) |
| Product owner agent, PO cache (F-NEW) | ✅ | – |
| QA agent (runs the product's own pytest in the product checkout) | ✅ | – |
| Write guard `ProjectConfig.product_file()` + `allowed_write_paths` | ✅ | – |
| Release gate / blockers (human decision + green check + unchanged hash) | ✅ | – |
| Run evidence (`runs/<project>/<run_id>/`, manifest, trace, `--record-result`, `--verify-only`) | ✅ | manifest field `implementer_mode` |
| Cost model / tracing | ✅ | – |
| Implementer | – | `web_slots` (HTML slots) → new `python_module` capability `run_python_implementer` under the existing role `backend_api_engineer`: reads brief + PO stories + current stub, 1 LLM call, AST safety + stub-contract check, writes only `cfg.target_file` via the write guard |
| Human gate hint | – | from config (`review_hint`) instead of the Nordwerk browser hint |
| AC mapping | – | configurable pattern (`ac_test_pattern`, here `test_hp_acNN_*`) |


## 2. Quotation case delivered by the Factory

Task given to the Factory (brief `docs/customer-02/brief-t6.md`): implement `calculate_quote` in `quotation/pricing.py` for HP-BOX with quantity 1 and 50 incl. discount, rounding, shipping and total under HP-V1, and reject quantity 0 – checked by the team's product tests, not by the agent.

| | |
|---|---|
| Run | `6b975659-9a72-4e7a-b980-d4f0333c648d` (raw data `runs/quotation-02/6b975659…`, Factory PR #55) |
| Project / task | `quotation-02` / `CUST-002`, customer issue #2 |
| Inputs | product `c23811d` (stub + checks + fixtures + catalogue loader), Factory `68b15a1`, brief `docs/customer-02/brief-t6.md` |
| Model / settings | Ollama qwen3:4b, temperature 0, JSON mode, reasoning off, implementer max. 3072 output tokens |
| Structured handover | PO agent → user stories (`requirements/*.json`, PO cache hit) → backend-api-agent → `implementation-N.json` (file + sha256) → QA agent → `qa-round-N.json` (failed tests as feedback) → gate `review-1.json` |
| Round 0 | implementer wrote `pricing.py` (`2cbf2412…`) → product checks 8 passed / 9 failed: `NameError: load_catalog` (import missing) → QA `changes_requested` with the failing tests as feedback |
| Round 1 (correction) | implementer added the import (`6618da55…`) → **17 passed / 0 failed** → QA `approved` |
| Correction rounds | 1 of max. 2 |
| Human gate | Francisco, `approved`, 13:46 UTC (14:46 local), review hint: diff + `pytest` + expected Q01/Q03/E01 values; no comment recorded |
| Result | `released`, product result commit `910ec24`, artifact sha256 `6618da55…`; HP_AC01 / HP_AC02 / HP_AC04 passed |
| Agent contribution | `quotation/pricing.py`, 102 lines (validation, catalogue prices, quantity discount, ROUND_HALF_UP in integer cents, shipping, totals) |
| LLM calls / agent credits | 4 agent calls with LLM (implementer 2, QA 1) + PO from cache → 3 LLM calls in the manifest, **3.95 credits** (implementer 1.31 + 1.43, QA 1.20 + 0.01, PO 0.00) |
| Duration | agent time ≈ 68 s; workflow incl. human wait 1695 s (≈ 28 min until the gate decision) |
| Manual product work (counts as human work) | stub `quotation/pricing.py` (interface only), `quotation/catalog.py`, tests, fixtures, README – no business logic. The agent result was committed unchanged (`910ec24`). |

Notes: the run started on a product checkout with local changes (`product_dirty_at_start: true`); the PO result came from the F-NEW cache of an earlier run `d59125d8` that is not in the repository (test run, its agent costs are `unknown`).

Product logic is deterministic Python without LLM; prices come from the binding customer catalogue (`quotation/catalog.py`).


## 3. Checks

| Check | Expected (customer values) | Automated test | Result |
|---|---|---|---|
| Q01: HP-BOX × 1 | goods 250, shipping 1200, total 1450 cent | `test_hp_ac02_*[Q01]` (lines + totals + integer cents) | ✅ passed |
| Q03: HP-BOX × 50 | list 12500, discount 625, goods 11875, shipping 1200, total 13075 cent | `test_hp_ac02_*[Q03]` | ✅ passed |
| E01: quantity 0 | understandable error, no quote | `test_hp_ac04_*[E01]` (raises `QuoteError`, input not modified) | ✅ passed |
| Independence | no Factory/LLM/network imports, no lookup of reference cases, fixtures unchanged | `test_hp_ac01_*` + `tests/test_fixtures.py` | ✅ passed |
| Project separation | HansePack run changes no Nordwerk file; Nordwerk stays separately runnable | Factory `tests/factory/test_project_separation.py` (7 tests) + Nordwerk check above | ✅ 48 passed on the final Factory state ([`factory-pytest.txt`](session-06/factory-pytest.txt)) |

- Product test command: `cd client-02-quotation && python -m pytest tests -q` (expected values only from `fixtures/HansePack_Referenzfaelle.json`, never from the agent)
- Factory test command: `python -m pytest` (separation test included in the standard run, mocked agents, temporary git repos)
- Before the Factory run (stub): 9 failed / 8 passed – as expected. In the run: round 0 8/9, round 1 17/0. Final product state `910ec24`: **17 passed** ([`product-pytest.txt`](session-06/product-pytest.txt), Fatih)
- Human review at the gate: Francisco, 13:46 UTC, decision based on the gate summary (QA 17/17); no separate code diff review recorded
- Known gaps for S7 (not tested today): the agent code does not yet reject `bool` quantities, quantities > 10 000, duplicate SKUs or more than 3 lines (E02–E10)


## Cost

Project-switch effort (second customer) is recorded separately from Factory development and delivery.

| Category | Who | Quantity | Credits |
| -------- | --- | -------- | ------- |
| Project switch `CUST-002`: product repo, customer fixtures with checksums, provenance checks, README | Francisco | 1.5 h | 150.00 |
| Project switch `FACTORY-S6`: Factory brief + completed project config | Francisco | 0.5 h | 50.00 |
| Project switch `CUST-002`: planning, issue definitions, first project config | Rafael | 1.0 h | 100.00 |
| Customer delivery `CUST-002`: S6 evidence documentation and planning | Rafael | 1.5 h | 150.00 |
| Review `CUST-002`: pull requests of the initial HansePack setup | Rafael | 0.5 h | 50.00 |
| Project switch `CUST-002`: Nordwerk `v1.0` frozen check + catalogue loader | Fatih | 0.2 h | 20.00 |
| Factory development `FACTORY-S6`: ProjectConfig extension (implementer, ac_test_pattern, review_hint) | Daniil | 0.75 h | 75.00 |
| Factory development `FACTORY-S6`: workflow dispatcher & dynamic human gate hints | Daniil | 0.75 h | 75.00 |
| Customer delivery `CUST-002`: functional product issues definition for HansePack | Daniil | 0.25 h | 25.00 |
| Factory development `FACTORY-S6`: created the generic code implementer for the backend api engineer | Caitlin | 3 h | 300.00 |
| Customer delivery `CUST-002`: product checks Q01/Q03/E01 + interface stub | Fatih | 0.4 h | 40.00 |
| Customer delivery `CUST-002`: evidence skeleton, final checks, completion of this index | Fatih | 0.35 h | 35.00 |
| Factory development `FACTORY-S6`: project separation test (PR #48), course sync (PR #47) | Fatih | 0.3 h | 30.00 |
| Review `FACTORY-S6`: review of the first implementer version (bug list) | Fatih | 0.15 h | 15.00 |
| Agents `CUST-002`: run `6b975659` (incl. failed round 0) | – | 3 LLM calls | 3.95 |
| Agents: earlier test run(s), e.g. `d59125d8` (not in the repository) | – | unknown | unknown |
| Human review at the gate `CUST-002` (runs `796ac9f1`, `6b975659`) | Francisco | 0.1 h | 10.00 |
| CI | – | none (Actions disabled) | 0 |

Unknown values are marked `unknown`, not 0.

### Plan

| Session | Planned scope | Budget (credits) |
|---|---|---|
| S6 | HP-AC01 first state, HP-AC02 (Q01, Q03), HP-AC04 E01, project separation | – (no budget agreed before the session) · **actual 1128.95** |
| S7 | HP-AC03 (Q01–Q14), HP-AC04 (E01–E10), HP-AC05 web UI, HP-AC06 JSON export, HP-AC07 release candidate | 1600 (team planning: 5 people × ≈ 3 h = 1500 + ≈ 25 agent runs à ≈ 4 credits) |
| S8 (reserve) | CR-02 / HP-V2 shipping rule (HP-AC08), HP-AC09 release | 600 reserve (one rule change + regression + release, based on the S5 change request CR-01: ≈ 685) |

Budgets are a team planning proposal, not agreed with the instructor yet.

Actual S6 effort (from `costs/usage.csv`): **11.25 h human + 3.95 agent credits = 1128.95 credits** (`CUST-002` 558.95, `FACTORY-S6` 570.00).
Of this, **project-switch effort** for the second customer: **3.2 h = 320 credits** (product repo + fixtures + README 1.5 h, Factory brief + config 0.5 h – Francisco; planning + first config 1.0 h – Rafael; Nordwerk freeze check + catalogue loader 0.2 h – Fatih).
One-off Factory development (`FACTORY-S6`, separate): 5.7 h incl. 0.25 h product issues booked there by Daniil.


## Reuse learning

- **Reused unchanged:** LangGraph workflow, PO agent + PO cache, QA agent, write guard `product_file()`, release gate/blockers, run evidence, cost model – the HansePack run needed no change to any of them. The project separation test passes without new separation code (write guard + own `runs_dir` from S3).
- **Customer-specific:** new product repo with fixtures/checks/stub, project config + brief, and one new capability (`python_module` implementer) because the Nordwerk implementer could only fill HTML slots.
- **Weakness to investigate next:** the implementer's static check accepts code that uses a name it never imports (round 0 failed with `NameError: load_catalog` and needed a correction round + 2.6 credits); in addition the `python_module` implementer has no deterministic mock-LLM tests in `tests/factory` yet.
- No causal saving compared with Nordwerk is claimed – the two orders are different.


## Next steps (max. 3)

1. S7: extend the product checks to all Q01–Q14 / E01–E10 (`TODAY_VALID` / `TODAY_INVALID`) and let the Factory close the known gaps (`bool` quantity, > 10 000, duplicate SKU, > 3 lines).
2. Factory: mock-LLM tests for `run_python_implementer` and an undefined-name check before writing, so missing imports are rejected without a paid QA round.
3. Run every Factory run from a clean product checkout and keep all test runs (incl. `d59125d8`) with their costs in the repository.
