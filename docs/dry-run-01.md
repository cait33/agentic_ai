# Dry Run 01 – Persistent Work Items

> Max. 1 page. Fill in the <…> values before the 15:00 freeze.

## 1. What was implemented?
- REST API `/work-items` (create, list, mark done, delete) persisted in PostgreSQL (`db/migrations/001_work_items.sql`, `src/app/work_items.py`).
- API/persistence tests in `tests/api/test_work_items.py` against the real database.
- Agent workflow `src/agents/workflow.py`: Architect agent → QA agent → human gate.

## 2. Which humans and agents were involved?
| Step | Actor | Artefact |
|---|---|---|
| Issue / requirement | <human> | GitHub issue #<n> |
| Implementation of the API | <human / agent> | `src/app/work_items.py` |
| Architecture review | software-architect-agent | trace `<run_id>` |
| Test run + verdict | qa-agent | trace `<run_id>` |
| Final approval | <reviewer> (human gate) | `evidence/session-02/decisions/<workflow_id>.json` |

## 3. Where did a human correct or approve?
- <e.g. reviewer approved despite architect "changes_requested" because …>
- <corrections made to agent output, if any>

## 4. What did the workflow cost?
| Item | Quantity | Credits |
|---|---|---|
| Architect agent (1 LLM call) | <s>, <in>/<out> tokens | <x> |
| QA agent (0 LLM calls, all tests green) | <s> | <x> |
| Human implementation | <h> | <h × 100> |
| Human review | <h> | <h × 100> |
| CI runs | <n> | <n × 1> |
| **Total** | | **<sum>** |

Observation: the QA agent only calls the LLM when tests fail, so a green run costs ≈0.015 credits instead of ≈1.7 for an LLM review.

## 5. What do we try differently next time?
- <e.g. let the PO agent write acceptance criteria first and have the QA agent check them>
