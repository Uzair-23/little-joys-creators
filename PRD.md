# PRD: Little Joys Creator Selection

| | |
|---|---|
| **Project** | Little Joys creator selection (galvor.ai tech intern take-home) |
| **Author** | Uzair |
| **Status** | Ready to implement |
| **Time budget** | 2 days, about 10 to 12 hours of real work |
| **Companion docs** | `implementation_plan.md` (phase-wise steps and prompts), `AGENTS.md` (agent rules) |

---

## 1. Summary

Little Joys, an Indian kids' nutrition brand, has 100 ads with performance data and 20 candidate creators with feed data. It wants to know **which 5 creators to work with next and what each should say**, using only its own data.

This project delivers:
1. A **reproducible analysis pipeline** (Python) that audits the data, finds what works in the brand's own ads, profiles and scores creators, stress-tests the ranking, and writes creator briefs.
2. A **report for the marketing manager** that gives the answer first and states its limits plainly.
3. A **public GitHub repo** with README, tests, and AI-use evidence, plus a one-page note.

The product principle is **trust over polish**: a plain answer with sound, checkable reasoning beats a polished one the brand cannot rely on.

---

## 2. Problem and context

### 2.1 Business question
> Which 5 of these 20 creators should we work with next, and what should each of them say? The answer must come from the brand's own data, not general opinion.

### 2.2 What makes this hard (known data traps)

| # | Trap | Consequence if ignored |
|---|---|---|
| T1 | LJ-004: about ₹6.6L spend, about 5.0x ROAS, about 30% of all revenue | Every "what works" finding is really "what LJ-004 did" |
| T2 | LJ-089: about ₹4.3L spend, 1,544 add-to-carts, zero purchases | Probably a tracking fault; would wrongly condemn its creative style |
| T3 | Tiny-spend ads with extreme ROAS or CVR (for example LJ-072: about ₹4k spend, about 3.0x ROAS) | Luck is read as skill |
| T4 | Duplicate creatives (LJ-003/059, LJ-036/056, LJ-073/093) with different results | Double counting; but also a free measure of noise |
| T5 | CR-20 already worked with Little Joys; audience skews about 70% male | Picking a creator who is not "next" and not a fit |
| T6 | CR-14: audience data from Facebook, about 35% outside India, about 0.27 plays per follower | Followers overstate reach |
| T7 | CR-05: child performer account with about 2.8M followers | Compliance and child-safety exposure |
| T8 | CR-17: 20 of 20 posts sponsored, low engagement, many hidden likes | Possible ad farm; weak trust |
| T9 | Sponsored posts get roughly half the plays of organic | Overstated reach forecasts |
| T10 | Audience data exists for only 3 of 20 creators | Audience fit mostly inferred |
| T11 | Competing or adjacent brands in `brands_visible` | Conflicts and weak differentiation |
| T12 | All labels are AI-made; a few are missing | Findings built on wrong labels |
| T13 | Only 100 ads and about 35 labels | Chance patterns; need interval estimates and multiple-comparison control |
| T14 | Ads launched at different times and ran different lengths | Totals are not comparable; use rates |
| T15 | Hidden like counts appear as 0 or very low | False "low engagement" |
| T16 | No creator costs or rate cards | Cost-efficiency cannot be claimed |

All traps must be **confirmed or refuted in code** in Phase 1 and recorded in `docs/data_audit.md`.

---

## 3. Goals and non-goals

