# Dry Run 01 – Persistent Work Items

Issue: [#10](https://github.com/cait33/agentic_ai/issues/10) · Task: `WF-DRYRUN-02` · Workflow: `df946132-32f8-4348-bea4-6802e61006b4`

## 1. What was implemented?
- REST API `/work-items` (create, list, mark done, delete), persisted in PostgreSQL via an idempotent migration (`db/migrations/001_work_items.sql`, `src/app/work_items.py`).
- 8 API/persistence tests against the real database (`tests/api/test_work_items.py`).
- Agent workflow `src/agents/workflow.py`: Architect agent → QA agent → human gate, hand-over via LangGraph state, shared `EngineeringTask` (`src/models/task.py`), 11 workflow tests.

## 2. Which humans and agents were involved?
| Step | Actor | Artefact |
|---|---|---|
| Requirement | Team (human) | Issue #10 |
| Implementation | Fatih (human, AI-assisted) | `src/app/work_items.py`, tests |
| Architecture review | software-architect-agent (qwen3:4b) | trace `4726e9d4-0b91-4d94-b826-45dfb9a77ac8` |
| Test run + verdict | qa-agent | trace `bbb706ae-c818-47d7-99a4-eb44c45d6832` (19/19 passed) |
| Final decision | Fatih (human gate) | `evidence/session-02/decisions/df946132-32f8-4348-bea4-6802e61006b4.json` |

## 3. Where did a human correct or approve?
- The architect's answer was cut off at the 768-token output limit (qwen3 spends tokens on reasoning) → result `unparseable` → workflow recommended `escalate_to_human`.
- Fatih reviewed `work_items.py` manually and, with QA 19/19 green, decided `approved` with a written justification.
- A first run (`776fba10…`) was approved without a comment; we discarded it as evidence and repeated the run with a documented decision.

## 4. What did the workflow cost?
| Item | Quantity | Credits |
|---|---|---|
| Architect agent | 1 call, 40 s, 1008 in / 768 out tokens | 1.45 |
| QA agent | 0 LLM calls, 1.6 s | 0.02 |
| Human review at gate | 0.25 h | 25.0 |
| Human implementation (workflow, human gate, API, tests) | 4.0 h | 400.0 |
| CI runs | 0 (GitHub Actions not enabled in repo) | 0 |
| **Agents total** | | **1.47** |
| **Workflow total (agents + humans)** | | **426.47** |

Agent cost is negligible compared to human time (1.47 vs. 425 credits, < 0.4 %). The QA agent calls the LLM only when tests fail, so a green run costs ≈0.02 instead of ≈1.5 credits for an LLM review.

## 5. What do we try differently next time?
- Raise the output-token budget for reasoning models (or disable thinking) for the architect, so its review is parseable instead of escalating every time.
- Mark unparseable architect results as `invalid_output` in its trace (currently logged as `success`).
- Put the PO agent in front of the workflow, so acceptance criteria exist before implementation and QA can check against them.
