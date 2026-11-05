"""Ad modeling and creative pattern evaluation module.

Implements Phase 2 methodology (PRD.md sections 8.2 and 9):
1. Builds primary analysis set (excluding LJ-089 tracking fault and ads with spend < min_spend_inr).
2. Quantifies baseline noise from duplicate creative pairs (used as context only).
3. Evaluates pre-registered features with spend-weighted aggregations and bootstrap intervals on the difference.
4. Strictly enforces the LJ-004 50% rule: effect without LJ-004 must retain >= 50% of baseline effect and same sign.
5. Treats product_form as a context variable (stratified by launch period only).
6. Computes leave-one-out influence for top 5 spend ads and pairwise Jaccard pattern overlap.
7. Generates:
   - data/processed/ads_analysis_set.csv
   - outputs/tables/ad_noise_from_duplicates.csv
   - outputs/tables/ad_lj004_traits.csv
   - outputs/tables/ad_leave_one_out_influence.csv
   - outputs/tables/ad_pattern_overlap.csv
   - outputs/tables/ad_product_form_context.csv
   - outputs/tables/ad_group_metrics.csv
   - outputs/tables/ad_findings.csv
   - outputs/tables/ad_not_concluded.csv
   - outputs/figures/ad_findings_forest.png
   - outputs/figures/funnel_by_pattern.png
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from lj.config import CONFIG, FIGURES_DIR, PROCESSED_DIR, SEED, TABLES_DIR
from lj.load import load_ads
from lj.metrics import compute_ad_metrics
from lj.stats import bh_correct, bootstrap_ci, weighted_ratio

# Empirical label error rates from Phase 1 spot-check (audit_labels_sample.csv)
LABEL_ERROR_RATES: Dict[str, float] = {
    "language": 0.0000,
    "hook_type": 0.1667,
    "child_on_screen": 0.0833,
    "creator_type": 0.0000,
    "ad_format": 0.0833,
}


def build_analysis_set(
    ads_df: pd.DataFrame,
    min_spend: Optional[float] = None,
    config: Dict[str, Any] = CONFIG,
    return_exclusions: bool = False,
) -> Union[pd.DataFrame, Tuple[pd.DataFrame, pd.DataFrame]]:
    """Build analysis dataset by excluding tracking faults and sub-threshold spend ads."""
    ads_cfg = config.get("ads", {})
    fault_ads = ads_cfg.get("suspected_tracking_fault", ["LJ-089"])
    thresh = min_spend if min_spend is not None else float(ads_cfg.get("min_spend_inr", 10000))
    spend_col = "spend_inr" if "spend_inr" in ads_df.columns else "spend"

    mask = (~ads_df["ad_id"].isin(fault_ads)) & (ads_df[spend_col] >= thresh)
    analysis_df = ads_df[mask].copy().reset_index(drop=True)
    if return_exclusions:
        excl_df = ads_df[~mask].copy().reset_index(drop=True)
        return analysis_df, excl_df
    return analysis_df


def calibrate_duplicate_noise(
    ads_df: pd.DataFrame,
    output_path: Optional[Path | str] = None,
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Quantify observational noise by measuring variation across identical creative pairs (context only)."""
    if "roas" not in ads_df.columns:
        ads_df = compute_ad_metrics(ads_df)

    out_file = Path(output_path) if output_path is not None else TABLES_DIR / "ad_noise_from_duplicates.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    pairs = [
        ("LJ-003", "LJ-059"),
        ("LJ-036", "LJ-056"),
        ("LJ-073", "LJ-093"),
    ]

    records = []
    for id1, id2 in pairs:
        r1 = ads_df[ads_df["ad_id"] == id1].iloc[0]
        r2 = ads_df[ads_df["ad_id"] == id2].iloc[0]

        roas_diff_abs = abs(float(r1["roas"]) - float(r2["roas"]))
        roas_mean = (float(r1["roas"]) + float(r2["roas"])) / 2.0
        roas_diff_pct = (roas_diff_abs / roas_mean * 100) if roas_mean > 0 else 0.0

        cvr_diff_abs = abs(float(r1["cvr"]) - float(r2["cvr"]))
        cvr_mean = (float(r1["cvr"]) + float(r2["cvr"])) / 2.0
        cvr_diff_pct = (cvr_diff_abs / cvr_mean * 100) if cvr_mean > 0 else 0.0

        hook_diff_abs = abs(float(r1["hook_rate"]) - float(r2["hook_rate"]))
        hold_diff_abs = abs(float(r1["hold_rate"]) - float(r2["hold_rate"]))

        records.append({
            "pair_id": f"PAIR-{id1}-{id2}",
            "ad_id_1": id1,
            "ad_id_2": id2,
            "spend_1": float(r1["spend_inr"]),
            "spend_2": float(r2["spend_inr"]),
            "roas_1": round(float(r1["roas"]), 4),
            "roas_2": round(float(r2["roas"]), 4),
            "roas_diff_abs": round(roas_diff_abs, 4),
            "roas_diff_pct": round(roas_diff_pct, 2),
            "cvr_1": round(float(r1["cvr"]), 6),
            "cvr_2": round(float(r2["cvr"]), 6),
            "cvr_diff_abs": round(cvr_diff_abs, 6),
            "cvr_diff_pct": round(cvr_diff_pct, 2),
            "hook_rate_1": round(float(r1["hook_rate"]), 4),
            "hook_rate_2": round(float(r2["hook_rate"]), 4),
            "hook_diff_abs": round(hook_diff_abs, 4),
            "hold_rate_1": round(float(r1["hold_rate"]), 4),
            "hold_rate_2": round(float(r2["hold_rate"]), 4),
            "hold_diff_abs": round(hold_diff_abs, 4),
        })

    df_noise = pd.DataFrame(records)
    df_noise.to_csv(out_file, index=False)

    summary_noise = {
        "median_roas_diff_abs": float(df_noise["roas_diff_abs"].median()),
        "max_roas_diff_abs": float(df_noise["roas_diff_abs"].max()),
        "median_cvr_diff_abs": float(df_noise["cvr_diff_abs"].median()),
        "max_cvr_diff_abs": float(df_noise["cvr_diff_abs"].max()),
        "median_hook_diff_abs": float(df_noise["hook_diff_abs"].median()),
        "median_hold_diff_abs": float(df_noise["hold_diff_abs"].median()),
    }
    return df_noise, summary_noise


