# Company

> Team-owned document. Replace all placeholders during Session 1.

## Name

EventAI

## Mission

Development of reliable and resilient software systems to improve daily operations.

## Team members

- Francisco
- Caitlin
- Daniil
- Rafael

## Working rules

## How technical decisions are made
- Architecture decisions and structural guidelines proposed by the Software Architect Agent require agreement between the human Software Architect and the Integration Engineer before adoption.
- Code changes must pass all automated CI tests before being considered for a pull request review.

## When human approval is mandatory
- Deployment & Main Merge: No agent is permitted to push directly to `main` or trigger production releases. Merging requires explicit approval from the accountable human.
- Database Schema & Migrations: Any change modifying PostgreSQL schemas or pgvector tables requires review and sign-off by the accountable human (Data & RAG Engineer).
- Tool Access Escalation: Agents cannot grant themselves new tools or elevated permissions.

## How agents may create or modify artifacts
- Agents only write artifacts to staging directories, designated branches, or temporary trace outputs.
- Agents must never overwrite source code in `src/` directly without opening a pull request or reviewable diff.
- Every artifact created by an agent must include machine-readable metadata: executing agent name, timestamp, model used, and trace ID.

## How incidents are escalated
- Runtime Errors & Loop Halts: If an agent encounters an unrecoverable API error or enters a tool call loop (> 3 retries), execution terminates immediately, an incident record is logged, and the accountable human is notified via issue assignment.
- Unparseable Outputs: If an agent output cannot be structured, the task falls back to the responsible human.

## How cost overruns are handled
- Max. 25,000 tokens or a local runtime timeout of 60 seconds per single task execution.
- If an agent exceeds 80% of its task token budget, it must abort, log the partial trace, and request human intervention.

---

## Required Decisions

## 1. Which role will first receive technical support from an agent?
- Role: Software Architect (Agent)
- Reason: The software architect focuses primarily on analysis, structuring, code reviews, and the creation of architectural design records (ADRs). Since these tasks are heavily text- and analysis-based and do not require destructive write access to the production code, this role is ideal for getting started. Review by a human integration engineer ensures technical implementability.

## 2. Which role will deliberately remain human initially?
- Role: Managing Director or Customer Lead
- Reason: Business decisions, prioritization in customer interactions, legal and corporate responsibilities require human judgment and an understanding of context that cannot be captured fully in prompts. Negotiations and approvals remain entirely the responsibility of humans.

## 3. Where is a human approval gate necessary?
- Gate: Merge in `main`-Branch and changes to the database schema
- Reason: To ensure the integrity of the system and traceability for evaluation, no agent is allowed to integrate code into the baseline without supervision. A human must verify the quality before the code becomes active.
