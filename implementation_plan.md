# Implementation Plan: Little Joys Creator Selection (galvor.ai take-home)

**Question to answer:** Which 5 of the 20 creators should Little Joys work with next, and what should each of them say, using only the brand's own data?


**Guiding rule:** a plain answer with sound reasoning beats a polished one nobody can trust. Every number in the final answer must trace to a script, and every limitation must be stated.

**Companion document:** `PRD.md` holds the full specification (folder structure, config, module specs, scoring formulas, output schemas, acceptance criteria). This plan tells you **what to do, in what order, with which commands and prompts**.

---

## 0. How to use this document

1. Do **Phase 0** by hand, before you open any AI prompt.
2. At the start of **every new Antigravity conversation**, paste the **Standing instructions** block (section 1 below) first, then the phase prompt. There is no rules file in the repo, so this block is what keeps the agent on track.
3. For each phase: read the goal, paste the phase prompt (in a quote block), then run the **verify** steps yourself before moving on.
4. One phase per conversation or task. Do not let the agent skip ahead.
5. All commands run from the **repo root** (`little-joys-creators/`) unless a path is shown.



If time runs short, protect in this order: audit, ad findings, gates and ranking, briefs for the top 5, report, README, note. Cut first: extra figures, notebook, recording polish, stretch items.

### What I found when inspecting the data (confirm each one in Phase 1)

| Item | Observation | Why it matters |
|---|---|---|
| LJ-004 | About ₹6.6L spend, about 5.0x ROAS, about 30% of all revenue | One ad can drive every "what works" finding |
| LJ-089 | About ₹4.3L spend, 1,544 add-to-carts, **0 purchases** | Probably a tracking fault, not a failed creative |
| LJ-072 and similar | About ₹4k spend, about 3.0x ROAS | Tiny samples look like winners by luck |
| Duplicate transcripts | LJ-003/059, LJ-036/056, LJ-073/093 | Same creative, different results: gives a noise estimate |
| CR-20 | Audience file lists Little Joys as a past brand; about 70% male audience | Not a "next" creator |
| CR-14 | Audience data is from Facebook; about 35% outside India; about 0.27 plays per follower | Reach and audience fit are doubtful |
| CR-05 | Child performer, about 2.8M followers | Child-safety and compliance question |
| CR-17 | 20 of 20 posts sponsored, low engagement rate, many hidden likes | Possible ad-farm account |
| Sponsored vs organic | Sponsored posts get roughly half the plays of organic for most creators | Do not forecast sponsored reach from organic reach |
| Audience data | Only 3 of 20 creators have it | Audience fit for the rest is inferred; label it so |
| Competitor brands | Gritzo, Himalaya, Cadbury, Chupa Chups and others appear in posts | Check conflicts per creator |
| Ad labels | AI-generated, a few missing | Spot-check any label you rely on |

---

## 1. Standing instructions (paste at the start of every Antigravity conversation)

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

## Phase 0: Environment and setup (do this yourself, about 45 min)

### 0.1 Install prerequisites

| Tool | Check command | Notes |
|---|---|---|
| Python 3.11 or newer | `python --version` (or `python3 --version`) | Install from python.org if older |
| Git | `git --version` | |
| GitHub account | n/a | Repo must be **public** |
| GitHub CLI (optional) | `gh --version` | Makes repo creation one command |
| Google Antigravity | n/a | Download from the official Antigravity site, sign in with a Google account |

### 0.2 Create the project folder and repo

Run in the folder where you keep projects (for example `~/projects`):

```bash
mkdir little-joys-creators
cd little-joys-creators
git init -b main
mkdir -p data/raw data/processed src/lj/templates tests outputs/tables outputs/figures outputs/briefs outputs/videos docs/ai_usage/session_artifacts notebooks
```

Copy the five files from `little-joys-data.zip` into `data/raw/`:

```bash
# from the folder that contains the zip
unzip little-joys-data.zip -d little-joys-creators/data/raw
# Windows PowerShell:
# Expand-Archive little-joys-data.zip -DestinationPath little-joys-creators\data\raw
```

You should now have `data/raw/ads.csv`, `creators.csv`, `creator_posts.csv`, `creator_audience.csv`, `README.md`. Rename the data README so it does not clash with yours:

