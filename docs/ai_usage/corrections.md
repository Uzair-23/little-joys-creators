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
