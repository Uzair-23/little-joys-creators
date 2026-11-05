"""Creator scoring and ranking pipeline module (Phase 4).

Scores creators passing hard gates across 5 normalized components [0, 1]:
1. creative_fit (weight 0.30): weighted match to surviving Phase 2 findings via label_map.yaml.
2. reach_quality (weight 0.25): percentile rank of sponsored-adjusted plays_per_follower capped at 0.95.
3. engagement_quality (weight 0.20): percentile rank of engagement_rate_median discounted for hidden likes.
4. audience_fit (weight 0.15): known audience demographic score, or 0.50 neutral when unknown.
5. commercial_risk (weight 0.10): 1 - sum(penalties) for adjacent brands, sponsored saturation, inactivity, child performer.

Confidence labeling:
- 5 points scheme: posts >= 12 (+1), likes visible (+1), audience known (+1), >= 2 findings (+1), transcripts >= 12 (+1).
- 4-5: high, 2-3: medium, 0-1: low.
"""
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import yaml

from lj.config import CONFIG, PROCESSED_DIR, TABLES_DIR
from lj.gates import evaluate_gates
from lj.load import load_posts
from lj.stats import percentile_rank

# Keywords for heuristic matching from label_map.yaml
PROBLEM_HOOK_PATTERN = re.compile(
    r"\b(problem|challenge|struggle|mistake|myth|concern|worry|tired|tantrum|issue)\b",
    re.IGNORECASE,
)
FUSSY_EATING_PATTERN = re.compile(
    r"\b(fussy|picky|refusing food|mealtime tantrum|eating habit|weight gain|not eating|eating)\b",
    re.IGNORECASE,
)


def compute_creative_fit_for_creator(
    creator_id: str,
    creator_posts: pd.DataFrame,
    ad_findings_df: pd.DataFrame,
    label_map: Dict[str, Any],
) -> Tuple[float, List[str], int]:
    """Compute weighted match against surviving Phase 2 findings.
    
    Returns (creative_fit_score, findings_used_list, count_findings_matched).
    """
    n_posts = len(creator_posts)
    if n_posts == 0:
        return 0.0, [], 0

    weights = []
    match_shares = []
    findings_used = []
    matched_findings_count = 0

    # 1. Finding F01: language == Hindi (Supported, effect = 0.1049)
    f01 = ad_findings_df[ad_findings_df["finding_id"] == "F01"]
    if len(f01) > 0:
        w = float(f01.iloc[0]["effect"])
        # Pure Hindi matching
        share_hindi = float((creator_posts["language"].fillna("").str.strip().str.lower() == "hindi").mean())
        weights.append(w)
        match_shares.append(share_hindi)
        findings_used.append("F01(Hindi)")
        if share_hindi > 0.10:
            matched_findings_count += 1

    # 2. Finding F05: child_in_first_3s == yes (Supported, effect = 0.0809)
    f05 = ad_findings_df[ad_findings_df["finding_id"] == "F05"]
    if len(f05) > 0:
        w = float(f05.iloc[0]["effect"])
        # Proxy via children_on_camera == yes
        share_kids = float((creator_posts["children_on_camera"].fillna("").str.strip().str.lower() == "yes").mean())
        weights.append(w)
        match_shares.append(share_kids)
        findings_used.append("F05(child_in_first_3s_proxy)")
        if share_kids > 0.10:
            matched_findings_count += 1

    # 3. Finding F02: hook_type == problem_statement (Directional, effect = 0.0360)
    f02 = ad_findings_df[ad_findings_df["finding_id"] == "F02"]
    if len(f02) > 0:
        w = float(f02.iloc[0]["effect"])
        # Keyword match on hook_style
        problem_matches = creator_posts["hook_style"].fillna("").apply(lambda s: bool(PROBLEM_HOOK_PATTERN.search(s)))
        share_problem = float(problem_matches.mean())
        weights.append(w)
        match_shares.append(share_problem)
        findings_used.append("F02(problem_statement)")
        if share_problem > 0.10:
            matched_findings_count += 1

    # 4. Finding F07: main_benefit == fussy_eating (Directional, effect = 0.0512)
    f07 = ad_findings_df[ad_findings_df["finding_id"] == "F07"]
    if len(f07) > 0:
        w = float(f07.iloc[0]["effect"])
        # Keyword match on topic
        fussy_matches = creator_posts["topic"].fillna("").apply(lambda s: bool(FUSSY_EATING_PATTERN.search(s)))
        share_fussy = float(fussy_matches.mean())
        weights.append(w)
        match_shares.append(share_fussy)
        findings_used.append("F07(fussy_eating)")
        if share_fussy > 0.10:
            matched_findings_count += 1

    # 5. Finding F08: production == ugc (Directional, effect = 0.0137)
    f08 = ad_findings_df[ad_findings_df["finding_id"] == "F08"]
    if len(f08) > 0:
        w = float(f08.iloc[0]["effect"])
        # production_quality_1to5 <= 3 and casual formats
        ugc_mask = (creator_posts["production_quality_1to5"].fillna(3) <= 3) & (
            creator_posts["content_form"].fillna("").str.lower().isin(
                ["piece_to_camera", "demo_or_haul", "still_or_carousel"]
            )
        )
        share_ugc = float(ugc_mask.mean())
        weights.append(w)
        match_shares.append(share_ugc)
        findings_used.append("F08(ugc)")
        if share_ugc > 0.10:
            matched_findings_count += 1

    total_weight = sum(weights)
    if total_weight > 0:
        weighted_score = sum(w * s for w, s in zip(weights, match_shares)) / total_weight
    else:
        weighted_score = 0.0

    return float(np.clip(weighted_score, 0.0, 1.0)), findings_used, matched_findings_count