```bash
mv data/raw/README.md data/raw/DATA_README.md        # Windows: ren data\raw\README.md DATA_README.md
```

Copy `PRD.md` and `implementation_plan.md` into the repo root.

### 0.3 Virtual environment

Run from the repo root.

```bash
python -m venv .venv

# activate
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\Activate.ps1       # Windows PowerShell
# .venv\Scripts\activate.bat       # Windows cmd

python -m pip install --upgrade pip
```

### 0.4 Libraries

Create `requirements.txt` in the repo root:

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

Install:

```bash
pip install -r requirements.txt
pip freeze > requirements.lock.txt
```

Library roles: `pandas` and `numpy` for data work; `scipy` and `statsmodels` for intervals and tests; `scikit-learn` only for simple scaling or similarity; `matplotlib` for static charts; `plotly` only if you build an interactive view; `pyyaml` for config; `jinja2` and `markdown` to render the report; `pytest` for tests; `jupyterlab` for exploration only.

### 0.5 Make the package importable

Create `pyproject.toml` in the repo root:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "lj"
version = "0.1.0"
requires-python = ">=3.11"

[tool.setuptools.packages.find]
where = ["src"]
```

Then:

```bash
touch src/lj/__init__.py        # Windows: type nul > src\lj\__init__.py
pip install -e .
python -c "import lj; print('ok')"
```

### 0.6 `.gitignore`

```text
.venv/
__pycache__/
*.pyc
.ipynb_checkpoints/
.DS_Store
outputs/videos/
```

### 0.7 Create the starter `config.yaml`

Copy the full `config.yaml` from `PRD.md` section 8.1 into the repo root. These are starting values; each one gets justified or changed with evidence in Phases 2 to 5.

### 0.8 First commit and GitHub repo

```bash
git add .
git commit -m "chore: project scaffold, raw data, PRD, plan, config"

# with GitHub CLI
gh auth login
gh repo create little-joys-creators --public --source=. --push

