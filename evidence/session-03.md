# Session 03 – Erster Factory-Durchlauf (Kundenprojekt 01 Nordwerk)

Stand: 26.10.2026. Kursupdate Session 3 (Infrastruktur, keine Eigenleistung) gemergt via PR #16.

## Repositories und Commits

| | Repo | Commit |
|---|---|---|
| Factory | [cait33/agentic_ai](https://github.com/cait33/agentic_ai) | Code: `3d18a68` (PR #20), Evidenz: `2c622e4` (PR #21) |
| Produkt | [franciscotbatista99/client-01-website](https://github.com/franciscotbatista99/client-01-website) | Eingabe: `d777b34` (Scaffold, PR #3), Ergebnis: `63be7a6` (Agentenlauf) |

- Kunden-Issue: [client-01-website#2](https://github.com/franciscotbatista99/client-01-website/issues/2), Teil-Task AC-04: #1
- Projektkonfiguration: `projects/website-01.json` (Projekt-ID `website-01`, Produktpfad `../client-01-website`, per `PRODUCT_PATH` überschreibbar, Task `CUST-001`, Schreibbereich `site/`, max. 2 Korrekturschleifen)
- Kundenbrief für die Factory: `docs/customer-01/brief.md` (Pflichttexte N-01, N-02, N-03, N-08, N-09; Tagesumfang)

## Verantwortung

| Bereich | Accountable human |
|---|---|
| Auftrag / Requirements | Francisco |
| Technische Lieferung | Rafael (`backend_api_engineer`) |
| Prüfung (QA) | Fatih |
| Freigabe | Fatih |

Dokumentiert in Issue #2 (Kommentar). Offene Fragen und Annahmen ebenfalls in Issue #2.

## Factory-Durchlauf

`python -m src.agents.customer_workflow --project projects/website-01.json --reviewer Fatih`

| Run-ID | Ablauf | Ergebnis |
|---|---|---|
| `ec76867e-cae1-4187-b1b2-5942a48f606a` | PO → Web-Implementer → QA (Produktcheck) → Human Gate | approved, 0 Korrekturschleifen |

Evidenz: `runs/website-01/ec76867e-cae1-4187-b1b2-5942a48f606a/` (`manifest.json`, `trace.jsonl`, `requirements/`, `implementation-0.json`, `qa-round-0.json`, `review-0.json`)

- Modell: Ollama `qwen3:4b` (ID `359d7dd4bcda`), temperature 0, JSON-Modus, reasoning aus
- Agentenfähigkeiten und Rollen:
  - `product-owner-agent` – Rolle `product_owner_requirements` (accountable: Francisco): Brief → 4 User Stories mit Akzeptanzkriterien (strukturierte Übergabe im State)
  - `web-implementer-agent` – Rolle `backend_api_engineer` (accountable: Rafael): erhält Stories + Brief, echter LLM-Aufruf, Tool `write_product_slots` schreibt `site/index.html` im Produkt-Checkout (nur `site/`, nur zwischen AGENT-Markierungen)
  - `qa-agent` – Rolle `qa_test_engineer` (accountable: Fatih): Tool `run_pytest` führt `tests/` im Produkt-Checkout aus (7 passed, kein LLM-Aufruf nötig)
- Rollenentscheidung: Das 12-Rollen-Modell hat keine Frontend-Rolle; die Website-Umsetzung ist der Umsetzungsrolle `backend_api_engineer` zugeordnet (Verantwortung in `organization/roles.yaml` um „customer product implementation“ erweitert). Keine neue Rolle.
- Artefakt: `site/index.html`, sha256 `cf685b7f…c6c91cb`; Diff siehe Produkt-Commit `63be7a6`
- Kontrollierter Ablauf: Schleifenlimit 2, danach `escalate_to_human`; Schreibschutz außerhalb `site/` (siehe Factory-Test)
- Manuelle Eingriffe: keine am Agentenergebnis. Manuell (Mensch): HTML-Gerüst, CSS, README und Produktcheck (Commit `694bc55`).
- Hinweis: `factory_dirty_at_start: true` – im Factory-Checkout lagen nur nicht versionierte Altdateien (`logs/agent-runs.jsonl`, `docs/requirements/PO-RUN-03/`), Factory-Code unverändert gegenüber `3d18a68`.

## Prüfung und Freigabe

| AC | Automatischer Produktcheck (`tests/test_site.py`) | Mensch |
|---|---|---|
| AC-01 Firmenname + Hauptaussage | passed (`test_ac01_*`) | im Browser geprüft |
| AC-02 (Teil) Wartungsplanung mit Pflichttext | passed (`test_ac02_*`) | im Browser geprüft |
| AC-04 Kontaktlink `mailto:kontakt@nordwerk.example` + Übungshinweis | passed (`test_ac04_*`) | Linkziel und Hinweis geprüft |
| AC-03, AC-05–AC-08 | nicht fällig (T4) | – |

- Human Gate: **approved** durch Fatih, 2026-10-26 11:06:53 UTC, für Artefakt-Hash `cf685b7f…`, Eingabe-Commit `d777b34`. Kommentar: „AC-01, AC-04, Wartungsplanung im Browser geprüft, Mailto-Link korrekt, keine erfundenen Inhalte“ (`review-0.json`).
- Produkt läuft ohne Factory: `python3 -m http.server 8000 --directory site`; Produkttest separat: `python3 -m pytest tests -q` → 7 passed (Commit `63be7a6`).
- Factory-Test: `tests/factory/test_customer_workflow.py` (22 Fälle, Mock-LLM): Projektzuordnung, abgewiesene Schreibzugriffe außerhalb `site/` (nur temporärer Checkout), Übergabe PO → Implementer → QA, Auto-Korrektur, Eskalation nach 2 Schleifen. Standardlauf `python -m pytest -q`: 82 passed, 9 skipped (DB-Tests ohne laufende PostgreSQL).

## Kosten

| Kategorie | Menge | Credits |
|---|---|---|
| Agenten Lauf `ec76867e` (PO 45,5 s / 712 in / 637 out; Implementer 19,5 s / 1265 in / 207 out; QA 1,7 s, 0 Calls) | 2 LLM-Calls | 2,74 |
| Fehlläufe | keine im Kundenworkflow | 0 |
| CI | nicht ausgeführt (Actions im Repo deaktiviert) | 0 |
| Mensch Lieferung (Fatih) | 0,75 h | 75 |
| Mensch Review (Fatih) | 0,1 h | 10 |
| Mensch Nacharbeit (Fatih) | 0,25 h | 25 |
| Mensch Factory-Entwicklung (Fatih, Task `FACTORY-S3`, nicht im Lieferbudget) | 0,75 h | 75 |
| Weitere Teammitglieder | TODO: Zeilen in `costs/usage.csv` ergänzen | TODO |
| **Summe Lieferung CUST-001 (bisher erfasst)** | Agenten 2,74 + Mensch 110 | **112,74** (Teilkosten, Team unvollständig) |

Planbudget (Teamplanung; TODO: mit Dozent bestätigen): Lieferung T3 300 Credits, T4 800 Credits (ca. 3 h bzw. 8 h Personenzeit für Inhalte, Produktchecks, Review und Nacharbeit, plus ca. 30 Credits Agentenläufe inkl. Fehlläufe), Reserve T5 400 Credits (CR-01, SR-01, Abnahme). Factory-Entwicklung wird getrennt unter `FACTORY-S3` erfasst. Ist-Werte: `costs/usage.csv`.

Transparenz: Der Factory-Code (Projektkonfiguration, Web-Implementer, Kunden-Workflow, Factory-Test) wurde mit KI-Assistenz (Claude) entworfen und von Fatih integriert, getestet und verantwortet. Die Zeit ist als Factory-Entwicklung erfasst.

## Engpass und Hypothese

- Engpass (Run `ec76867e`, `trace.jsonl`): Der PO-Agent benötigte 45,5 s von 66,7 s Agentenlaufzeit (68 %) und erzeugte 637 Output-Tokens, obwohl der Brief die Pflichtinhalte bereits strukturiert vorgibt. Der Implementer selbst brauchte 19,5 s.
- Beobachtung Mensch: Die menschliche Nacharbeit (Git-Branches, Entpacken, blockierender Pull durch versioniertes `logs/agent-runs.jsonl`) war um ein Vielfaches teurer als die 2,74 Agenten-Credits.
- Hypothese für T4: Wenn der PO-Output pro Task gecacht und in Korrekturschleifen nicht neu erzeugt wird und die Story-Anzahl auf die fälligen ACs begrenzt ist, sinkt die Agentenlaufzeit pro Lauf um mindestens 40 %. Messgröße: `duration_seconds` aller Agenten pro Run in `runs/website-01/*/trace.jsonl`, Vergleich T3 vs. T4 bei gleichem Modell.

## Nächste Schritte (max. 3)

1. T4: AC-02 vollständig (N-04, N-05), AC-03 Zielgruppen/Arbeitsweise, AC-05 Navigation als zusätzliche AGENT-Slots und Produktchecks.
2. Produktchecks für AC-06/AC-07 ergänzen (375/1280 px, Fokus, Überschriftenstruktur) und `logs/agent-runs.jsonl` aus der Versionierung nehmen.
3. Hypothese messen: PO-Caching umsetzen und Laufzeit pro Run vergleichen.


# Session 03 – First Factory Run (Customer Project 01 Nordwerk)

As of October 26, 2026. Course update Session 3 (infrastructure, no in-house work) merged via PR #16.

## Repositories and commits

| | Repo | Commit |
|---|---|---|
| Factory | [cait33/agentic_ai](https://github.com/cait33/agentic_ai) | Code: '3d18a68' (PR #20), Evidence: '2c622e4' (PR #21) |
| Product | [franciscotbatista99/client-01-website](https://github.com/franciscotbatista99/client-01-website) | Input: 'd777b34' (Scaffold, PR #3), Result: '63be7a6' (Agent Run) |
| Product | [franciscotbatista99/client-01-website](https://github.com/franciscotbatista99/client-01-website) | Code: '8ec8161'

- Customer Issue: [client-01-website#2](https://github.com/franciscotbatista99/client-01-website/issues/2), Part-Task AC-04: #1
- Project configuration: 'projects/website-01.json' (project ID 'website-01', product path '../client-01-website', overwritable via 'PRODUCT_PATH', task 'CUST-001', write area 'site/', max. 2 correction loops)
- Customer letter for the factory: 'docs/customer-01/brief.md' (mandatory texts N-01, N-02, N-03, N-08, N-09; daily scope)

## Responsibility

| Area | Accountable human |
|---|---|
| Order / Requirements | Francisco |
| Technical delivery | Rafael ('backend_api_engineer') |
| Test (QA) | Fatih |
| Release | Fatih |

Documented in Issue #2 (Commentary). Open questions and assumptions also in Issue #2.

## Factory run

'python -m src.agents.customer_workflow --project projects/website-01.json --reviewer Fatih'

| Run ID | Process | Result |
|---|---|---|
| 'ec76867e-cae1-4187-b1b2-5942a48f606a' | PO → Web Implementer → QA (Product Check) → Human Gate | approved, 0 correction loops |

Evidence: 'runs/website-01/ec76867e-cae1-4187-b1b2-5942a48f606a/' ('manifest.json', 'trace.jsonl', 'requirements/', 'implementation-0.json', 'qa-round-0.json', 'review-0.json')



- Model: Ollama 'qwen3:4b' (ID '359d7dd4bcda'), temperature 0, JSON mode, reasoning from
- Agent skills and roles:
  - 'product-owner-agent' – Role 'product_owner_requirements' (accountable: Francisco): Letter → 4 user stories with acceptance criteria (structured handover in the state)
  - 'web-implementer-agent' – role 'backend_api_engineer' (accountable: Rafael): receives stories + letter, real LLM call, tool 'write_product_slots' writes 'site/index.html' in product checkout (only 'site/', only between AGENT markers)
  - 'qa-agent' – role 'qa_test_engineer' (accountable: Fatih): Tool 'run_pytest' executes 'tests/' in product checkout (7 passed, no LLM call required)
- Role decision: The 12-role model has no front-end role; the website implementation is assigned to the implementation role 'backend_api_engineer' (responsibility in 'organization/roles.yaml' extended by „customer product implementation“). No new role.
- Artifact: 'site/index.html', sha256 'cf685b7f…c6c91cb'; diff see product commit '63be7a6'
- Controlled flow: Loop limit 2, then 'escalate_to_human'; write protection outside 'site/' (see factory test)
- Manual interventions: none on the agent result. Manual (human): HTML framework, CSS, README and product check (commit '694bc55').
- Note: 'factory_dirty_at_start: true' – the factory checkout only contained unversioned legacy files ('logs/agent-runs.jsonl', 'docs/requirements/PO-RUN-03/'), factory code unchanged from '3d18a68'.

## Review and release

| AC | Automatic product check ('tests/test_site.py') | Human |
|---|---|---|
| AC-01 company name + main statement | passed ('test_ac01_*') | checked in browser |
| AC-02 (part) Maintenance planning with mandatory text | passed ('test_ac02_*') | checked in browser |
| AC-04 contact link 'mailto:kontakt@nordwerk.example` + practice hint | passed ('test_ac04_*') | Link target and hint checked |
| AC-03, AC-05–AC-08 | not due (T4) | – |

- Human Gate: **approved** by Fatih, 2026-10-26 11:06:53 UTC, for artifact hash 'cf685b7f…', input commit 'd777b34'. Comment: „AC-01, AC-04, maintenance scheduling checked in browser, mailto link correct, no fictitious content“ ('review-0.json').
- Product runs without factory: 'python3 -m http.server 8000 --directory site'; product test separately: 'python3 -m pytest tests -q' → 7 passed (commit '63be7a6').
- Factory test: 'tests/factory/test_customer_workflow.py' (22 cases, mock LLM): Project mapping, rejected write accesses outside 'site/' (temporary checkout only), passing PO → Implementer → QA, auto-correction, escalation after 2 loops. Standard run 'python -m pytest -q': 82 passed, 9 skipped (DB tests without running PostgreSQL).

## Cost

| Category | Quantity | Credits |
|---|---|---|
| Agent Run 'ec76867e' (PO 45.5 s / 712 in / 637 out; Implementer 19.5 s / 1265 in / 207 out; QA 1.7 s, 0 calls) | 2 LLM calls | 2.74 |
| Misses | none in the customer workflow | 0 |
| CI | not executed (actions disabled in repo) | 0 |
| Human Delivery (Fatih) | 0.75 h | 75 |
| Human Review (Fatih) | 0.1 h | 10 |
| Human Rework (Fatih) | 0.25 h | 25 |
| Human Factory Development (Fatih, Task 'FACTORY-S3', not in the delivery budget) | 0.75 h | 75 |
| Human Delivery (Caitlin) | 0.25 h | 25 |
| Human Product Review (Caitlin) | 0.75 h | 75 |
| Human Factory Tests (Caitlin) | 0.75 h | 75 |
| **Total delivery CUST-001 (recorded so far)** | Agents 2.74 + Human 110 | **112.74** (partial costs, team incomplete) |

Plan budget (team planning; TODO: confirm with lecturer): Delivery T3 300 credits, T4 800 credits (approx. 3 hours or 8 hours of person time for content, product checks, review and rework, plus approx. 30 credits agent runs including missed runs), reserve T5 400 credits (CR-01, SR-01, acceptance). Factory development is recorded separately under 'FACTORY-S3'. Actual values: 'costs/usage.csv'.

Transparency: The factory code (project configuration, web implementer, customer workflow, factory testing) was designed with AI assistance (Claude) and integrated, tested, and managed by Fatih. Time is recorded as factory development.

## Bottleneck and hypothesis

- Bottleneck (Run 'ec76867e', 'trace.jsonl'): The PO agent required 45.5 s of 66.7 s agent runtime (68%) and generated 637 output tokens, even though the letter already specifies the required content in a structured manner. The implementer himself needed 19.5 s.
- Human observation: Human rework (git branches, unpacking, blocking pull through versioned 'logs/agent-runs.jsonl') was many times more expensive than the 2.74 agent credits.
- Hypothesis for T4: If the PO output is cached per task and not regenerated in correction loops and the story count is limited to the ACs due, the agent runtime per run decreases by at least 40%. Measure: 'duration_seconds' of all agents per run in 'runs/website-01/*/trace.jsonl', comparison T3 vs. T4 for the same model.

## Next steps (max. 3)

1. T4: AC-02 complete (N-04, N-05), AC-03 audiences/mode of work, AC-05 navigation as additional AGENT slots and product checks.
2. Add product checks for AC-06/AC-07 (375/1280 px, focus, heading structure) and remove 'logs/agent-runs.jsonl' from versioning.
3. Measure hypothesis: Implement PO caching and compare runtime per run.