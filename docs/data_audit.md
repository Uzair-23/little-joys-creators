# Little Joys Creator Selection: Data Audit Report (Phase 1)

| | |
|---|---|
| **Dataset Date** | Data as of 26 October 2026 |
| **Pipeline Module** | `src/lj/audit.py`, `src/lj/labels_check.py` |
| **Artifacts** | `outputs/tables/audit_*.csv` |
| **Status** | Phase 1 Complete (Audit, Quality Checks & Label Spot-Check) |

---

## 1. Executive Summary

A comprehensive data audit was executed on the four raw data files (`ads.csv`, `creators.csv`, `creator_posts.csv`, `creator_audience.csv`) using the pipeline in `src/lj/audit.py`.

Key numbers verified by code:
- **Ads dataset**: 100 ads with total spend of **₹72,64,228** and total revenue of **₹1,08,70,509** (overall spend-weighted ROAS of **1.50**).
- **Creators dataset**: 20 candidate creators across diverse parenting, pediatric, culinary, and lifestyle niches.
- **Creator posts dataset**: 392 posts (19 creators with 20 posts each, 1 creator CR-18 with 12 posts).
- **Audience dataset**: Known for only **3 of 20 creators** (CR-14, CR-15, CR-20); the remaining 17 creators require inferred audience attributes.
- **Label Spot-Check**: 12 ads sampled with fixed seed (`seed: 42`) into `outputs/tables/audit_labels_sample.csv` for human verification.

---

## 2. Evaluation of Known Data Traps (T1 – T16)

Every suspected trap was tested directly against the raw data. Findings, exact numbers, and pipeline actions are detailed below.

