## Tasks/Responsibilities

| Person    | Tasks |
| --------- | ----- |
| Fatih     | Task 3: F-NEW (PO output reuse, `src/factory/po_cache.py`, 6 Factory tests, PR #40) |
| Fatih     | Task 3: R-01 with F-NEW on fresh checkouts of R-BASE (runs `e9902441`, `c97a41cc`), comparison + decision (PR #41) |
| Fatih     | Task 4: start/test instructions + maintenance note (product README), AC-01–AC-10 checklist, final regression, `session-05.md`, costs |
| Daniil    | Task 3: human gate reviewer for both F-NEW R-01 runs |
| Daniil    | Task 1 (CR-01): Factory implementation (`web_implementer.py` en_ slots & bilingual nav prompt), operated & reviewed CR-01 DE + EN runs (`cf17b507`, `3d6a20c0`), browser review and evidence PR |
| Francisco | Task 1 (CR-01): English page skeleton `site/en.html` (`lang="en"`, own title, sections, empty AGENT slots for the Factory) |
| Francisco | Task 1 (CR-01): product checks `tests/test_cr01_en.py` for the English page (17 checks; 10 failed / 30 passed on the empty skeleton, as expected before the Factory run) |
| Francisco | Task 1 (CR-01): helped with the CR-01 brief `docs/customer-01/cr01-en.md` and project config `projects/website-01-cr01-en.json` |
| Rafael    | Task 2 (SR-01): reviewed ENISA statement, defined component inventory, and drafted SR-01 document |
| Rafael    | Task 2 (SR-01): Extracted local environment versions (Python 3.14.6, pytest 9.1.1) and created the component inventory |
| Caitlin   | Task 2: research and co wrote php vulnerabilities answer |

Only the existing roles (`organization/roles.yaml`) were used; no new agents or roles.
Merged without a second review (time pressure): Factory PR #40. TODO: further PRs.


## Repositories and commits

Factory (https://github.com/cait33/agentic_ai):
From commit 5bfec75 (https://github.com/cait33/agentic_ai/commit/5bfec755f4195446c5a2dadb6ff6c3d420845083)
to commit c0d520f (https://github.com/cait33/agentic_ai/commit/c0d520fc056dc9693f802905e486f9c043e728fa)
Client01 (https://github.com/franciscotbatista99/client-01-website):
From commit d14e681 (https://github.com/franciscotbatista99/client-01-website/commit/d14e681c142d91895116581f55e105aa278abce0) (= `rc-1` `cdbcba6` + acceptance docs)
to commit TODO

Release: tag `TODO (e.g. v1.0)` → commit `TODO`.
Handover: product `README.md` (start, tests, maintenance) · AC checklist `docs/acceptance.md` · browser review `TODO`.

Three separate states (not mixed):
- (a) Nordwerk customer release: `main` / tag `TODO`
- (b) isolated R-01 experiment: branches `r01-baseline`, `r01-fnew-run1`, `r01-fnew-run2` (not merged, not part of the delivery)
- (c) intentionally faulty test copy from S4: `projects/website-01-faultcase.json` (never in the delivery)


## 1. Customer change CR-01

- Change issue + impact analysis: Issue #1 (CUST-001) – English view and target group extension
- Brief / configs: `docs/customer-01/brief-cr01-de.md`, `docs/customer-01/brief-cr01-en.md`, `projects/website-01-cr01-de.json`, `projects/website-01-cr01-en.json`
- Factory change for CR-01 (e.g. language of the implementer prompt): PR `evidence/cr01-runs` (`src/agents/web_implementer.py` extended with `en_` slots and bilingual navigation prompt structure)

| | DE view `site/index.html` | EN view `site/en.html` |
|---|---|---|
| Run | `cf17b507-afe6-4e4e-a6d1-6e8106d73365` | `3d6a20c0-48c5-4894-9c6d-34044170619f` |
| Inputs | product `d14e681`, factory `brief-cr01-de.md` | product `d14e681`, factory `brief-cr01-en.md` |
| Agent-created diff / review PR | PR `evidence/cr01-runs` | PR `evidence/cr01-runs` |
| Product check | 23 passed / 0 failed (`tests/test_site.py`) | 17 passed / 0 failed (`tests/test_cr01_en.py`) |
| Correction rounds | 0 | 1 (run `b920be11` rejected due to missing language switch and anchor mismatch; resolved in prompt and brief) |
| Human gate (name, UTC) | Daniil, 2026-11-09 12:35 UTC (approved) | Daniil, 2026-11-09 12:20 UTC (approved) |
| Result commit / artifact sha256 | `a87f454` / `c82fd3f5b4c35f1d7c7271e75f40b794d547b31c76380e763d1e1e78b0702304` | `d703b1e` / `24f1c8a6193a7b4cbc9f5a39d7579f740e93cb48a11ef60ec7bfe7611cc3bada` |
| Agent costs | 2.4845 credits (PO 1.2166 + Imp 1.2509 + QA 0.0170) | 2.4538 credits (PO 1.2523 + Imp 1.1873 + QA 0.0142) |

New automated checks: `tests/test_cr01_en.py` (17 checks: required content, `lang="en"`, title, language switch, anchor resolution, mailto targets, no invented numbers/texts) and `tests/test_site.py` extensions for DE language switch and audience.
Regression AC-01–AC-08: 40 passed on the final combined state (23 DE + 17 EN).
Browser review 375/1280 px + keyboard, both views: Tested and approved (by Daniil via `http.server 8000`).
Manual product work (not by the agent): Skeleton setup of `site/en.html` structure with empty AGENT slots, creation of `tests/test_cr01_en.py` by Francisco.


## 2. Security enquiry SR-01

- Customer response (PHP vulnerabilities)
- Component inventory (runtime + build/test, version/reference or "not used")
- Sources + access date
- Above is in `docs\phpSecurityConsiderations.md` in the product repo
- Prepared by and fact checked by: Rafael and Caitlin


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

| AC | Automated check | Manual evidence | Result |
|---|---|---|---|
| AC-01 Company name + main statement | `test_ac01_*` | Browser header inspection (DE & EN) | Passed |
| AC-02 Three services with text | `test_ac02_*` | Checked service cards and typography | Passed |
| AC-03 Target groups (incl. "Technische Einkaufsabteilungen"), approach, no invented promises | `test_ac03_*` | Verified 3rd group in DE and EN purchasing group | Passed |
| AC-04 Contact link + course notice | `test_ac04_*` | Clicked mailto links, verified HAW project notice | Passed |
| AC-05 Navigation, internal links, local assets | `test_ac05_*` | Tested anchor jumps and bilingual switch | Passed |
| AC-06 No overflow 375/1280 px | `test_ac06_*` (heuristic) | browser review (DevTools 375/1280px) | Passed |
| AC-07 Title, lang, headings, focus | `test_ac07_*` | browser review (outline + single H1) | Passed |
| AC-08 Fresh checkout without Factory | `test_ac08_*` | fresh checkout test execution | Passed |
| AC-09 CR-01 met, German content/nav/contact still work | `test_cr01_en.py`, `test_site.py` | browser review both views | Passed |
| AC-10 Component inventory, SR-01 response, recorded customer acceptance | – | `docs/phpSecurityConsiderations.md` documented | Passed |

Final regression on the release state: product `python3 -m pytest tests -q` → 40 passed; Factory `tests/factory` → 41 passed (`evidence/session-05/factory-pytest.txt`); `--verify-only` run `TODO` → `TODO`.

- **Technical approval (team):** Daniil & Francisco, 2026-11-09 13:30 UTC, release `TODO`
- **Customer acceptance (instructor):** TODO – accepted / accepted with outstanding defects (list) / pending. Not self-declared by the team.
- Outstanding defects / open tasks: TODO


## Cost

CI: no GitHub Actions runs in S5 (Actions disabled, verified locally via pytest).

| Category | Quantity | Credits |
| -------- | -------- | ------- |
| Agents CR-01 (`CUST-001`, runs `3d6a20c0` + `cf17b507`) | 4 LLM calls, 2 QA runs | 4.94 |
| Human delivery CR-01 (`CUST-001`) | Francisco 0.9 h, Caitlin 0.25 h | 115.00 |
| Human review CR-01 (gate, browser review) | Daniil 0.25 h | 25.00 |
| SR-01 (`CUST-001`, response + inventory, fact check) | Rafael 2.0 h, Caitlin 2.0 h | 400.00 |
| Human delivery acceptance/handover (`CUST-001`) | Daniil 0.4 h | 40.00 |
| **Session delivery CUST-001 (S5)** | total customer delivery S5 | **584.94** |
| Factory development `FACTORY-S5` (one-off, separate): F-NEW | Fatih 0.1 h | 10.00 |
| Rework (`FACTORY-S5`): updated cost total, merged in repository changes | Caitlin 0.15 h | 15.00 |
| Factory development `FACTORY-S5`: CR-01 language adaptation | Daniil 0.4 h | 40.00 |
| R-01 F-NEW runs, operational (separate) | agents 2.74 + 1.34 = 4.08; human Fatih 0.25 h (25), Daniil review 0.03 h (3) | 32.08 |

### Totals S3–S5 (from `costs/usage.csv`)

| | S3 (26.10.) | S4 (02.11.) | S5 (09.11.) | Total |
|---|---:|---:|---:|---:|
| Customer delivery `CUST-001` | 437.74 | 793.34¹ | 584.94 | 1816.02 |
| Factory development | 550.00 (`FACTORY-S3`) | 241.20 (`FACTORY-S4`) | 65.00 (`FACTORY-S5`) | 856.20 |
| R-01 (baseline / experiment) | – | 82.72 | 32.08 | 114.80 |

¹ incl. 25.0 S3 rework on the S4 day (see `session-04.md`).
Budget S5: 600.00 credits · plan vs. actual: 584.94 credits (−15.06 credits / within budget) · reason: efficient 1st-round agent execution on DE and fast resolution of EN navigation without expensive correction loops.

Recompute from the CSV:
```bash
python3 -c "import csv,collections as c;d=c.defaultdict(float);[d.__setitem__((r['date'],r['task_id']),d[(r['date'],r['task_id'])]+float(r['credits'])) for r in csv.DictReader(open('costs/usage.csv'))];[print(k,round(v,2)) for k,v in sorted(d.items())]"


## Three transferable lessons

1. **Measure the bottleneck before optimising, and isolate one variable.** The S4 traces showed the PO agent at 41–68 % of agent time; changing only the PO step (model, settings, task fixed, fresh R-BASE clones) made the effect attributable: −1 LLM call, −51 % credits, identical artifact hash.
2. **Strict slot contracts and whitelists prevent agent drift during change requests.** In CR-01, having automated checks (`test_cr01_en_only_required_texts` and `internal_anchors_resolve`) immediately caught when the implementer agent injected German navigation anchors into the English page. Providing concrete markup contracts in the system prompt guided the agent to zero test failures in the second attempt.
3. **Decouple view-specific test suites during multi-step runs.** Running the full product test suite against an empty `en.html` blocked the initial DE run at the Human Gate. Splitting `product_test_paths` in the project configurations allowed isolated agent iterations while maintaining full regression confidence at final integration.