def bootstrap_difference_ci(
    df: pd.DataFrame,
    feature: str,
    level: str,
    num_col: str,
    den_col: str,
    n_iterations: int = 5000,
    seed: int = 42,
    ci_level: float = 0.95,
) -> Tuple[float, float, float, float]:
    """Compute point estimate, 95% bootstrap CI on the difference (group - rest), and empirical p-value."""
    grp_mask = (df[feature] == level).to_numpy()
    nums = df[num_col].to_numpy(dtype=float)
    dens = df[den_col].to_numpy(dtype=float)

    grp_num = nums[grp_mask]
    grp_den = dens[grp_mask]
    rest_num = nums[~grp_mask]
    rest_den = dens[~grp_mask]

    pt_grp = float(np.sum(grp_num) / np.sum(grp_den)) if np.sum(grp_den) > 0 else np.nan
    pt_rest = float(np.sum(rest_num) / np.sum(rest_den)) if np.sum(rest_den) > 0 else np.nan
    pt_diff = pt_grp - pt_rest

    n_grp = len(grp_num)
    n_rest = len(rest_num)
    if n_grp < 2 or n_rest < 2 or np.isnan(pt_diff):
        return (pt_diff, np.nan, np.nan, np.nan)

    rng = np.random.default_rng(seed)
    grp_idx = rng.integers(0, n_grp, size=(n_iterations, n_grp))
    rest_idx = rng.integers(0, n_rest, size=(n_iterations, n_rest))

    grp_boot_num = np.sum(grp_num[grp_idx], axis=1)
    grp_boot_den = np.sum(grp_den[grp_idx], axis=1)
    rest_boot_num = np.sum(rest_num[rest_idx], axis=1)
    rest_boot_den = np.sum(rest_den[rest_idx], axis=1)

    valid = (grp_boot_den > 0) & (rest_boot_den > 0)
    if not np.any(valid):
        return (pt_diff, np.nan, np.nan, np.nan)

    diffs = (grp_boot_num[valid] / grp_boot_den[valid]) - (rest_boot_num[valid] / rest_boot_den[valid])

    alpha = 1.0 - ci_level
    ci_low = float(np.percentile(diffs, 100 * (alpha / 2.0)))
    ci_high = float(np.percentile(diffs, 100 * (1.0 - alpha / 2.0)))

    if pt_diff > 0:
        p_val = 2.0 * float(np.mean(diffs <= 0))
    else:
        p_val = 2.0 * float(np.mean(diffs >= 0))
    p_val = min(1.0, max(1.0 / n_iterations, p_val))

    return (pt_diff, ci_low, ci_high, p_val)


def build_lj004_traits_table(
    analysis_df: pd.DataFrame,
    output_path: Optional[Path | str] = None,
) -> pd.DataFrame:
    """Build table listing all labels carried by LJ-004, spend/revenue shares, and effect retention."""
    out_file = Path(output_path) if output_path is not None else TABLES_DIR / "ad_lj004_traits.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    lj4_rows = analysis_df[analysis_df["ad_id"] == "LJ-004"]
    if len(lj4_rows) == 0:
        return pd.DataFrame()
    lj4 = lj4_rows.iloc[0]

    features = [
        "language",
        "hook_type",
        "hook_driver",
        "ad_format",
        "child_on_screen",
        "child_in_first_3s",
        "brand_first_said",
        "main_benefit",
        "production",
        "product_form",
    ]

    records = []
    for feat in features:
        if feat not in analysis_df.columns:
            continue
        val = lj4[feat]
        grp = analysis_df[analysis_df[feat] == val]
        rest = analysis_df[analysis_df[feat] != val]

        n_ads = len(grp)
        tot_spend = float(grp["spend_inr"].sum())
        lj4_spend = float(lj4["spend_inr"])
        spend_share_pct = round(lj4_spend / tot_spend * 100, 2) if tot_spend > 0 else 0.0

        tot_rev = float(grp["revenue_inr"].sum())
        lj4_rev = float(lj4["revenue_inr"])
        rev_share_pct = round(lj4_rev / tot_rev * 100, 2) if tot_rev > 0 else 0.0

        # Baseline effect on ROAS
        roas_grp = weighted_ratio(grp, "revenue_inr", "spend_inr")
        roas_rest = weighted_ratio(rest, "revenue_inr", "spend_inr")
        eff_with = roas_grp - roas_rest

        # Without LJ-004
        grp_no = grp[grp["ad_id"] != "LJ-004"]
        rest_no = rest[rest["ad_id"] != "LJ-004"]
        roas_grp_no = weighted_ratio(grp_no, "revenue_inr", "spend_inr") if len(grp_no) > 0 else np.nan
        roas_rest_no = weighted_ratio(rest_no, "revenue_inr", "spend_inr") if len(rest_no) > 0 else np.nan
        eff_no = roas_grp_no - roas_rest_no if pd.notna(roas_grp_no) and pd.notna(roas_rest_no) else np.nan

        share_retained = round(eff_no / eff_with, 4) if (eff_with > 0 and pd.notna(eff_no)) else np.nan
        depends_on_lj004 = bool(pd.isna(share_retained) or share_retained < 0.50 or eff_no <= 0)

        records.append({
            "feature": feat,
            "lj004_value": str(val),
            "n_ads_in_analysis_set": n_ads,
            "total_spend_inr": tot_spend,
            "lj004_spend_inr": lj4_spend,
            "lj004_spend_share_pct": spend_share_pct,
            "total_revenue_inr": tot_rev,
            "lj004_revenue_inr": lj4_rev,
            "lj004_revenue_share_pct": rev_share_pct,
            "roas_effect_with_lj004": round(eff_with, 4),
            "roas_effect_without_lj004": round(eff_no, 4) if pd.notna(eff_no) else np.nan,
            "share_retained": share_retained,
            "depends_on_lj004": depends_on_lj004,
        })

    df_traits = pd.DataFrame(records)
    df_traits.to_csv(out_file, index=False)
    return df_traits


