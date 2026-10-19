# Dry Run 01 – Persistent Work Items

Issue: [#10](https://github.com/cait33/agentic_ai/issues/10) · Task: `WF-DRYRUN-03` · Workflow: `08afe4bb-2897-4a96-9316-88bf98f64f20`

## 1. What was implemented?
- REST API `/work-items` (create, list, mark done, delete), persisted in PostgreSQL via an idempotent migration (`db/migrations/001_work_items.sql`, `src/app/work_items.py`), 8 API/persistence tests against the real database.
- Agent workflow `src/agents/workflow.py`: **PO agent → Architect agent → QA agent → human gate**. Hand-over via LangGraph state; all agents receive the shared `EngineeringTask` (`src/models/task.py`).
- Input: project brief `tests/briefs/work-items.md`; PO output: `docs/requirements/WF-DRYRUN-03/`.

## 2. Which humans and agents were involved?
| Step | Actor | Artefact |
|---|---|---|
| Requirement | Fatih (human) | Issue #10, brief `tests/briefs/work-items.md` |
| Requirements, user stories, backlog | product-owner-agent | trace `8079d2a1-1e1d-4adb-a249-44f7e9c7de27`, `docs/requirements/WF-DRYRUN-03/` |
| Implementation | Fatih (human, AI-assisted) | `src/app/work_items.py`, tests |
| Architecture review | software-architect-agent | trace `605d975d-bc32-4e1e-889c-0b73b7c6bf10` |
| Test run + verdict | qa-agent | trace `6df7608e-038a-4785-96c5-bb437f9d757b` (21/21 passed) |
| Final decision | Fatih (human gate) | `evidence/session-02/decisions/08afe4bb-2897-4a96-9316-88bf98f64f20.json` |

## 3. Where did a human correct or approve?
- **PO output:** the model invented an acceptance criterion not in the brief (US3 "only owner can delete") and missed "invalid input rejected" and "API tests" → corrected by the human at the gate.
- **Architect:** answer cut off at the 768-token limit → `unparseable` → workflow recommended `escalate_to_human`. Fatih reviewed `work_items.py` manually; with QA green he decided `approved` and documented why.
- **Agent fix during the dry run:** the PO agent first always returned `unparseable` (qwen3 kept "thinking" in plain text). We switched it to Ollama structured output (JSON schema) → valid result in 23 s.

## 4. What did the workflow cost? (WF-DRYRUN-03)
| Item | Quantity | Credits |
|---|---|---|
| PO agent | 1 call, 22.6 s, 328 in / 480 out tokens | 1.25 |
| Architect agent | 1 call, 43.3 s, 1008 in / 768 out tokens | 1.48 |
| QA agent | 0 LLM calls, 1.6 s | 0.02 |
| Human review at gate | 0.25 h | 25.0 |
| Human implementation (workflow, human gate, API, tests) | 15.0 h | 1500.0 |
| CI runs | 0 (GitHub Actions not enabled in repo) | 0 |
| **Agents total** | | **2.75** |
| **Workflow total (agents + humans)** | | **1527.75** |

Agent cost is negligible compared to human time (about 0.2 %). The QA agent calls the LLM only when tests fail, so a green run costs ≈0.02 instead of ≈1.5 credits.

## 5. What do we try differently next time?
- Use structured output (JSON schema) for the architect as well, so it stops escalating because of truncated free text.
- Mark unparseable architect results as `invalid_output` in its trace (currently logged as `success`).
- Let the QA agent check the PO's acceptance criteria against the brief to catch invented or missing requirements before the human gate.
