# Little Joys: Creator Selection Pipeline & Campaign Allocation

## The Question & The Answer

**The Question:** Which 5 creators should Little Joys recruit for its kids' nutrition and milk mix powder campaign, based strictly on empirical ad performance and creator audience fit?

**The Answer:**
1. **CR-08 (`@the_mum_wife_playbook`)** &mdash; *Rank #1, Score 0.6829, Robust (100.0%)*: Relatable Mom-Next-Door; top balanced reach (0.6186) and engagement (0.9412) addressing breakfast picky-eating.
2. **CR-02 (`@livesimply_withkripa`)** &mdash; *Rank #2, Score 0.6651, Robust (100.0%)*: Domestic comedic storyteller; viral reach (1.0000) for morning commotion skits.
3. **CR-04 (`@hello_ps8`)** &mdash; *Rank #3, Score 0.6383, Robust (99.9%)*: Sentimental lifestyle mom; category-leading engagement (1.0000) for active morning routines.
4. **CR-03 (`@ekamichildcare`)** &mdash; *Rank #4, Score 0.5960, Robust (99.95%)*: Pediatric clinical authority; trusted doctor guidance on child protein intake gaps.
5. **CR-16 (`@paediatrics_decoded`)** &mdash; *Rank #5, Score 0.5180, Marginal (42.85%)*: Dedicated pediatrician; highest creative fit (0.6084) via pure Hindi nutrition explainers.  
*Primary Empirical Backup:* **CR-15 (`@tej.lil.diary`)** &mdash; *Rank #6, Score 0.5174, High Confidence*: Only creator with verified audience data (83.4% women, 88.3% India).

---

## Repository Map

```text
little-joys-creators/
├── config.yaml                     # Pipeline configuration (weights, thresholds, seed: 42)
├── label_map.yaml                  # Creator post tags mapped to surviving ad findings
├── pyproject.toml / requirements.txt# Python dependencies & packaging
├── README.md                       # Master project overview & reproduction guide
├── implementation_plan.md          # 9-phase architectural blueprint & specifications
├── PRD.md                          # Product requirements document
│
├── data/
│   ├── raw/                        # Ground-truth source data (ads, creators, creator_posts, audience)
│   └── processed/                  # Computed creator feature matrix (creator_features.csv)
│
├── src/lj/                         # Modular reproducible Python engine
│   ├── load.py                     # Data ingestion with strict schema casting
│   ├── audit.py                    # Phase 1 data audit & anomaly diagnostics
│   ├── labels_check.py             # Phase 1 AI label spot-check error measurement
│   ├── metrics.py                  # Core performance metrics computation
│   ├── stats.py                    # Bootstrap confidence intervals & hypothesis testing
│   ├── ad_model.py                 # Phase 2 creative regression & 50% LJ-004 test
│   ├── creator_features.py         # Phase 3 creator feature engineering & medians
│   ├── gates.py                    # Phase 4 hard qualification gates
│   ├── scoring.py                  # Phase 4 multi-attribute scoring & ranking
│   ├── sensitivity.py              # Phase 5 Dirichlet weight perturbation & scenario models
│   ├── claims.py                   # Phase 6 empirical claims extraction & compliance flags
│   ├── briefs.py                   # Phase 6 9-part creator brief rendering engine
│   ├── report.py                   # Phase 7 HTML & Markdown executive report generator
│   └── run_all.py                  # Phase 8 master orchestrator (all 11 stages)
│
├── outputs/
│   ├── tables/                     # 27 generated analytical tables (.csv)
│   ├── figures/                    # Visualization plots (.png)
│   ├── briefs/                     # 5 finalized creator briefs (CR-02, 03, 04, 08, 16)
│   ├── report.html                 # Executive marketing manager interactive HTML report
│   └── report.md                   # Complete 8-part strategy report in Markdown
│
├── docs/                           # Analytical documentation & decision logs
│   ├── data_audit.md               # Phase 1 audit diagnostics & platform noise floor
│   ├── ad_findings.md              # Phase 2 surviving creative findings & LJ-004 unmasking
│   ├── creator_profiles.md         # Phase 3 structured creator profiles
│   ├── selection_logic.md          # Phase 4 qualification gates & scoring scheme
│   ├── robustness.md               # Phase 5 sensitivity analysis & backup strategy
│   ├── claims_whitelist.md         # Phase 6 claims whitelist & ASCI/FSSAI review
│   └── ai_usage/                   # AI steering logs, prompts, and corrections
│       ├── prompt_log.md           # Prompt history per phase
│       └── corrections.md          # AI correction log & human overrules
│
└── tests/                          # 47 comprehensive unit & reproducibility tests
```

---

## Setup From Scratch

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/uzair-sayeed/little-joys-creators.git
cd little-joys-creators

# Create and activate a fresh virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies and local package in editable mode
pip install -r requirements.txt
pip install -e .
```

### 2. Verify Installation
```bash
pytest -q
```

---

## How to Reproduce All Results

To run the full end-to-end pipeline from raw data to finished HTML report:

```bash
python -m lj.run_all
```

This runs all 11 stages sequentially, writing 27 tables in `outputs/tables/`, 3 figures in `outputs/figures/`, 5 briefs in `outputs/briefs/`, and `outputs/report.html`:
```text
======================================================================
       LITTLE JOYS CREATOR SELECTION: FULL REPRODUCIBLE PIPELINE