def compute_leave_one_out_influence(
    analysis_df: pd.DataFrame,
    features_to_eval: List[Tuple[str, str, str]],
    output_path: Optional[Path | str] = None,
) -> pd.DataFrame:
    """Compute leave-one-out influence for top 5 ads by spend across candidate patterns."""
    out_file = Path(output_path) if output_path is not None else TABLES_DIR / "ad_leave_one_out_influence.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    top5_ads = analysis_df.sort_values("spend_inr", ascending=False).head(5)["ad_id"].tolist()

    records = []
    for feat, lvl, family in features_to_eval:
        if feat not in analysis_df.columns:
            continue
        grp = analysis_df[analysis_df[feat] == lvl]
        rest = analysis_df[analysis_df[feat] != lvl]
        if len(grp) == 0:
            continue

        num_col = "revenue_inr" if family == "conversion" else "video_3s_views"
        den_col = "spend_inr" if family == "conversion" else "impressions"

        base_grp = weighted_ratio(grp, num_col, den_col)
        base_rest = weighted_ratio(rest, num_col, den_col)
        base_eff = base_grp - base_rest

        row = {
            "feature": feat,
            "level": lvl,
            "metric_family": family,
            "baseline_effect": round(base_eff, 4),
        }

        diffs = []
        for ad_id in top5_ads:
            grp_loo = grp[grp["ad_id"] != ad_id]
            rest_loo = rest[rest["ad_id"] != ad_id]
            eff_loo = (
                weighted_ratio(grp_loo, num_col, den_col) - weighted_ratio(rest_loo, num_col, den_col)
                if len(grp_loo) > 0 and len(rest_loo) > 0
                else np.nan
            )
            row[f"effect_drop_{ad_id}"] = round(eff_loo, 4) if pd.notna(eff_loo) else np.nan
            if pd.notna(eff_loo):
                diffs.append(abs(eff_loo - base_eff))

        row["max_influence_top5"] = round(max(diffs), 4) if diffs else np.nan
        records.append(row)

    df_loo = pd.DataFrame(records)
    df_loo.to_csv(out_file, index=False)
    return df_loo


def compute_pattern_overlap(
    analysis_df: pd.DataFrame,
    patterns: List[Tuple[str, str]],
    output_path: Optional[Path | str] = None,
) -> pd.DataFrame:
    """Compute pairwise Jaccard overlap (|A ∩ B| / |A ∪ B|) between candidate pattern ad sets."""
    out_file = Path(output_path) if output_path is not None else TABLES_DIR / "ad_pattern_overlap.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    pattern_names = [f"{f}={lvl}" for f, lvl in patterns]
    n = len(patterns)
    ad_sets = [
        set(analysis_df[analysis_df[f] == lvl]["ad_id"].tolist())
        for f, lvl in patterns
    ]

    records = []
    for i in range(n):
        for j in range(n):
            set_i = ad_sets[i]
            set_j = ad_sets[j]
            intersection = len(set_i & set_j)
            union = len(set_i | set_j)
            jaccard = round(intersection / union, 4) if union > 0 else 0.0
            records.append({
                "pattern_1": pattern_names[i],
                "pattern_2": pattern_names[j],
                "n_ads_1": len(set_i),
                "n_ads_2": len(set_j),
                "intersection": intersection,
                "union": union,
                "jaccard_similarity": jaccard,
            })

    df_overlap = pd.DataFrame(records)
    df_overlap.to_csv(out_file, index=False)
    return df_overlap


def analyze_product_form_context(
    analysis_df: pd.DataFrame,
    output_path: Optional[Path | str] = None,
) -> pd.DataFrame:
    """Analyze product_form as a context variable, stratified by launch period only."""
    out_file = Path(output_path) if output_path is not None else TABLES_DIR / "ad_product_form_context.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    df = analysis_df.copy()
    median_launch = df["launch_date"].dropna().median()
    df["launch_period"] = np.where(df["launch_date"] < median_launch, "early", "late")

    records = []
    for period in ["all", "early", "late"]:
        p_df = df if period == "all" else df[df["launch_period"] == period]
        for pf, grp in p_df.groupby("product_form"):
            rest = p_df[p_df["product_form"] != pf]
            records.append({
                "launch_period": period,
                "product_form": str(pf),
                "n_ads": len(grp),
                "spend_inr": float(grp["spend_inr"].sum()),
                "revenue_inr": float(grp["revenue_inr"].sum()),
                "roas": round(weighted_ratio(grp, "revenue_inr", "spend_inr"), 4),
                "cvr": round(weighted_ratio(grp, "purchases", "link_clicks"), 6),
                "hook_rate": round(weighted_ratio(grp, "video_3s_views", "impressions"), 4),
                "hold_rate": round(weighted_ratio(grp, "thruplays", "video_3s_views"), 4),
                "roas_vs_rest": round(
                    weighted_ratio(grp, "revenue_inr", "spend_inr") - weighted_ratio(rest, "revenue_inr", "spend_inr"), 4
                ) if len(rest) > 0 else np.nan,
            })

    df_context = pd.DataFrame(records)
    df_context.to_csv(out_file, index=False)
    return df_context


