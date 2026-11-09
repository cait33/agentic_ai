# Session 05 - 09/11/2026

Deliver customer change CR-01 from the versioned baseline `rc-1` with the same Factory, answer security enquiry SR-01 with sources, evaluate one Factory change (F-NEW) against the S4 baseline on R-01, and hand over a release accepted against AC-01–AC-10.

> TODO markers = still open at the time of writing; remove before the final commit.


## Tasks/Responsibilities

| Person    | Tasks |
| --------- | ----- |
| Fatih     | Task 3: F-NEW (PO output reuse, `src/factory/po_cache.py`, 6 Factory tests, PR #40) |
| Fatih     | Task 3: R-01 with F-NEW on fresh checkouts of R-BASE (runs `e9902441`, `c97a41cc`), comparison + decision (PR #41) |
| Fatih     | Task 4: start/test instructions + maintenance note (product README), AC-01–AC-10 checklist, final regression, `session-05.md`, costs |
| Daniil    | Task 3: human gate reviewer for both F-NEW R-01 runs |
| Daniil    | Task 1 (CR-01): TODO |
| Francisco | Task 1 (CR-01): English page skeleton `site/en.html` (`lang="en"`, own title, sections, empty AGENT slots for the Factory) |
| Francisco | Task 1 (CR-01): product checks `tests/test_cr01_en.py` for the English page (17 checks; 10 failed / 30 passed on the empty skeleton, as expected before the Factory run) |
| Francisco | Task 1 (CR-01): helped with the CR-01 brief `docs/customer-01/cr01-en.md` and project config `projects/website-01-cr01-en.json` |
| Rafael    | Task 2 (SR-01): TODO |
| Caitlin   | Task 2: research and co wrote php vulnerabilities answer |

Only the existing roles (`organization/roles.yaml`) were used; no new agents or roles.
Merged without a second review (time pressure): Factory PR #40. TODO: further PRs.


## Repositories and commits

Factory (https://github.com/cait33/agentic_ai):
From commit 5bfec75 (https://github.com/cait33/agentic_ai/commit/5bfec755f4195446c5a2dadb6ff6c3d420845083)
to commit TODO (final S5 commit)
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

TODO (Francisco/Daniil):
- Change issue + impact analysis: `TODO #`
- Brief / configs: `docs/customer-01/cr01.md`, `projects/TODO`
- Factory change for CR-01 (e.g. language of the implementer prompt): PR `TODO`

| | DE view `site/index.html` | EN view `site/en.html` |
|---|---|---|
| Run | `TODO` | `TODO` |
| Inputs | product `TODO`, factory `TODO` | product `TODO`, factory `TODO` |
| Agent-created diff / review PR | `TODO` | `TODO` |
| Product check | `TODO`/`TODO` | `TODO`/`TODO` |
| Correction rounds | TODO | TODO |
| Human gate (name, UTC) | TODO | TODO |
| Result commit / artifact sha256 | `TODO` | `TODO` |
| Agent costs | TODO credits | TODO credits |

New automated checks: `TODO` (EN required content, `lang="en"`, title, language switch, "Technische Einkaufsabteilungen" on DE).
Regression AC-01–AC-08: `TODO` passed on the final state.
Browser review 375/1280 px + keyboard, both views: `TODO` (by TODO).
Manual product work (not by the agent): TODO.


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
| AC-01 Company name + main statement | `test_ac01_*` | TODO | TODO |
| AC-02 Three services with text | `test_ac02_*` | – | TODO |
| AC-03 Target groups (incl. "Technische Einkaufsabteilungen"), approach, no invented promises | `test_ac03_*` + TODO | TODO | TODO |
| AC-04 Contact link + course notice | `test_ac04_*` | TODO | TODO |
| AC-05 Navigation, internal links, local assets | `test_ac05_*` | TODO | TODO |
| AC-06 No overflow 375/1280 px | `test_ac06_*` (heuristic) | browser review TODO | TODO |
| AC-07 Title, lang, headings, focus | `test_ac07_*` | browser review TODO | TODO |
| AC-08 Fresh checkout without Factory | `test_ac08_*` | fresh checkout TODO | TODO |
| AC-09 CR-01 met, German content/nav/contact still work | TODO | browser review both views TODO | TODO |
| AC-10 Component inventory, SR-01 response, recorded customer acceptance | – | TODO | TODO |

Final regression on the release state: product `python3 -m pytest tests -q` → TODO passed; Factory `tests/factory` → TODO passed (`evidence/session-05/factory-pytest.txt`); `--verify-only` run `TODO` → `TODO`.

- **Technical approval (team):** TODO name, TODO UTC, release `TODO`
- **Customer acceptance (instructor):** TODO – accepted / accepted with outstanding defects (list) / pending. Not self-declared by the team.
- Outstanding defects / open tasks: TODO


## Cost

CI: no GitHub Actions runs in S5 (Actions disabled) – TODO confirm.

| Category | Quantity | Credits |
| -------- | -------- | ------- |
| Agents CR-01 (`CUST-001`, runs TODO) | TODO LLM calls | TODO |
| Human delivery CR-01 (`CUST-001`) | TODO | TODO |
| Human review CR-01 (gate, browser review) | TODO | TODO |
| SR-01 (`CUST-001`, response + inventory, fact check) | TODO | TODO |
| Human delivery acceptance/handover (`CUST-001`) | TODO | TODO |
| Customer delivery (`CUST-001`): created issues describing CR-01 | Caitlin 0.25 h | 25 |
| Customer delivery (`SR-01`): php vulnerabilities answer | Caitlin 2.00 h | 200 |
| **Session delivery CUST-001 (S5)** | TODO | **TODO** |
| Factory development `FACTORY-S5` (one-off, separate): F-NEW | Fatih 0.1 h | 10.00 |
| Rework (`FACTORY-S5`): updated cost total, merged in repository changes | Caitlin 0.15 h | 15.00 |
| Factory development `FACTORY-S5`: CR-01 language adaptation | TODO | TODO |
| R-01 F-NEW runs, operational (separate) | agents 2.74 + 1.34 = 4.08; human Fatih 0.25 h (25), Daniil review 0.03 h (3) | 32.08 |

### Totals S3–S5 (from `costs/usage.csv`)

| | S3 (26.10.) | S4 (02.11.) | S5 (09.11.) | Total |
|---|---:|---:|---:|---:|
| Customer delivery `CUST-001` | 437.74 | 793.34¹ | TODO | TODO |
| Factory development | 550.00 (`FACTORY-S3`) | 241.20 (`FACTORY-S4`) | TODO (`FACTORY-S5`) | TODO |
| R-01 (baseline / experiment) | – | 82.72 | 32.08 | 114.80 |

¹ incl. 25.0 S3 rework on the S4 day (see `session-04.md`).
Budget S5: TODO · plan vs. actual: TODO · reason: TODO.

Recompute from the CSV:
```
python3 -c "import csv,collections as c;d=c.defaultdict(float);[d.__setitem__((r['date'],r['task_id']),d[(r['date'],r['task_id'])]+float(r['credits'])) for r in csv.DictReader(open('costs/usage.csv'))];[print(k,round(v,2)) for k,v in sorted(d.items())]"
```


## Three transferable lessons

1. **Measure the bottleneck before optimising, and isolate one variable.** The S4 traces showed the PO agent at 41–68 % of agent time; changing only the PO step (model, settings, task fixed, fresh R-BASE clones) made the effect attributable: −1 LLM call, −51 % credits, identical artifact hash.
2. TODO (e.g. from CR-01: what the slot contract / automated checks made easy or hard for a change request)
3. TODO (e.g. from SR-01 or acceptance: separating known facts, assumptions and customer decisions; technical approval ≠ customer acceptance)
