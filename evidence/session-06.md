# Session 06 - 16/11/2026

Switch the existing Factory to a second customer (HansePack, customer project 02) and deliver a small, correctly calculating quotation case (Q01, Q03, E01) in a new, separate product repository – without changing the Nordwerk product.

> TODO markers = still open at the time of writing; remove before the final commit.


## Tasks/Responsibilities

| Task | Person | What |
| ---- | ------ | ---- |
| 1 | Francisco | Product repo `client-02-quotation`, customer fixtures + `SHA256SUMS` + `SOURCE.md`, README, customer issue TODO # |
|1 | Rafael | Project config projects/quotation-02.json, Factory brief docs/brief.md
| 1 | Fatih | Nordwerk `v1.0` frozen and checked (fresh checkout, tests, startup; Factory PR #50) |
| 1 | Daniil | Product planning: created functional product issues for `client-02-quotation` covering catalog validation, quotation calculation, web UI & export, and CR-02 shipping rules |
| 2 | Daniil | Factory adaptation: extended `ProjectConfig` with `implementer`, `ac_test_pattern`, and `review_hint` fields |
| 2 | Daniil | Factory adaptation: added dynamic dispatcher logic and generic review hints in `customer_workflow.py` |
| 2 | Caitlin | TODO (code implementer `run_python_implementer`?) |
| 2 | Daniil + Caitlin | Real Factory run on `quotation-02`: TODO |
| 2 | Francisco | Human reviewer at the gate: TODO |
| 3 | Fatih | Product checks Q01/Q03/E01 + interface stub `quotation/pricing.py` (product PR #1), catalogue loader `quotation/catalog.py` (product PR #3), Factory project separation test (Factory PR #48) |
|4 | Rafael | Time tracking, plan S6/S7 + reserve S8, this index

Only existing roles (`organization/roles.yaml`) were used; no new agents or roles. The Python implementer runs under the existing role `backend_api_engineer`.
Merged without a second review: Factory PR #49 (self-merged); direct pushes to `main`: Factory `69fa757`, `787e069` (project config). TODO: further.


## Repositories and commits

| | Repository | From | To |
|---|---|---|---|
| Factory | https://github.com/cait33/agentic_ai | `c0338aa` (end of S5) | TODO (final S6 commit) |
| HansePack product (new) | https://github.com/franciscotbatista99/client-02-quotation | `585341d` (initial commit) | TODO (result commit) |
| Nordwerk product (frozen) | https://github.com/franciscotbatista99/client-01-website | tag `v1.0` → `f1575ad` | unchanged |

Course materials S6–S8 synced into the Factory from `MARS-Group-HAW/agentic_ai` `course/session-03` (`f66013c`) via PR #47.


## 1. Order clarified, product repo created, Factory switched

- Customer issue: #2 (today's scope Q01/Q03/E01, open questions, explicit assumptions, responsibility)
- Customer fixtures: `fixtures/HansePack_Katalog.json` (sha256 `70f0e1a7…`), `fixtures/HansePack_Referenzfaelle.json` (sha256 `7deb994e…`), unchanged from the course repo; checked by `tests/test_fixtures.py` and `test_hp_ac01_fixtures_unchanged`
- Product start/test: README TODO; `python -m pytest tests -q`; CLI TODO
- Project config: `projects/quotation-02.json` – own `project_id`, product checkout `../client-02-quotation`, `target_file` `quotation/pricing.py`, `allowed_write_paths` `["quotation/"]`, `runs_dir` `runs/quotation-02`, `implementer` TODO
- Factory brief: docs/brief-t6.md

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
| Implementer | – | `web_slots` (HTML slots) → new `python_module` capability under role `backend_api_engineer`: TODO |
| Human gate hint | – | from config (`review_hint`) instead of the Nordwerk browser hint |
| AC mapping | – | configurable pattern (`ac_test_pattern`, here `test_hp_acNN_*`) |


## 2. Quotation case delivered by the Factory

Task given to the Factory: TODO (e.g. "Implement the Python calculation for HP-BOX with quantity 1 and 50 incl. discount, shipping and total. Reject quantity 0.")

| | |
|---|---|
| Run | `TODO` |
| Project / task | `quotation-02` / `TODO` |
| Inputs | product `TODO`, Factory `TODO`, brief `TODO` |
| Model / settings | TODO (Ollama qwen3:4b, temperature 0, JSON mode, reasoning off?) |
| Structured handover | PO agent → user stories (`requirements/*.json`) → implementer → `implementation-N.json` (file + sha256) → QA → `qa-round-N.json` → gate `review-N.json` |
| Agent contribution | `quotation/pricing.py` written by the implementer: TODO lines |
| Product check in the run | TODO passed / TODO failed |
| Correction rounds | TODO |
| Human gate | TODO name, time, decision, comment |
| Result commit / artifact sha256 | `TODO` / `TODO` |
| LLM calls / agent credits | TODO / TODO |
| Manual product work (counts as human work) | stub `quotation/pricing.py` (interface only), `quotation/catalog.py`, tests, fixtures, README – no business logic; TODO further |

Product logic is deterministic Python without LLM; prices come from the binding customer catalogue (`quotation/catalog.py`).


## 3. Checks

| Check | Expected (customer values) | Automated test | Result |
|---|---|---|---|
| Q01: HP-BOX × 1 | goods 250, shipping 1200, total 1450 cent | `test_hp_ac02_*[Q01]` (lines + totals + integer cents) | TODO |
| Q03: HP-BOX × 50 | list 12500, discount 625, goods 11875, shipping 1200, total 13075 cent | `test_hp_ac02_*[Q03]` | TODO |
| E01: quantity 0 | understandable error, no quote | `test_hp_ac04_*[E01]` (raises `QuoteError`, input not modified) | TODO |
| Independence | no Factory/LLM/network imports, no lookup of reference cases, fixtures unchanged | `test_hp_ac01_*` | TODO |
| Project separation | HansePack run changes no Nordwerk file; Nordwerk stays separately runnable | Factory `tests/factory/test_project_separation.py` (7 tests) + Nordwerk check above | 48 passed ([`factory-pytest.txt`](session-06/factory-pytest.txt)); TODO rerun on final state |

- Product test command: `cd client-02-quotation && python -m pytest tests -q` (expected values only from `fixtures/HansePack_Referenzfaelle.json`, never from the agent)
- Factory test command: `python -m pytest` (separation test included in the standard run, mocked agents, temporary git repos)
- Before the Factory run (stub): 9 failed / 8 passed – as expected. After the run: TODO
- Human review of result + code diff: TODO name, time


## Cost

Project-switch effort (second customer) is recorded separately from Factory development and delivery.

| Category | Who | Quantity | Credits |
| -------- | --- | -------- | ------- |
| Project switch: product repo, fixtures, issue, README | Rafael & Francisco | 1.5 h | 150.00 |
| Project switch: project config, brief | Rafael & Francisco | 1.0 h | 100.00 |
| Customer delivery: S6 evidence documentation and planning | Rafael | 1.5 h | 150.00 |
| Human review at the gate | Rafael | 1.0 h | 100.00 |
| Project switch: Nordwerk frozen check | Fatih | TODO | TODO |
| Factory development `FACTORY-S6`: ProjectConfig extension (implementer, ac_test_pattern, review_hint) | Daniil | 0.75 h | 75.00 |
| Factory development `FACTORY-S6`: workflow dispatcher & dynamic human gate hints | Daniil | 0.75 h | 75.00 |
| Customer delivery `CUST-002`: functional product issues definition for HansePack | Daniil | 0.25 h | 25.00 |
| Customer delivery: product checks, stub, catalogue loader | Fatih | TODO | TODO |
| Agents (Factory run(s), incl. failed attempts) | – | TODO calls | TODO |
| Human review at the gate | TODO | TODO | TODO |
| CI | – | none (Actions disabled) | 0 |

Unknown values are marked `unknown`, not 0.

### Plan

| Session | Planned scope | Budget (credits) |
|---|---|---|
| S6 | HP-AC01 first state, HP-AC02 (Q01, Q03), HP-AC04 E01, project separation | TODO |
| S7 | HP-AC03 (Q01–Q14), HP-AC04 (E01–E10), HP-AC05 web UI, HP-AC06 JSON export, HP-AC07 release candidate | TODO |
| S8 (reserve) | CR-02 / HP-V2 shipping rule (HP-AC08), HP-AC09 release | TODO |

Actual project-start effort S6: TODO h / TODO credits.


## Reuse learning

- **Reused:** TODO (see table in section 1)
- **Customer-specific:** TODO
- **Weakness to investigate next:** TODO
- No causal saving compared with Nordwerk is claimed – the two orders are different.


## Next steps (max. 3)

1. TODO
2. TODO
3. TODO
