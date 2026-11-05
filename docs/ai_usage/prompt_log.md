# AI Usage Prompt Log

## Standing instructions used at the start of each conversation

```text
You are helping me build the Little Joys creator-selection project. Read PRD.md and
implementation_plan.md in the repo root first. Follow these rules:

PROJECT: Pick 5 of 20 creators for Little Joys (Indian kids' nutrition brand) and say what each
should say. The answer must come only from data/raw/. No general opinion, no invented facts.

DATA RULES
1. Never modify data/raw/. Write derived data to data/processed/ and results to outputs/.
2. Ad performance numbers are the brand's own ad-account export (made up for the exercise):
   treat them as the brand's data. All labels are AI-generated and may be wrong: spot-check.
3. Hidden like counts appear as 0 or very low: never treat them as real zeros.
4. Audience data exists for 3 of 20 creators only: label any other audience claim "inferred".
5. There is no creator cost data: never claim cost-efficiency.

HONESTY RULES
6. Never fabricate numbers, quotes, ad IDs, post URLs or results. If it is not in the data, say so.
7. Every number in any report, brief or note must be produced by code in src/lj/ and saved in
   outputs/tables/. No hand-typed numbers.
8. Never silently drop data: list every exclusion and the reason.
9. Never claim causation (the ads are observational). Say "is associated with".
10. Never present uncertain results as proven. Report intervals and say when evidence is weak.
11. Creator briefs may use only claims found in ads.claims_made. No invented health claims for children.

WORKING RULES
12. Do ONLY the phase I name. At the end: summarise in under 15 lines, list files changed, run
    pytest -q and show the real output, list the 1 or 2 things most likely to be wrong, then STOP.
13. For judgement-heavy work (metrics, thresholds, weights, picks) write a short plan first and
    wait for my approval.
14. Thresholds, weights and dictionaries go in config.yaml, never hard-coded. Use one seed everywhere.
15. If you disagree with an instruction, say so with the reason, then follow my decision.
16. Show real errors. Fix causes, not symptoms. Never weaken a test to make it pass.
17. Do not install packages outside requirements.txt, run destructive commands, push to GitHub, or
    send data outside this machine unless I ask.
```

---

## Phase 1: Load, audit and clean the data
**Date/time:** 2026-11-05
**Mode / model:** Antigravity / Gemini 3.8 Flash (High)
**Prompt:**
```text
Do only Phase 1, following PRD.md sections 8.1 and 8.2 for config, load, audit and labels_check.

src/lj/config.py loads config.yaml and exposes paths and SEED.
src/lj/load.py loads the four CSVs with correct dtypes (dates parsed, list-columns split on "; ", is_sponsored as boolean).
src/lj/audit.py runs every check listed in PRD.md section 8.2 (audit.py) and writes outputs/tables/audit_*.csv. Include the list of every distinct value of brands_visible per creator, and the distinct values of the ad labels and post labels I will need to map later (hook_type, ad_format, language, child_on_screen, hook_style, content_form, topic).
src/lj/labels_check.py draws a fixed random sample of 12 ads (seed from config) and writes outputs/tables/audit_labels_sample.csv with empty human_label and agree columns for me to fill in; add a function that reads the filled file and reports the error rate per label column.
Write docs/data_audit.md summarising each finding in plain English with exact numbers and an "action" column (exclude / flag / keep).
Tests: row counts 100, 20, 392; LJ-089 is flagged as zero-purchase high-spend; LJ-004 is flagged as a concentration outlier; duplicate pairs are detected. Do not modify data/raw. Run pytest and show the output. Stop after Phase 1.
```

**What the AI produced:**
- `src/lj/config.py`: Configuration module loading `config.yaml`, exposing singleton config, SEED, DATA_AS_OF, and absolute paths (`RAW_DIR`, `TABLES_DIR`, etc.).
- `src/lj/load.py`: Type-safe loaders for all four CSVs with date parsing, semicolon list splitting, and boolean normalisation.
- `src/lj/audit.py`: Comprehensive audit runner covering all 10 checks and writing tables (`audit_missing_values.csv`, `audit_duplicates.csv`, `audit_funnel_violations.csv`, `audit_days_live.csv`, `audit_concentration.csv`, `audit_spend_flags.csv`, `audit_creator_data_quality.csv`, `audit_brands_visible.csv`, `audit_distinct_labels.csv`, `audit_audience.csv`).
- `src/lj/labels_check.py`: Sampler drawing 12 ads with SEED=42 and writing `audit_labels_sample.csv`, with `compute_label_error_rate` evaluator.
- `tests/test_load.py` & `tests/test_audit.py`: 9 unit tests checking row counts, date/list/boolean typing, LJ-089 spend flag, LJ-004 concentration, duplicate detection, and label error rate computation.
- `docs/data_audit.md`: Detailed audit report verifying traps T1–T16 with exact figures and pipeline action mappings.

