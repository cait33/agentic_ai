# Dry Run 01 – Persistent Work Items

Issue: [#10](https://github.com/cait33/agentic_ai/issues/10) · Task: `WF-DRYRUN-03` / `WF-VERIFY-FINAL` · Workflows: `08afe4bb-2897-4a96-9316-88bf98f64f20` and `89279231-0888-41fd-b456-e124d7b4b230`

## 1. What was implemented?
- REST API `/work-items` (create, list, mark done, delete), persisted in PostgreSQL via an idempotent migration (`db/migrations/001_work_items.sql`, `src/app/work_items.py`), 8 API/persistence tests against the real database.
- Agent workflow `src/agents/workflow.py`: **PO agent → Architect agent → QA agent → human gate**. Hand-over via LangGraph state; all agents receive the shared `EngineeringTask` (`src/models/task.py`).
- Input: project brief `tests/briefs/work-items.md`; PO output: `docs/requirements/WF-DRYRUN-03/`.
- Broadened operational role coverage with 8 functional agent roles (Product Owner, Software Architect, QA, Backend API, Data & RAG, Agent Engineer, DevOps, and Cost Observability).

## 2. Which humans and agents were involved?
| Step / Role | Actor | Artefact / Evidence                                                       |
|---|---|---------------------------------------------------------------------------|
| Requirement | Fatih (human) | Issue #10, brief `tests/briefs/work-items.md`                             |
| Requirements & Stories | product-owner-agent | trace `780bceb8-7694-40c2-939e-44a116e59975`, `docs/requirements/WF-VERIFY-FINAL/`                |
| Implementation | Fatih (human, AI-assisted) | `src/app/work_items.py`, tests                                            |
| Architecture Review | software-architect-agent | trace `cb26c387-e8e9-4a99-aee3-78d5129fa94a` (structured output schema, status: `approved`)       |
| Test Run & Verdict | qa-agent | trace `e8838ddf-c19a-44ee-b0c1-f48cfa2b0307` (33 passed, 0 failed, verdict: `approved`)           |
| Final Approval Gate | Daniil (human gate) | `evidence/session-02/decisions/89279231-0888-41fd-b456-e124d7b4b230.json` |
| Operational Audits | backend, data, devops, cost, agent agents | Traces in `logs/agent-runs.jsonl` verifying operational behavior          |

## 3. Where did a human correct or approve?
- **PO Output Corrections:** In the initial run, the model hallucinated an unrequested requirement (US3: "only owner can delete"). This criterion was rejected at the human gate and permanently removed from `docs/requirements/WF-DRYRUN-03/user_stories.json`.
- **Architect Structured Output Fix:** During early runs, the architect model generated unstructured free-text reasoning that was truncated by token limits, leading to an `unparseable` result and necessary escalation. We resolved this by enforcing strict Pydantic JSON schema mode on Ollama (`format=_LLMArchitectOutput.model_json_schema()`), yielding a valid `approved` verdict in 5.5 seconds.
- **Workflow Recommendation Guard:** The workflow routing was adjusted so that any unparseable or incomplete upstream result immediately triggers `escalate_to_human`, while clean completions produce an `approved` recommendation.

## 4. What did the workflow cost? (WF-VERIFY-FINAL Baseline)
| Item | Quantity | Credits |
|---|---|---|
| PO agent | 1 call, 8.8 s, 328 in / 489 out tokens | 1.11 |
| Architect agent | 1 call, 5.5 s, 984 in / 196 out tokens | 1.08 |
| QA agent | 0 LLM calls, 3.0 s runtime | 0.03 |
| Human review at gate | 0.25 h | 25.0 |
| Human implementation & tests | 15.0 h | 1500.0 |
| CI runs | 0 (local evaluation environment) | 0.0 |
| **Agents total** | | **2.22** |
| **Workflow total (agents + humans)** | | **1527.22** |

## 5. What do we try differently next time?
- Structured JSON output mode completely eliminated parsing escalations in the architect agent; we will standardize this schema enforcement across all future LLM-backed roles.
- Carry downstream artifacts deeper into subsequent prompts: the PO requirements are now passed directly into the architecture review prompt to verify alignment automatically.
- Keep deterministic checks (static code inspection, regex, test execution) for operational roles to maintain zero-token overhead for routine audits.