| # | Trap / Hypothesis | Finding & Exact Numbers from Code | Action | Pipeline Implementation |
|---|---|---|---|---|
| **T1** | **LJ-004 concentration outlier** | **CONFIRMED**: Spend ₹6,59,494 (9.08% of total spend), Revenue ₹32,98,791 (**30.35% of total revenue**), ROAS **5.00**. Top 1 ad generates nearly a third of all revenue. | **Keep & Test Both Ways** | Pre-registered in `config.yaml` (`outlier_ads: ["LJ-004"]`). Every creative finding in Phase 2 must be evaluated with and without LJ-004. |
| **T2** | **LJ-089 tracking fault** | **CONFIRMED**: Spend ₹4,26,568 (5.87% of total spend), 1,544 add-to-carts, **0 purchases**, ₹0 revenue. The zero purchase count amidst high add-to-carts represents an instrumentation failure. | **Exclude from Performance Models** | Excluded from the performance analysis set (`suspected_tracking_fault: ["LJ-089"]`); retained in spend tracking and duplicate calibration. |
| **T3** | **Tiny-spend ads with volatile ROAS** | **CONFIRMED**: Exactly 20 ads have spend < ₹10,000 (ranging from ₹298 to ₹9,569). E.g., LJ-072 spent ₹4,117 and generated ₹12,350 revenue (ROAS 3.00 with only 18 purchases). | **Exclude below ₹10k threshold** | Set `min_spend_inr: 10000` for analysis set, with sensitivity variants at ₹5k, ₹10k, and ₹20k. |
| **T4** | **Duplicate creative pairs** | **CONFIRMED**: Exactly **3 unique pairs** of identical creatives detected, matching on **both** transcript and hook line:<br>1. **LJ-003 / LJ-059**: ROAS 0.78 vs 0.58 (diff: 0.20)<br>2. **LJ-036 / LJ-056**: ROAS 1.42 vs 2.30 (diff: 0.88)<br>3. **LJ-073 / LJ-093**: ROAS 0.78 vs 1.27 (diff: 0.49) | **Keep & Use as Noise Baseline** | Deduplicated across criteria to prevent double counting. Differences establish observational noise. Any creative finding in Phase 2 must show effect sizes exceeding this duplicate-pair variance. |
| **T5** | **CR-20 past partner & male skew** | **CONFIRMED**: Audience file records past brand as `Little Joys`. Audience is **70.1% male** and only 29.9% female (fails the 50% female gate). | **Exclude** | Hard gate exclusion: `already_partner` (Little Joys) and `audience_mismatch` (<50% women). |
| **T6** | **CR-14 foreign audience & platform** | **CONFIRMED**: Audience data is from `Facebook` (not Instagram); **35.6% outside India** (India share 64.4%, Pakistan 10.3%, Bangladesh 6.5%). Median plays per follower is only 0.27 (3,06,092 median plays / 11,20,817 followers). | **Exclude / Gate Out** | Hard gate exclusion: `min_india_share_known: 0.80` (64.4% < 80.0%). Flagged for platform discrepancy. |
| **T7** | **CR-05 child performer compliance** | **CONFIRMED**: Handle `theshilpashow`, 2.83M followers, persona `precocious child performer`. 20 of 20 posts feature children on camera, primarily scripted comedic performances. | **Soft Flag & Compliance Review** | Flagged with `child_performer_flag`. Retained for scoring but penalized under commercial risk (0.20 penalty); requires legal/compliance check. |
| **T8** | **CR-17 sponsored saturation & hidden likes** | **CONFIRMED**: Exactly 20 of 20 posts (**100%**) are sponsored. 6 of 20 posts (30%) have hidden likes (likes ≤ 5). Low organic engagement. | **Soft Flag / Penalty** | Flagged with `sponsored_saturation_100%` and `hidden_likes_30%`. Evaluated on comments/reshares only, penalized in commercial risk score. |
| **T9** | **Sponsored vs organic reach gap** | **CONFIRMED**: For creators with ≥3 sponsored and ≥3 organic posts (n=8 creators), the median ratio of sponsored median plays to organic median plays is **0.58** (42% discount). Overall pooled median plays: Organic = 4,44,695 vs Sponsored = 4,26,418. | **Adjust in Reach Scoring** | Reach scoring must use sponsored median where available, or organic median scaled by the pooled 0.58 factor. Never forecast sponsored reach directly from organic. |
| **T10** | **Audience data scarcity** | **CONFIRMED**: Audience file contains exactly 3 creators (CR-14, CR-15, CR-20). The remaining 17 creators have zero first-party audience metrics. | **Keep & Label Inferred** | Set `audience_fit` to neutral (0.50) for unmeasured creators, and reduce their confidence score by 1 point. All reports must label them "inferred". |
| **T11** | **Competitor & adjacent brands visible** | **CONFIRMED**: 203 creator-brand co-occurrences found across 195 distinct brand names. Confirmed direct competitor `Gritzo` appears in CR-08. Adjacent snacks/wellness include `Cadbury`, `Chupa Chups`, `Himalaya`, `Bournvita`, `Keekee`, `Troovy`, `Little Tummys`. | **Flag & Categorise** | Direct competitors fail `direct_competitor` gate; adjacent brands trigger penalty in commercial risk score. |
| **T12** | **AI label errors and missingness** | **CONFIRMED**: Ads have missing values in `ad_copy` (12), `hook_type` (2), `hook_text_on_screen` (15), `ad_format` (2), `story_structure` (2), `child_role` (2). 12-ad spot-check reveals **6.67% overall error rate** (4 errors across 60 evaluated labels): `hook_type` 16.67% error rate, `ad_format` 8.33%, `child_on_screen` 8.33%, `language` 0.00%, `creator_type` 0.00%. | **Spot-Check & Quote Rate** | Measured error rates recorded in audit and quoted in report. Creative findings must use robust groups and fallback mappings to avoid reliance on fragile labels. |
| **T13** | **Small sample chance findings (100 ads)** | **CONFIRMED**: 100 ads partitioned across ~35 categorical levels creates small sample groups (<8 ads). High risk of p-hacking and false discovery. | **Strict Finding Rule** | Require `min_group_size: 8`, two-metric consistency (`[roas, cvr]` or `[hook_rate, hold_rate]`), Benjamini-Hochberg FDR control, and bootstrap intervals. |
| **T14** | **Ad duration & days live discrepancy** | **CONFIRMED**: Reported `days_live` equals calendar difference `(stopped - launch)` in exactly **26 ads** (26.0%) and is exactly one day less in **74 ads** (74.0%), never more. Exactly **0 ads** have an absolute difference greater than 1 day. This reflects a standard 1-day platform counting convention (exclusive vs inclusive boundary), not a data error. | **Keep & Use Rates** | Not a data corruption issue. However, because ads ran differing lengths (1 to 25 days; all stopped by 2026-10-03), cumulative totals are non-comparable; evaluation must use rate metrics. |
| **T15** | **Hidden like counts** | **CONFIRMED**: 10 posts across 3 creators (CR-17: 6 posts, CR-09: 3 posts, CR-02: 1 post) have likes ≤ 5 (mostly 0 or 1), reflecting hidden like settings. | **Flag & Adjust Basis** | Never treat hidden likes as real zero engagement. Switch engagement calculation to `(comments + reshares) / plays` and apply confidence penalty. |
| **T16** | **Absence of creator cost data** | **CONFIRMED**: Neither `creators.csv` nor `creator_posts.csv` contains rate cards, historical fees, or production costs. | **Strict Non-Claim Rule** | Never claim or report cost-efficiency, creator ROI, or expected CPM/CPA for creator partnerships. |

