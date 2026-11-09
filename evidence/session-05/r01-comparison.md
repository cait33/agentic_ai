# R-01 comparison: F-BASE vs. F-NEW (Session 5, task 3)

## Change under test

- **Hypothesis (S4):** the PO agent dominates agent runtime (S3 68 %, S4 53 %, R-01 baseline 41 %) although the brief states the content verbatim. Reusing the PO output when brief, PO prompt and model settings are unchanged reduces agent time per R-01 run by ≥ 40 % with the same check quality.
- **F-BASE** `01017ae` → **F-NEW** `b7f4161` (PR #40): `src/factory/po_cache.py`, cache key = sha256(brief, PO system prompt, provider, model, temperature, format version); only successful PO results are cached; hit/miss recorded in trace + manifest; reused requirements copied into the run directory; `--no-po-cache` disables it. 6 new deterministic Factory tests (mock LLM), `tests/factory` 41 passed. Only other code difference F-BASE→F-NEW: task ID in `projects/website-01.json` + its test (not used by R-01).
- Merged without a second review (time pressure).

## Comparability

| | Baseline (S4) | F-NEW run 1 | F-NEW run 2 |
|---|---|---|---|
| Run | `3ba82f0f` | `e9902441` | `c97a41cc` |
| Factory | F-BASE `01017ae` | F-NEW `b7f4161` | F-NEW `b7f4161` |
| Product input (R-BASE + `test_r01.py`) | `66339b6` | `66339b6` (fresh clone `~/r01-new1`) | `66339b6` (fresh clone `~/r01-new2`) |
| Task / criteria | `docs/customer-01/r01.md`, `test_r01.py` + 23 checks | same | same |
| Model / settings | qwen3:4b `359d7dd4bcda`, temp 0, JSON mode, reasoning off | same | same |
| PO cache | n/a | empty → miss, stored | hit (source `e9902441`) |
| Reviewer | Daniil | Daniil | Daniil |

Each run used its own fresh checkout of `66339b6`; no R-01 result files or patches from an earlier run were reused. The only thing carried from run 1 to run 2 is the PO cache entry – this is the change under test, documented as such.

## Results (raw data: `runs/website-01-r01/<run>/trace.jsonl`, `manifest.json`)

| | Baseline `3ba82f0f` | F-NEW run 1 `e9902441` (miss) | F-NEW run 2 `c97a41cc` (hit) |
|---|---:|---:|---:|
| PO agent | 25.9 s, 1 call, 659/368 tok | 28.0 s, 1 call, 659/368 tok | **0.0 s, 0 calls** |
| Web implementer | 36.8 s, 1580/518 tok | 37.3 s, 1580/518 tok | 27.7 s, 1580/518 tok |
| QA | 0.8 s | 0.7 s | 0.7 s |
| **Agent time total** | **63.6 s** | **66.0 s (+4 %)** | **28.3 s (−55 %)** |
| LLM calls | 2 | 2 | 1 |
| **Agent credits** | **2.72** | **2.74 (+1 %)** | **1.34 (−51 %)** |
| Product check | 25/25 | 25/25 | 25/25 |
| Regression (AC-01–08) | 23/23 | 23/23 | 23/23 |
| Artifact sha256 | `ce03f072…` | `ce03f072…` (identical) | `ce03f072…` (identical) |
| Correction rounds / faults | 0 / none | 0 / none | 0 / none |
| Human review at gate (Daniil), from trace¹ | 153 s ≈ 2.5 min (noted manually 13:25–13:27) | 54 s ≈ 0.9 min (start 11:23:25; noted ≈ 11:24:30–11:25:00) | 59 s ≈ 1.0 min (start 11:27:19) |
| Rework | 0 | 0 | 0 |
| Workflow duration incl. human wait | 216 s | 120 s | 87 s |

¹ Gate time = workflow duration incl. human wait − agent time (216.4−63.6 / 120.5−66.0 / 87.3−28.3 s); same method for all three runs. It includes reading the gate output and the browser check.

## Interpretation and limits

- **Effect:** with a cache hit the PO call disappears (−25.9 to −28.0 s, −1 LLM call); total agent time −55 % and credits −51 % vs. baseline, with identical output (same artifact hash) and identical check results. The hypothesis threshold (≥ 40 %) is met for the hit run.
- **Variability:** the implementer time varied between 27.7 s and 37.3 s with identical tokens (≈ ±15 % around the mean), i.e. part of the −55 % is runtime noise. Removing only the PO share gives ≈ −41 % (63.6 s → 37.7 s). Sample: 1 baseline run, 2 F-NEW runs (1 miss, 1 hit) – a preliminary observation, not a statistically robust result.
- **Cold start:** without a matching cache entry (new or changed brief) F-NEW behaves like F-BASE (run 1: +4 %, within noise). The benefit therefore only appears for repeated runs on an unchanged brief (re-runs after rejection, repeated experiments) – not for a new customer request such as CR-01.
- **Review time** was shorter in the F-NEW runs, but the reviewer had already seen the identical result in the baseline; this is a learning effect, not an effect of F-NEW.
- **Risk:** stale stories if relevant input changes outside the key (e.g. product state). Mitigated by keying on brief, prompt and model; product changes do not affect PO input.

## Decision

**Keep F-NEW** (enabled by default, `--no-po-cache` available): the saving is deterministic when it applies (one LLM call less, no change of output or check results), it costs nothing on a miss, and it is fully traceable in trace/manifest. **Adapt later** only if more runs show a quality difference; repeat the comparison with ≥ 2 runs per variant when time allows.

## Costs (separate)

- F-NEW development (`FACTORY-S5`, one-off): Fatih 0.1 h = 10 credits (integration, tests, PR #40; AI-assisted).
- R-01 comparison runs (operational, `R-01`): agents 2.74 + 1.34 = 4.08 credits; human operation Fatih 0.25 h = 25 credits; review Daniil 113 s ≈ 0.03 h = 3 credits.