def compute_audience_fit_score(
    audience_known: bool,
    women_share: Optional[float],
    india_share: Optional[float],
    age_split_str: Optional[str],
    config: Dict[str, Any] = CONFIG,
) -> float:
    """Compute normalized audience fit score in [0, 1]."""
    if not audience_known:
        return float(config.get("scoring", {}).get("unknown_audience_score", 0.50))

    # Benchmark targets: women >= 80% (1.0), India >= 90% (1.0)
    w_score = min(1.0, (float(women_share) if pd.notna(women_share) else 0.0) / 0.80)
    ind_score = min(1.0, (float(india_share) if pd.notna(india_share) else 0.0) / 0.90)

    # Core parenting age share (25-34 + 35-44)
    age_score = 0.80  # Default reasonable score if age split present
    if pd.notna(age_split_str):
        # Extract percentage for 25-34
        m25 = re.search(r"25-34\s+([\d\.]+)%", str(age_split_str))
        m35 = re.search(r"35-44\s+([\d\.]+)%", str(age_split_str))
        p25 = float(m25.group(1)) if m25 else 0.0
        p35 = float(m35.group(1)) if m35 else 0.0
        core_parent_pct = (p25 + p35) / 100.0
        age_score = min(1.0, core_parent_pct / 0.70)

    return float(np.clip((w_score + ind_score + age_score) / 3.0, 0.0, 1.0))


def compute_commercial_risk_score(
    row: pd.Series,
    config: Dict[str, Any] = CONFIG,
) -> Tuple[float, List[str]]:
    """Compute commercial risk component (1 - penalties) in [0, 1]."""
    cr_cfg = config.get("creators", {})
    spon_flag = float(cr_cfg.get("sponsored_share_flag", 0.70))
    inactive_days = int(cr_cfg.get("inactive_days_flag", 45))

    penalties = 0.0
    reasons = []

    # 1. Adjacent brand exposure: 0.1 each, capped at 0.3
    adj_str = str(row.get("adjacent_brands", "none"))
    if adj_str.strip().lower() != "none" and adj_str.strip():
        adj_count = len([x for x in adj_str.split(";") if x.strip()])
        p_adj = min(0.3, 0.1 * adj_count)
        penalties += p_adj
        reasons.append(f"adjacent_brands_penalty ({adj_count} brands: -{p_adj:.2f})")

    # 2. Sponsored saturation: above 0.70 scaled up to 0.3
    spon_share = float(row.get("sponsored_share", 0.0))
    if spon_share > spon_flag:
        p_spon = min(0.3, (spon_share - spon_flag) / (1.0 - spon_flag) * 0.3)
        penalties += p_spon
        reasons.append(f"sponsored_saturation_penalty ({spon_share:.1%}: -{p_spon:.2f})")

    # 3. Inactivity: 0.2 if days_since_last_post > 45
    days_last = row.get("days_since_last_post")
    if pd.notna(days_last) and int(days_last) > inactive_days:
        penalties += 0.2
        reasons.append(f"inactivity_penalty ({int(days_last)}d: -0.20)")

    # 4. Child performer: 0.2
    if bool(row.get("child_performer_flag", False)):
        penalties += 0.2
        reasons.append("child_performer_penalty (-0.20)")

    total_penalty = float(np.clip(penalties, 0.0, 1.0))
    risk_score = 1.0 - total_penalty
    return float(np.clip(risk_score, 0.0, 1.0)), reasons