### 3.1 Goals
- **G1.** Recommend exactly 5 creators (plus a backup for each marginal pick), each with a reason traceable to the data.
- **G2.** For each pick, provide a concrete brief (angle, format, language, hook lines, beats, proof, do/don't, risks).
- **G3.** Quantify uncertainty everywhere (intervals, confidence labels, robust/likely/marginal).
- **G4.** Make the whole result reproducible with one command from a fresh clone.
- **G5.** Make the reasoning auditable by a non-technical reader.
- **G6.** Show responsible use of AI tools (rules file, prompts, corrections).

### 3.2 Non-goals
- No web app or dashboard as the primary deliverable (an optional Streamlit page is a stretch item only).
- No machine-learning model that "predicts sales"; the data (100 ads) cannot support it.
- No creator cost, ROI or budget model (no rate cards in the data).
- No scraping of Instagram or any outside data. Only `data/raw/` plus the ad videos if downloaded for label checks.
- No legal or compliance rulings. Compliance items are flagged for human review.
- No modification of the raw data.

---

## 4. Users and use cases

| User | Need | How this product serves them |
|---|---|---|
| **Marketing manager at Little Joys** (primary) | Decide whom to approach and what to ask them to say; be able to defend the decision | A short report, answer first, with plain-language reasoning, confidence and risks |
| **Brand's analyst / growth lead** (secondary) | Check the work and reuse it | Repo with tests, tables, config and a one-command rerun |
| **galvor.ai reviewers** (evaluators) | Judge product thinking, AI-tool use and trustworthiness | README, note, audit, robustness, AI logs, corrections log |

### Key user stories
1. As the manager, I want the 5 creators and one-line reasons on the first screen, so I can act today.
2. As the manager, I want to know which picks are solid and which are marginal, so I know where to double check.
3. As the manager, I want a brief per creator in their own voice and language, so outreach is concrete.
4. As the manager, I want to know why other attractive creators (large followings) were excluded.
5. As the analyst, I want to change a threshold or weight in one file and re-run everything.
6. As a reviewer, I want to trace any number in the report back to a table and a script.

---

## 5. Scope of the deliverables

| ID | Deliverable | Format | Location |
|---|---|---|---|
| D1 | Answer for the marketing manager | HTML and Markdown | `outputs/report.html`, `outputs/report.md` |
| D2 | Creator briefs (5) | Markdown | `outputs/briefs/<creator_id>.md` |
| D3 | Pipeline code with tests | Python package | `src/lj/`, `tests/` |
| D4 | Public GitHub repo with README | Repo | repo root |
| D5 | One-page note (key choices, what next) | Markdown | `docs/note.md` |
| D6 | AI tool use evidence | Markdown + artifacts | `AGENTS.md`, `docs/ai_usage/` |
| D7 | Optional 3-minute screen recording | Video link | referenced in README and email |
| D8 | Audit, findings, selection and robustness docs | Markdown | `docs/` |

---

## 6. Complete folder structure

```text
little-joys-creators/
├── AGENTS.md                         # rules for AI agents (repo root so tools find it)
├── PRD.md                            # this document
├── implementation_plan.md            # phase-wise plan and prompts
├── README.md                         # question, answer, setup, reproduce, limits
├── pyproject.toml                    # makes `lj` importable (pip install -e .)
├── requirements.txt                  # direct dependencies
├── requirements.lock.txt             # pip freeze output
├── config.yaml                       # seed, thresholds, weights, brand dictionary, paths
├── label_map.yaml                    # maps ad-label values to post-label values (see 8.3)
├── .gitignore
│
├── data/
│   ├── raw/                          # READ-ONLY. Never modify.
│   │   ├── ads.csv
│   │   ├── creators.csv
│   │   ├── creator_posts.csv
│   │   ├── creator_audience.csv
│   │   └── DATA_README.md            # renamed copy of the provided README
│   └── processed/                    # derived data written by the pipeline
│       ├── ads_clean.csv
│       ├── ads_analysis_set.csv
│       ├── posts_clean.csv
│       └── creator_features.csv
│
├── src/
│   └── lj/
│       ├── __init__.py
│       ├── config.py                 # loads config.yaml, label_map.yaml; paths; SEED
│       ├── load.py                   # typed loading of the four CSVs
│       ├── audit.py                  # Phase 1: data audit and flags
│       ├── labels_check.py           # Phase 1: label spot-check sample and error-rate tally
│       ├── metrics.py                # Phase 2: per-ad funnel metrics
│       ├── stats.py                  # shared: spend-weighted aggregation, bootstrap, BH correction
│       ├── ad_model.py               # Phase 2: what works; findings and "could not conclude"
│       ├── creator_features.py       # Phase 3: one row per creator
│       ├── gates.py                  # Phase 4: hard gates and soft flags
│       ├── scoring.py                # Phase 4: components, total, rank, confidence
│       ├── sensitivity.py            # Phase 5: robustness analysis
│       ├── claims.py                 # Phase 6: claims whitelist builder
│       ├── briefs.py                 # Phase 6: brief generation and validation
│       ├── report.py                 # Phase 7: render report from tables only
│       ├── run_all.py                # Phase 8: orchestrates every stage
│       └── templates/
│           ├── report.html.j2
│           ├── report.md.j2
│           └── brief.md.j2
│
├── tests/
│   ├── conftest.py                   # tiny synthetic fixtures
│   ├── test_load.py
│   ├── test_audit.py
│   ├── test_stats.py
│   ├── test_metrics.py
│   ├── test_ad_model.py
│   ├── test_creator_features.py
│   ├── test_gates.py
│   ├── test_scoring.py
│   ├── test_sensitivity.py
│   ├── test_claims.py
│   ├── test_briefs.py
│   ├── test_report.py                # every number in report exists in outputs/tables
│   └── test_reproducibility.py       # two runs, same seed, identical outputs
│
├── outputs/
│   ├── tables/                       # every number in the report comes from here
│   │   ├── audit_missing_values.csv
│   │   ├── audit_duplicates.csv
│   │   ├── audit_funnel_violations.csv
│   │   ├── audit_concentration.csv
│   │   ├── audit_spend_flags.csv
│   │   ├── audit_creator_data_quality.csv
│   │   ├── audit_labels_sample.csv
│   │   ├── ad_metrics.csv
│   │   ├── ad_noise_from_duplicates.csv
│   │   ├── ad_group_metrics.csv
│   │   ├── ad_findings.csv
│   │   ├── ad_not_concluded.csv
│   │   ├── creator_ranking.csv
│   │   ├── gate_results.csv
│   │   ├── sensitivity_top5_frequency.csv
│   │   ├── sensitivity_variants.csv
│   │   └── claims_whitelist.csv
│   ├── figures/
│   │   ├── ad_findings_forest.png
│   │   ├── funnel_by_pattern.png
│   │   ├── creator_reach_vs_followers.png
│   │   ├── score_components_top8.png
│   │   └── top5_stability.png
│   ├── briefs/
│   │   └── <creator_id>.md           # five files, one per pick
│   ├── videos/                       # git-ignored; optional downloaded ad videos
│   ├── report.html
│   └── report.md
│
├── docs/
│   ├── data_audit.md                 # Phase 1
│   ├── ad_findings.md                # Phase 2 (pre-registered feature list first)
│   ├── creator_profiles.md           # Phase 3
│   ├── selection_logic.md            # Phase 4
│   ├── robustness.md                 # Phase 5
│   ├── claims_whitelist.md           # Phase 6
│   ├── decision_log.md               # dated list of key decisions and why
│   ├── open_questions.md             # questions for galvor.ai, answers received
│   ├── note.md                       # D5: one-page note
│   └── ai_usage/
│       ├── prompt_log.md
│       ├── corrections.md            # times the AI was wrong and how it was caught
│       └── session_artifacts/        # exported plans, task lists, walkthroughs
│
└── notebooks/                        # exploration only, never required to reproduce results
    └── 00_exploration.ipynb
```

---

## 7. Setup and environment (summary)

Full commands are in `implementation_plan.md` Phase 0. Requirements:

- Python 3.11+, Git, a public GitHub repo.
- Virtual environment in `.venv/` (git-ignored); `pip install -r requirements.txt`; `pip install -e .`.
- Google Antigravity as the main IDE and agent, with command execution set to review before running.

`requirements.txt`:

```text
pandas>=2.2
numpy>=1.26
scipy>=1.12
statsmodels>=0.14
scikit-learn>=1.4
matplotlib>=3.8
plotly>=5.20
pyyaml>=6.0
jinja2>=3.1
markdown>=3.5
pytest>=8.0
jupyterlab>=4.0
```

---

## 8. Functional requirements

### 8.1 Configuration (`config.yaml`)

Every threshold, weight and dictionary lives here, never inside functions.

```yaml
seed: 42
data_as_of: "2026-10-26"

paths:
  raw: data/raw
  processed: data/processed
  tables: outputs/tables
  figures: outputs/figures
  briefs: outputs/briefs

ads:
  min_spend_inr: 10000
  min_spend_variants: [5000, 10000, 20000]
  outlier_ads: ["LJ-004"]
  suspected_tracking_fault: ["LJ-089"]     # excluded from performance conclusions
  zero_purchase_spend_flag_inr: 100000     # flag ads above this spend with zero purchases
  min_group_size: 8
  bootstrap_iterations: 5000
  ci_level: 0.95
  features_to_test:                        # PRE-REGISTERED before looking at results
    - language
    - hook_type
    - hook_driver
    - ad_format
    - child_on_screen
    - child_in_first_3s
    - brand_first_said
    - main_benefit
    - production
    - product_form
  consistency_metric_pairs:                # a finding needs same direction on >= 2 of these
    - [roas, cvr]
    - [hook_rate, hold_rate]

creators:
  min_posts_for_confidence: 12
  min_posts_per_group_for_ratio: 3         # organic and sponsored each
  hidden_likes_threshold: 5                # likes <= this counted as hidden
  hidden_likes_share_flag: 0.25
  sponsored_share_flag: 0.70
  inactive_days_flag: 45
  reach_cap_percentile: 0.95

gates:
  already_partner_brand: "Little Joys"
  min_women_share_known: 0.50              # only applied where audience is known
  min_india_share_known: 0.80
  min_child_family_share: 0.15             # share of posts with kids on camera or family/food topics
  min_posts: 8

brand_categories:                          # explicit; unknown brands are listed, not guessed
  competitor_kids_nutrition: ["Gritzo"]    # extend after inspecting brands_visible
  adjacent_food_snacks: ["Cadbury", "Chupa Chups"]
  adjacent_wellness: ["Himalaya"]
  # add others after Phase 1 audit lists every brand seen

scoring:
  weights:
    creative_fit: 0.30
    reach_quality: 0.25
    engagement_quality: 0.20
    audience_fit: 0.15
    commercial_risk: 0.10
  unknown_audience_score: 0.50             # neutral; confidence is lowered separately
  top_n: 5

sensitivity:
  draws: 2000
  dirichlet_concentration: 50
  robust_threshold: 0.80
  likely_threshold: 0.50
```

### 8.2 Module specifications

#### `load.py`
| Function | Input | Output | Requirements |
|---|---|---|---|
| `load_ads()` | `data/raw/ads.csv` | DataFrame | Dates parsed; numeric dtypes; list-columns split on `"; "` into Python lists |
| `load_creators()` | `creators.csv` | DataFrame | Same |
| `load_posts()` | `creator_posts.csv` | DataFrame | `posted_on` parsed; `is_sponsored` normalised to boolean |
| `load_audience()` | `creator_audience.csv` | DataFrame | Keep as provided; normalise the platform and brand lists |

Raw files are never written to.

#### `audit.py`
Produces the tables in `outputs/tables/audit_*.csv` and returns a summary dict. Checks:

1. Missing values per column (ads, creators, posts).
2. Duplicate `transcript` and `hook_line` across ads, with each pair's spend, ROAS and launch date.
3. Impossible funnel values: purchases > add-to-carts, clicks > impressions, ThruPlays > 3-second views, add-to-carts > clicks.
4. `days_live` vs dates recomputed against `data_as_of`.
5. Concentration: share of total spend and revenue by the top 1, 3, 5, 10 ads.
6. Spend flags: ads with spend above `zero_purchase_spend_flag_inr` and zero purchases; ads below `min_spend_inr`.
7. Creator data quality: posts per creator, posts dated after `data_as_of`, share of hidden likes, sponsored share, transcripts available.
8. Every distinct value of `brands_visible` per creator, and which are not yet in `brand_categories`.
9. Audience file: creators covered, platform, share outside India, gender split, past brands (including Little Joys).

Each finding gets an `action` (exclude / flag / keep) in `docs/data_audit.md`.

#### `labels_check.py`
- Draw a **fixed random sample of 10 to 15 ads** (seed from config).
- Output `audit_labels_sample.csv` with transcript, `hook_line` and the labels to verify (`hook_type`, `language`, `child_on_screen`, `creator_type`, `ad_format`) and empty columns `human_label`, `agree` for the user to fill.
- A helper reads the filled file and reports the **label error rate** per column, which `docs/data_audit.md` and the report quote.

#### `stats.py` (shared, unit-tested)
| Function | Behaviour |
|---|---|
| `weighted_ratio(df, num, den)` | `sum(num) / sum(den)` for a group (never an average of ratios) |
| `bootstrap_ci(df, num, den, n, seed, level)` | Resamples ads with replacement; returns point estimate and interval |
| `bh_correct(pvalues)` | Benjamini-Hochberg adjusted values |
| `percentile_rank(series)` | 0 to 1 rank used for score normalisation |

#### `metrics.py`
Adds to each ad: `roas`, `cpa`, `cvr`, `ctr`, `hook_rate`, `hold_rate`, `atc_rate`, `aov`. Division by zero yields NaN, not 0 or infinity. Writes `ad_metrics.csv`.

#### `ad_model.py`
1. Builds the **analysis set**: all ads minus `suspected_tracking_fault`, minus ads below `min_spend_inr`; writes `ads_analysis_set.csv`.
2. **Noise from duplicates:** for the duplicate pairs, report absolute and relative ROAS and CVR differences to `ad_noise_from_duplicates.csv`. This calibrates how large a difference must be to be believed.
3. For each feature in `features_to_test`, for each label level with at least `min_group_size` ads, compute spend-weighted ROAS, CVR, hook rate and hold rate with bootstrap intervals; with and without LJ-004; at each `min_spend_variants` value. Writes `ad_group_metrics.csv`.
4. Applies the **finding rule** (section 9.2) and writes `ad_findings.csv` (surviving patterns) and `ad_not_concluded.csv` (everything else, with the reason it failed).
5. Checks confounds: repeat the key comparisons within `product_form`.
6. Produces `ad_findings_forest.png` (point and interval) and `funnel_by_pattern.png`.

`ad_findings.csv` columns: `finding_id, feature, level, comparison_level, metric_pair, effect, ci_low, ci_high, n_ads, spend_inr, survives_without_lj004, survives_spend_variants, confound_note, supporting_ad_ids`.

#### `creator_features.py`
Writes `creator_features.csv`, one row per creator, with:

| Group | Columns |
|---|---|
| Identity | `creator_id, handle, followers, persona, verified` |
| Reach | `median_plays, plays_per_follower, plays_iqr, organic_median_plays, sponsored_median_plays, sponsored_organic_ratio, ratio_note` |
| Engagement | `engagement_rate_median, likes_hidden_share, engagement_basis` (`full` or `comments_reshares_only`) |
| Consistency | `share_posts_above_own_median` |
| Fit signals | `share_kids_on_camera, share_product_shown, share_food_nutrition_topics, dominant_language, language_mix, format_mix` |
| Sponsorship | `sponsored_share, distinct_sponsor_brands, days_since_last_post` |
| Risk | `competitor_brands, adjacent_brands, uncategorised_brands, child_performer_flag` |
| Audience | `audience_known (bool), women_share, india_share, age_split, audience_platform` |
| Quality | `posts_available, transcripts_available` |

Any NaN has a companion reason column.

#### `gates.py`
Each gate returns `(passed: bool, reason: str)`. All thresholds from config. Output `gate_results.csv` with one column per gate plus `gate_reasons`.

| Gate | Fails when |
|---|---|
| `already_partner` | `already_partner_brand` appears in the audience file's past brands or in the creator's `brands_visible` on a sponsored post |
| `audience_mismatch` | Audience known and women share below `min_women_share_known`, or India share below `min_india_share_known` |
| `direct_competitor` | A `competitor_kids_nutrition` brand appears in a sponsored post in the recent window |
| `no_family_content` | Share of posts with kids on camera or family/food/nutrition topics below `min_child_family_share` |
| `too_little_evidence` | Posts available below `min_posts` |

Soft flags (never remove, always show): `child_performer_flag`, `sponsored_saturation`, `hidden_metrics`, `inactive`, `medical_authority_persona`.

#### `scoring.py`
Only creators who pass all hard gates are scored. All components are scaled 0 to 1.

| Component | Definition |
|---|---|
| `creative_fit` | Weighted match between the creator's content (language, formats, kids-on-camera share, topics) and the **surviving** Phase 2 findings, via `label_map.yaml`. Each finding contributes `effect_weight × match_share`, where `match_share` is the share of the creator's posts matching the finding's level. Findings used are listed per creator |
| `reach_quality` | Percentile rank of sponsored-adjusted `plays_per_follower`, capped at `reach_cap_percentile`. Sponsored-adjusted = sponsored median if enough sponsored posts, else organic median × the pooled median sponsored/organic ratio |
| `engagement_quality` | Percentile rank of `engagement_rate_median`; multiplied by `(1 − 0.5 × hidden_likes_share)` where likes are hidden |
| `audience_fit` | Known: average of women-share, India-share and 25 to 40 age-share scores. Unknown: `unknown_audience_score` |
| `commercial_risk` | `1 − penalty`, where penalty sums: adjacent brand exposure (0.1 each, capped at 0.3), sponsored share above flag (scaled up to 0.3), inactivity (0.2), child-performer flag (0.2); capped at 1 |

`total = Σ weight × component`. `creator_ranking.csv` columns: `creator_id, handle, passed_gates, gate_reasons, creative_fit, reach_quality, engagement_quality, audience_fit, commercial_risk, total, rank, confidence, confidence_reasons, findings_used, soft_flags`.

**Confidence label** from a points scheme: +1 for each of posts_available ≥ `min_posts_for_confidence`; likes not hidden; audience known; at least two Phase 2 findings behind fit; transcripts available. 4 to 5 = high, 2 to 3 = medium, 0 to 1 = low.

#### `sensitivity.py`
1. Dirichlet weight draws around the base weights (`draws`, `dirichlet_concentration`); record top-5 membership.
2. Variants: min spend from `min_spend_variants`; with and without LJ-004; gate thresholds ±; leave-one-component-out; drop the weakest finding.
3. Output `sensitivity_top5_frequency.csv` (`creator_id, share_in_top5, label, best_backup`) and `sensitivity_variants.csv`.
4. Label: robust (≥ `robust_threshold`), likely (≥ `likely_threshold`), marginal (otherwise). Marginal picks get the highest-ranked non-picked creator as backup.
5. Output `top5_stability.png`.

#### `claims.py`
Builds `claims_whitelist.csv` and `docs/claims_whitelist.md` from the unique entries in `ads.claims_made`: claim text, ads using it, spend-weighted ROAS of ads using it, and a `needs_compliance_review` flag (true for protein quantities, immunity, growth, brain development or other health outcomes).

#### `briefs.py`
For each final pick, render `outputs/briefs/<creator_id>.md` from `brief.md.j2` with the nine parts defined in `AGENTS.md` section 7. Validation (also tested):
- Every angle, format and hook style cites at least one ad ID that exists in `ads.csv` and creator post URLs that exist in `creator_posts.csv`.
- Every claim used appears in the whitelist.
- Hook lines present in three variants, in the creator's dominant language, with a flag for native-speaker review where applicable.
- No brief states a health outcome for children beyond the whitelist.

#### `report.py`
Renders `report.html` and `report.md` from templates and **only** from files in `outputs/tables/`. A test fails if a number in the report is not found in any table.

#### `run_all.py`
Runs, in order: `audit`, `labels_check` (sample build only), `metrics`, `ad_model`, `creator_features`, `gates`, `scoring`, `sensitivity`, `claims`, `briefs`, `report`. Prints one line per stage (rows in, rows out, rows excluded). Stops on the first failure with a non-zero exit code.

### 8.3 Label mapping (`label_map.yaml`)

Ad labels (for example `hook_type`, `ad_format`, `language`) and post labels (for example `hook_style`, `content_form`, `language`) use **different vocabularies**. Phase 1 lists the distinct values of each. Phase 3 creates `label_map.yaml` as an explicit, human-reviewed mapping, for example:

```yaml
language:            # ad value -> post value(s)
  Hinglish: ["hinglish", "hindi-english"]
ad_format_to_post_content_form:
  skit: ["skit", "family_scene"]
  talking_head: ["talking_head", "expert_talk"]
child_on_screen_to_children_on_camera:
  "yes": ["yes"]
```

Values above are placeholders; the real keys come from the data. Any ad label with no mapping is listed and excluded from the fit component, never guessed.

### 8.4 Final recommendation requirements

The report's first screen must contain a table:

| Creator | Why (one line) | Message in one sentence | Confidence | Robustness | Main risk |
|---|---|---|---|---|---|

Followed by backups, the excluded creators with reasons, and the limits.

---

## 9. Methodology rules (summary of `AGENTS.md` section 5)

### 9.1 Metrics
Hook rate, hold rate, CTR, add-to-cart rate, CVR, ROAS, CPA, AOV; group values are **ratios of sums** (spend-weighted).

### 9.2 Finding rule
A pattern counts only if:
1. It points the same way on at least two metrics of a pair in `consistency_metric_pairs`.
2. It survives removing LJ-004.
3. The group has at least `min_group_size` ads.
4. It is not fully explained by `product_form` or launch period.
5. It holds at every `min_spend_variants` value (or the report says it does not).

The interval must also be wider than the noise from duplicate pairs would suggest; the audit states this threshold explicitly.

### 9.3 Selection
Hard gates, then score, then confidence, then sensitivity, then pick top 5 with backups.

---

## 10. Non-functional requirements

| Area | Requirement |
|---|---|
| **Reproducibility** | Fixed seed; two runs produce byte-identical CSVs; clean-clone run reproduces the original rankings |
| **Traceability** | Every number in the report maps to a row in `outputs/tables/`; every brief element maps to ad IDs and post URLs |
| **Transparency** | Every exclusion, assumption and limit documented in `docs/` |
| **Performance** | Entire pipeline runs in under 5 minutes on a laptop (data is under 1 MB) |
| **Readability** | Report understandable by a non-technical manager in 5 minutes; no unexplained jargon |
| **Maintainability** | Config-driven thresholds; module per stage; type hints and docstrings |
| **Portability** | Works on macOS, Linux and Windows; no Makefile required |
| **Safety** | No modification of raw data; no external data transmission; no invented claims |
| **Accessibility** | Charts use colour-blind-safe palettes and have text titles |

---

## 11. Testing and quality

| Test file | Must assert |
|---|---|
| `test_load.py` | Row counts 100, 20, 392; list columns split; dates parsed |
| `test_audit.py` | LJ-089 flagged (high spend, zero purchases); LJ-004 flagged as concentration outlier; duplicate pairs detected |
| `test_stats.py` | `weighted_ratio` on hand-made data matches manual result; bootstrap reproducible; BH correct on known values |
| `test_metrics.py` | Zero denominators give NaN |
| `test_ad_model.py` | Analysis set excludes LJ-089 and ads below min spend; a synthetic pattern that depends on one outlier is rejected |
| `test_creator_features.py` | Medians correct; hidden-likes handling; ratio withheld with too few posts |
| `test_gates.py` | CR-20 fails `already_partner`; a creator with known male-skewed audience fails `audience_mismatch` |
| `test_scoring.py` | A 100%-sponsored creator gets a risk penalty; unknown audience gives neutral score and lower confidence |
| `test_sensitivity.py` | Same seed gives identical frequencies |
| `test_claims.py` | Whitelist equals the unique set from `ads.claims_made` |
| `test_briefs.py` | No claim outside the whitelist; all cited ad IDs and URLs exist |
| `test_report.py` | Every numeric token in the report appears in an output table |
| `test_reproducibility.py` | Two full runs produce identical tables |

`pytest -q` must pass before any phase is called done. Tests are never weakened to pass.

---

## 12. Acceptance criteria

The project is complete when **all** of the following are true:

- [ ] `python -m lj.run_all` completes from a fresh clone and `pytest -q` passes.
- [ ] `docs/data_audit.md` confirms or refutes each trap T1 to T16 with numbers and an action.
- [ ] Label error rate is measured on a sample and quoted in the report.
- [ ] `outputs/tables/ad_findings.csv` lists 3 to 6 surviving patterns with intervals, and `ad_not_concluded.csv` lists the rest.
- [ ] `creator_ranking.csv` covers all 20 creators with gate reasons, scores, rank and confidence.
- [ ] CR-20 is excluded with the stated reason; CR-14, CR-05 and CR-17 are either excluded or visibly flagged.
- [ ] Final 5 chosen, each labelled robust, likely or marginal, with backups for marginal ones.
- [ ] Five briefs exist; each cites ad IDs and post URLs; all claims are whitelisted; language flags are set.
- [ ] Report answers the question on its first screen and includes "What this data cannot tell you".
- [ ] Every number in the report traces to a table (test passes).
- [ ] `git diff data/raw` is empty after the initial commit.
- [ ] README, `docs/note.md`, `AGENTS.md`, `prompt_log.md`, `corrections.md` and session artifacts are in the repo.
- [ ] Repo is public.

### Quality bar for the answer ("would a marketing manager trust it?")
- Do the exclusions make sense to someone who knows the brand?
- Are fragile findings labelled fragile?
- Are the limits stated before the reader has to find them?
- Could a sceptical reader reproduce the result in under 15 minutes?

---

## 13. Report specification

Length: about 2 to 3 pages plus appendix. Sections, in order:

1. **The answer:** table of 5 creators (section 8.4), backups.
2. **What the brand's own ads tell us:** 3 to 5 findings with numbers and intervals; "could not conclude" list.
3. **Why these 5 and not the others:** gates, exclusions, ranking logic in plain words.
4. **How sure we are:** robust, likely, marginal; what would change the answer.
5. **What each creator should say:** brief summaries linking to full briefs.
6. **What this data cannot tell you:** no costs or rate cards; audience data for 3 of 20; one account, limited period; AI labels with measured error rate; Instagram performance is not ad performance; sponsored reach is lower; observational, not causal.
7. **Before you sign anyone:** rate card, audience insights from the creator, compliance review, exclusivity and competitor clauses, partnership disclosure.
8. **Appendix:** audit summary, sensitivity chart, method pointers.

Visuals: ad findings forest plot with intervals; funnel by pattern; reach vs followers; top-8 score components; top-5 stability.

---

## 14. One-page note specification (`docs/note.md`)

1. **Key choices and why** (5 to 6 bullets): excluding LJ-089; min-spend threshold from duplicate-pair noise; LJ-004 tested both ways; gates before scores; confidence labels; claim whitelist.
2. **What I did not trust and what I did about it:** AI labels (measured error rate); made-up performance treated as the brand's data; unknown audience.
3. **What I would build next with one more week:** requesting audience data from shortlisted creators; a lookalike audience estimate; a test design (A/B or geo split) to validate picks; a cost model once rate cards exist; model-assisted video content analysis with human review; a hook generator evaluated on held-out ads.
4. **Where AI helped and where I overruled it:** two or three concrete examples from `corrections.md`.

---

## 15. AI tool use requirements

- Primary tool: Google Antigravity (planning mode for judgement phases; faster mode for mechanical work).
- `AGENTS.md` at repo root; one phase per task; plans reviewed before code for Phases 2, 4, 5, 6.
- `docs/ai_usage/prompt_log.md`: main prompts per phase, what the AI produced, what was checked, what was changed or rejected.
- `docs/ai_usage/corrections.md`: every case where the AI was wrong or overconfident and how it was caught. Aim for at least 3 genuine entries.
- `docs/ai_usage/session_artifacts/`: exported plans, task lists and walkthroughs.
- The user is the guardrail: hand-check at least 3 numbers per phase and record them.

---

## 17. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Label vocabulary mismatch between ads and posts makes fit scoring weak | High | Medium | Explicit `label_map.yaml`; unmapped labels excluded and listed; confidence lowered |
| Findings are chance patterns | High | High | Pre-registration, intervals, BH correction, two-metric rule, with/without LJ-004 |
| Agent drifts or overreaches | Medium | High | `AGENTS.md`, one phase per task, plan approval, hand-checks |
| Briefs in unfamiliar languages are poor | Medium | Medium | Flag for native review; keep hooks short; say so in the note |
| Time overrun | Medium | Medium | Priority order in section 16; commit every phase |
| Ranking depends on weight choices | High | Medium | Sensitivity analysis; robust/likely/marginal labels; backups |
| Over-polished report hides limits | Medium | High | Limits section mandatory and tested for presence |
| Compliance missteps in kids' claims | Medium | High | Claim whitelist, human-review flag, compliance reminder |
| Clean-clone run fails | Medium | High | Phase 8 clean-room test; pinned lock file |

---

## 18. Open questions (email galvor.ai; asking is not marked down)

Log answers in `docs/open_questions.md`. Do not wait for replies; state your assumption and proceed.

1. Is LJ-089's zero purchase count a known tracking issue, or should it be treated as real?
2. What does Little Joys sell (product forms and price points), and are some products priority for the next campaign?
3. Should I treat Little Joys' past partners as ineligible, or can a past partner be re-engaged?
4. Is there a budget or rate-card range per creator, even approximate?
5. What is the label error rate you have measured for your system, so I can compare it with my sample?
6. Are the ad performance dates comparable across all ads (same attribution window)?
7. Is a Hindi/Hinglish creator acceptable for ads currently running in other languages?

---

## 19. Glossary

| Term | Meaning |
|---|---|
| ROAS | Return on ad spend: revenue divided by spend |
| CVR | Conversion rate: purchases divided by link clicks |
| CTR | Click-through rate: link clicks divided by impressions |
| Hook rate | 3-second views divided by impressions (does the opening grab attention?) |
| Hold rate | ThruPlays divided by 3-second views (do viewers stay?) |
| CPA | Cost per purchase |
| AOV | Average order value |
| Spend-weighted | Computed from totals (sum of revenue divided by sum of spend), not by averaging ad-level ratios |
| Bootstrap interval | A range from repeatedly resampling the ads; shows how uncertain an estimate is |
| BH correction | Benjamini-Hochberg adjustment limiting false findings when testing many patterns |
| Gate | A pass/fail rule that removes a creator before scoring |
| Sponsored-adjusted reach | Reach estimate that accounts for sponsored posts reaching fewer people |
| Robust / likely / marginal | How often a pick stays in the top 5 across stress tests |
