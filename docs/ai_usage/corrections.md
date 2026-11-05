# AI Usage Corrections Log

This log documents every instance where the AI generated incorrect code, incorrect assumptions, or overconfident claims, and how it was detected and corrected.

---

### Entry 1: Type Coercion Error on Ad Duration and Creator Plays
- **Phase:** Phase 1 (Data Loading & Audit)
- **What the AI proposed/generated:** In `src/lj/load.py`, the AI initially grouped `duration_s` under `int_cols` with `.astype("Int64")` across `ads.csv` and `creator_posts.csv`.
- **How it failed / was caught:** Execution of `load_ads()` threw `TypeError: cannot safely cast non-equivalent object to int64` during test execution. Inspecting `ads.csv` revealed that `duration_s` contains floating-point values with decimals (e.g., 50.4, 22.1, 63.8 seconds). Furthermore, in `creator_posts.csv`, 39 rows have missing `duration_s` and `plays` because they are static images or carousels (`still_or_carousel`), not video reels.
- **Root Cause:** Assuming video duration in seconds was strictly integer-valued without inspecting the raw distribution first.
- **The Fix:** Fixed causes, not symptoms: separated `duration_s` and `plays` into `float_cols` with `pd.to_numeric(..., errors="coerce").astype("float64")`, correctly preserving floating-point second fractions and nullable values for photo/carousel posts.


---

### Entry 2: Duplicate Pairs Double Counting & days_live Strict Equality
- **Phase:** Phase 1 Fix-up (Audit & Metrics)
- **What the AI proposed/generated:**
  1. In `src/lj/audit.py`, duplicate creatives were checked separately by `transcript` and `hook_line`. Because all three identical creative pairs match on both fields, the summary reported 6 pairs instead of 3 unique pairs.
  2. The `days_live` check used strict equality (`days_live == (stopped - launch)`), flagging 74 ads as discrepancies rather than recognizing the platform's standard 1-day counting convention.
- **How it failed / was caught:** Caught during audit review. Inspecting the raw data confirmed that exactly 3 unique pairs exist (matching on both transcript and hook line) and that the 74 ads with difference = -1 are simply an exclusive-boundary date counting convention, with 0 ads exceeding 1 day.
- **The Fix:**
  1. Deduplicated pairs across transcript and hook_line, reporting unique pairs with `match_type` (`both`).
  2. Updated `audit_days_live` to report the full distribution of `days_live - calculated_days` (26 at 0 days, 74 at -1 day), flagging only ads where `abs(difference) > 1` (0 flagged).
  3. Added synthetic unit test verifying 2-day differences are flagged while 1-day differences are not.


---

### Entry 3: Outlier Sensitivity in Candidate Ad Findings (LJ-004 False Leads)
- **Phase:** Phase 2 (Ad Modeling & Findings)
- **What the AI proposed/generated:** Initial aggregations of feature levels showed strong positive ROAS for `hook_type == story_open` (ROAS 2.39) and `language == Hinglish` (ROAS 2.18), which an uncalibrated analysis would promote as top-performing creative patterns.
- **How it failed / was caught:** Caught by the mandatory pre-registered 5-part finding rule requiring re-evaluation with `LJ-004` omitted. When `LJ-004` was excluded, `story_open` ROAS collapsed to 0.92 (worse than the non-LJ-004 benchmark of 1.22), and `Hinglish` lift collapsed to +0.06x (well within the 0.49x duplicate noise floor).
- **The Fix:** Adhered strictly to the finding rule: both patterns were rejected, flagged as `fails_without_lj004`, and moved to `outputs/tables/ad_not_concluded.csv`. Documented this clearly in `docs/ad_findings.md` as false leads driven entirely by a single high-spend outlier.


---

### Entry 4: Failure to Enforce 50% Retention Rule on LJ-004 Outlier Sensitivity
- **Phase:** Phase 2 Correction Pass (Ad Modeling & Finding Rule)
- **What the AI proposed/generated:** In the initial Phase 2 run, the AI promoted `ad_format=child_led`, `child_on_screen=one`, `hook_driver=curiosity_gap`, and `main_benefit=protein_intake` as surviving conversion findings because their effects remained positive without `LJ-004`. The AI also used the duplicate-pair noise floor as a pass/fail cutoff threshold and treated `product_form=milk_mix_powder` as a creative finding.
- **How it failed / was caught:** User correction caught that the strict methodology rule requires the effect without `LJ-004` to maintain the same sign **and retain at least 50%** of the baseline effect. Without `LJ-004`, `child_led` ROAS lift dropped from +2.33 to +0.93 (39.8% retained < 50%), `child_on_screen=one` dropped to 37.2% retained, `curiosity_gap` dropped to 21.5% retained, and `protein_intake` dropped to 30.5% retained. All of these traits were carried by `LJ-004` and failed the 50% rule. Furthermore, duplicate-pair noise was improperly used as a cutoff filter, and `product_form` was confounded with creative features.
- **The Fix:** 
  1. Updated `evaluate_finding_rule` and `evaluate_ad_features` in `src/lj/ad_model.py` to strictly enforce `share_retained >= 0.50` and same sign. All patterns retaining < 50% without `LJ-004` are now marked `depends_on_lj004: True` and rejected into `ad_not_concluded.csv`.
  2. Removed all usage of the duplicate-pair noise floor as a pass/fail threshold, preserving it strictly as contextual benchmark information.
  3. Reclassified `product_form` as a context variable, stratified by launch period only (`outputs/tables/ad_product_form_context.csv`).
  4. Added `outputs/tables/ad_lj004_traits.csv` documenting the 10 traits carried by `LJ-004`, `outputs/tables/ad_leave_one_out_influence.csv` evaluating top 5 spend ads, and `outputs/tables/ad_pattern_overlap.csv` computing Jaccard similarities.
  5. Added unit test `test_pattern_keeping_under_50_pct_without_lj004_rejected_synthetic` in `tests/test_ad_model.py`.