def score_and_rank_creators(
    features_df: Optional[pd.DataFrame] = None,
    gates_df: Optional[pd.DataFrame] = None,
    posts_df: Optional[pd.DataFrame] = None,
    ad_findings_df: Optional[pd.DataFrame] = None,
    label_map: Optional[Dict[str, Any]] = None,
    config: Dict[str, Any] = CONFIG,
    output_path: Optional[Path | str] = None,
) -> pd.DataFrame:
    """Execute creator scoring and produce creator_ranking.csv."""
    if features_df is None:
        feat_path = PROCESSED_DIR / "creator_features.csv"
        features_df = pd.read_csv(feat_path)
    if gates_df is None:
        gates_df = evaluate_gates(features_df, config=config)
    if posts_df is None:
        posts_df = load_posts()
    if ad_findings_df is None:
        ad_findings_df = pd.read_csv(TABLES_DIR / "ad_findings.csv")
    if label_map is None:
        label_map_path = Path("label_map.yaml")
        if label_map_path.exists():
            with open(label_map_path, "r", encoding="utf-8") as f:
                label_map = yaml.safe_load(f)
        else:
            label_map = {}

    out_file = Path(output_path) if output_path is not None else TABLES_DIR / "creator_ranking.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    weights_cfg = config.get("scoring", {}).get("weights", {
        "creative_fit": 0.30,
        "reach_quality": 0.25,
        "engagement_quality": 0.20,
        "audience_fit": 0.15,
        "commercial_risk": 0.10,
    })
    w_fit = float(weights_cfg["creative_fit"])
    w_reach = float(weights_cfg["reach_quality"])
    w_eng = float(weights_cfg["engagement_quality"])
    w_aud = float(weights_cfg["audience_fit"])
    w_risk = float(weights_cfg["commercial_risk"])

    reach_cap = float(config.get("creators", {}).get("reach_cap_percentile", 0.95))
    min_posts_conf = int(config.get("creators", {}).get("min_posts_for_confidence", 12))
    hidden_flag = float(config.get("creators", {}).get("hidden_likes_share_flag", 0.25))

    # Pooled median sponsored-to-organic ratio for reach adjustment
    valid_ratios = features_df["sponsored_organic_ratio"].dropna()
    pooled_ratio = float(valid_ratios.median()) if len(valid_ratios) > 0 else 0.5606

    # Merged dataset with gate status
    merged = pd.merge(features_df, gates_df[["creator_id", "passed_all", "gate_reasons", "soft_flags"]], on="creator_id")

    # Filter passing creators for relative scoring components
    passing_creators = merged[merged["passed_all"] == True].copy()

    # Precompute sponsored-adjusted plays_per_follower for passing creators
    adj_reach_series = []
    for _, r in passing_creators.iterrows():
        folls = float(r["followers"])
        if folls <= 0:
            adj_reach_series.append(0.0)
            continue

        # If sponsored_median_plays available with enough posts
        if pd.notna(r["sponsored_median_plays"]) and r["sponsored_median_plays"] > 0 and pd.notna(r["sponsored_organic_ratio"]):
            adj_plays = float(r["sponsored_median_plays"])
        else:
            org_plays = float(r["organic_median_plays"]) if pd.notna(r["organic_median_plays"]) else float(r["median_plays"])
            adj_plays = org_plays * pooled_ratio
        
        adj_reach_series.append(adj_plays / folls)

    passing_creators["adj_plays_per_follower"] = adj_reach_series

    # Percentile ranks across passing creators
    if len(passing_creators) > 0:
        reach_pcts = percentile_rank(passing_creators["adj_plays_per_follower"], ascending=True)
        # Cap at reach_cap_percentile and scale to [0, 1]
        passing_creators["reach_quality"] = np.minimum(reach_pcts, reach_cap) / reach_cap

        eng_pcts = percentile_rank(passing_creators["engagement_rate_median"].fillna(0.0), ascending=True)
        # Hidden likes penalty on engagement quality
        hidden_penalties = passing_creators["likes_hidden_share"].apply(
            lambda h: (1.0 - 0.5 * h) if h > hidden_flag else 1.0
        )
        passing_creators["engagement_quality"] = eng_pcts * hidden_penalties
    else:
        passing_creators["reach_quality"] = []
        passing_creators["engagement_quality"] = []

    # Map scores back to full dataframe
    scored_records = []

    for _, r in merged.iterrows():
        cid = str(r["creator_id"])
        handle = str(r["handle"])
        passed = bool(r["passed_all"])
        gate_reasons = str(r["gate_reasons"])
        soft_flags = str(r["soft_flags"])

        if not passed:
            scored_records.append({
                "creator_id": cid,
                "handle": handle,
                "passed_gates": False,
                "gate_reasons": gate_reasons,
                "creative_fit": np.nan,
                "reach_quality": np.nan,
                "engagement_quality": np.nan,
                "audience_fit": np.nan,
                "commercial_risk": np.nan,
                "total": np.nan,
                "rank": np.nan,
                "confidence": "disqualified",
                "confidence_reasons": "failed_hard_gates",
                "findings_used": "none",
                "soft_flags": soft_flags,
            })
            continue

        c_pass = passing_creators[passing_creators["creator_id"] == cid].iloc[0]

        # 1. Creative fit
        c_posts = posts_df[posts_df["creator_id"] == cid].copy()
        fit_score, findings_list, findings_matched_cnt = compute_creative_fit_for_creator(
            cid, c_posts, ad_findings_df, label_map
        )
        findings_used_str = "; ".join(findings_list)

        # 2. Reach quality
        reach_q = float(c_pass["reach_quality"])

        # 3. Engagement quality
        eng_q = float(c_pass["engagement_quality"])

        # 4. Audience fit
        aud_fit = compute_audience_fit_score(
            bool(r["audience_known"]),
            r.get("women_share"),
            r.get("india_share"),
            r.get("age_split"),
            config,
        )

        # 5. Commercial risk
        comm_risk, risk_reasons = compute_commercial_risk_score(r, config)

        # Total score
        total_score = (
            w_fit * fit_score +
            w_reach * reach_q +
            w_eng * eng_q +
            w_aud * aud_fit +
            w_risk * comm_risk
        )

        # Confidence points (0 to 5)
        conf_points = 0
        conf_notes = []
        if int(r["posts_available"]) >= min_posts_conf:
            conf_points += 1
            conf_notes.append("posts>=12")
        if float(r["likes_hidden_share"]) <= hidden_flag:
            conf_points += 1
            conf_notes.append("likes_visible")
        if bool(r["audience_known"]):
            conf_points += 1
            conf_notes.append("audience_known")
        if findings_matched_cnt >= 2:
            conf_points += 1
            conf_notes.append(f"{findings_matched_cnt}_findings_matched")
        if int(r["transcripts_available"]) >= min_posts_conf:
            conf_points += 1
            conf_notes.append("transcripts>=12")

        if conf_points >= 4:
            conf_label = "high"
        elif conf_points >= 2:
            conf_label = "medium"
        else:
            conf_label = "low"

        conf_reasons_str = f"{conf_points}/5 points ({', '.join(conf_notes)})"

        scored_records.append({
            "creator_id": cid,
            "handle": handle,
            "passed_gates": True,
            "gate_reasons": "all_gates_passed",
            "creative_fit": round(fit_score, 4),
            "reach_quality": round(reach_q, 4),
            "engagement_quality": round(eng_q, 4),
            "audience_fit": round(aud_fit, 4),
            "commercial_risk": round(comm_risk, 4),
            "total": round(total_score, 4),
            "rank": np.nan,  # Assigned after sorting
            "confidence": conf_label,
            "confidence_reasons": conf_reasons_str,
            "findings_used": findings_used_str,
            "soft_flags": soft_flags,
        })

    df_scored = pd.DataFrame(scored_records)

    # Rank passing creators by total score descending
    pass_mask = df_scored["passed_gates"] == True
    ranked_indices = df_scored[pass_mask].sort_values(by="total", ascending=False).index
    df_scored.loc[ranked_indices, "rank"] = np.arange(1, len(ranked_indices) + 1).astype(int)

    # Sort final table: passing creators first by rank, then disqualified
    df_final = pd.concat([
        df_scored[pass_mask].sort_values(by="rank"),
        df_scored[~pass_mask],
    ], ignore_index=True)

    df_final.to_csv(out_file, index=False)
    return df_final


def main() -> None:
    """CLI runner for scoring pipeline."""
    print("=== Running Creator Scoring & Ranking Pipeline (Phase 4) ===")
    df_ranking = score_and_rank_creators()
    print(f"Scored table saved: {len(df_ranking)} creators to outputs/tables/creator_ranking.csv")
    print("\nTop Ranked Creators (Passing Hard Gates):")
    cols_preview = ["rank", "creator_id", "handle", "total", "creative_fit", "reach_quality", "engagement_quality", "audience_fit", "commercial_risk", "confidence"]
    print(df_ranking[df_ranking["passed_gates"] == True][cols_preview].to_string(index=False))


if __name__ == "__main__":
    main()

