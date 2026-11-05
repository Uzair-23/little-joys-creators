# Creator Selection Logic & Methodology (Phase 4)

**Document Purpose:** Explains the empirical qualification gates, component score formulas, weighting rationale, and confidence scheme used to filter and rank creators for Little Joys kids' nutrition campaigns.

---

## 1. Hard Disqualification Gates (`src/lj/gates.py`)

A creator must pass all five hard gates to be scored. Disqualification is absolute and binary; thresholds are defined in `config.yaml` to prevent ad-hoc filtering.

| Gate | Criterion & Threshold | Rationale | Disqualified Creators in Dataset |
|---|---|---|---|
| **`already_partner`** | Fails if `already_partner_brand` (`"Little Joys"`) appears in the creator's audience export (`brands_in_past_year`) or on any sponsored post in `creator_posts.csv` (`brands_visible`). | The brand brief requires recruiting **new** creators. Re-contracting past creators violates the prospecting objective and biases reach metrics toward past brand spend. | **CR-09** (`doc_mama_and_babies`: sponsored post with Little Joys)<br>**CR-20** (`storiesbyvihaa`: audience export lists Little Joys) |
| **`audience_mismatch`** | If audience data is **known**, fails if `women_share < 50%` OR `india_share < 80%`. *(Bypassed if audience is unexported/inferred)*. | Little Joys kids' nutrition products are purchased predominantly by mothers and caregivers residing in India. Accounts skewed toward male followers or non-Indian traffic represent severe ad-spend leakage. | **CR-14** (`parentingtips_surat`: India share is 64.4% < 80%)<br>**CR-20** (`storiesbyvihaa`: women share is 29.9% < 50%) |
| **`direct_competitor`** | Fails if a direct competitor brand from `brand_categories.competitor_kids_nutrition` (`["Gritzo"]`) appears on any sponsored post. | Advertising with creators who actively endorse direct competitors creates immediate brand confusion and trust dilution among parents. | **CR-05** (`sia_3vedi`)<br>**CR-10** (`couple_adishiv`)<br>**CR-11** (`raja_choudhary04`) |
| **`no_family_content`** | Fails if the combined share of posts featuring children on camera OR family/food/nutrition topics is $< 15\%$. | Creators whose content is unrelated to family life, parenting, or children cannot authentically integrate a pediatric nutritional product. | **CR-06** (`thatkushalmistry`: observational comedy with 0% kids and 0% food/nutrition) |
| **`too_little_evidence`** | Fails if `posts_available < 8`. | Statistical metrics (medians, engagement rates, language share) cannot be reliably estimated from sparse posting histories. | *None* (all creators have $\ge 11$ posts) |

---

## 2. Non-Disqualifying Soft Flags

Soft flags are tracked and displayed alongside every creator for transparency. They inform human review during briefing but do not automatically disqualify:

1. **`child_performer_flag`:** Flagged when persona describes a child performer (e.g. CR-05). Raises potential child labor and compliance sensitivities.
2. **`sponsored_saturation`:** Flagged when `sponsored_share > 70%` (e.g. CR-09, CR-17, CR-19). Indicates commercial fatigue where followers may tune out brand recommendations.
3. **`hidden_metrics`:** Flagged when `likes_hidden_share > 25%` (e.g. CR-17). Triggers recalculation to `comments_reshares_only`.
4. **`inactive`:** Flagged when `days_since_last_post > 45` days.
5. **`medical_authority_persona`:** Flagged when the creator is a doctor or pediatrician (e.g. CR-01, CR-03, CR-16). Requires stricter compliance around medical endorsement standards.

---

## 3. Score Components & Weighting (`src/lj/scoring.py`)

Every passing creator is evaluated on 5 normalized components $[0, 1]$, weighted by pre-registered weights from `config.yaml`:

$$\text{Total Score} = 0.30 \times \text{Fit} + 0.25 \times \text{Reach} + 0.20 \times \text{Engagement} + 0.15 \times \text{Audience} + 0.10 \times \text{Risk}$$