======================================================================
[01/11] audit              ... completed (10 audit tables generated in outputs/tables/)
[02/11] labels_check       ... completed (verified existing 12-ad spot-check sample)
[03/11] metrics            ... completed (computed performance metrics for 100 ads)
[04/11] ad_model           ... completed (8 surviving creative findings under 50% LJ-004 rule)
[05/11] creator_features   ... completed (computed features for 20 creators in data/processed/)
[06/11] gates              ... completed (13/20 creators passed hard qualification gates)
[07/11] scoring            ... completed (scored and ranked 13 passing creators across 5 components)
[08/11] sensitivity        ... completed (2,000 Dirichlet draws; 4 robust picks identified)
[09/11] claims             ... completed (353 claims extracted from brand ads and whitelisted)
[10/11] briefs             ... completed (5 creator briefs rendered in outputs/briefs/)
[11/11] report             ... completed (rendered report.md and report.html from outputs/tables/ only)
======================================================================
SUCCESS: All 11 stages executed cleanly.
======================================================================
```

To run the complete test suite including bit-for-bit reproducibility:
```bash
pytest -q
```

---

## Method Summary

* **Phase 0 & 1 &mdash; Ingestion, Audit & Noise Floor ([docs/data_audit.md](docs/data_audit.md)):**  
  Ingested 100 ads, 20 creators, 303 posts, and 3 audience exports with strict typing. Unmasked data traps: ad `LJ-089` possessed inverted dates (-1 days live), and duplicate creative pairs (`LJ-003/059`, `LJ-036/056`, `LJ-073/093`) established an empirical platform noise baseline (median ROAS difference: 0.4915x, CVR difference: 0.0046). Evaluated AI label error rates (16.7% on hooks, 8.3% on formats).

* **Phase 2 &mdash; Creative Findings & The LJ-004 Test ([docs/ad_findings.md](docs/ad_findings.md)):**  
  Tested 59 candidate patterns across Hook Rate, Hold Rate, and ROAS. Enforced the strict 50% LJ-004 retention rule: ad `LJ-004` (₹32.99L revenue, 5.00x ROAS) created severe outlier distortions. Out of 59 patterns, only 8 survived (2 Supported, 6 Directional). Discovered the critical Hindi attention-vs-sales split (+0.1049 hook lift, but lower bottom-funnel ROAS) and child-in-opening frame lift (+0.0809).

* **Phase 3 &mdash; Creator Feature Engineering ([docs/creator_profiles.md](docs/creator_profiles.md)):**  
  Calculated robust median engagement, sponsored delivery discounts, and brand exposure across 20 creators without silent NaNs. Built `label_map.yaml` explicitly mapping creator content traits to surviving empirical ad findings.

* **Phase 4 &mdash; Qualification Gates & Scoring ([docs/selection_logic.md](docs/selection_logic.md)):**  
  Implemented 5 hard qualification gates, disqualifying 7 creators for competitor conflicts (`Gritzo`), existing brand partnerships (`CR-20`, `CR-09`), demographic mismatch (`CR-14`), or lack of family content (`CR-06`). Scored 13 passing creators across 5 weighted dimensions: Creative Fit (30%), Reach (25%), Engagement (20%), Audience (15%), and Risk (10%).

* **Phase 5 &mdash; Sensitivity & Robustness ([docs/robustness.md](docs/robustness.md)):**  
  Conducted 2,000 Dirichlet weight draws and scenario stress tests (`top5_stability.png`). Confirmed Picks 1 to 4 are rock-solid (Robust &ge; 99.9%). Classified CR-16 as marginal (42.85%) due to reach sensitivity, and designated CR-15 as the primary High Confidence replacement (83.4% verified mothers audience).

* **Phase 6 &mdash; Empirical Claims Whitelist & Briefs ([docs/claims_whitelist.md](docs/claims_whitelist.md)):**  
  Extracted 353 unique claims from brand ads, calculating spend-weighted ROAS and flagging regulated health outcomes. Rendered 5 bespoke 9-part briefs in `outputs/briefs/` tying every angle, hook, and format to real ad IDs and creator post URLs with zero unwhitelisted health claims.

* **Phase 7 &mdash; Marketing Leadership Report ([outputs/report.html](outputs/report.html)):**  
  Rendered interactive HTML and Markdown executive reports strictly from data tables. Answer-first 8-part structure featuring embedded sensitivity charts, forest plots, qualification audits, and actionable contracting checklists.

* **Phase 8 &mdash; Master Pipeline & Reproducibility:**  
  Built `src/lj/run_all.py` providing single-command execution and `tests/test_reproducibility.py` enforcing exact bit-for-bit table reproducibility across consecutive runs.

---

## Known Limitations

1. **No Commercial Rate Card or Cost Data:** The dataset contains zero creator pricing information. The pipeline optimizes creative fit and reach efficiency, but cannot model Customer Acquisition Cost (CAC) without creator rate quotes.
2. **Inferred Audience Demographics for 17 Creators:** Demographics are empirically verified for only 3 accounts (CR-14, CR-15, CR-20). The remaining 17 creators rely on neutral baseline scoring; candidate screenshots must be verified before contract signing.
3. **Observational Associations:** Findings reflect observational lifts in historical Meta ad campaigns, not guaranteed causal increments.
4. **AI-Generated Label Noise:** AI tagging demonstrated a 16.7% error rate on hook classifications during manual spot-checks.
5. **Sponsored Delivery Discount:** Creator sponsored posts average lower delivery than viral organic posts, which is accounted for via our sponsored reach discount adjustment.

---

## AI Tool Use & Governance

In compliance with project standards, complete steering logs, prompt histories, and human-in-the-loop overrides are documented in:
* **[docs/ai_usage/prompt_log.md](docs/ai_usage/prompt_log.md):** Chronological prompt logs across all phases.
* **[docs/ai_usage/corrections.md](docs/ai_usage/corrections.md):** Detailed log of AI failure points, hallucination catches, and methodological overrules (e.g. enforcing the strict 50% LJ-004 test).

