# Session 04 - 02/11/2026

Deliver an independently runnable release candidate meeting AC-01–AC-08. The Factory handles further customer tasks and reliably distinguishes accepted results from results requiring correction. Save a baseline measurement for the improvement in Session 5.


## Tasks/Responsibilities

| Person    | Tasks                                                                                  |
| --------- | -------------------------------------------------------------------------------------- |
| Fatih     | Factory: implementer knows all 7 slots, prompt with markup                             |
| Fatih     | Factory tests: gate approved / rejected / escalated                                    |
| Fatih     | Product checks for required content, contact/navigation targets and local links/assets |
| Fatih     | Release gate (human + green check + unchanged hash), verify-only mode, failure case    |
| Fatih     | R-01 setup fix, R-01 baseline run, fresh checkout (AC-08)                              |
| Daniil    | Product structure: new sections with IDs + h2                                          |
| Daniil    | Empty AGENT markers for nav, audiences, approach                                       |
| Daniil    | Create the CSS for navigation, focus and 375 px                                        |
| Daniil    | Factory development: slot interface sync (7 slots, Pydantic model, system prompt) & merge conflict resolution   |
| Daniil    | Human gate reviewer for R-01                                                           |
| Francisco | Update S4 brief docs/customer-01/brief.md                                              |
| Francisco | Review: human gate reviewer for the customer run, review PR #16                        |
| Francisco | Helping Preparing R-01                                                                 |
| Francisco | Manually review the website and fill out the template                                  |
| Rafael    | Prepare R-01: separate checkout ~/client-01-website-r01                                |
| Rafael    | Own config projects/website-01-r01.json                                                |
| Rafael    | Fresh-checkout instructions for AC-08 in the README, tag `rc-1`                        |
| Caitlin   | Create issues for the criteria for this session                                        |
| Caitlin   | Create a template for the browser review                                               |
| Caitlin   | Create session-04.md                                                                   |