---

## 3. Data Audit Check Details

### 3.1 Missing Value Analysis (`audit_missing_values.csv`)
- **`ads.csv` (100 rows, 56 columns)**:
  - `ad_copy`: 12 missing (12.0%)
  - `hook_text_on_screen`: 15 missing (15.0%)
  - `hook_type`: 2 missing (2.0%) — ads LJ-001, LJ-010
  - `ad_format`: 2 missing (2.0%) — ads LJ-001, LJ-010
  - `story_structure`: 2 missing (2.0%) — ads LJ-001, LJ-010
  - `creator_age`: 1 missing (1.0%)
  - `child_role`: 2 empty lists (2.0%)
  - `brand_first_said`: 2 missing (2.0%)
- **`creators.csv` (20 rows, 21 columns)**:
  - `bio`: 3 missing (15.0%) — CR-06, CR-13, CR-18
  - All profile metrics, follower counts, handles, and categorisation narratives are 100% complete.
- **`creator_posts.csv` (392 rows, 32 columns)**:
  - `transcript`: 279 missing (71.2%) — transcripts are present for ~6 posts per creator (113 total).
  - `transcript_language`: 278 missing (70.9%).
  - `brands_visible`: 233 missing/empty (59.4%) — indicates posts with no sponsored or identifiable brand tags.
  - `child_ages`: 142 missing/empty (36.2%) — indicates posts where no child was present or aged.
  - `on_screen_text`: 55 missing (14.0%).
  - `duration_s` & `plays`: 39 missing (9.9%) — corresponds exactly to still image / carousel posts (`still_or_carousel`).
  - `hook_style`: 1 missing (0.3%).
- **`creator_audience.csv` (3 rows, 10 columns)**:
  - `brands_in_past_year`: 1 missing (CR-14 has no recorded brand deals).
  - All demographic splits, platforms, and locations are 100% complete for the 3 records.

### 3.2 Duplicate Creative Analysis (`audit_duplicates.csv`)
Exactly **3 unique pairs** of ads have identical creatives, matched on **both** transcript and hook line (deduplicated across match types to avoid double counting):
1. **PAIR-LJ-036-LJ-056** (Matched: `both`):
   - Both launched 2026-09-21.
   - LJ-036: Spend ₹63,859, Purchases 146, Revenue ₹90,878, ROAS 1.42, CVR 3.49%.
   - LJ-056: Spend ₹15,591, Purchases 58, Revenue ₹35,874, ROAS 2.30, CVR 3.56%.
   - CVR is almost identical (3.49% vs 3.56%), but ROAS varies by **0.88x** due to AOV differences.
2. **PAIR-LJ-073-LJ-093** (Matched: `both`):
   - LJ-073 launched 2026-08-20; LJ-093 launched 2026-09-17.
   - LJ-073: Spend ₹14,738, Purchases 22, Revenue ₹11,492, ROAS 0.78, CVR 1.83%.
   - LJ-093: Spend ₹75,334, Purchases 164, Revenue ₹95,767, ROAS 1.27, CVR 3.32%.
   - ROAS delta is **0.49x**; CVR differs by 1.49 percentage points.
3. **PAIR-LJ-003-LJ-059** (Matched: `both`):
   - LJ-003 launched 2026-09-02; LJ-059 launched 2026-09-23.
   - LJ-003: Spend ₹1,05,761, Purchases 133, Revenue ₹82,907, ROAS 0.78, CVR 0.96%.
   - LJ-059: Spend ₹15,484, Purchases 14, Revenue ₹9,048, ROAS 0.58, CVR 1.42%.
   - ROAS delta is **0.20x**.

**Conclusion**: Identical creative assets experience natural performance variation of ±0.20 to ±0.88 in ROAS and ±0.5% to ±1.5% in CVR due to auction bidding, audience sampling, and launch timing. Any Phase 2 creative finding must exceed this noise band to be deemed credible.

