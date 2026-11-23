# Session 07 - 23/11/2026

Complete the HansePack quotation calculator for the original HP-V1 rules (HP-AC01–HP-AC07), show that the Factory blocks an incorrect delivery after an intentionally injected discount fault, and preserve an R-02 baseline measurement for the Factory improvement in Session 8.

## Tasks/Responsibilities

| Task | Person | What |
| ---- | ------ | ---- |
| 1 | Daniil + Caitlin | Customer task E06/E09/E10 (input validation) through the Factory: real run `TODO`, result diff, human decision |
| 1 | Daniil + Caitlin | Small web UI (FastAPI + plain HTML/JS): enter lines, calculate, show result + errors, net notice (product PR #TODO) |
| 1 | Daniil + Caitlin | JSON download with the same calculated data as the display, integer cents, rule version (product PR #TODO) |
| 2 | Fatih | Product checks for all Q01–Q14 / E01–E10 (line values + totals) + JSON export contract test `tests/test_export.py` (product PR #9, `cb4c821`) |
| 2 | Fatih | Fresh checkout without the Factory, product and Factory tests run separately, organisation of the human UI review |
| 3 | Fatih + Francisco | Factory tests for passed and blocked gate states with mocked LLM (Factory PR #TODO) |
| 3 | Fatih + Francisco | Controlled discount fault on a separate branch: fault run `TODO` + correction run `TODO` |
| 3 | Francisco | Human reviewer at the gate: fault run TODO, correction run TODO |
| 4 | Rafael (+ Francisco) | Tags Q-BASE / F-BASE, R-02 baseline run `TODO` on an isolated copy, bottleneck + hypothesis for S8 |
| 4 | Rafael | Time tracking, plan deviations, this index |

Only existing roles (`organization/roles.yaml`) were used; no new agents or roles.
Merged without a second review: TODO; direct pushes to `main`: TODO. Reviewed by a second person: TODO.


## Repositories and commits

| | Repository | From | To |
|---|---|---|---|
| Factory | https://github.com/cait33/agentic_ai | `3269bdd` (end of S6) | TODO (merge commit of the final S7 evidence PR) |
| HansePack product | https://github.com/franciscotbatista99/client-02-quotation | `910ec24` (end of S6) | TODO (release candidate) |
| Nordwerk product (frozen) | https://github.com/franciscotbatista99/client-01-website | tag `v1.0` → `f1575ad` | unchanged |

Release candidate = Q-BASE: tag `TODO` → product `TODO`. F-BASE: tag `TODO` → Factory `TODO`.


## 1. Calculation scope completed, small UI built

- Starting point: the S6 agent code (`910ec24`) already gets all Q01–Q14 right. E06 (duplicate SKU), E09 (`True` as quantity) and E10 (quantity 10 001) are not rejected yet, and there is no web UI and no JSON export.
- Customer issue: #TODO (S7 scope: E06/E09/E10, web UI, JSON export)
- Factory task: brief `TODO`. Project config `projects/quotation-02.json` reused; changes: TODO (brief path, `review_hint` for E06/E09/E10)
- Web UI: FastAPI + plain HTML/CSS/JavaScript.
  - Files: `TODO`.
  - Made by: TODO (Factory run / by hand by Daniil + Caitlin – manual work counts as human work).
  - Start command: `TODO`.
  - Dependencies and startup documented in the README: TODO (the README still says "no runtime dependencies").
- Validation: invalid input reaches `calculate_quote` in Python and is rejected there with `QuoteError`; the UI only shows the server error (no UI-only validation)
- Net notice "Nettobeträge – Lehrprojekt, kein verbindliches Angebot" visible on the page
- JSON export `quotation/export.py`: built from the same `calculate_quote` result as the display. Per line: SKU, quantity, unit price, list amount, discount %, discount and line net. Totals: goods net, shipping, total, currency `EUR` and `rule_version` `HP-V1`. Money values are integer cents.

### Factory run: input validation E06/E09/E10

Task given to the Factory: reject duplicate SKUs (E06), Boolean quantities (E09) and quantities > 10 000 (E10) in `quotation/pricing.py` with `QuoteError`. No silent type coercion or SKU aggregation is allowed, and Q01–Q14 must stay correct. Results are checked by the team's product tests, not by the agent.

| | |
|---|---|
| Run | `TODO` (raw data `runs/quotation-02/TODO…`, Factory PR #TODO) |
| Project / task | `quotation-02` / `CUST-002`, customer issue #TODO |
| Inputs | product `TODO` (`git status` clean: TODO), Factory `TODO`, brief `TODO` |
| Model / settings | TODO |
| Structured handover | PO agent → user stories (`requirements/*.json`) → backend-api-agent → `implementation-N.json` (file + sha256) → QA agent → `qa-round-N.json` (failed tests as feedback) → gate `review-N.json` |
| Round 0 | TODO |
| Round 1 (correction) | TODO |
| Correction rounds | TODO of max. 2 |
| Human gate | TODO (name), `TODO`, TODO UTC (TODO local), review hint: diff + `pytest` + E06/E09/E10; comment: TODO |
| Result | TODO, product result commit `TODO`, artifact sha256 `TODO…` |
| Agent contribution | TODO (`quotation/pricing.py`, lines changed, link to diff) |
| LLM calls / agent credits | TODO |
| Duration | agent time ≈ TODO s; workflow incl. human wait TODO s |
| Manual product work (counts as human work) | TODO |

Notes: TODO (e.g. checkout state at start, PO cache hit/miss, test runs not in the repository).


## 2. Customer-provided results tested

| Check | Expected (customer values) | Automated test | Result |
|---|---|---|---|
| Q01–Q14 line values (HP-V1) | List amount, discount %, discount and line net, with tier boundaries 49/50/99/100. Rounding cases: Q04 1237.5 → 1238, Q13 3187.5 → 3188, Q14 662.5 → 663 (HALF_UP). | `test_hp_ac03_lines_match_customer_values[Q01–Q14]` | TODO |
| Q01–Q14 totals (HP-V1) | goods net, shipping, total; Q06 shipping after discount (45 000 → 1200), Q07 at threshold (50 000 → 0) | `test_hp_ac03_totals_*` | TODO |
| E01–E10 | Rejected in Python with `QuoteError` and no quote. Input is not modified, types are not coerced and SKUs are not aggregated. | `test_hp_ac04_*[E01–E10]`, `test_hp_ac04_duplicate_sku_is_not_aggregated`, `test_hp_ac04_no_silent_type_coercion` | TODO |
| JSON export | required fields, integer cents, rule version, export = calculation | `tests/test_export.py` (`test_hp_ac06_*`) | TODO |
| Independence | no Factory/LLM/network imports, no lookup of reference answers, fixtures unchanged | `test_hp_ac01_*` + `tests/test_fixtures.py` | TODO |
| Factory | gate passed/blocked, loop limit, project separation | Factory `python -m pytest` | TODO passed ([`factory-pytest.txt`](session-07/factory-pytest.txt)) |

- Product test command: `cd client-02-quotation && python -m pytest` (expected values only from `fixtures/HansePack_Referenzfaelle.json`, never from the agent)
- Factory test command: `python -m pytest` in the Factory repo, run separately
- Product check results:
  - Before the Factory run (`66f9c5e`, after product PR #9): 89 passed / 8 failed / 1 skipped. The 8 failures are E06, E09 and E10, including the no-aggregation and no-coercion checks. The skipped test is the export test, because `quotation/export.py` was not implemented yet.
  - In the run: TODO.
  - Final candidate `TODO`: **TODO passed** ([`product-pytest.txt`](session-07/product-pytest.txt), Fatih).
- Expected values unchanged; differences found: TODO (none / which, how resolved, escalation to the instructor)
- Human UI review: TODO (name), TODO (time), product `TODO`.
  - Multi-line quotation: TODO (e.g. Q12: HP-BOX × 50 + HP-TAPE × 10 → total 17 075 cent).
  - JSON downloaded and compared with the display: TODO.
  - Invalid quantity TODO → error "TODO"; no quotation shown: TODO.
  - Net notice visible: TODO.

**Fresh checkout:** TODO (name), TODO (time):
- clone of `TODO`, with `git status` clean;
- installed as in the README;
- `python -m pytest` → TODO passed;
- UI starts with `TODO`;
- no Factory, LLM or database needed.

Record: [`evidence/session-07/fresh-checkout.txt`](session-07/fresh-checkout.txt).


## 3. Controlled business fault injected

Fault injected on an isolated copy of the candidate: the 5 % discount starts **above 50** instead of **from 50**. Exactly one condition was changed in `quotation/pricing.py` (`quantity <= 49` → `quantity <= 50`); customer expectations and tests are unchanged.

| | |
|---|---|
| Isolated state | branch `TODO`, checkout `TODO`, based on candidate `TODO`, fault commit `TODO`; Factory config `TODO` |
| Expected effect | Q03 total 13 700 instead of 13 075 cent. Q12 contains HP-BOX × 50, so it gives 17 700 instead of 17 075. Checked in advance on `66f9c5e`: exactly 6 tests turn red (`test_hp_ac02_lines/totals[Q03]`, `test_hp_ac03_lines/totals[Q03]`, `test_hp_ac03_lines/totals[Q12]`). |
| Fault run | `TODO`: product check TODO failed → gate TODO (no "approved" offered / `changes_requested` / correction round) → `not_released`, blockers: TODO |
| Correction | TODO (by the agent in a correction round / by hand), commit `TODO` |
| Correction run | `TODO`: TODO passed / 0 failed, artifact hash TODO (identical to the candidate: TODO) |
| Human gate | Francisco: fault run `TODO` (TODO UTC), correction run `TODO` (TODO UTC) |
| Delivered? | No – the fault state was never merged, tagged or released |

- Factory gate tests (mocked LLM): `tests/factory/TODO`, Factory PR #TODO. Result: TODO passed.
  - Passed state: green check + human approval → `released`.
  - Blocked state: red check → no approval, `not_released`.
  - The loop-limit and project-separation tests still pass.
- Mock tests show the workflow logic, not real LLM use; real LLM runs: TODO


## 4. R-02 baseline before improvement

Task R-02 (verbatim, `TODO`): add `calculation_note` to exported quotation JSON with fixed text `Net amounts; shipping shown separately.`. Preserve display, money values and error handling. Add a test for the field; all existing business tests must still pass. Experiment only – not merged into the customer candidate.

| | |
|---|---|
| Q-BASE / F-BASE | product `TODO` (tag `TODO`) / Factory `TODO` (tag `TODO`) |
| Branch / checkout | `TODO` in isolated copy `TODO`, `git status` clean at start: TODO; result `TODO`, not merged |
| Input / criteria | R-02 text, `TODO` (R-02 test) + all existing business tests |
| Model / settings | TODO |
| Run | `TODO` (raw data `runs/TODO/…`, Factory PR #TODO); second run: TODO / not done (time) |
| Check quality | TODO/TODO green, correction rounds TODO, failed attempts: TODO |
| Agent time / LLM calls | TODO s (PO TODO s, implementer TODO s, QA TODO s) / TODO |
| Review / rework | TODO (name), TODO min / TODO min |
| Known costs | agents TODO credits; human TODO credits; unknown: TODO |
| Result | TODO (a failed full run also counts as baseline and stays visible) |


## Cost

Factory development and the R-02 experiment are recorded separately from customer delivery.

| Category | Who | Quantity | Credits |
| -------- | --- | -------- | ------- |
| Customer delivery `CUST-002`: Factory task E06/E09/E10 (brief, run operation) | Daniil | TODO h | TODO |
| Customer delivery `CUST-002`: Factory task E06/E09/E10 (brief, run operation) | Caitlin | TODO h | TODO |
| Customer delivery `CUST-002`: web UI + JSON export | Daniil | TODO h | TODO |
| Customer delivery `CUST-002`: web UI + JSON export | Caitlin | TODO h | TODO |
| Customer delivery `CUST-002`: product checks Q01–Q14 / E01–E10 + export test (product PR #9) | Fatih | TODO h | TODO |
| Customer delivery `CUST-002`: fresh checkout, organisation of the human UI review | Fatih | TODO h | TODO |
| Customer delivery `CUST-002`: time tracking, plan, this index | Rafael | TODO h | TODO |
| Review `CUST-002`: human UI/export review | TODO | TODO h | TODO |
| Review `CUST-002`: human gate (task run, fault run, correction run) | Francisco | TODO h | TODO |
| Factory development `FACTORY-S7`: gate tests passed/blocked (mocked LLM) | Fatih | TODO h | TODO |
| Factory development `FACTORY-S7`: gate tests passed/blocked (mocked LLM) | Francisco | TODO h | TODO |
| Factory development `FACTORY-S7`: fault case (fault branch, fault + correction runs) | Fatih | TODO h | TODO |
| Factory development `FACTORY-S7`: fault case (fault branch, fault + correction runs) | Francisco | TODO h | TODO |
| R-02 baseline (separate): setup, run operation, recording | Rafael | TODO h | TODO |
| R-02 baseline (separate): support | Francisco | TODO h | TODO |
| Agents `CUST-002`: run `TODO` (incl. failed rounds) | – | TODO LLM calls | TODO |
| Agents `FACTORY-S7`: fault run `TODO` + correction run `TODO` | – | TODO LLM calls | TODO |
| Agents `R-02`: run `TODO` (incl. failed runs) | – | TODO LLM calls | TODO |
| Agents: test runs not in the repository | – | unknown | unknown |
| CI | – | TODO (none – Actions disabled / N runs incl. failed runs) | TODO |

Unknown values are marked `unknown`, not 0.

### Plan

| Session | Planned scope | Budget (credits) |
|---|---|---|
| S7 | HP-AC03 (Q01–Q14), HP-AC04 (E01–E10), HP-AC05 web UI, HP-AC06 JSON export, HP-AC07 release candidate | 1600 (team planning from S6: 5 people × ≈ 3 h = 1500 + ≈ 25 agent runs à ≈ 4 credits) · **actual TODO** |
| S8 (reserve) | CR-02 / HP-V2 shipping rule (HP-AC08), HP-AC09 release, Factory change + R-02 repeat | 600 reserve |

Budgets are a team planning proposal, not agreed with the instructor yet.

Actual S7 effort (from `costs/usage.csv`): **TODO h human + TODO agent credits + TODO CI = TODO credits** (`CUST-002` TODO, `FACTORY-S7` TODO, R-02 TODO).
Plan deviations: TODO (planned vs. actual and reason, incl. budget over/under).


## Bottleneck and hypothesis

- **Observed bottleneck:** TODO (with numbers from `trace.jsonl` / `manifest.json` of today's runs)
- **Small Factory change planned for S8:** TODO
- **Hypothesis / measure:** if TODO, then TODO changes from TODO (R-02 baseline) to TODO with the same check quality; measured per R-02 run, F-BASE vs. F-NEW, same Q-BASE and model
- The baseline was recorded on F-BASE `TODO` before any change; the change is implemented only afterwards.


## Next steps (max. 3)

1. S8: CR-02 / HP-V2 shipping rule (1500 cent below 40 000 cent goods net, free from 40 000) through the Factory; tests against the HP-V2 expectations, versioned release and handover (HP-AC08, HP-AC09).
2. S8: implement the planned Factory change and repeat R-02 on the same Q-BASE with the same model; compare with this baseline.
3. TODO (open finding from today)