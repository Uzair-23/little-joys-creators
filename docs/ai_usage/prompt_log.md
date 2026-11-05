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


---

## Phase 2: What works in the brand's own ads
**Date/time:** 2026-11-05
**Mode / model:** Antigravity / Gemini 3.8 Flash (High)
**Prompt:**
```text
Read docs/data_audit.md and config.yaml. Do only Phase 2, following PRD.md sections 8.2 (stats, metrics, ad_model) and 9. Before writing code, produce a short plan covering the metrics, the analysis-set rules, the pre-registered features, and the finding rule, and wait for my approval. After approval: implement stats.py (weighted_ratio, bootstrap_ci, bh_correct, percentile_rank), metrics.py and ad_model.py. Use the duplicate-creative pairs to quantify noise and print that number. Save all tables to outputs/tables/ (ad_metrics.csv, ad_noise_from_duplicates.csv, ad_group_metrics.csv, ad_findings.csv, ad_not_concluded.csv) and charts to outputs/figures/ (forest-style plots with intervals, not bare bars). Add tests on a tiny hand-made DataFrame where the correct spend-weighted ROAS is known, and a test that a pattern depending on one outlier is rejected. Report which candidate findings fail the finding rule and why. Do not describe any pattern as proven.
```

**What the AI produced:**
- A detailed Phase 2 pre-implementation plan covering funnel metrics, analysis set rules, noise calibration thresholds from duplicate pairs, and 5-part finding rule criteria.
- `src/lj/stats.py`: Statistical aggregation and inference module implementing `weighted_ratio`, `bootstrap_ci` (5,000 iterations, seed 42), `bh_correct` (FDR adjustment), and `percentile_rank`.
- `src/lj/metrics.py`: Computes 8 funnel metrics (`roas`, `cpa`, `cvr`, `ctr`, `hook_rate`, `hold_rate`, `atc_rate`, `aov`) with safe divide handling.
- `src/lj/ad_model.py`: End-to-end model pipeline that builds `data/processed/ads_analysis_set.csv` (79 ads), computes duplicate noise (`outputs/tables/ad_noise_from_duplicates.csv`), computes group metrics with bootstrap CIs (`outputs/tables/ad_group_metrics.csv`), evaluates the 5-part finding rule producing `outputs/tables/ad_findings.csv` and `outputs/tables/ad_not_concluded.csv`, and generates forest plots and funnel charts in `outputs/figures/`.
- `docs/ad_findings.md`: Complete report on surviving findings (F01–F10), observational noise floor calibration, outlier robustness against `LJ-004`, and non-concluded patterns with explicit rejection reasons.
- `tests/test_stats.py`, `tests/test_metrics.py`, `tests/test_ad_model.py`: 13 new unit tests covering hand-crafted spend-weighted ROAS, synthetic outlier rejection, duplicate noise calibration, metric calculations, and safe divide handling.

**What I checked:**
- Verified `weighted_ratio` on hand-crafted DataFrame matches expected spend-weighted ratio (5200/1100 = 4.727 != 3.5 simple mean).
- Verified duplicate creative pairs baseline noise: median ROAS delta = 0.4914, median CVR delta = 0.0046.
- Verified that `hook_type == story_open` and `language == Hinglish` are rejected due to dependency on `LJ-004`.
- Verified analysis set row count is 79 (excludes `LJ-089` and 20 ads with spend < ₹10k).
- Ran `pytest -q` and confirmed all 23 tests passed.

**What I changed or rejected, and why:**
- Fixed signature compatibility for `bootstrap_ci` to accept both `n_iterations` and `n_boot`, and `bh_correct` to return either adjusted p-values or tuple with rejection mask when `alpha` is supplied.
- Fixed `build_analysis_set` to support returning exclusions (`return_exclusions=True`) and handle both `spend` and `spend_inr` column naming.
- Ensured `percentile_rank` correctly supports `ascending` flag.


---

## Phase 2 Correction Pass: Strict 50% LJ-004 Rule, Leave-One-Out, and Pattern Overlap
**Date/time:** 2026-11-05
**Mode / model:** Antigravity / Gemini 3.8 Flash (High)
**Prompt:**
```text
Do a Phase 2 correction pass. Do not loosen any rule.

Enforce the LJ-004 test exactly as specified: the effect without LJ-004 must have the same sign and at least 50% of the baseline effect. Print a table for all 59 tested patterns: effect with, effect without, share retained, and pass/fail. I calculate that child_led (+2.33 to +0.93), child_on_screen=one, child_in_first_3s, curiosity_gap, protein_intake, semi_pro and milk_mix_powder all keep under 50%. Show me what the code says, and re-run so the findings table reflects the rule.
LJ-004 carries all of those labels. Add a table outputs/tables/ad_lj004_traits.csv listing LJ-004’s label values and which patterns it belongs to, and add a column depends_on_lj004 to the findings and not-concluded tables.
Add leave-one-out influence for the top 5 ads by spend (not only LJ-004): for each surviving pattern, report the effect when each of those ads is dropped.
Add outputs/tables/ad_pattern_overlap.csv with the Jaccard overlap of ad sets between patterns, and note in docs/ad_findings.md that overlapping patterns are not independent.
Search the code and tell me exactly where the duplicate-pair noise floor is used. It must be context only. Remove any use as a pass/fail threshold, including the “within noise” label for Hinglish.
Treat product_form as a context variable, not a creative finding. When testing it, do not stratify by itself; stratify by launch period only.
Confirm the findings table has columns: tier (supported/directional), metric_family, 95% interval on the difference, adjusted p-value, label error rate, depends_on_lj004. List any that are missing and add them.
Add a test that a pattern keeping under 50% of its effect without LJ-004 is rejected.
Update docs/ad_findings.md with the honest framing: which patterns survive, which depend on LJ-004, which overlap, and the Hindi attention-versus-sales split. Log this correction in docs/ai_usage/corrections.md as an earlier failure to apply the 50% rule.
Run pytest, show real output, and stop.
```

**What the AI produced:**
- Updated `src/lj/ad_model.py` with the exact 50% retention test (`effect_no / effect_with >= 0.50` and same sign) without LJ-004.
- Added `outputs/tables/ad_lj004_traits.csv` showing all 10 labels of LJ-004, their spend/revenue shares, and effect retention.
- Added `outputs/tables/ad_leave_one_out_influence.csv` evaluating leave-one-out impact of the top 5 ads by spend (LJ-004, LJ-069, LJ-035, LJ-063, LJ-097).
- Added `outputs/tables/ad_pattern_overlap.csv` computing pairwise Jaccard similarity across candidate patterns.
- Reclassified `product_form` as a context variable stratified by launch period only (`outputs/tables/ad_product_form_context.csv`).
- Removed all pass/fail cutoff usage of duplicate-pair noise floor.
- Updated `ad_findings.csv` to include all required columns (`tier`, `metric_family`, `ci_diff_low`, `ci_diff_high`, `adj_p_value`, `label_error_rate`, `depends_on_lj004`).
- Added tests in `tests/test_ad_model.py` for synthetic 50% retention rejection, real LJ-004 dependent pattern rejection, and required columns check.
- Updated `docs/ad_findings.md` and `docs/ai_usage/corrections.md`.

**What I checked:**
- Verified that all 10 traits of LJ-004 keep under 50% on ROAS lift without LJ-004.
- Verified that 8 patterns survive (2 Supported: Hindi attention, Child in first 3s attention; 6 Directional).
- Confirmed all 25 tests pass in `pytest -q`.