### 3.3 Funnel Integrity (`audit_funnel_violations.csv`)
- **Violations Found**: 0.
- All 100 ads satisfy:
  - `purchases <= add_to_carts` (0 violations)
  - `link_clicks <= impressions` (0 violations)
  - `thruplays <= video_3s_views` (0 violations)
  - `add_to_carts <= link_clicks` (0 violations)

### 3.4 Days Live Distribution & Counting Convention (`audit_days_live.csv`)
Analysis of `days_live - calculated_days` (launch to stopped date, or to 2026-10-26 if blank):

| Difference (`days_live - calculated`) | Ad Count | Share of Ads | Flagged (`abs(diff) > 1`) | Interpretation |
|---|---|---|---|---|
| **0 days** | 26 | 26.0% | **False** | Exact match: `days_live` equals calendar duration (inclusive boundary). |
| **-1 day** | 74 | 74.0% | **False** | One-day convention: `days_live` equals calendar duration minus 1 (exclusive stop date / boundary). |
| **> 1 day** | 0 | 0.0% | — | Zero ads exhibit discrepancies greater than 1 day. |

**Key Finding**: This 1-day variance is a **consistent platform counting convention** (whether the stop date hour is counted as a full calendar day), not a data corruption error. Exactly 0 ads exceed the allowable 1-day boundary. All 100 ads were stopped by 3 October 2026 (zero ads live as of 26 October 2026). Days live ranges from 1 to 25 days (mean: 17.5 days). Totals cannot be compared across ads; analysis must use rate metrics.

### 3.5 Spend and Revenue Concentration (`audit_concentration.csv`)
Concentration is heavily skewed toward top-performing creatives:

| Top K Ads | Cumulative Spend (₹) | Spend Share | Cumulative Revenue (₹) | Revenue Share | Top Revenue Ad IDs |
|---|---|---|---|---|---|
| **Top 1** | ₹6,59,494 | 9.08% | ₹32,98,791 | **30.35%** | LJ-004 |
| **Top 3** | ₹14,94,868 | 20.58% | ₹49,27,998 | **45.33%** | LJ-004, LJ-041, LJ-022 |
| **Top 5** | ₹21,68,970 | 29.86% | ₹58,04,382 | **53.39%** | LJ-004, LJ-041, LJ-022, LJ-063, LJ-034 |
| **Top 10** | ₹33,83,184 | 46.57% | ₹70,69,634 | **65.04%** | LJ-004, LJ-041, LJ-022, LJ-063, LJ-034, LJ-031, LJ-088, LJ-093, LJ-036, LJ-077 |

**LJ-004 Impact**: Ad LJ-004 alone accounts for **30.35%** of all revenue. Any aggregate metric without LJ-004 controls will merely reflect LJ-004's creative features (Hinglish, problem_statement, explainer_to_camera, milk powder).

### 3.6 Spend Anomaly Flags (`audit_spend_flags.csv`)
- **Zero-Purchase High-Spend**:
  - `LJ-089`: Spend ₹4,26,568, Add-to-Carts 1,544, Purchases 0, Revenue ₹0. Confirmed instrumentation failure.
- **Below Minimum Spend (< ₹10,000)**:
  - Exactly 20 ads flagged (LJ-001, LJ-005, LJ-011, LJ-012, LJ-016, LJ-027, LJ-030, LJ-038, LJ-039, LJ-043, LJ-049, LJ-054, LJ-058, LJ-070, LJ-071, LJ-072, LJ-083, LJ-094, LJ-099, LJ-100).
  - Spend ranges from ₹298 (LJ-083) to ₹9,569 (LJ-038).

### 3.7 Creator Data Quality (`audit_creator_data_quality.csv`)
- **Post Volume**: 19 creators have exactly 20 posts. Only `CR-18` has 12 posts (still above the `min_posts: 8` gate).
- **Future Dated Posts**: `CR-18` has 1 post dated after `data_as_of` (posted 2026-10-27 vs `data_as_of` 2026-10-26).
- **Hidden Likes (likes ≤ 5)**:
  - `CR-17`: 6 of 20 posts (30.0%) have hidden likes (flagged).
  - `CR-09`: 3 of 20 posts (15.0%) have hidden likes.
  - `CR-02`: 1 of 20 posts (5.0%) has hidden likes.
- **Sponsored Saturation**:
  - `CR-17`: 20 of 20 posts (100.0%) are sponsored (flagged).
  - `CR-09`: 16 of 20 posts (80.0%) are sponsored (flagged).
  - `CR-19`: 15 of 20 posts (75.0%) are sponsored (flagged).
  - `CR-13`: 12 of 20 posts (60.0%) are sponsored.
