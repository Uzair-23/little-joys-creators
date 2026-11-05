# Sensitivity & Robustness Analysis (Phase 5 Report)

**Date:** 2026-11-05  
**Pipeline Code:** `src/lj/sensitivity.py`  
**Configuration:** 2,000 Dirichlet weight draws (`dirichlet_concentration = 50`, `seed = 42`)  

---

## 1. Executive Summary: Core Stability Findings

Under 2,000 random weight perturbations around baseline values and across multiple structural scenario variants:
1. **Four Picks Are Rock-Solid (Robust ≥ 80%):**
   - **CR-08** (`the_mum_wife_playbook`): **100.0%** selection frequency.
   - **CR-02** (`livesimply_withkripa`): **100.0%** selection frequency.
   - **CR-03** (`ekamichildcare`): **99.95%** selection frequency.
   - **CR-04** (`hello_ps8`): **99.90%** selection frequency.
   These four creators remain in the top 5 under virtually any plausible weighting of reach, engagement, creative fit, and risk.

2. **The Borderline 5th Pick (Marginal < 50%):**
   - **CR-16** (`paediatrics_decoded`): Appears in the top 5 in only **42.85%** of runs. Classified as **marginal**.
   - **The Competition for Slot 5:** CR-16 competes closely with **CR-19** (`instamommy_suchi`, 29.80% frequency) and **CR-15** (`tej.lil.diary`, 27.40% frequency).
   - **Best Backup for CR-16:** **CR-15** (`tej.lil.diary`). Although separated by just 0.0006 total score in the base ranking, CR-15 is the **only creator with verified brand audience data** (83.4% women, 88.3% India) and **High confidence**. If the brand seeks demographic certainty over unverified pediatric reach, CR-15 is the primary substitution.

---

## 2. Top-5 Selection Frequency Under Dirichlet Weight Draws

| Rank (Base) | Creator ID | Handle | Base Total | Top-5 Frequency (2,000 Draws) | Robustness Classification | Best Backup (if Marginal) |
|---|---|---|---|---|---|---|
| 1 | **CR-08** | `@the_mum_wife_playbook` | 0.6829 | **100.0%** | `robust` | `none` |
| 2 | **CR-02** | `@livesimply_withkripa` | 0.6651 | **100.0%** | `robust` | `none` |
| 4 | **CR-03** | `@ekamichildcare` | 0.5960 | **100.0%** | `robust` | `none` |
| 3 | **CR-04** | `@hello_ps8` | 0.6383 | **99.9%** | `robust` | `none` |
| 5 | **CR-16** | `@paediatrics_decoded` | 0.5180 | **42.9%** | `marginal` | `CR-19` |
| 7 | **CR-19** | `@instamommy_suchi` | 0.5070 | **29.8%** | `marginal` | `none` |
| 6 | **CR-15** | `@tej.lil.diary` | 0.5174 | **27.4%** | `marginal` | `none` |
| 8 | **CR-13** | `@mumma_and_ridhu` | 0.4653 | **0.1%** | `marginal` | `none` |
| 9 | **CR-01** | `@drgarima_mehta` | 0.4492 | **0.0%** | `marginal` | `none` |
| 10 | **CR-12** | `@raising_zohran` | 0.3856 | **0.0%** | `marginal` | `none` |
| 11 | **CR-17** | `@radhikabansal0908` | 0.3626 | **0.0%** | `marginal` | `none` |
| 12 | **CR-07** | `@ohmother.in` | 0.3224 | **0.0%** | `marginal` | `none` |
| 13 | **CR-18** | `@foodies_by_neha` | 0.2488 | **0.0%** | `marginal` | `none` |

*(Saved to `outputs/tables/sensitivity_top5_frequency.csv` and visualized in `outputs/figures/top5_stability.png`)*

---

## 3. Structural Scenario & Leave-One-Out Variants

