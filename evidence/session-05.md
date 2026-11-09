# Session 05 - 09/11/2026

Deliver customer change CR-01 from the versioned baseline `rc-1` with the same Factory, answer security enquiry SR-01 with sources, evaluate one Factory change (F-NEW) against the S4 baseline on R-01, and hand over a release accepted against AC-01–AC-10.

## Tasks/Responsibilities

| Person    | Tasks |
| --------- | ----- |
| Fatih     | Task 3: F-NEW (PO output reuse, `src/factory/po_cache.py`, 6 Factory tests, PR #40) |
| Fatih     | Task 3: R-01 with F-NEW on fresh checkouts of R-BASE (runs `e9902441`, `c97a41cc`), comparison + decision (PR #41) |
| Fatih     | Task 4: start/test instructions + maintenance note (product README, PR #20), CR-01 checks for the German page `tests/test_cr01_de.py` (4), AC-01–AC-10 checklist (PR #22), final regression (`--verify-only` run `2fb2d0dd`), fresh checkout, browser review, technical approval, tag `v1.0`, `session-05.md`, costs |
| Daniil    | Task 3: human gate reviewer for both F-NEW R-01 runs |
| Daniil    | Task 1 (CR-01): implementer + briefs + configs for the English view (Factory PR #43), Factory runs DE + EN, product change (product PR #21) |
| Francisco | Task 1 (CR-01): English page skeleton `site/en.html` (`lang="en"`, own title, sections, empty AGENT slots for the Factory) |
| Francisco | Task 1 (CR-01): product checks `tests/test_cr01_en.py` for the English page (17 checks; 10 failed / 30 passed on the empty skeleton, as expected before the Factory run) |
| Francisco | Task 1 (CR-01): helped with the CR-01 brief `docs/customer-01/cr01-en.md` and project config `projects/website-01-cr01-en.json` |
| Rafael    | Task 2 (SR-01): reviewed ENISA statement, defined component inventory, and drafted SR-01 document |
| Rafael    | Task 2 (SR-01): Extracted local environment versions (Python 3.14.6, pytest 9.1.1) and created the component inventory |
| Caitlin   | Task 2: research and co wrote php vulnerabilities answer |

Only the existing roles (`organization/roles.yaml`) were used; no new agents or roles.
Merged without a second review (time pressure): Factory PR #40 (Fatih), Factory PR #43 and product PR #21 (both self-merged by Daniil). Pushed directly to `main` without PR: product `b81446a` (`en.html` skeleton + `test_cr01_en.py`, Francisco), product `725a267` (SR-01 response, Caitlin/Rafael), Factory cost/evidence updates by Francisco, Caitlin, Rafael.


## Repositories and commits

Factory (https://github.com/cait33/agentic_ai):
From commit 5bfec75 (https://github.com/cait33/agentic_ai/commit/5bfec755f4195446c5a2dadb6ff6c3d420845083)
to the merge commit of the final S5 evidence PR (`main` at 15:00)
Client01 (https://github.com/franciscotbatista99/client-01-website):
From commit d14e681 (https://github.com/franciscotbatista99/client-01-website/commit/d14e681c142d91895116581f55e105aa278abce0) (= `rc-1` `cdbcba6` + acceptance docs)
to commit f1575ad (https://github.com/franciscotbatista99/client-01-website/commit/f1575ad7c802e7fbcff7d9cab23ea999fd532015)

Release: tag `v1.0` → commit `f1575ad` (merge of acceptance PR #22).
Handover: product `README.md` (start, tests, maintenance) · AC checklist `docs/acceptance.md` · browser review recorded in `docs/acceptance.md` (Fatih, 13:55–13:57 local).

Three separate states (not mixed):
- (a) Nordwerk customer release: `main` / tag `v1.0`
- (b) isolated R-01 experiment: branches `r01-baseline`, `r01-fnew-run1`, `r01-fnew-run2` (not merged, not part of the delivery)
- (c) intentionally faulty test copy from S4: `projects/website-01-faultcase.json` (never in the delivery)


## 1. Customer change CR-01

- Change issue + impact analysis: issues by Caitlin in the product repo (CR-01 task and acceptance criteria for both views)
- Briefs: `docs/customer-01/brief-cr01.md`, `brief-cr01-de.md`, `brief-cr01-en.md`; configs `projects/website-01-cr01-de.json` (target `site/index.html`), `projects/website-01-cr01-en.json` (target `site/en.html`), task ID `CR-01`
- Factory change for CR-01: Factory PR #43 (Daniil) – implementer prompt with German and English navigation (language switch "English"/"Deutsch"); no new agents or roles
- Manual product work (not by the agent): English page skeleton with empty AGENT slots (`b81446a`, Francisco)

| | DE view `site/index.html` | EN view `site/en.html` |
|---|---|---|
| Run | `TODO (Daniil)` | `TODO (Daniil)` |
| Inputs | product `TODO`, factory `c6cc9fa` | product `TODO`, factory `c6cc9fa` |
| Agent-created diff / review PR | product PR #21 (`75452ea`) | product PR #21 (`75452ea`) |
| Product check | `test_site.py` 23/23 | `test_cr01_en.py` 17/17 |
| Correction rounds | TODO (Daniil) | TODO (Daniil) |
| Human gate (name, time) | TODO (Daniil) | TODO (Daniil) |
| Agent costs | TODO credits | TODO credits |

New automated checks: `tests/test_cr01_en.py` (17: required EN content, `lang="en"`, title, language switch, contact, no invented content; Francisco) and `tests/test_cr01_de.py` (4: "Technische Einkaufsabteilungen", existing target groups kept, language switch "English"; Fatih, verified red on a manipulated copy).
Regression AC-01–AC-08: 23/23 on the final state; all product checks 44/44 on `v1.0`.
Browser review 375/1280 px + keyboard, both views, language switch both directions: Fatih, 13:55–13:57 local, no findings except the cosmetic defect below.
Known defect (cosmetic, open): on `en.html` each service description repeats the service name and "Request information" appears as text and as link.


## 2. Security enquiry SR-01

- Customer response (PHP vulnerabilities)
- Component inventory (runtime + build/test, version/reference or "not used")
- Sources + access date
- Above is in `docs/phpSecurityConsiderations.md` in the product repo (`725a267`)
- Prepared by and fact checked by: Rafael and Caitlin (no independent second check; recorded in `docs/acceptance.md`)


## 3. Factory experiment: F-BASE vs. F-NEW on R-01

Full comparison with raw data: [`evidence/session-05/r01-comparison.md`](session-05/r01-comparison.md) (PR #41).

| | |
|---|---|
| Hypothesis (S4) | reusing the PO output when brief, PO prompt and model settings are unchanged reduces agent time per R-01 run by ≥ 40 % with the same check quality |
| Change | F-BASE `01017ae` → F-NEW `b7f4161` (PR #40): `src/factory/po_cache.py`, config field `reuse_po_output`, CLI `--no-po-cache`; key = sha256(brief, PO system prompt, provider, model, temperature, format); only successful PO results cached; hit/miss in trace + manifest |
| Only variable | PO cache (model, settings, task, criteria, workflow unchanged) |
| R-BASE | `66339b6` (`rc-1` + `tests/test_r01.py`), each run on its own fresh clone (`~/r01-new1`, `~/r01-new2`); no earlier R-01 output used as input |
| Model / settings | Ollama qwen3:4b `359d7dd4bcda`, temperature 0, JSON mode, reasoning off |
| Factory tests | `tests/factory` 41 passed (6 new, mock LLM) |

| | Baseline `3ba82f0f` (S4) | F-NEW run 1 `e9902441` (miss) | F-NEW run 2 `c97a41cc` (hit) |
|---|---:|---:|---:|
| Agent time | 63.6 s | 66.0 s (+4 %) | 28.3 s (−55 %) |
| LLM calls | 2 | 2 | 1 |
| Agent credits | 2.72 | 2.74 | 1.34 (−51 %) |
| Product check / regression | 25/25 · 23/23 | 25/25 · 23/23 | 25/25 · 23/23 |
| Artifact sha256 | `ce03f072…` | identical | identical |
| Correction rounds / faults | 0 / none | 0 / none | 0 / none |
| Review (Daniil) / rework | 153 s / 0 | 54 s / 0 | 59 s / 0 |
| Result commit | `97305f3` (`r01-baseline`) | `c672b28` (`r01-fnew-run1`) | `e55e372` (`r01-fnew-run2`) |

Limits: implementer runtime noise ≈ ±15 % (PO share alone ≈ −41 %); 1 baseline + 2 F-NEW runs = preliminary observation; benefit only for repeated runs on an unchanged brief (not for a new request like CR-01); shorter review time is a learning effect (same result seen before).

**Decision: keep F-NEW** (enabled by default, `--no-po-cache` available) – deterministic saving when it applies, no change of output or checks, no cost on a miss, fully traceable.

Known issue (unchanged since S4): manifest field `max_output_tokens_implementer` shows 2048 (hard-coded), actual value 3072.


## 4. Acceptance and handover

Full checklist: product `docs/acceptance.md` (PR #22, part of `v1.0`). Handover: product `README.md` (start, tests, maintenance note; PR #20).

| AC | Automated check | Manual evidence | Result |
|---|---|---|---|
| AC-01 Company name + main statement | `test_ac01_*`, `test_cr01_en_*` | browser review | pass |
| AC-02 Three services with text | `test_ac02_*` | – | pass |
| AC-03 Target groups (incl. "Technische Einkaufsabteilungen"), approach, no invented promises | `test_ac03_*`, `test_cr01_de_*`, `test_cr01_en_only_required_texts` | browser review | pass |
| AC-04 Contact link + course notice | `test_ac04_*`, `test_cr01_en_contact_*`, `test_cr01_en_notice_*` | contact links usable in both views | pass |
| AC-05 Navigation, internal links, local assets | `test_ac05_*`, `test_cr01_en_internal_*`, `test_cr01_en_local_*` | nav + language switch DE ↔ EN | pass |
| AC-06 No overflow 375/1280 px | `test_ac06_*` (heuristic), `test_cr01_en_viewport_*` | browser review both views | pass |
| AC-07 Title, lang, headings, focus | `test_ac07_*`, `test_cr01_en_language_and_title` | keyboard/focus both views | pass |
| AC-08 Fresh checkout without Factory | `test_ac08_*` | fresh clone `3fa2424`, 13:55 local: 40 passed, both pages load, no Factory/LLM/DB | pass |
| AC-09 CR-01 met, German content/nav/contact still work | `test_cr01_en.py` 17, `test_cr01_de.py` 4, regression 23 | browser review both views | pass (cosmetic defect open) |
| AC-10 Component inventory, SR-01 response, recorded customer acceptance | – | `docs/phpSecurityConsiderations.md`; acceptance below | pass |

Final regression on the release state: product `python -m pytest tests -q` → 44 passed on `v1.0`; Factory `tests/factory` → 41 passed (`evidence/session-05/factory-pytest.txt`); `--verify-only` run `2fb2d0dd-e75f-45b9-b0cc-2c8512b34212` on product `3fa2424` → 40 passed / 0 failed, approved by Fatih, `release_status: released`, artifact sha256 `33373692…` (raw data `runs/website-01/2fb2d0dd…`).

- **Technical approval (team):** Fatih, 2026-11-09 14:05 local, release `v1.0` → `f1575ad`
- **Customer acceptance (instructor, Prof. Clemen):** accepted, 2026-11-09 ≈ 13:40 local, as communicated to the team; the decision was given on the state presented then, before product PR #21 was merged (13:47). Not self-declared.
- Outstanding defects / open tasks: cosmetic duplicate texts on `en.html`; SR-01 had no independent fact check; known manifest issue `max_output_tokens_implementer` (2048 shown, 3072 used).


## Cost

Task IDs in S5: `CR-01`, `SR-01` and `CUST-001` (acceptance/handover) together form the customer delivery for Nordwerk in S5; Caitlin's SR-01 row is recorded as `CUST-01` (typo, counted as SR-01). `R-01` and `FACTORY-S5` are separate.
CI: no GitHub Actions runs in S5 (Actions disabled).

| Category | Quantity | Credits |
| -------- | -------- | ------- |
| Agents CR-01 (runs DE + EN, Daniil) | TODO (Daniil) LLM calls | TODO |
| Human delivery CR-01: EN skeleton, EN checks, brief/config help (Francisco) | 0.9 h | 90.00 |
| Human delivery CR-01: issues for CR-01 (Caitlin, recorded as `CUST-001`) | 0.25 h | 25.00 |
| Human delivery CR-01: briefs, implementer, runs, product change (Daniil) | TODO | TODO |
| Human delivery SR-01: response + inventory (Rafael 2.0 h, Caitlin 2.0 h) | 4.0 h | 400.00 |
| Human delivery acceptance/handover `CUST-001` (Fatih: README, DE checks, regression, fresh checkout, browser review, checklist, tag, evidence) | 1.0 h | 100.00 |
| Agent: final `--verify-only` run `2fb2d0dd` (QA, 0 LLM calls) | 1 run | 0.01 |
| **Session delivery S5 (CR-01 + SR-01 + CUST-001)** | without Daniil's CR-01 rows | **615.01 + TODO** |
| Factory development `FACTORY-S5` (one-off, separate): F-NEW | Fatih 0.1 h | 10.00 |
| Rework (`FACTORY-S5`): S4 feedback, updated cost total | Caitlin 0.15 h | 15.00 |
| Factory development `FACTORY-S5`: implementer for the English view (PR #43) | TODO (Daniil) | TODO |
| R-01 F-NEW runs, operational (separate) | agents 2.74 + 1.34 = 4.08; human Fatih 0.25 h (25), Daniil review 0.03 h (3) | 32.08 |

### Totals S3–S5 (from `costs/usage.csv`)

| | S3 (26.10.) | S4 (02.11.) | S5 (09.11.) | Total |
|---|---:|---:|---:|---:|
| Customer delivery Nordwerk | 437.74 | 793.34¹ | 615.01 + TODO | TODO |
| Factory development | 550.00 (`FACTORY-S3`) | 241.20 (`FACTORY-S4`) | 25.00 + TODO (`FACTORY-S5`) | TODO |
| R-01 (baseline / experiment) | – | 82.72 | 32.08 | 114.80 |

¹ incl. 25.0 S3 rework on the S4 day (see `session-04.md`).

Recompute from the CSV:
```
python3 -c "import csv,collections as c;d=c.defaultdict(float);[d.__setitem__((r['date'],r['task_id']),d[(r['date'],r['task_id'])]+float(r['credits'])) for r in csv.DictReader(open('costs/usage.csv'))];[print(k,round(v,2)) for k,v in sorted(d.items())]"
```


## Three transferable lessons

1. **Measure the bottleneck before optimising, and isolate one variable.** The S4 traces showed the PO agent at 41–68 % of agent time; changing only the PO step (model, settings, task fixed, fresh R-BASE clones) made the effect attributable: −1 LLM call, −51 % credits, identical artifact hash.
2. **A versioned skeleton plus a slot contract makes a change request deliverable with the same Factory.** The English view only needed an HTML skeleton with empty AGENT markers, new checks and an extended implementer prompt – no new agents. What the contract did not cover (prompt still saying "German-language", unused `en_*` fields, no check for the new German content) was only found in review; next time write the checks for *all* changed views before the run.
3. **Keep authoring, checking and approving separate – and in that order.** Several changes reached `main` without a second reviewer (direct pushes, self-merged PRs), SR-01 was fact-checked by its own authors, and the customer accepted before the final change was merged. The release is still traceable because every state has a commit, a check result and a named approver, but the next delivery should plan a non-author review before merge and present the final tagged state for acceptance.
