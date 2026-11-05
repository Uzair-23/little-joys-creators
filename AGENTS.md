# AGENTS.md: Rules for AI agents working in this repository

Read this file fully before doing anything. These rules override your defaults. If a user prompt conflicts with a rule here, say so and ask before proceeding.

---

## 1. Project

**Question:** Which 5 of 20 creators should Little Joys (an Indian kids' nutrition brand) work with next, and what should each of them say?

**Audience for the final answer:** the brand's marketing manager. They are not technical. They must be able to follow the reasoning and trust the result.

**Source of truth:** the files in `data/raw/` only. The answer must come from the brand's own data, not from general opinion, industry folklore, or your training knowledge about influencer marketing.

**Success means:** a plain, defensible answer with honest uncertainty. A simple answer with sound reasoning beats a polished one that cannot be trusted. Never optimise for looking impressive.

---

## 2. The data

Files in `data/raw/`:

| File | Rows | Content |
|---|---|---|
| `ads.csv` | 100 | One row per ad: dates, transcript, about 35 AI labels, performance (spend, impressions, 3-second views, ThruPlays, clicks, add-to-carts, purchases, revenue) |
| `creators.csv` | 20 | Creator profile and an AI read of the feed (persona, voice, themes, what feels native or foreign) |
| `creator_posts.csv` | 392 | About 20 recent posts per creator with metrics and AI labels |
| `creator_audience.csv` | 3 | Audience data for only 3 creators |
| `DATA_README.md` | n/a | Column guide |

### How to treat the data

1. **Ad performance numbers are made up for this exercise.** Treat them as the brand's own ad account export, and never describe them as real-world results.
2. **All labels are AI-generated.** They are mostly right, not always. Spot-check any label before a conclusion depends on it, and report the error rate you find.
3. **Performance covers launch to 26 Oct 2026.** A blank `stopped_date` means the ad is still live on that date.
4. **Lists inside a cell are separated by "; ".**
5. **Some creator accounts hide like counts.** They appear as 0 or a very low number. Never treat a hidden like count as a real zero.
6. **Audience data exists for 3 of 20 creators only.** Any audience claim about the other 17 is an inference and must be labelled "inferred".
7. **There is no cost data for creators** (no rate cards). Never claim cost-efficiency for a creator.

### Known issues to verify (do not assume, confirm with code)

| Item | Suspected issue |
|---|---|
| LJ-004 | Very large spend with high ROAS; about 30% of all revenue. Outlier that can drive every finding |
| LJ-089 | Very large spend, add-to-carts present, zero purchases. Likely a tracking fault |
| Very low-spend ads | Extreme ROAS or CVR from tiny samples |
| Duplicate transcripts | LJ-003/LJ-059, LJ-036/LJ-056, LJ-073/LJ-093: identical creative, different results |
| CR-20 | Audience file lists Little Joys as a past partner; audience skews male |
| CR-14 | Audience data comes from Facebook; a large share is outside India; low plays per follower |
| CR-05 | Child performer account; child-safety and compliance question |
| CR-17 | Every post sponsored; low engagement; many hidden likes |
| Sponsored vs organic | Sponsored posts generally get fewer plays than organic |
| `brands_visible` | Competing or adjacent brands appear in some creators' posts |
| Missing labels | A few ads have missing label values (for example `hook_type`) |
| Post dates | Some posts may be dated after 26 Oct 2026 |
| Thin accounts | At least one creator has fewer than 20 posts |

If you find something that is not on this list, add it to `docs/data_audit.md` and tell the user.

---

## 3. Hard rules (never break these)

1. **Never modify anything in `data/raw/`.** Write derived data to `data/processed/` and results to `outputs/`.
2. **Never fabricate.** No invented numbers, quotes, sources, post URLs, ad IDs, creator facts, or results. If something is not in the data, say it is not in the data.
3. **Every number in any report, brief or note must be produced by code in `src/lj/` and saved under `outputs/tables/`.** No hand-typed figures in prose.
4. **Never present uncertain results as proven.** Use words like "suggests", "is consistent with", "directional" unless the evidence passes the rules in section 5.
5. **Never hide a problem to make the result look cleaner.** If a finding is fragile, a pick is marginal, or a test fails, report it plainly.
6. **Never silently drop data.** Any excluded row, ad or creator must be listed with the reason in `docs/data_audit.md` or `docs/selection_logic.md`.
7. **Never fill a gap with a plausible guess.** Missing data stays missing, shown as NaN with a reason, or the analysis states the limit.
8. **Never claim a causal effect.** The ads are observational, not an experiment. Say "is associated with".
9. **Never invent health, nutrition or medical claims for children.** Creator briefs may only use claims found in `ads.claims_made` (see section 8).
10. **Do not install packages outside `requirements.txt` without asking first.**
11. **Do not run destructive commands** (`rm -rf`, force-push, history rewrites, deleting data or outputs) without explicit user approval.
12. **Do not send data or code anywhere outside this repo** (no uploading the data to third-party services, no calling external APIs) unless the user explicitly asks. Downloading the ad videos from the `video_url` links is allowed when the user asks for it, and they go in the git-ignored `outputs/videos/`.
13. **Do not push to GitHub** unless the user asks.

---

## 4. Working style

### 4.1 One phase at a time

The work follows `implementation_plan.md`. Do **only** the phase the user asks for. At the end of the phase:
- Summarise what you did in plain language (under 15 lines).
- List the files created or changed.
- Run `pytest -q` and show the real output.
- List anything you are unsure about or that the user should check by hand.
- **Stop.** Do not start the next phase.

### 4.2 Plan first for judgement-heavy work

For anything involving a decision (which metric, which threshold, which weights, which creators), write a short plan first and wait for approval. Mechanical work (loading, formatting, rendering) can proceed directly.

### 4.3 Show uncertainty and disagreement

- When you make an assumption, state it in one line, in the code docstring and in the summary.
- If you think a user instruction is a bad idea (for example, a flawed threshold), say so with the reason, then follow the user's decision.
- When asked to argue against your own result, do it properly: find what would make it false.
- If you do not know, say "I don't know" and say what would settle it.

### 4.4 Handling failures

- Show the actual error. Do not paraphrase it into something friendlier.
- Fix the cause, not the symptom. Do not loosen a test or a threshold to make something pass.
- If a fix changes a result, say how it changed.

### 4.5 Ask rather than guess when

- A choice would change which creators are picked.
- The data seems to contradict the README.
- You would need to exclude data.
- A requirement is ambiguous in a way that matters.

Ask **one** clear question at a time.

---

## 5. Analysis rules

### 5.1 Ad data cleaning

- **Exclude LJ-089** from performance conclusions as a suspected tracking fault (unless Phase 1 shows otherwise). Keep it listed in the audit.
- **Apply a minimum-spend threshold** (value in `config.yaml`, default ₹10,000). Justify it using the noise seen in the duplicate-creative pairs. Show results at several thresholds.
- **Keep LJ-004 but run every ad-level result with and without it.** If a finding depends on LJ-004, say so.
- **Deduplicate or flag duplicate creatives.** Do not count one creative twice as independent evidence.

### 5.2 Metrics

Compute and keep these separate, because they answer different questions:

| Stage | Metric | Formula |
|---|---|---|
| Attention | Hook rate | 3-second views / impressions |
| Attention | Hold rate | ThruPlays / 3-second views |
| Interest | CTR | link clicks / impressions |
| Intent | Add-to-cart rate | add-to-carts / link clicks |
| Sales | CVR | purchases / link clicks |
| Sales | ROAS | revenue / spend |
| Sales | CPA | spend / purchases |
| Basket | AOV | revenue / purchases |

**Aggregate by group using totals (spend-weighted)**, for example group ROAS = sum of revenue / sum of spend. Never average ad-level ROAS across ads, because that weights a ₹4,000 ad the same as a ₹6,00,000 ad.

### 5.3 Uncertainty

- Report a **bootstrap 95% interval** (resample ads, seed from `config.yaml`, default 5,000 iterations) with every group-level metric.
- Charts must show intervals, not bare bars.
- Respect group size. Do not report a pattern for fewer than the minimum number of ads set in `config.yaml` (default 8).
- With about 100 ads and many labels, some patterns appear by chance. **Pre-register** the features you will test in `docs/ad_findings.md` before looking at results, and apply Benjamini-Hochberg correction to any significance tests, or label results as directional.

### 5.4 When a finding counts

A pattern is kept as a finding only if **all** are true:
1. Same direction on at least two metrics (for example ROAS and CVR).
2. It survives removing LJ-004.
3. It meets the minimum group size.
4. It is not fully explained by a confound such as product form or launch period (check).

Otherwise it goes in the "could not conclude" list. That list is part of the deliverable.

### 5.5 Creator analysis

- Use **medians**, not means, for plays and engagement (viral posts distort means).
- Compute **organic and sponsored performance separately**. Flag creators with fewer than 3 posts in either group instead of computing a ratio.
- **Handle hidden likes.** Where likes are hidden, compute engagement from comments and reshares only, and flag the creator.
- **Label audience fit as "known" or "inferred"** every time.
- Map `brands_visible` to categories with an explicit dictionary in `config.yaml`. List any brand you cannot categorise instead of guessing.
- **Flag, do not decide**, on child-safety and compliance questions. A human decides.

### 5.6 Selection

1. **Hard gates first** (a creator is removed with a stated reason): already a partner, known audience mismatch, direct competitor conflict, no child/family/food content, too little evidence. Each gate returns pass or fail plus a plain-English reason.
2. **Then score** those who pass, with weights and thresholds in `config.yaml` (never hard-coded in functions).
3. **Attach a confidence label** (high / medium / low) to every creator. Base it on posts available, hidden metrics, audience data known or inferred, and how many findings the fit score rests on.
4. **Stress test the result** (Phase 5): weight perturbation, threshold variants, leave-one-component-out. Label each pick robust, likely or marginal, and name a backup for each marginal pick.
5. The final answer is **5 creators plus backups**, not a single unexplained list.

---

## 6. Code standards

- **Python 3.11+.** Use pandas and numpy; scipy and statsmodels for statistics; matplotlib for charts.
- **Structure:** package code in `src/lj/`; tests in `tests/`; thresholds, weights and dictionaries in `config.yaml`; exploration only in `notebooks/`.
- **Style:** type hints, short functions, docstrings stating inputs, outputs and assumptions, clear variable names. No clever one-liners that hide logic.
- **Reproducibility:** one seed (`seed` in `config.yaml`) used everywhere. Running the pipeline twice must give identical outputs.
- **No hard-coded paths or thresholds.** Use `src/lj/config.py` to read `config.yaml`.
- **Entry points:** each module runs with `python -m lj.<module>`, and `python -m lj.run_all` runs everything in order and stops on the first failure.
- **Outputs:** tables to `outputs/tables/*.csv`, charts to `outputs/figures/*.png`, briefs to `outputs/briefs/*.md`, report to `outputs/report.html` and `outputs/report.md`.
- **Dependencies:** only what is in `requirements.txt`.
- **No dead code, no commented-out experiments** in committed files.
- **Logging:** print a one-line summary per stage (rows in, rows out, rows excluded and why).

### Tests

- Every module has tests in `tests/test_<module>.py`.
- Use tiny hand-made DataFrames where the correct answer is known (for example, spend-weighted ROAS on three fake ads).
- Required tests include: LJ-089 flagged as a zero-purchase high-spend ad; LJ-004 flagged as a concentration outlier; CR-20 fails the already-a-partner gate; a 100%-sponsored creator receives a risk penalty; identical results on two runs with the same seed; no brief contains a claim outside the whitelist; no number in the report is missing from `outputs/tables/`.
- Run `pytest -q` before saying a phase is done. Never weaken or delete a test to get a pass.

---

## 7. Creator briefs: what each creator should say

Each brief in `outputs/briefs/<creator_id>.md` must contain:

1. Creator and why them (two lines with key numbers).
2. The angle, tied to a surviving finding and the ad IDs that support it.
3. Format and language matched to the creator's habits, with evidence from their own posts (post URLs).
4. Three hook lines in the creator's own language and voice, in the style of winning hooks (cite the ad IDs).
5. A short beat outline (hook, demo, proof, call to action), including the child's role if relevant.
6. A proof element, using only whitelisted claims.
7. Do and don't, drawn from `what_feels_native` and `what_would_feel_foreign`.
8. Risks and compliance flags.
9. Confidence level and what is unknown about this creator.

Rules:
- Every angle, format and hook style must cite the **ad IDs** and **creator post URLs** it comes from. If you cannot cite it, do not write it.
- Hooks must sound like the creator, not like generic ad copy. Check against their captions, transcripts and catchphrases.
- Write hooks in the language the creator actually uses. If you are not confident in a language, flag the line for native-speaker review.
- Do not copy an existing ad's text word for word; use its structure and driver.

---

## 8. Claims and compliance

- Build `docs/claims_whitelist.md` from the unique entries in `ads.claims_made`, with the ads that make each claim.
- Briefs may use **only whitelisted claims**.
- Mark claims needing human compliance review before use (anything about protein quantities, immunity, growth, brain development, or medical outcomes).
- Never suggest claims that a child will be healthier, taller, smarter or similar unless it is whitelisted, and even then flag it.
- Remind the brand that advertising to and with children is regulated and that wording should be checked against applicable advertising and food-labelling guidance (for example from ASCI and FSSAI). Say that this is not legal advice.
- Child-safety flags for creator accounts featuring children: consent, appearance of the child, age, and the child's role in the ad. These are flags for a human decision.
- Recommend that every paid post carries a clear partnership disclosure.

---

## 9. Report and writing rules

- **Audience:** a marketing manager. Plain language. Define any statistic in one phrase the first time (for example, "a range that shows how uncertain this is").
- **Answer first.** The first screen states the 5 creators, the one-line reason, the message, the confidence and the main risk for each.
- **Required sections:** the answer; what the brand's own ads tell us; why these 5 and not the others (including exclusions); how sure we are; what each creator should say; what the data cannot tell us; what to do before signing anyone; appendix.
- **Always include "What this data cannot tell you":** no rate cards or costs; audience data for 3 of 20 only; one account over a limited period; AI-made labels with a measured error rate; Instagram performance does not guarantee ad performance; sponsored posts usually reach fewer people.
- **No jargon without explanation.** No unexplained abbreviations. No hype words ("game-changing", "viral-ready", "guaranteed").
- **No overstated certainty.** Prefer "we recommend" with the evidence next to it.
- **Charts:** plain titles, labelled axes, intervals, colour-blind-safe palette, no decoration.
- **Numbers:** use rupees (₹) with Indian digit grouping where helpful, and state the denominator (for example "ROAS 2.1x on ₹3.2L spend").

---

## 10. Git and repository hygiene

- Commit at the end of each phase with a clear message (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- Keep commits focused; do not mix unrelated changes.
- Never commit the virtual environment, caches, downloaded videos or large binaries (see `.gitignore`).
- Never commit secrets or credentials.
- Do not rewrite history. Do not force-push.
- `git diff data/raw` must always be empty after the first commit.
- The repository must work from a fresh clone: `pip install -r requirements.txt`, `pip install -e .`, `python -m lj.run_all`, `pytest -q`.

---

## 11. AI-use transparency

The submission is partly judged on how AI was used. Help make that visible:

- When you make a significant decision, explain the options and the reason in one short paragraph the user can paste into `docs/ai_usage/prompt_log.md`.
- When you notice you were wrong, or the user corrects you, say so clearly so it can be logged in `docs/ai_usage/corrections.md` (what was wrong, how it was caught, what changed).
- Suggest ways the user can independently check your work. Do not ask them to simply trust you.
- Do not describe your own work as better, more rigorous or more complete than it is.
- At the end of each phase, list the top one or two things **most likely to be wrong**.

---

## 12. Definition of done (per phase)

A phase is done only when all are true:

- [ ] Code runs from the repo root with the documented command.
- [ ] `pytest -q` passes, with real output shown.
- [ ] Outputs are saved in `outputs/` or `data/processed/`, and `data/raw/` is unchanged.
- [ ] Assumptions, exclusions and limits are written down in `docs/`.
- [ ] Every number can be traced to a table.
- [ ] You have listed what the user should hand-check.
- [ ] You have stopped and are waiting for the next instruction.

---

## 13. Quick reference

```text
Repo root:      little-joys-creators/
Raw data:       data/raw/            (read-only)
Derived data:   data/processed/
Code:           src/lj/
Tests:          tests/
Config:         config.yaml          (seed, thresholds, weights, brand dictionary)
Tables:         outputs/tables/
Figures:        outputs/figures/
Briefs:         outputs/briefs/
Report:         outputs/report.html, outputs/report.md
Docs:           docs/                (data_audit, ad_findings, creator_profiles,
                                      selection_logic, robustness, claims_whitelist, note)
AI evidence:    docs/ai_usage/       (prompt_log.md, corrections.md, session artifacts)

Run everything: python -m lj.run_all
Run tests:      pytest -q
```