Role change: `agent_engineer` is Fatih from Session 4 on (previously Caitlin), `organization/roles.yaml` commit `cd68ac4`.
Manual product work (not by the agent): navigation markup, approach text and target-group draft by Daniil (product PR #13), slot marker fix (product PR #15).
Merged without a second review (time pressure): Factory PR #26, #30, product PR #10.


## Repositories and commits

Factory (https://github.com/cait33/agentic_ai):
From commit cd68ac4 (https://github.com/cait33/agentic_ai/commit/cd68ac4680b62ae0c54f3e421eb47b9841ea2c67)
to commit TODO (final main hash after this file and the costs are merged)
Client01 (https://github.com/franciscotbatista99/client-01-website):
From commit ce6074a (https://github.com/franciscotbatista99/client-01-website/commit/ce6074ab25b3fe8488d112b4fef73cbfbf1b1cef)
to commit d14e681 (https://github.com/franciscotbatista99/client-01-website/commit/d14e681)

Release candidate: tag `rc-1` → commit `cdbcba6` (merge of review PR #16).
AC checklist: `docs/acceptance.md` · browser review: `tests/browser_test_s4.md` (product repo).


## Factory run

Customer run `37079911-0dab-49e6-a4b9-0cec9c71d06d` (task `CUST-001`; the run manifest records `CUST-002` because the project config used that ID at run time – the team later decided to keep `CUST-001` for the whole customer order, evidence left unchanged), evidence `runs/website-01/37079911…` (PR #29):

| | |
|---|---|
| Inputs | product `2104d64`, factory `2dfb868`, brief `docs/customer-01/brief.md` |
| Model / settings | Ollama qwen3:4b `359d7dd4bcda`, temperature 0, JSON mode, reasoning off |
| Agents | PO 62.9 s (2256 in / 694 out) → web implementer 53.7 s (3414 in / 505 out) → QA 1.2 s |
| Tool actions | implementer wrote slots `nav`, `services`, `audiences`; `header`, `approach`, `contact`, `footer` unchanged |
| Product check | 23/23, AC-01–AC-08 passed, 0 correction rounds |
| Result | product `cdbcba6` = `rc-1`, artifact sha256 `a7a4bbd4…` |
| Costs | 2 LLM calls, 3.34 credits, token usage complete |

Factory changes for this run (reused config and workflow): implementer with 7 slots and "empty = unchanged" rule (PR #26, restored after merge conflict #27 in PR #28), release gate and AC mapping from product test names (PR #26), task ID `CUST-001` in `projects/website-01.json`.
Known issue: manifest field `max_output_tokens_implementer` shows 2048 (hard-coded), the actual value is 3072.


## Review and release

- Human gate: approved by Francisco, 2026-11-02 11:46 UTC, `release_status: released`, reviewed artifact hash `a7a4bbd4…`.
- Review diff: product PR #16 (`ef904f4`), merged into `cdbcba6`, tagged `rc-1`.
- Release gate: a state counts as released only if the human approved, the product check is green and the artifact hash is unchanged since QA; otherwise `not_released` with blockers.
- Product checks (`tests/test_site.py`, 23): A required content, B contact/navigation targets, C local links/assets, plus heuristics for AC-06–AC-08. Browser review 375/1280 px and keyboard/focus: `tests/browser_test_s4.md`. Fresh checkout: Fatih, 13:36, 23 passed, page loads, no Factory/LLM/DB.
- Controlled failure case on an isolated copy of `rc-1` (`projects/website-01-faultcase.json`, `--verify-only`, no agent writes):
  - run `536b4d37`: one fault `mailto:kontakt@nordwerk.exmaple` → 2 AC-04 tests red → gate offered no "approved" → escalated, `not_released`
  - run `41cd73ed`: fault reverted → 23/23 → `released`, hash identical to the candidate
- Deterministic Factory tests (mock LLM): `tests/factory`, 35 passed (released, red check, hash changed after QA, escalated, verify-only); stored in `evidence/session-04/factory-pytest.txt` + `.xml`. Real LLM runs: `37079911`, `536b4d37` (QA failure analysis), `3ba82f0f`.


## Baseline R-01

| | |
|---|---|
| R-BASE | `rc-1` → `cdbcba6` |
| F-BASE | `01017ae` (Factory code unchanged afterwards; later commits only add evidence) |
| Branch / checkout | `r01-baseline` in `~/client-01-website-r01`, input `66339b6` (rc-1 + `tests/test_r01.py`), result `97305f3`, not merged |
| Input / criteria | `docs/customer-01/r01.md` (verbatim task), `tests/test_r01.py` (2) + 23 existing checks |
| Model / settings | qwen3:4b `359d7dd4bcda`, temperature 0, JSON mode, reasoning off |
| Run | `3ba82f0f-41aa-413a-8776-9707f96ad117`, evidence `runs/website-01-r01/3ba82f0f…` (PR #33) |
| Check quality | 25/25 green, 0 correction rounds, failed attempts: none |
| Agent time | 63.6 s (PO 25.9 s, implementer 36.8 s, QA 0.8 s) |
| Review / rework | Daniil 13:25–13:27 local (≈ 2 min) / 0 min |
| Known costs | agents 2.72 credits; human 80.0 credits (Fatih 25, Daniil 5, Francisco 50) |
| Repeats | none (time) – one complete baseline run as required |


## Cost

Budgeted for Session 4 (delivery): 800 credits

| Category | Quantity | Credits |
| -------- | -------- | ------- |
| Agents CUST-001 (run 37079911) | 2 LLM calls | 3.34 |
| CI | no runs (Actions disabled) | 0.00 |
| Human Delivery CUST-001 (Fatih) | 0.80 h | 80.0 |
| Human Delivery CUST-001 (Rafael) | 2.00 h | 200.0 |
| Human Delivery CUST-001 (Caitlin) | 0.75 h | 75.0 |
| Human Review CUST-001 (Caitlin) | 1.00 h | 100.0 |
| Human Delivery CUST-001 (Daniil: semantic sections, IDs, AGENT markers) | 0.75 h | 75.0 |
| Human Delivery CUST-001 (Daniil: CSS navigation, focus outlines, 375 px mobile) | 0.75 h | 75.0 |
| Human Delivery CUST-001 (Francisco: updated S4 brief docs/customer-01/brief.md) | 1.25 h | 125.0 |
| Human Review CUST-001 (Francisco: manual browser review 375/1280 px, focus) | 0.25 h | 25.0 |
| Human Review CUST-001 (Francisco: human gate run 37079911 approval) | 0.10 h | 10.0 |
| **Session delivery CUST-001 (fully recorded)** | Agents 3.34 + Human 765.0 | **768.34** |
| **Total delivery CUST-001 (S3 + S4)** | Session 3 (437.74) + Session 4 (768.34) | **1206.08** |
| Factory development `FACTORY-S4` (separate, not in delivery budget) | agents 1.20 (failure case) + human 240.0 (Fatih 65, Caitlin 100, Daniil 75) | 241.20 |
| R-01 baseline (separate) | agents 2.72 + human 80.0 (Fatih 25, Daniil 5, Francisco 50) | 82.72 |
| S3 rework on S4 day (`CUST-001`, feedback fixes) | Fatih 0.25 h | 25.0 |

Plan vs. actual S4 delivery: 800 → 768.34 (-4.0 % deviation).
Reason for deviation: High agent precision on the first attempt (0 correction rounds needed for customer delivery) and modular slot architecture kept delivery within the planned 800 credits budget.
Cost data corrections on 2026-11-02 (values unchanged, marked "T4-Korrektur" in `notes`): duplicate rows removed, date format normalized to `2026-11-02`, consistent task ID `CUST-001` maintained for customer delivery.
S3 follow-up: 7 cost rows reassigned after feedback (values unchanged); S3 plan 300 vs. actual 437.74 (+46 %) kept as recorded.
## Bottleneck and hypothesis

- Bottleneck: the PO agent dominates agent runtime although the brief already specifies the content verbatim – S3 run `ec76867e` 45.5 s of 66.7 s (68 %), S4 run `37079911` 62.9 s of 117.8 s (53 %), R-01 run `3ba82f0f` 25.9 s of 63.6 s (41 %).
- Hypothesis for S5: if the PO output is reused when the brief hash is unchanged (and limited to the stories of the current task), agent time per R-01 run drops by at least 40 % (from 63.6 s to ≤ 38 s) with the same check quality (25/25, same number of correction rounds).
- Measure: sum of `duration_seconds` of all agents per run in `runs/website-01-r01/*/trace.jsonl`, R-01 baseline (S4) vs. R-01 repeat after the change (S5), same model and R-BASE.