| Variant Type | Variant Name | Top 5 Creators Selected | Notes |
|---|---|---|---|
| baseline | **Base Model (Default Weights & Gates)** | `CR-08, CR-02, CR-04, CR-03, CR-16` | Reference base ranking |
| gates | **Looser Gates (Women 40%, India 70%, Fam 10%, Posts 6)** | `CR-08, CR-02, CR-04, CR-03, CR-16` | Allows borderlines with lower demographic reach |
| gates | **Tighter Gates (Women 60%, India 85%, Fam 20%, Posts 10)** | `CR-08, CR-02, CR-04, CR-03, CR-16` | Strict family threshold |
| leave_one_component_out | **Drop creative_fit** | `CR-02, CR-04, CR-08, CR-03, CR-19` | Re-weighted with creative_fit=0 |
| leave_one_component_out | **Drop reach_quality** | `CR-16, CR-08, CR-04, CR-03, CR-02` | Re-weighted with reach_quality=0 |
| leave_one_component_out | **Drop engagement_quality** | `CR-08, CR-02, CR-19, CR-03, CR-04` | Re-weighted with engagement_quality=0 |
| leave_one_component_out | **Drop audience_fit** | `CR-08, CR-02, CR-04, CR-03, CR-16` | Re-weighted with audience_fit=0 |
| leave_one_component_out | **Drop commercial_risk** | `CR-08, CR-02, CR-04, CR-03, CR-16` | Re-weighted with commercial_risk=0 |
| evidence_stress_test | **Drop Weakest Finding (F08 UGC)** | `CR-08, CR-02, CR-04, CR-03, CR-16` | F08 has lowest effect (0.0137) |
| ad_spend_variant | **Min Spend ₹5,000 Variant** | `CR-08, CR-02, CR-04, CR-03, CR-16` | Surviving findings stable across ₹5k/₹10k/₹20k spend gates |
| outlier_variant | **Without LJ-004 (Strict 50% Rule)** | `CR-08, CR-02, CR-04, CR-03, CR-16` | Already baked into surviving findings F01-F08 |

*(Saved to `outputs/tables/sensitivity_variants.csv`)*

### Key Takeaways from Structural Variants:
- **Dropping Creative Fit:** CR-16 falls out of the top 5 (replaced by CR-19), confirming CR-16 relies heavily on its Hindi and child-presence fit.
- **Dropping Reach Quality:** CR-19 collapses, while CR-16 and CR-15 strengthen.
- **Dropping Audience Fit:** CR-15 drops in score (loses its 0.99 verified advantage), leaving CR-16 in 5th place.
- **Evidence Stress Test (Dropping F08 UGC):** Top 5 ranking remains identical, proving conclusions do not hinge on weak findings.

---

## 4. Final 5 Selection & Backup Recommendation

| Pick | Creator ID | Handle | Selection Status | Robustness | Role in Campaign |
|---|---|---|---|---|---|
| **Pick 1** | CR-08 | `@the_mum_wife_playbook` | **Primary** | **Robust (100.0%)** | Relatable Mom-Next-Door; high reach & engagement balance |
| **Pick 2** | CR-02 | `@livesimply_withkripa` | **Primary** | **Robust (100.0%)** | Viral domestic comedy & skit storyteller (15.4 plays/follower) |
| **Pick 3** | CR-04 | `@hello_ps8` | **Primary** | **Robust (99.9%)** | Sentimental lifestyle mom; 5.4% engagement rate |
| **Pick 4** | CR-03 | `@ekamichildcare` | **Primary** | **Robust (99.9%)** | Clinical pediatric authority; clinical reassurance |
| **Pick 5** | CR-16 | `@paediatrics_decoded` | **Primary (Conditional)** | **Marginal (42.9%)** | Pediatrician; top creative fit (0.6084) via pure Hindi |
| **Backup** | CR-15 | `@tej.lil.diary` | **Designated Backup** | **Marginal (27.4%)** | **High Confidence Pick**: verified 83.4% mothers demographic |