- **Inactivity (>45 days)**:
  - `CR-09`: Last post 48 days prior to `data_as_of` (flagged).

### 3.8 Distinct Brand & Label Inventories (`audit_brands_visible.csv`, `audit_distinct_labels.csv`)
- **Distinct Brands**: 195 distinct brands identified across candidate posts.
  - Competitor `Gritzo` appears in CR-08.
  - Adjacent wellness/food brands include `Himalaya Babycare` (CR-15), `Cadbury` (CR-17), `Bournvita` (CR-19), `Troovy` (CR-04), `Little Tummys` (CR-04).
- **Ad Label Vocabulary**:
  - `hook_type` (10 values): `problem_statement` (25), `story_open` (19), `educational_explainer` (15), `visual_action` (12), `question` (11), `personal_testimony` (6), `direct_product` (4), `pattern_interrupt` (3), `bold_claim` (2), `result_reveal` (1).
  - `ad_format` (7 values): `voiceover_montage` (46), `skit` (19), `explainer_to_camera` (18), `child_led` (7), `other` (5), `silent_brand_film` (2), `podcast_interview` (1).
  - `language` (8 values): `English` (37), `Hinglish` (35), `Hindi` (19), `Malayalam` (3), `Tamil` (2), `Kannada` (2), `Punjabi` (1), `no speech` (1).
  - `child_on_screen` (3 values): `one` (62), `none` (22), `multiple` (16).
- **Post Label Vocabulary**:
  - `content_form` (11 values): `piece_to_camera` (137), `voiceover_montage` (82), `still_or_carousel` (39), `music_edit` (37), `skit` (30), `demo_or_haul` (27), `event_footage` (17), `interview` (14), `reaction` (7), `news_package` (1), `other` (1).
  - `children_on_camera` (2 values): `no` (250), `yes` (142).
  - `language` (13 values): `Hindi` (155), `English` (100), `Hindi/English (Hinglish)` (44), `Telugu` (30), `Hindi and English` (18), `Gujarati` (17), `English and Hindi` (9), `none` (8), `Hindi/English` (4), `English and Gujarati` (3), `Telugu/Hindi` (2), `English and Telugu` (1), `telugu` (1).

---

## 4. Label Spot-Check Sample (`audit_labels_sample.csv`)

A fixed random sample of 12 ads was drawn (`seed: 42`) by `src/lj/labels_check.py` to audit Galvor's AI labels:

| Ad ID | AI Language | AI Hook Type | AI Child on Screen | AI Creator Type | AI Ad Format | Opening Hook Snippet |
|---|---|---|---|---|---|---|
| **LJ-001** | English | *NaN (missing)* | one | parent_or_caregiver | *NaN (missing)* | "This is what a real day looks like in my postpartum weight loss journey..." |
| **LJ-011** | English | educational_explainer | one | none_visible | voiceover_montage | "3 hidden jobs magnesium does in your child's body" |
| **LJ-019** | no speech | problem_statement | one | none_visible | silent_brand_film | "ಮಕ್ಕಳಲ್ಲಿ ಕ್ಯಾಲ್ಸಿಯಂ ಕೊರತೆಯ 3 ಲಕ್ಷಣಗಳು" (Kannada on-screen text) |
| **LJ-023** | Hinglish | question | one | parent_or_caregiver | explainer_to_camera | "Here's how I support my child's immunity before school..." |
| **LJ-031** | Hindi | visual_action | one | parent_or_caregiver | skit | "देखो मेरे पास क्या है! ओ माय गॉड, गमी!" |
| **LJ-040** | Hinglish | problem_statement | one | none_visible | voiceover_montage | "Agar aapke bache ka digestion poor hai..." |
| **LJ-045** | Kannada | story_open | one | parent_or_caregiver | voiceover_montage | "Breakfast ಮಾಡುವಾಗ help ಮಾಡ್ತಾಳೆ..." |
| **LJ-046** | Hinglish | story_open | multiple | parent_or_caregiver | voiceover_montage | "Is hafte na main ek bahut hi interesting book padh rahi thi..." |
| **LJ-054** | English | question | none | food_or_chef | voiceover_montage | "What if I say this beautiful looking slices of bread can be..." |
| **LJ-071** | Hindi | question | multiple | professional_presenter | other | "इनमें से एक पैनकेक में है 12 ग्राम एक्स्ट्रा प्रोटीन..." |
| **LJ-081** | Hinglish | story_open | one | child_presenter | child_led | "Har evening mein khud apna 3 ingredient protein shake banata hoon..." |
| **LJ-084** | Hinglish | question | none | multiple | explainer_to_camera | "Why is it so expensive in comparison?" |