# without it: create an empty PUBLIC repo on github.com, then
# git remote add origin https://github.com/<your-username>/little-joys-creators.git
# git push -u origin main
```

### 0.9 Antigravity setup

1. Open Antigravity, sign in, choose **Open Folder** and select `little-joys-creators`.
2. Select the `.venv` interpreter for the workspace (command palette, then "Python: Select Interpreter").
3. Set terminal command execution to a mode where you **review commands before they run**, not fully automatic. You are the guardrail.
4. Use the planning mode for Phases 2, 4, 5 and 6 (design decisions), and the faster mode for mechanical work such as Phase 8.
5. Open a terminal inside Antigravity and confirm: `which python` (or `where python`) points at `.venv`.
6. Create `docs/ai_usage/prompt_log.md` and `docs/ai_usage/corrections.md` now (templates in Phase 9) and fill them as you go.

**Checkpoint:** `python -c "import pandas, scipy, lj; print('ready')"` prints `ready`, repo is on GitHub, `PRD.md`, `implementation_plan.md` and `config.yaml` are committed.

---

## Phase 1: Load, audit and clean the data (about 1.5 h)

**Goal:** a trusted, documented dataset, and an explicit list of everything that is wrong with it.

**Files to create:** `src/lj/config.py`, `src/lj/load.py`, `src/lj/audit.py`, `src/lj/labels_check.py`, `tests/test_load.py`, `tests/test_audit.py`, `docs/data_audit.md`.

> **Antigravity prompt (Phase 1)**
> [Paste the standing instructions first.] Do only Phase 1, following PRD.md sections 8.1 and 8.2 for `config`, `load`, `audit` and `labels_check`.
> 1. `src/lj/config.py` loads `config.yaml` and exposes paths and SEED.
> 2. `src/lj/load.py` loads the four CSVs with correct dtypes (dates parsed, list-columns split on "; ", `is_sponsored` as boolean).
> 3. `src/lj/audit.py` runs every check listed in PRD.md section 8.2 (audit.py) and writes `outputs/tables/audit_*.csv`. Include the list of every distinct value of `brands_visible` per creator, and the distinct values of the ad labels and post labels I will need to map later (hook_type, ad_format, language, child_on_screen, hook_style, content_form, topic).
> 4. `src/lj/labels_check.py` draws a fixed random sample of 12 ads (seed from config) and writes `outputs/tables/audit_labels_sample.csv` with empty `human_label` and `agree` columns for me to fill in; add a function that reads the filled file and reports the error rate per label column.
> 5. Write `docs/data_audit.md` summarising each finding in plain English with exact numbers and an "action" column (exclude / flag / keep).
> 6. Tests: row counts 100, 20, 392; LJ-089 is flagged as zero-purchase high-spend; LJ-004 is flagged as a concentration outlier; duplicate pairs are detected.
> Do not modify data/raw. Run pytest and show the output. Stop after Phase 1.

**Run:**

```bash
python -m lj.audit
python -m lj.labels_check          # builds the sample file
pytest -q
```

**Verify yourself (do not skip):**
- Open `outputs/tables/audit_*.csv` and spot-check three numbers by hand (for example, LJ-004 revenue share).
- Open `ads.csv` in a spreadsheet, filter LJ-089, and confirm purchases are 0 while add-to-carts are not.
- Compare the audit to the table at the top of this plan. If it found something new, add it to `docs/data_audit.md`. If it missed one, tell the agent.
- **Label spot-check:** open `audit_labels_sample.csv`, read each transcript, fill `human_label` and `agree`, then run the error-rate function. Record the error rate in `docs/data_audit.md`. Optional: download a few videos to confirm (`curl -L -o outputs/videos/ad_001.mp4 "<video_url>"`; the folder is git-ignored).

**Done when:** audit tables exist, `docs/data_audit.md` is written, label error rate is recorded, tests pass, commit made (`git add -A && git commit -m "feat: data load and audit"`).

---

## Phase 2: What works in the brand's own ads (about 2 h)

**Goal:** a short, defensible list of creative patterns that actually relate to performance, with honest uncertainty.

**Files to create:** `src/lj/stats.py`, `src/lj/metrics.py`, `src/lj/ad_model.py`, `tests/test_stats.py`, `tests/test_metrics.py`, `tests/test_ad_model.py`, `docs/ad_findings.md`.

### Method

1. **Metrics per ad:** ROAS, CPA, CVR, CTR, hook rate (3s views / impressions), hold rate (ThruPlays / 3s views), add-to-cart rate, AOV.
2. **Analysis set (documented):** exclude LJ-089; apply the minimum-spend threshold; keep LJ-004 but run **every** result with and without it.
3. **Noise calibration:** use the three duplicate-creative pairs to see how far results differ for identical creatives. Choose the min-spend threshold and the "difference big enough to believe" level from this, and write the reasoning down.
4. **Aggregate by label level** using **spend-weighted ratios** (sum of revenue / sum of spend), not the mean of ad-level ROAS. Add a **bootstrap 95% interval** by resampling ads (5,000 iterations, fixed seed).
5. **Pre-register the features to test** (they are already in `config.yaml`; write them in `docs/ad_findings.md` *before* you look at results).
6. **Multiple comparisons:** with 100 ads and many labels, some patterns appear by chance. Apply Benjamini-Hochberg correction to any tests you report, or state clearly that results are directional.
7. **Keep a finding only if** (a) the direction is the same on at least two paired metrics, (b) it survives dropping LJ-004, (c) the group has at least 8 ads, (d) it is not fully explained by `product_form`, and (e) it holds across the min-spend variants. Everything else is labelled "not enough evidence".
8. **Separate funnel stages.** Hook and hold rates show what gets attention; CVR and ROAS show what sells. A creative can win attention and lose sales; say which is which.

> **Antigravity prompt (Phase 2)**
> [Paste the standing instructions first.] Read docs/data_audit.md and config.yaml. Do only Phase 2, following PRD.md sections 8.2 (stats, metrics, ad_model) and 9.
> Before writing code, produce a short plan covering the metrics, the analysis-set rules, the pre-registered features, and the finding rule, and wait for my approval.
> After approval: implement `stats.py` (weighted_ratio, bootstrap_ci, bh_correct, percentile_rank), `metrics.py` and `ad_model.py`. Use the duplicate-creative pairs to quantify noise and print that number. Save all tables to outputs/tables/ (`ad_metrics.csv`, `ad_noise_from_duplicates.csv`, `ad_group_metrics.csv`, `ad_findings.csv`, `ad_not_concluded.csv`) and charts to outputs/figures/ (forest-style plots with intervals, not bare bars). Add tests on a tiny hand-made DataFrame where the correct spend-weighted ROAS is known, and a test that a pattern depending on one outlier is rejected. Report which candidate findings fail the finding rule and why. Do not describe any pattern as proven.

**Run:**

```bash
python -m lj.metrics
python -m lj.ad_model
pytest -q
```

**Verify yourself:**
- Recompute one group's ROAS by hand in a spreadsheet (SUM revenue / SUM spend) and compare.
- Change the seed in `config.yaml` (for example `seed: 7`), rerun, and confirm that conclusions do not change. Set it back to 42 afterwards.
- Read each finding and ask: could this just be LJ-004, the product form, or a handful of small ads?

**Done when:** `docs/ad_findings.md` lists 3 to 6 surviving patterns and an explicit "what we could not conclude" list, tests pass, committed.

---

## Phase 3: Creator profiles, features and label mapping (about 1.5 h)

**Goal:** one comparable row per creator with true reach, engagement quality, content fit and risk flags, plus a reviewed mapping between ad labels and post labels.

**Files to create:** `src/lj/creator_features.py`, `label_map.yaml`, `tests/test_creator_features.py`, `docs/creator_profiles.md`.

### Features per creator (full column list in `PRD.md` section 8.2)

| Group | Feature | Notes |
|---|---|---|
| Reach | median plays, plays per follower, spread (IQR) | Medians, not means: viral outliers distort |
| Reach | organic vs sponsored median plays and their ratio | Withhold the ratio if fewer than 3 posts in either group |
| Engagement | (likes + comments + reshares) / plays | For hidden-likes accounts use comments and reshares only, and flag them |
| Consistency | share of posts above the creator's own median | |
| Fit | share with children on camera, product shown, food/nutrition topics; dominant language; format mix | From post labels |
| Sponsorship | sponsored share, distinct sponsor brands, days since last post | High saturation lowers trust |
| Risk | competing or adjacent brands in `brands_visible`; child-performer flag | Use the dictionary in `config.yaml`; list unknown brands, do not guess |
| Audience | known vs inferred | Always label |
| Data quality | posts available, transcripts available | |

### Label mapping

Ad labels and post labels use different vocabularies. Using the distinct values the Phase 1 audit listed, create `label_map.yaml` (examples in `PRD.md` section 8.3). Review every mapping yourself. Any ad label with no mapping is listed and excluded from the fit score, never guessed.

> **Antigravity prompt (Phase 3)**
> [Paste the standing instructions first.] Read docs/data_audit.md and docs/ad_findings.md. Do only Phase 3.
> 1. `src/lj/creator_features.py` writes `data/processed/creator_features.csv`, one row per creator, with the columns in PRD.md section 8.2 (creator_features). Use medians. Handle hidden likes and withhold organic/sponsored ratios when a group has fewer than 3 posts. Map `brands_visible` to categories using `brand_categories` in config.yaml, and list every brand not in the dictionary instead of guessing. Every NaN needs a reason column.
> 2. Propose a `label_map.yaml` from the distinct label values in the Phase 1 audit tables, for each surviving finding in docs/ad_findings.md. Mark every mapping you are unsure about with a comment. I will review it.
> 3. Write `docs/creator_profiles.md` with a 3 to 4 line profile per creator quoting `persona`, `what_feels_native` and the numbers behind them.
> 4. Tests on a small synthetic posts table. Do not rank or score yet.

**Run:**

```bash
python -m lj.creator_features
pytest -q
```

**Verify yourself:**
- Open 3 creators' Instagram posts (links in `post_url`) and compare plays, the sponsored label and the children-on-camera label to the file.
- Look at CR-17 and the other heavily sponsored creators and see what their organic posts look like.
- Review every line of `label_map.yaml`. This file decides your fit scores.

**Done when:** `creator_features.csv` has 20 rows, no silent NaNs, profiles written, `label_map.yaml` reviewed by you, committed.

---

## Phase 4: Gates, scoring and selecting the 5 (about 1.5 h)

**Goal:** a transparent, rule-based shortlist where anyone can see why each creator is in or out.

**Files to create:** `src/lj/gates.py`, `src/lj/scoring.py`, `tests/test_gates.py`, `tests/test_scoring.py`, `docs/selection_logic.md`.

### Step A: hard gates (a creator is removed, with a stated reason)

| Gate | Rule | Expected effect |
|---|---|---|
| Already a partner | Little Joys appears in past brands or in recent sponsored posts | CR-20 out |
| Audience mismatch (where known) | Mostly outside India, or heavily male for a mother-focused product | CR-14 and CR-20 flagged |
| Direct competitor | Competing kids' nutrition brand in recent sponsored posts | Check per creator |
| No family or food content | Almost no posts with children or food/nutrition topics | Likely CR-06 and CR-18 |
| Too little evidence | Fewer than 8 posts | Flag as low confidence |

Soft flags (kept, but shown prominently): child-performer account (CR-05), sponsored saturation (CR-17), hidden metrics, inactivity, medical-authority personas where claim risk is higher.

### Step B: scoring (only creators who pass the gates)

Score is a weighted sum of 0 to 1 components. Weights live in `config.yaml`. Component definitions are in `PRD.md` section 8.2 (scoring).

| Component | Starting weight |
|---|---|
| Creative fit with surviving ad findings | 0.30 |
| Reach quality (sponsored-adjusted plays per follower) | 0.25 |
| Engagement quality | 0.20 |
| Audience fit (known scored; unknown neutral plus lower confidence) | 0.15 |
| Commercial risk | 0.10 |

Each creator also gets a **confidence label** (high / medium / low) from the points scheme in the PRD.

> **Antigravity prompt (Phase 4)**
> [Paste the standing instructions first.] Read docs/ad_findings.md, docs/creator_profiles.md, label_map.yaml and PRD.md section 8.2 (gates, scoring). Do only Phase 4.
> First write a plan describing the gates and score components and wait for my approval. After approval: implement `gates.py` (each gate returns pass/fail plus a human-readable reason; thresholds from config.yaml) and `scoring.py` (components, weights from config.yaml, confidence label). Output `outputs/tables/gate_results.csv` and `outputs/tables/creator_ranking.csv` with every creator, gate results, component scores, total, rank, confidence, findings used and soft flags. The creative-fit component must use only surviving findings from docs/ad_findings.md and list which ones it used. Write `docs/selection_logic.md` explaining each gate and weight in plain English. Tests: CR-20 fails the already-a-partner gate; a synthetic creator with 100% sponsored posts gets a risk penalty; an unknown audience gives the neutral score and lowers confidence. Do not choose the final 5 yet; show the ranking and the borderline cases (ranks 4 to 8).

**Run:**

```bash
python -m lj.gates
python -m lj.scoring
pytest -q
```

**Verify yourself:**
- Read the ranking top to bottom. If a creator surprises you, trace the components that put them there.
- Look at ranks 4 to 8: those are the decisions where being wrong costs the brand.
- Check each gate reason for the excluded creators against the raw files.

**Done when:** a ranked table with reasons exists, committed.

---

## Phase 5: Robustness and sensitivity (about 1 h)

**Goal:** show which of the 5 picks are solid and which depend on your assumptions.

**Files to create:** `src/lj/sensitivity.py`, `tests/test_sensitivity.py`, `docs/robustness.md`.

Checks to run:
1. **Weight perturbation:** 2,000 random weight vectors (Dirichlet around your weights); record how often each creator lands in the top 5.
2. **Threshold perturbation:** min spend (5k, 10k, 20k), with and without LJ-004, gate thresholds slightly looser and tighter.
3. **Leave-one-component-out:** drop each score component in turn.
4. **Evidence stress test:** rerun with the weakest finding removed.
5. **Classify** each of the top 5 as *robust* (in the top 5 in at least 80% of runs), *likely* (at least 50%), or *marginal*, and name a backup for each marginal pick.

> **Antigravity prompt (Phase 5)**
> [Paste the standing instructions first.] Read config.yaml and docs/selection_logic.md. Do only Phase 5, following PRD.md section 8.2 (sensitivity). Implement the five checks above. Save `outputs/tables/sensitivity_top5_frequency.csv`, `outputs/tables/sensitivity_variants.csv` and `outputs/figures/top5_stability.png`. Write `docs/robustness.md` stating, for each creator in the base top 5, the percentage of runs in which they stay in the top 5, a robust / likely / marginal label, and the best backup. Test that results are identical when run twice with the same seed.

**Run:**

```bash
python -m lj.sensitivity
pytest -q
```

**Verify yourself:** change the seed and confirm the robust/marginal labels stay the same. If they flip, your result is less stable than it looks, and the report must say so.

**Done when:** final 5 chosen (with backups), reasoning in `docs/robustness.md`, committed.

---

## Phase 6: What each creator should say (about 1.5 h)

**Goal:** a concrete, creator-specific brief per pick, built from (a) what worked in the brand's ads and (b) what feels native to that creator. Nothing generic.

**Files to create:** `src/lj/claims.py`, `src/lj/briefs.py`, `src/lj/templates/brief.md.j2`, `tests/test_claims.py`, `tests/test_briefs.py`, `outputs/briefs/<creator_id>.md` (five files), `docs/claims_whitelist.md`.

### Each brief contains

1. **Creator and why them:** two lines, with key numbers.
2. **Angle:** the single message, linked to a surviving finding and ad IDs.
3. **Format and language:** matched to the creator's habits, with evidence from their own posts (post URLs).
4. **Three hook lines** in the creator's own language and voice, in the style of the winning hooks (cite the ad IDs).
5. **Beats of the video:** hook, demo, proof, call to action, and the child's role if relevant.
6. **Proof element:** only a whitelisted claim.
7. **Do and don't:** from `what_feels_native` and `what_would_feel_foreign`.
8. **Risks and compliance flags:** child consent and appearance, medical-claim wording, competitor exposure, paid-partnership disclosure.
9. **Confidence** from Phase 5, and what we do not know about this creator.

### Claims whitelist

`claims.py` builds the whitelist from the unique entries in `ads.claims_made` (with the ads that use each claim and their spend-weighted ROAS). Flag claims needing human compliance review (protein quantities, immunity, growth, brain development, any health outcome). Advertising children's nutrition is regulated, so recommend the brand verify wording against applicable ASCI and FSSAI guidance. You are not giving legal advice; say so.

> **Antigravity prompt (Phase 6)**
> [Paste the standing instructions first.] Read docs/ad_findings.md, docs/robustness.md, data/processed/creator_features.csv, and the `what_feels_native`, `what_would_feel_foreign`, `catchphrases`, `voice` and `language_use` fields in creators.csv. Do only Phase 6.
> 1. `src/lj/claims.py` builds `outputs/tables/claims_whitelist.csv` and `docs/claims_whitelist.md` from the unique entries in ads.claims_made, with the ad IDs that use each claim and a `needs_compliance_review` flag.
> 2. `src/lj/briefs.py` renders `outputs/briefs/<creator_id>.md` for each of the final 5, following the 9-part structure in implementation_plan.md Phase 6. Every angle, format and hook style must cite the ad IDs and creator post URLs it comes from. Hook lines must be in the creator's own language and voice, and flagged for native-speaker review if needed. Use only whitelisted claims. Do not invent statistics.
> 3. Tests that fail if a brief contains a claim not in the whitelist, or cites an ad ID or post URL that does not exist.
> Show me the first brief for review before writing the rest.

**Run:**

```bash
python -m lj.claims
python -m lj.briefs
pytest -q
```

**Verify yourself:**
- Read each brief as if you were the creator. Would it sound like them? Compare with their real captions and transcripts.
- Check every cited ad ID and post URL exists and says what the brief claims.
- If a hook is in a language you do not read well, say so in your note and flag it for the brand to review.

**Done when:** five briefs exist, tests pass, committed.

---

## Phase 7: The answer for the marketing manager (about 1.5 h)

**Goal:** a document a marketing manager can read in five minutes, act on, and trust.

**Files to create:** `src/lj/report.py`, `src/lj/templates/report.html.j2`, `src/lj/templates/report.md.j2`, `tests/test_report.py`, `outputs/report.html`, `outputs/report.md`.

### Structure (about 2 to 3 pages plus appendix; full spec in `PRD.md` section 13)

1. **The answer:** a table of the 5 creators (why in one line, the message in one sentence, confidence, robustness, main risk), plus backups.
2. **What the brand's own ads tell us:** 3 to 5 findings with numbers and intervals, plus the "could not conclude" list.
3. **Why these 5 and not the others:** the gates (including CR-20 and CR-14) and the ranking logic in plain words.
4. **How sure we are:** robust, likely, marginal.
5. **What each creator should say:** summaries with links to the full briefs.
6. **What this data cannot tell you:** no rate cards or costs; audience data for 3 of 20; one account over a limited period; AI-made labels with your measured error rate; Instagram performance does not guarantee ad performance; sponsored reach is lower; findings are associations, not causes.
7. **Before you sign anyone:** rate card, audience insights from the creator, compliance review, exclusivity and competitor clauses, partnership disclosure.
8. **Appendix:** audit summary, sensitivity chart, pointers to the repo.

Write for a non-technical reader: no jargon without explanation, charts with intervals and plain titles.

> **Antigravity prompt (Phase 7)**
> [Paste the standing instructions first.] Read everything in docs/ and outputs/. Do only Phase 7. Write `src/lj/report.py` and the templates so it renders `outputs/report.html` and `outputs/report.md` using Jinja2 from files in outputs/tables/ only. Use the 8-part structure in implementation_plan.md Phase 7, answer first, written for a marketing manager. Include the sensitivity chart and one chart of the ad findings with intervals. Write a test that fails if a number appears in the report that is not in any outputs/tables file, and a test that the "What this data cannot tell you" section is present. Show me the rendered outline before polishing.

**Run:**

```bash
python -m lj.report
# open outputs/report.html in a browser
pytest -q
```

**Verify yourself:** read it as the marketing manager. Does the first screen answer the question? Pick five numbers at random and trace each back to a CSV. Ask a friend who knows nothing about the project to read the first page and tell you what they would do.

**Done when:** the report renders from one command, committed.

---

## Phase 8: One command, tests and README (about 1 h)

**Goal:** a reviewer clones the repo, runs one command, and gets the same answer.

**Files to create or finish:** `src/lj/run_all.py`, `tests/test_reproducibility.py`, `README.md`.

`run_all.py` runs, in order: audit, labels_check (sample build only), metrics, ad_model, creator_features, gates, scoring, sensitivity, claims, briefs, report. It prints one line per stage and stops on the first failure.

`README.md` must contain:
- The question and the answer in 5 lines (the 5 creators).
- Repo map.
- Setup from scratch (the exact commands from Phase 0).
- How to reproduce: `python -m lj.run_all`.
- Method summary (one paragraph per phase) and links to `docs/`.
- Known limitations.
- AI tool use: pointer to `docs/ai_usage/`.

> **Antigravity prompt (Phase 8)**
> [Paste the standing instructions first.] Do only Phase 8. Create `src/lj/run_all.py` running every stage in the order above and stopping on the first failure, printing a one-line summary per stage. Write `tests/test_reproducibility.py` that runs the pipeline twice and asserts identical output tables. Write the README as specified in implementation_plan.md Phase 8. Then test from scratch: create a fresh virtualenv in /tmp, install requirements.txt, run `python -m lj.run_all`, and `pytest -q`. Report exactly what happened. Fix anything that breaks, but do not change any analysis results.

**Clean-room test (do this yourself too):**

```bash
cd ..
git clone https://github.com/<your-username>/little-joys-creators.git test-clone
cd test-clone
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt && pip install -e .
python -m lj.run_all
pytest -q
```

Compare `outputs/tables/creator_ranking.csv` from the clone with your original (they must be identical).

**Done when:** the clone reproduces your results exactly, committed and pushed.

---

## Phase 9: Note, AI evidence, recording and submission (about 1.5 h)

### 9.1 One-page note (`docs/note.md`)

- **Key choices and why** (5 to 6 bullets): excluding LJ-089, min-spend threshold from the duplicate-pair noise, LJ-004 tested both ways, hard gates before scoring, confidence labels, whitelisted claims.
- **What I did not trust, and what I did about it:** AI labels (your measured error rate), made-up performance treated as the brand's data, unknown audience.
- **What I would build next with one more week:** audience data requests to shortlisted creators; a lookalike audience estimate; a test design (A/B or geo split) to validate the picks; a cost-per-result model once rate cards exist; model-assisted video content analysis with a human check; a hook generator evaluated on held-out ads.
- **Where AI helped and where I overruled it:** two or three concrete examples from `corrections.md`.

### 9.2 AI tool use evidence

Keep these in `docs/ai_usage/`:
- `prompt_log.md`: your main prompts, per phase, in order.
- `corrections.md`: **the most valuable file.** Times the AI was wrong or overconfident and what you did. Record as they happen: a wrong label inference, a number that did not match your hand check, a claim in a brief not in the whitelist, an outlier that leaked into a finding.
- `session_artifacts/`: exported or copied plans, task lists and walkthroughs from Antigravity. Check the Antigravity interface for where these live and copy them in.
- The **standing instructions block** from section 1 of this plan: paste it into `prompt_log.md` as "Standing instructions used at the start of each conversation".

Template for `prompt_log.md`:

```markdown
## Phase N: <name>
**Date/time:**
**Mode / model:**
**Prompt:** (paste)
**What the AI produced:**
**What I checked:**
**What I changed or rejected, and why:**
```

Note: the assignment asks for your `CLAUDE.md` or `AGENTS.md` "if you used one". This plan does not use one; the standing instructions block plays that role and is included in the log, so the reviewers can see exactly how you steered the AI.

### 9.3 Optional 3-minute recording (recommended)

Script: 30 s on the question and the answer; 60 s on the three biggest data traps you found (LJ-089, LJ-004, CR-20/CR-14) and how you handled them; 45 s on robustness (which picks are solid); 30 s on one thing the AI got wrong and how you caught it; 15 s on what you would do next. Record with any screen recorder and upload as an unlisted link.

### 9.4 Final pre-submission checklist

- [ ] Repo is **public**; README renders; `requirements.txt` and `pyproject.toml` committed.
- [ ] `python -m lj.run_all` works from a fresh clone, and `pytest -q` passes.
- [ ] `outputs/report.html` and `outputs/report.md` are committed and open.
- [ ] Every number in the report traces to `outputs/tables/`.
- [ ] Five briefs in `outputs/briefs/`, each using only whitelisted claims.
- [ ] `docs/note.md` is one page.
- [ ] `docs/ai_usage/` contains `prompt_log.md`, `corrections.md` and session artifacts.
- [ ] No raw data was modified; `git diff data/raw` is empty after the first commit.
- [ ] The answer states its limits (audience data for 3 of 20, no costs, AI-made labels, performance numbers from one account).
- [ ] Email sent to the address the assignment came from with: repo link, note, recording link (if any). Tell them before the deadline if you will be late.

---

## Appendix A: Command cheat sheet (all from repo root)

```bash
source .venv/bin/activate                 # activate (Windows: .venv\Scripts\Activate.ps1)
python -m lj.audit                        # Phase 1
python -m lj.labels_check                 # Phase 1 (label sample)
python -m lj.metrics                      # Phase 2
python -m lj.ad_model                     # Phase 2
python -m lj.creator_features             # Phase 3
python -m lj.gates                        # Phase 4
python -m lj.scoring                      # Phase 4
python -m lj.sensitivity                  # Phase 5
python -m lj.claims                       # Phase 6
python -m lj.briefs                       # Phase 6
python -m lj.report                       # Phase 7
python -m lj.run_all                      # everything
pytest -q                                 # tests
jupyter lab                               # exploration only (notebooks/)
git add -A && git commit -m "<message>"   # commit after every phase
git push                                  # push after every phase
```

## Appendix B: Rules of thumb for working with the agent

1. **Paste the standing instructions first** in every new conversation.
2. **Plan first, code second** for any phase involving judgement (2, 4, 5, 6). Read the plan and challenge it.
3. **One phase per task.** Review the diff before approving the next.
4. **Hand-check three numbers** from every phase before moving on.
5. **Ask the agent to argue against its own result** ("what would make this finding false?") and put the useful part in `corrections.md`.
6. **Never accept a surprising result without tracing it.** Surprises are usually data issues.
7. **Keep config out of code** so you can show sensitivity.
8. **Commit at the end of every phase** so your git history shows the thinking.
9. If an agent proposes a bigger framework (a database, a web app, a model-training pipeline), ask whether it helps the brand trust the answer. Usually it does not; clarity does.

## Appendix C: Optional stretch items (only if time remains)

- A small Streamlit page (`pip install streamlit`, `streamlit run app.py`) showing the ranking with weight sliders, so the manager can see how picks change. Add it only after all phases are done.
- Transcript-based check of the creator briefs against the hooks of the best ads (similarity of structure, not wording).
- Downloading videos for the top 5 and bottom 5 ads and watching them to sanity-check the labels behind your Phase 2 findings.