def evaluate_ad_features(
    ads_with_metrics: pd.DataFrame,
    config: Dict[str, Any] = CONFIG,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Evaluate pre-registered features, enforce 50% LJ-004 rule, and produce findings and non-concluded tables."""
    ads_cfg = config.get("ads", {})
    all_features = ads_cfg.get("features_to_test", [])
    # Treat product_form as context only; creative features exclude product_form
    creative_features = [f for f in all_features if f != "product_form"]

    min_group_size = int(ads_cfg.get("min_group_size", 8))
    spend_variants = ads_cfg.get("min_spend_variants", [5000, 10000, 20000])
    base_min_spend = float(ads_cfg.get("min_spend_inr", 10000))
    bootstrap_n = int(ads_cfg.get("bootstrap_iterations", 5000))
    ci_level = float(ads_cfg.get("ci_level", 0.95))
    seed = int(config.get("seed", 42))

    analysis_set = build_analysis_set(ads_with_metrics, min_spend=base_min_spend, config=config)

    # Variant analysis sets for spend robustness
    variant_sets = {
        s: build_analysis_set(ads_with_metrics, min_spend=s, config=config)
        for s in spend_variants
    }

    # First pass: collect metrics and test patterns
    group_rows = []
    candidate_tests = []

    for feature in creative_features:
        if feature not in analysis_set.columns:
            continue

        for level, grp in analysis_set.groupby(feature, dropna=False):
            if pd.isna(level):
                continue
            level_str = str(level)
            n_ads = len(grp)
            spend_total = float(grp["spend_inr"].sum())
            supporting_ids = "; ".join(grp["ad_id"].tolist())
            has_lj004 = "LJ-004" in grp["ad_id"].values

            grp_no = grp[grp["ad_id"] != "LJ-004"]
            rest = analysis_set[analysis_set[feature] != level]
            rest_no = rest[rest["ad_id"] != "LJ-004"]

            # Conversion metrics
            roas_pt = weighted_ratio(grp, "revenue_inr", "spend_inr")
            roas_rest = weighted_ratio(rest, "revenue_inr", "spend_inr")
            roas_eff = roas_pt - roas_rest

            roas_grp_no = weighted_ratio(grp_no, "revenue_inr", "spend_inr") if len(grp_no) > 0 else np.nan
            roas_rest_no = weighted_ratio(rest_no, "revenue_inr", "spend_inr") if len(rest_no) > 0 else np.nan
            roas_eff_no = roas_grp_no - roas_rest_no if pd.notna(roas_grp_no) and pd.notna(roas_rest_no) else np.nan

            cvr_pt = weighted_ratio(grp, "purchases", "link_clicks")
            cvr_rest = weighted_ratio(rest, "purchases", "link_clicks")
            cvr_eff = cvr_pt - cvr_rest

            cvr_grp_no = weighted_ratio(grp_no, "purchases", "link_clicks") if len(grp_no) > 0 else np.nan
            cvr_rest_no = weighted_ratio(rest_no, "purchases", "link_clicks") if len(rest_no) > 0 else np.nan
            cvr_eff_no = cvr_grp_no - cvr_rest_no if pd.notna(cvr_grp_no) and pd.notna(cvr_rest_no) else np.nan

            # Attention metrics
            hook_pt = weighted_ratio(grp, "video_3s_views", "impressions")
            hook_rest = weighted_ratio(rest, "video_3s_views", "impressions")
            hook_eff = hook_pt - hook_rest

            hook_grp_no = weighted_ratio(grp_no, "video_3s_views", "impressions") if len(grp_no) > 0 else np.nan
            hook_rest_no = weighted_ratio(rest_no, "video_3s_views", "impressions") if len(rest_no) > 0 else np.nan
            hook_eff_no = hook_grp_no - hook_rest_no if pd.notna(hook_grp_no) and pd.notna(hook_rest_no) else np.nan

            hold_pt = weighted_ratio(grp, "thruplays", "video_3s_views")
            hold_rest = weighted_ratio(rest, "thruplays", "video_3s_views")
            hold_eff = hold_pt - hold_rest

            hold_grp_no = weighted_ratio(grp_no, "thruplays", "video_3s_views") if len(grp_no) > 0 else np.nan
            hold_rest_no = weighted_ratio(rest_no, "thruplays", "video_3s_views") if len(rest_no) > 0 else np.nan
            hold_eff_no = hold_grp_no - hold_rest_no if pd.notna(hold_grp_no) and pd.notna(hold_rest_no) else np.nan

            # Check spend variants robustness
            variant_robust_conv = True
            variant_robust_att = True
            for s_val, s_df in variant_sets.items():
                s_grp = s_df[s_df[feature] == level]
                s_rest = s_df[s_df[feature] != level]
                if len(s_grp) > 0 and len(s_rest) > 0:
                    s_roas_diff = weighted_ratio(s_grp, "revenue_inr", "spend_inr") - weighted_ratio(s_rest, "revenue_inr", "spend_inr")
                    s_hook_diff = weighted_ratio(s_grp, "video_3s_views", "impressions") - weighted_ratio(s_rest, "video_3s_views", "impressions")
                    if pd.notna(s_roas_diff) and s_roas_diff <= 0:
                        variant_robust_conv = False
                    if pd.notna(s_hook_diff) and s_hook_diff <= 0:
                        variant_robust_att = False

            # Retention without LJ-004
            roas_share = (roas_eff_no / roas_eff) if (roas_eff > 0 and pd.notna(roas_eff_no)) else np.nan
            hook_share = (hook_eff_no / hook_eff) if (hook_eff > 0 and pd.notna(hook_eff_no)) else np.nan

            roas_pass_lj004 = bool(pd.notna(roas_share) and roas_share >= 0.50 and roas_eff_no > 0)
            hook_pass_lj004 = bool(pd.notna(hook_share) and hook_share >= 0.50 and hook_eff_no > 0)

            # Confound check with product_form
            confound_note = "none_apparent"
            unique_pfs = grp["product_form"].dropna().unique()
            if len(unique_pfs) == 1:
                confound_note = f"co-occurs exclusively with product_form={unique_pfs[0]}"

            group_rows.append({
                "feature": feature,
                "level": level_str,
                "n_ads": n_ads,
                "spend_inr": spend_total,
                "has_lj004": has_lj004,
                "roas": round(roas_pt, 4),
                "roas_vs_rest": round(roas_eff, 4),
                "roas_no_lj004": round(roas_eff_no, 4) if pd.notna(roas_eff_no) else np.nan,
                "roas_share_retained": round(roas_share, 4) if pd.notna(roas_share) else np.nan,
                "cvr": round(cvr_pt, 6),
                "cvr_vs_rest": round(cvr_eff, 6),
                "hook_rate": round(hook_pt, 4),
                "hook_vs_rest": round(hook_eff, 4),
                "hook_no_lj004": round(hook_eff_no, 4) if pd.notna(hook_eff_no) else np.nan,
                "hook_share_retained": round(hook_share, 4) if pd.notna(hook_share) else np.nan,
                "hold_rate": round(hold_pt, 4),
                "hold_vs_rest": round(hold_eff, 4),
                "supporting_ad_ids": supporting_ids,
            })

            candidate_tests.append({
                "feature": feature,
                "level": level_str,
                "n_ads": n_ads,
                "spend_inr": spend_total,
                "has_lj004": has_lj004,
                "roas_eff": roas_eff,
                "roas_eff_no": roas_eff_no,
                "roas_share": roas_share,
                "roas_pass_lj004": roas_pass_lj004,
                "cvr_eff": cvr_eff,
                "cvr_eff_no": cvr_eff_no,
                "hook_eff": hook_eff,
                "hook_eff_no": hook_eff_no,
                "hook_share": hook_share,
                "hook_pass_lj004": hook_pass_lj004,
                "hold_eff": hold_eff,
                "hold_eff_no": hold_eff_no,
                "variant_robust_conv": variant_robust_conv,
                "variant_robust_att": variant_robust_att,
                "confound_note": confound_note,
                "supporting_ids": supporting_ids,
            })

    # Finding rule application
    finding_candidates = []
    not_concluded_rows = []

    for cand in candidate_tests:
        feature = cand["feature"]
        level = cand["level"]
        n_ads = cand["n_ads"]
        has_lj004 = cand["has_lj004"]

        # Rule 1: Min group size
        if n_ads < min_group_size:
            not_concluded_rows.append({
                "feature": feature,
                "level": level,
                "n_ads": n_ads,
                "spend_inr": cand["spend_inr"],
                "metric_family": "unclassified",
                "effect_with_lj004": round(cand["roas_eff"], 4),
                "effect_without_lj004": round(cand["roas_eff_no"], 4) if pd.notna(cand["roas_eff_no"]) else np.nan,
                "share_retained_no_lj004": round(cand["roas_share"], 4) if pd.notna(cand["roas_share"]) else np.nan,
                "depends_on_lj004": False,
                "reason": f"insufficient_sample_size ({n_ads} < {min_group_size} ads)",
                "supporting_ad_ids": cand["supporting_ids"],
            })
            continue

        # Check conversion path: ROAS and CVR both positive
        conv_eligible = (cand["roas_eff"] > 0) and (cand["cvr_eff"] > 0)
        # Check attention path: Hook and Hold both positive
        att_eligible = (cand["hook_eff"] > 0) and (cand["hold_eff"] > 0)

        # Evaluate LJ-004 dependency: if it carries LJ-004, does it retain < 50%?
        conv_depends_on_lj004 = has_lj004 and (not cand["roas_pass_lj004"])
        att_depends_on_lj004 = has_lj004 and (not cand["hook_pass_lj004"])

        promoted = False

        # Attempt promotion as Attention Finding
        if att_eligible and cand["hook_pass_lj004"] and cand["variant_robust_att"] and (cand["hold_eff_no"] > 0):
            pt, lo, hi, p = bootstrap_difference_ci(
                analysis_set, feature, level, "video_3s_views", "impressions",
                n_iterations=bootstrap_n, seed=seed, ci_level=ci_level
            )
            finding_candidates.append({
                "feature": feature,
                "level": level,
                "metric_family": "attention",
                "metric_pair": "hook_rate_and_hold_rate",
                "effect": round(pt, 4),
                "ci_diff_low": round(lo, 4),
                "ci_diff_high": round(hi, 4),
                "p_value": p,
                "effect_with_lj004": round(cand["hook_eff"], 4),
                "effect_without_lj004": round(cand["hook_eff_no"], 4),
                "share_retained_no_lj004": round(cand["hook_share"], 4),
                "depends_on_lj004": False,
                "n_ads": n_ads,
                "spend_inr": cand["spend_inr"],
                "survives_without_lj004": True,
                "survives_spend_variants": cand["variant_robust_att"],
                "confound_note": cand["confound_note"],
                "supporting_ad_ids": cand["supporting_ids"],
            })
            promoted = True

        # Attempt promotion as Conversion Finding
        elif conv_eligible and cand["roas_pass_lj004"] and cand["variant_robust_conv"] and (cand["cvr_eff_no"] > 0):
            pt, lo, hi, p = bootstrap_difference_ci(
                analysis_set, feature, level, "revenue_inr", "spend_inr",
                n_iterations=bootstrap_n, seed=seed, ci_level=ci_level
            )
            finding_candidates.append({
                "feature": feature,
                "level": level,
                "metric_family": "conversion",
                "metric_pair": "roas_and_cvr",
                "effect": round(pt, 4),
                "ci_diff_low": round(lo, 4),
                "ci_diff_high": round(hi, 4),
                "p_value": p,
                "effect_with_lj004": round(cand["roas_eff"], 4),
                "effect_without_lj004": round(cand["roas_eff_no"], 4),
                "share_retained_no_lj004": round(cand["roas_share"], 4),
                "depends_on_lj004": False,
                "n_ads": n_ads,
                "spend_inr": cand["spend_inr"],
                "survives_without_lj004": True,
                "survives_spend_variants": cand["variant_robust_conv"],
                "confound_note": cand["confound_note"],
                "supporting_ad_ids": cand["supporting_ids"],
            })
            promoted = True

        if not promoted:
            # Determine reason
            reasons = []
            depends = False
            if has_lj004 and (conv_depends_on_lj004 or att_depends_on_lj004):
                reasons.append("depends_on_lj004 (retains < 50% of effect without LJ-004)")
                depends = True
            if not conv_eligible and not att_eligible:
                reasons.append("inconsistent_paired_metrics")
            if not cand["variant_robust_conv"] and not cand["variant_robust_att"]:
                reasons.append("inconsistent_across_spend_variants")
            if cand["roas_eff"] <= 0 and cand["hook_eff"] <= 0:
                reasons.append("underperforms_analysis_set_benchmark")

            not_concluded_rows.append({
                "feature": feature,
                "level": level,
                "n_ads": n_ads,
                "spend_inr": cand["spend_inr"],
                "metric_family": "conversion" if cand["roas_eff"] > 0 else ("attention" if cand["hook_eff"] > 0 else "unclassified"),
                "effect_with_lj004": round(cand["roas_eff"], 4),
                "effect_without_lj004": round(cand["roas_eff_no"], 4) if pd.notna(cand["roas_eff_no"]) else np.nan,
                "share_retained_no_lj004": round(cand["roas_share"], 4) if pd.notna(cand["roas_share"]) else np.nan,
                "depends_on_lj004": depends,
                "reason": "; ".join(reasons) if reasons else "failed_finding_rule",
                "supporting_ad_ids": cand["supporting_ids"],
            })

    # Benjamini-Hochberg adjustment on surviving finding candidates
    finding_rows = []
    if len(finding_candidates) > 0:
        p_vals = [fc["p_value"] for fc in finding_candidates]
        adj_p_vals = bh_correct(p_vals)

        for i, fc in enumerate(finding_candidates):
            adj_p = float(adj_p_vals[i])
            tier = "supported" if adj_p <= 0.05 else "directional"
            feat_name = fc["feature"]
            label_err = LABEL_ERROR_RATES.get(feat_name, np.nan)

            finding_rows.append({
                "finding_id": f"F{i + 1:02d}",
                "feature": fc["feature"],
                "level": fc["level"],
                "tier": tier,
                "metric_family": fc["metric_family"],
                "metric_pair": fc["metric_pair"],
                "effect": fc["effect"],
                "ci_diff_low": fc["ci_diff_low"],
                "ci_diff_high": fc["ci_diff_high"],
                "p_value": round(fc["p_value"], 4),
                "adj_p_value": round(adj_p, 4),
                "label_error_rate": label_err if pd.notna(label_err) else "not_sampled",
                "depends_on_lj004": False,
                "effect_with_lj004": fc["effect_with_lj004"],
                "effect_without_lj004": fc["effect_without_lj004"],
                "share_retained_no_lj004": fc["share_retained_no_lj004"],
                "n_ads": fc["n_ads"],
                "spend_inr": fc["spend_inr"],
                "survives_without_lj004": True,
                "survives_spend_variants": fc["survives_spend_variants"],
                "confound_note": fc["confound_note"],
                "supporting_ad_ids": fc["supporting_ad_ids"],
            })

    df_group_metrics = pd.DataFrame(group_rows)
    df_findings = pd.DataFrame(finding_rows)
    df_not_concluded = pd.DataFrame(not_concluded_rows)

    df_group_metrics.to_csv(TABLES_DIR / "ad_group_metrics.csv", index=False)
    df_findings.to_csv(TABLES_DIR / "ad_findings.csv", index=False)
    df_not_concluded.to_csv(TABLES_DIR / "ad_not_concluded.csv", index=False)

    return df_group_metrics, df_findings, df_not_concluded


def evaluate_finding_rule(
    analysis_df: pd.DataFrame,
    feature: str,
    level: str,
    min_ads: int = 8,
    outlier_ad_id: str = "LJ-004",
    spend_variants: tuple = (15000, 20000),
    min_retention_ratio: float = 0.50,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Evaluate whether a single feature level satisfies the finding rule and the 50% outlier retention test."""
    spend_col = "spend_inr" if "spend_inr" in analysis_df.columns else "spend"
    rev_col = "revenue_inr" if "revenue_inr" in analysis_df.columns else "revenue"
    v3s_col = "video_3s_views" if "video_3s_views" in analysis_df.columns else "video_views_3s"

    grp = analysis_df[analysis_df[feature] == level]
    n_ads = len(grp)
    if n_ads < min_ads:
        return False, f"insufficient_sample_size ({n_ads} < {min_ads} ads)", {"n_ads": n_ads}

    roas_pt = weighted_ratio(grp, rev_col, spend_col)
    cvr_pt = weighted_ratio(grp, "purchases", "link_clicks")
    hook_pt = weighted_ratio(grp, v3s_col, "impressions")
    hold_pt = weighted_ratio(grp, "thruplays", v3s_col)

    rest_grp = analysis_df[analysis_df[feature] != level]
    rest_roas = weighted_ratio(rest_grp, rev_col, spend_col)
    rest_cvr = weighted_ratio(rest_grp, "purchases", "link_clicks")
    rest_hook = weighted_ratio(rest_grp, v3s_col, "impressions")
    rest_hold = weighted_ratio(rest_grp, "thruplays", v3s_col)

    roas_eff = roas_pt - rest_roas
    cvr_eff = cvr_pt - rest_cvr
    hook_eff = hook_pt - rest_hook
    hold_eff = hold_pt - rest_hold

    grp_no = grp[grp["ad_id"] != outlier_ad_id]
    rest_no = rest_grp[rest_grp["ad_id"] != outlier_ad_id]

    roas_no = weighted_ratio(grp_no, rev_col, spend_col) if len(grp_no) > 0 else np.nan
    rest_roas_no = weighted_ratio(rest_no, rev_col, spend_col) if len(rest_no) > 0 else np.nan
    roas_eff_no = roas_no - rest_roas_no if pd.notna(roas_no) and pd.notna(rest_roas_no) else np.nan

    cvr_no = weighted_ratio(grp_no, "purchases", "link_clicks") if len(grp_no) > 0 else np.nan
    rest_cvr_no = weighted_ratio(rest_no, "purchases", "link_clicks") if len(rest_no) > 0 else np.nan
    cvr_eff_no = cvr_no - rest_cvr_no if pd.notna(cvr_no) and pd.notna(rest_cvr_no) else np.nan

    hook_no = weighted_ratio(grp_no, v3s_col, "impressions") if len(grp_no) > 0 else np.nan
    rest_hook_no = weighted_ratio(rest_no, v3s_col, "impressions") if len(rest_no) > 0 else np.nan
    hook_eff_no = hook_no - rest_hook_no if pd.notna(hook_no) and pd.notna(rest_hook_no) else np.nan

    hold_no = weighted_ratio(grp_no, "thruplays", v3s_col) if len(grp_no) > 0 else np.nan
    rest_hold_no = weighted_ratio(rest_no, "thruplays", v3s_col) if len(rest_no) > 0 else np.nan
    hold_eff_no = hold_no - rest_hold_no if pd.notna(hold_no) and pd.notna(rest_hold_no) else np.nan

    has_outlier = outlier_ad_id in grp["ad_id"].values

    # Check 50% retention rule
    roas_share = roas_eff_no / roas_eff if (roas_eff > 0 and pd.notna(roas_eff_no)) else np.nan
    hook_share = hook_eff_no / hook_eff if (hook_eff > 0 and pd.notna(hook_eff_no)) else np.nan

    roas_passes_50 = bool(pd.notna(roas_share) and roas_share >= min_retention_ratio and roas_eff_no > 0)
    hook_passes_50 = bool(pd.notna(hook_share) and hook_share >= min_retention_ratio and hook_eff_no > 0)

    # Spend robustness
    spend_robust_conv = True
    spend_robust_att = True
    if spend_variants:
        for sv in spend_variants:
            sv_df = analysis_df[analysis_df[spend_col] >= sv]
            if len(sv_df) > 0:
                s_grp = sv_df[sv_df[feature] == level]
                s_rest = sv_df[sv_df[feature] != level]
                if len(s_grp) > 0 and len(s_rest) > 0:
                    s_roas_diff = weighted_ratio(s_grp, rev_col, spend_col) - weighted_ratio(s_rest, rev_col, spend_col)
                    s_hook_diff = weighted_ratio(s_grp, v3s_col, "impressions") - weighted_ratio(s_rest, v3s_col, "impressions")
                    if pd.notna(s_roas_diff) and s_roas_diff <= 0:
                        spend_robust_conv = False
                    if pd.notna(s_hook_diff) and s_hook_diff <= 0:
                        spend_robust_att = False

    # Outlier dependency rejection
    if has_outlier and not roas_passes_50 and not hook_passes_50:
        return False, f"depends_on_lj004 (retains < 50% of effect without {outlier_ad_id})", {
            "roas_eff": roas_eff,
            "roas_eff_no": roas_eff_no,
            "roas_share": roas_share,
            "hook_eff": hook_eff,
            "hook_eff_no": hook_eff_no,
            "hook_share": hook_share,
        }

    # Conversion promotion
    if (roas_eff > 0) and (cvr_eff > 0) and roas_passes_50 and spend_robust_conv and (cvr_eff_no > 0):
        return True, "survives_conversion_rule", {
            "metric_family": "conversion",
            "effect": round(roas_eff, 4),
            "share_retained": round(roas_share, 4),
        }

    # Attention promotion
    if (hook_eff > 0) and (hold_eff > 0) and hook_passes_50 and spend_robust_att and (hold_eff_no > 0):
        return True, "survives_attention_rule", {
            "metric_family": "attention",
            "effect": round(hook_eff, 4),
            "share_retained": round(hook_share, 4),
        }

    reasons = []
    if (roas_eff <= 0 or cvr_eff <= 0) and (hook_eff <= 0 or hold_eff <= 0):
        reasons.append("inconsistent_paired_metrics")
    if not spend_robust_conv and not spend_robust_att:
        reasons.append("inconsistent_across_spend_variants")

    return False, "; ".join(reasons) if reasons else "failed_finding_rule", {}


def plot_ad_findings_forest(
    df_findings: pd.DataFrame,
    output_path: Optional[Path | str] = None,
) -> None:
    """Generate forest-style plot showing effect sizes with 95% bootstrap intervals on difference."""
    out_file = Path(output_path) if output_path is not None else FIGURES_DIR / "ad_findings_forest.png"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if len(df_findings) == 0:
        return

    df = df_findings.sort_values("effect", ascending=True).reset_index(drop=True)
    y_pos = np.arange(len(df))

    fig, ax = plt.subplots(figsize=(10, max(5, len(df) * 0.8)), dpi=150)

    # Plot point estimates and horizontal error bars
    x_err_low = df["effect"] - df["ci_diff_low"]
    x_err_high = df["ci_diff_high"] - df["effect"]

    colors = ["#1f77b4" if t == "supported" else "#ff7f0e" for t in df["tier"]]

    ax.errorbar(
        df["effect"],
        y_pos,
        xerr=[x_err_low, x_err_high],
        fmt="o",
        color="#333333",
        ecolor="#555555",
        elinewidth=2,
        capsize=4,
        markersize=7,
        zorder=3,
    )

    # Scatter points with tier color
    ax.scatter(df["effect"], y_pos, c=colors, s=80, zorder=4)

    # Zero line
    ax.axvline(0, color="red", linestyle="--", alpha=0.7, linewidth=1.2, label="Null Effect (Diff = 0)")

    labels = [
        f"{r['feature']}={r['level']}\n[{r['metric_family'].upper()} | {r['tier'].upper()} | p={r['adj_p_value']:.3f}]"
        for _, r in df.iterrows()
    ]
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Spend-Weighted Difference vs Rest of Ads (Point Estimate & 95% Bootstrap CI)", fontsize=10)
    ax.set_title("Empirical Ad Findings: Effect Differences & 95% Intervals\n(Enforcing 50% LJ-004 Retention Rule)", fontsize=11, fontweight="bold")
    ax.grid(axis="x", alpha=0.3, linestyle=":")

    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", label="Supported (adj p <= 0.05)", markerfacecolor="#1f77b4", markersize=8),
        Line2D([0], [0], marker="o", color="w", label="Directional (adj p > 0.05)", markerfacecolor="#ff7f0e", markersize=8),
        Line2D([0], [0], color="red", linestyle="--", label="Null Difference = 0"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=9)

    plt.tight_layout()
    plt.savefig(out_file, bbox_inches="tight")
    plt.close()


def plot_funnel_by_pattern(
    df_group_metrics: pd.DataFrame,
    output_path: Optional[Path | str] = None,
) -> None:
    """Plot funnel metrics contrasting attention against conversion across patterns."""
    out_file = Path(output_path) if output_path is not None else FIGURES_DIR / "funnel_by_pattern.png"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    df = df_group_metrics[df_group_metrics["n_ads"] >= 8].copy()
    if len(df) == 0:
        return

    df["pattern"] = df["feature"] + "=" + df["level"]
    top_df = df.sort_values("n_ads", ascending=False).head(12)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=150)

    y_pos = np.arange(len(top_df))

    # Attention subplot (Hook & Hold)
    ax1.barh(y_pos - 0.2, top_df["hook_rate"] * 100, height=0.4, label="Hook Rate (3s/Imp %)", color="#4a90e2")
    ax1.barh(y_pos + 0.2, top_df["hold_rate"] * 100, height=0.4, label="Hold Rate (Thru/3s %)", color="#50e3c2")
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(top_df["pattern"], fontsize=9)
    ax1.set_xlabel("Percentage (%)", fontsize=10)
    ax1.set_title("Top-of-Funnel Attention Metrics", fontsize=11, fontweight="bold")
    ax1.legend(loc="lower right", fontsize=9)
    ax1.grid(axis="x", alpha=0.3)

    # Conversion subplot (ROAS)
    ax2.barh(y_pos, top_df["roas"], height=0.5, color="#f5a623", label="Spend-Weighted ROAS")
    ax2.axvline(1.59, color="black", linestyle="--", linewidth=1.2, label="Analysis Set ROAS (1.59x)")
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([])
    ax2.set_xlabel("Spend-Weighted ROAS", fontsize=10)
    ax2.set_title("Bottom-of-Funnel Conversion (ROAS)", fontsize=11, fontweight="bold")
    ax2.legend(loc="lower right", fontsize=9)
    ax2.grid(axis="x", alpha=0.3)

    plt.suptitle("Funnel Separation: Attention vs Conversion by Creative Pattern", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(out_file, bbox_inches="tight")
    plt.close()


def run_phase_2(config: Dict[str, Any] = CONFIG) -> None:
    """Execute complete Phase 2 empirical ad analysis."""
    print("=== Executing Phase 2 Ad Analysis (with Strict 50% LJ-004 Test) ===")
    raw_ads = load_ads()
    ads_with_metrics = compute_ad_metrics(raw_ads)

    # 1. Build analysis set
    base_min_spend = float(config.get("ads", {}).get("min_spend_inr", 10000))
    analysis_set = build_analysis_set(ads_with_metrics, min_spend=base_min_spend, config=config)
    analysis_set.to_csv(PROCESSED_DIR / "ads_analysis_set.csv", index=False)
    print(f"Analysis set saved: {len(analysis_set)} ads, Spend: ₹{analysis_set['spend_inr'].sum():,.0f}")

    # 2. Calibrate duplicate creative noise (context only)
    df_noise, summary_noise = calibrate_duplicate_noise(ads_with_metrics)
    print(f"Noise floor baseline: median ROAS delta = {summary_noise['median_roas_diff_abs']:.4f}, CVR delta = {summary_noise['median_cvr_diff_abs']:.6f}")

    # 3. Build LJ-004 Traits table
    df_lj4_traits = build_lj004_traits_table(analysis_set)
    print(f"LJ-004 traits table written: {len(df_lj4_traits)} traits evaluated")

    # 4. Product form context analysis (stratified by launch period only)
    df_pf_context = analyze_product_form_context(analysis_set)
    print(f"Product form context written: {len(df_pf_context)} rows")

    # 5. Evaluate creative features
    df_group_metrics, df_findings, df_not_concluded = evaluate_ad_features(ads_with_metrics, config=config)
    print(f"Surviving creative findings passing 50% LJ-004 rule: {len(df_findings)}")
    print(f"Non-concluded patterns logged: {len(df_not_concluded)}")

    # 6. Leave-one-out influence for top 5 spend ads on surviving + key candidate patterns
    eval_patterns = []
    for _, r in df_findings.iterrows():
        eval_patterns.append((r["feature"], r["level"], r["metric_family"]))
    # Add key rejected patterns to inspect LOO influence
    key_cand = [
        ("ad_format", "child_led", "conversion"),
        ("hook_driver", "curiosity_gap", "conversion"),
        ("child_on_screen", "one", "conversion"),
        ("main_benefit", "protein_intake", "conversion"),
    ]
    for p in key_cand:
        if p not in eval_patterns:
            eval_patterns.append(p)

    df_loo = compute_leave_one_out_influence(analysis_set, eval_patterns)
    print(f"Leave-one-out influence table written: {len(df_loo)} patterns evaluated")

    # 7. Pattern overlap (Jaccard similarity)
    overlap_patterns = [
        (r["feature"], r["level"]) for _, r in df_findings.iterrows()
    ]
    for feat, lvl, _ in key_cand:
        if (feat, lvl) not in overlap_patterns:
            overlap_patterns.append((feat, lvl))
    df_overlap = compute_pattern_overlap(analysis_set, overlap_patterns)
    print(f"Pattern overlap table written: {len(df_overlap)} pairs evaluated")

    # 8. Visualizations
    plot_ad_findings_forest(df_findings)
    plot_funnel_by_pattern(df_group_metrics)
    print("Figures generated successfully.")


if __name__ == "__main__":
    run_phase_2()