### Component 1: Creative Fit (Weight: 0.30)
* **Definition:** Measures how closely the creator's organic content aligns with empirical ad findings that survived Phase 2 validation.
* **Findings Used:**
  - `F01 (Supported)`: `language == Hindi` (Effect weight: 0.1049)
  - `F05 (Supported)`: `child_in_first_3s == yes` (Effect weight: 0.0809, proxied by `children_on_camera == yes`)
  - `F02 (Directional)`: `hook_type == problem_statement` (Effect weight: 0.0360, keyword match on `hook_style`)
  - `F07 (Directional)`: `main_benefit == fussy_eating` (Effect weight: 0.0512, keyword match on `topic`)
  - `F08 (Directional)`: `production == ugc` (Effect weight: 0.0137, quality $\le 3$ and organic format)
* **Formula:** $\text{creative\_fit} = \frac{\sum_f \text{effect}_f \times \text{match\_share}_f}{\sum_f \text{effect}_f}$. Unmapped findings (e.g. F06 `brand_first_said`) are excluded.

### Component 2: Reach Quality (Weight: 0.25)
* **Definition:** Evaluates creator delivery on sponsored campaigns, adjusting for organic baseline.
* **Sponsored Adjustment:** If the creator has $\ge 3$ sponsored posts, uses `sponsored_median_plays / followers`. If $< 3$ sponsored posts, uses $(\text{organic\_median\_plays} \times \text{pooled\_ratio}) / \text{followers}$, where `pooled_ratio` is the empirical median ratio (0.5606).
* **Percentile Rank:** Computes percentile rank across passing creators, capped at the 95th percentile (`reach_cap_percentile`) to prevent single viral outliers from dominating.

### Component 3: Engagement Quality (Weight: 0.20)
* **Definition:** Measures active audience interaction rate relative to plays.
* **Formula:** Percentile rank of `engagement_rate_median`. Where likes are hidden, engagement rate reflects `comments_reshares_only`, and an additional penalty is applied: $\text{engagement\_quality} \times (1 - 0.5 \times \text{likes\_hidden\_share})$.

### Component 4: Audience Fit (Weight: 0.15)
* **Definition:** Evaluates alignment with core target demographic (Indian mothers aged 25–40).
* **Known Audiences (CR-15):** Average of normalized women share score ($\min(1, \text{women\_share} / 0.80)$), India share score ($\min(1, \text{india\_share} / 0.90)$), and core parenting age score ($\min(1, \text{age\_25\_44} / 0.70)$).
* **Unknown / Inferred Audiences (12 passing creators):** Receives the neutral score `unknown_audience_score` (**0.50**) from `config.yaml`. They are neither penalized nor rewarded; instead, their uncertainty is reflected in a lower confidence score.

### Component 5: Commercial Risk (Weight: 0.10)
* **Definition:** Inverted penalty score ($1 - \text{penalties}$) measuring commercial fatigue and brand conflicts:
  - Adjacent brand exposure: $-0.10$ per brand from `adjacent_food_snacks` and `adjacent_wellness` (capped at $-0.30$).
  - Sponsored saturation: $-0.30 \times \frac{\text{sponsored\_share} - 0.70}{0.30}$ if sponsored share $> 70\%$.
  - Inactivity: $-0.20$ if days since last post $> 45$.
  - Child performer flag: $-0.20$ if persona indicates child performer.

---

## 4. Confidence Scoring Scheme (0 to 5 Points)

Each creator receives a confidence rating based on data completeness:
- $+1$: Post history $\ge 12$ posts (`posts_available >= min_posts_for_confidence`)
- $+1$: Likes visible (`likes_hidden_share <= 0.25`)
- $+1$: Audience export known from brand account (`audience_known == True`)
- $+1$: $\ge 2$ Phase 2 empirical findings matched in organic content
- $+1$: Transcripts available for $\ge 12$ posts

**Confidence Tiers:**
- **High (4–5 points):** Comprehensive demographic, engagement, and creative data available.
- **Medium (2–3 points):** Strong post and transcript history, but audience demographics must be inferred.
- **Low (0–1 points):** Multiple data gaps or severe metric masking.