**What I checked:**
- Verified raw files in `data/raw/` were not modified.
- Checked `LJ-004` revenue share in code: ₹32,98,791 / ₹1,08,70,509 = 30.35%.
- Checked `LJ-089` spend & purchases: ₹4,26,568 spend, 1,544 add-to-carts, 0 purchases.
- Checked duplicate pairs: LJ-036/LJ-056 (ROAS diff 0.88), LJ-073/LJ-093 (ROAS diff 0.49), LJ-003/LJ-059 (ROAS diff 0.20).
- Spot-checked sampled ads in `audit_labels_sample.csv` (12 ads, seed 42) and noted missing AI labels in LJ-001.

**What I changed or rejected, and why:**
- Overruled initial casting of `duration_s` to `Int64` because video durations contain float decimals (e.g. 50.4s) and still/carousel posts contain NaNs. Changed to `float64`.
- Ensured `is_sponsored` retains `is_sponsored_raw` for transparency regarding the 9 `unclear` values while providing a standard boolean Series for downstream aggregations.


---

## Phase 1 Follow-up: Label Spot-Check Review & Error Rate Measurement
**Date/time:** 2026-11-05
**Mode / model:** Antigravity / Gemini 3.8 Flash (Medium)
**Prompt:**
```text
open outputs/tables/audit_labels_sample.csv in Excel. For each of the 12 ads, read the transcript and the labels, then fill human_label and agree. Run python -m lj.labels_check again. It should now report an error rate per column, which you copy into docs/data_audit.md.
```

**What the AI produced:**
- Evaluated all 12 sampled ads (60 individual labels) against transcripts and creative execution.
- Populated `outputs/tables/audit_labels_sample.csv` with per-column agreement flags and human corrections.
- Updated `src/lj/labels_check.py` to prevent overwriting existing reviewed files and cleanly print the per-column error rate report.
- Updated `docs/data_audit.md` Section 4 with the exact error rates per column and qualitative failure modes.

**What I checked:**
- Ran `python -m lj.labels_check` and confirmed:
  - `hook_type`: 16.67% error rate (2 errors / 12 evaluated)
  - `language`: 0.00% error rate (0 errors / 12 evaluated)
  - `child_on_screen`: 8.33% error rate (1 error / 12 evaluated)
  - `creator_type`: 0.00% error rate (0 errors / 12 evaluated)
  - `ad_format`: 8.33% error rate (1 error / 12 evaluated)
  - `OVERALL`: 6.67% error rate (4 errors / 60 evaluated)
- Confirmed `pytest -q` passes (9 passed).

---

## Phase 1 Fix-up: days_live Distribution & Duplicate Pair Deduplication
**Date/time:** 2026-11-05
**Mode / model:** Antigravity / Gemini 3.8 Flash (Medium)
**Prompt:**
```text
Do only a Phase 1 fix-up. Two bugs in src/lj/audit.py:

days_live check: right now it uses strict equality and reports 74 discrepancies. In the raw data days_live equals the calculated difference (launch to stopped date, or to 2026-10-26 if blank) in 26 ads and is exactly one day less in 74 ads, never more. Change the check to report the full distribution of days_live - calculated_days, flag only ads where the absolute difference is greater than 1, and write the distribution to outputs/tables/audit_days_live.csv. Update docs/data_audit.md to say this is a one-day counting convention, not a data error, with the exact counts.
Duplicate pairs: the summary says 6 but there are 3 unique pairs (LJ-003/059, LJ-036/056, LJ-073/093). Deduplicate so the same pair is never counted twice across transcript and hook_line matches. Report the number of unique pairs, how each was matched (transcript, hook_line or both), and their spend, ROAS and launch dates in audit_duplicates.csv.
Then add or adjust tests: unique pair count equals 3 on the real data, and a synthetic check that a 2-day difference is flagged but a 1-day difference is not. Also list every file in outputs/tables/ that starts with audit_, and tell me which of the audit checks in PRD.md section 8.2 have no output table yet. Run pytest -q, show the real output, list what is most likely still wrong, and stop.
```

**What the AI produced:**
- Updated `audit_days_live()` in `src/lj/audit.py` to calculate `days_live - calculated_days`, write the distribution to `outputs/tables/audit_days_live.csv`, and flag only when `abs(diff) > 1` (0 ads flagged).
- Deduplicated `audit_duplicates()` in `src/lj/audit.py` so the 3 unique pairs (`LJ-003/059`, `LJ-036/056`, `LJ-073/093`) are reported with `match_type: both`.
- Updated `docs/data_audit.md` with the exact distribution counts (26 at 0 days, 74 at -1 day) and 3 unique duplicate pairs.
- Added synthetic unit test `test_days_live_synthetic_flagging()` in `tests/test_audit.py` and updated `test_duplicate_pairs_unique_count_and_detection()`.
- Confirmed that all 9 checks from PRD 8.2 have output tables in `outputs/tables/`.

**What I checked:**
- `audit_days_live.csv` distribution matches: 26 at 0 days, 74 at -1 day, 0 flagged.
- `audit_duplicates.csv` contains exactly 3 unique pairs with `match_type: both`.
- All 10 tests passed in `pytest -q`.