### 4.1 Measured AI Label Error Rates (from `python -m lj.labels_check`)

All 12 sampled ads (60 individual labels) were spot-checked by reading transcripts and reviewing creative execution against the label taxonomy:

| Label Column | Evaluated | Errors Found | Error Rate | Agreement Rate | Primary Failure Mode Observed |
|---|---|---|---|---|---|
| **`hook_type`** | 12 | 2 | **16.67%** | 83.33% | Missing value on `LJ-001`; declarative statement mislabeled as question on `LJ-023`. |
| **`ad_format`** | 12 | 1 | **8.33%** | 91.67% | Missing value on `LJ-001` (montage day-in-the-life). |
| **`child_on_screen`** | 12 | 1 | **8.33%** | 91.67% | `LJ-046` pets ("poonch wale bacche") misclassified as multiple children. |
| **`language`** | 12 | 0 | **0.00%** | 100.00% | High fidelity across English, Hinglish, Hindi, and Kannada. |
| **`creator_type`** | 12 | 0 | **0.00%** | 100.00% | High fidelity distinguishing parents, chefs, presenters, and child hosts. |
| **OVERALL** | **60** | **4** | **6.67%** | **93.33%** | Overall 93.3% accuracy; hook_type is the most fragile feature. |

### 4.2 Key Qualitative Takeaways
1. **Hook Type Fragility**: `hook_type` has the highest error rate (16.67%). The AI classifier tends to classify any hook with punctuation nuances or rhetorical phrasing as `question`, and occasionally drops labels completely.
2. **Context Misinterpretation**: On `LJ-046`, the colloquial phrase *"poonch wale bacche"* (referring affectionately to pet dogs during a postpartum/recovery journey) caused the AI to erroneously tag `child_on_screen: multiple`.
3. **Pipeline Safeguard**: Because label error rate is non-zero (6.67% overall, 16.67% on hook_type), Phase 2 creative findings will not rely on narrow single-label slices, and Phase 4 confidence scoring will require multiple supporting findings before boosting creator fit scores.

---

## 5. Master Action Table for Pipeline (Phases 2 – 6)

| Target / Item | Pipeline Stage | Decision / Action | Primary Reason |
|---|---|---|---|
| **LJ-089** | Phase 2 (Ad Model) | **EXCLUDE** | Tracking fault (1,544 add-to-carts, 0 purchases, ₹4.26L spend); would bias creative conclusions. |
| **Spend < ₹10k (20 ads)** | Phase 2 (Ad Model) | **EXCLUDE from base set** | Extreme sample volatility and noise; tested under sensitivity variants (₹5k, ₹10k, ₹20k). |
| **LJ-004** | Phase 2 (Ad Model) | **KEEP but test both ways** | Represents 30.35% of revenue; findings must hold with and without LJ-004. |
| **Duplicate pairs** | Phase 2 (Ad Model) | **KEEP & Calibrate** | Used to establish minimum effect size threshold for statistical significance. |
| **CR-20** | Phase 4 (Gates) | **EXCLUDE** | Hard gate: past Little Joys partner brand & 70.1% male audience. |
| **CR-14** | Phase 4 (Gates) | **EXCLUDE** | Hard gate: 35.6% audience outside India (India share 64.4% < 80.0% threshold) & Facebook platform. |
| **CR-05** | Phase 4 (Gates) | **KEEP with soft flag** | Child performer risk; requires compliance sign-off; penalized in commercial risk. |
| **CR-17** | Phase 4 (Gates) | **KEEP with soft flag** | 100% sponsored saturation & 30% hidden likes; penalized in commercial risk. |
| **CR-09** | Phase 4 (Gates) | **KEEP with soft flag** | Inactivity flag (48 days) & 80% sponsored posts; penalized in commercial risk. |
| **Audience unknown (17 creators)** | Phase 4 (Scoring) | **KEEP as inferred** | Neutral audience score (0.50); confidence score reduced; labelled "inferred". |
| **Hidden likes (CR-02, CR-09, CR-17)** | Phase 3 (Features) | **ADJUST basis** | Compute engagement on comments + reshares; discount engagement quality score. |

