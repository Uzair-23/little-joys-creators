"""Data audit module for Little Joys creator selection pipeline.

Implements all audit checks specified in PRD.md section 8.2:
1. Missing values per column (ads, creators, posts, audience).
2. Duplicate transcripts and hook_lines across ads with spend, ROAS, and dates (deduplicated).
3. Impossible funnel values (purchases > atc, clicks > impressions, etc.).
4. days_live vs dates recomputed against data_as_of (distribution & convention audit).
5. Concentration: share of total spend and revenue by top 1, 3, 5, 10 ads.
6. Spend flags: zero-purchase high-spend ads and ads below minimum spend.
7. Creator data quality: hidden likes, sponsored share, transcripts, post counts, future posts.
8. Distinct brands_visible per creator and config categorisation status.
9. Audience data quality: coverage, foreign audience share, gender split, past partnerships.
10. Distinct ad and post labels needed for downstream mapping.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from lj.config import CONFIG, DATA_AS_OF, TABLES_DIR
from lj.load import load_ads, load_audience, load_creators, load_posts


def audit_missing_values(
    ads: pd.DataFrame,
    creators: pd.DataFrame,
    posts: pd.DataFrame,
    audience: pd.DataFrame,
) -> pd.DataFrame:
    """Check missing values per column across all four datasets."""
    records = []
    datasets = {
        "ads": ads,
        "creators": creators,
        "creator_posts": posts,
        "creator_audience": audience,
    }
    for name, df in datasets.items():
        total_rows = len(df)
        for col in df.columns:
            series = df[col]
            if series.apply(lambda x: isinstance(x, list)).any():
                missing_count = int(series.apply(lambda x: len(x) == 0 if isinstance(x, list) else pd.isna(x)).sum())
            else:
                missing_count = int(series.isna().sum())

            pct = (missing_count / total_rows * 100) if total_rows > 0 else 0.0
            dtype_str = str(series.dtype)
            records.append({
                "dataset": name,
                "column": col,
                "missing_count": missing_count,
                "total_rows": total_rows,
                "missing_pct": round(pct, 2),
                "dtype": dtype_str,
            })
    return pd.DataFrame(records)


def audit_duplicates(ads: pd.DataFrame) -> pd.DataFrame:
    """Find ads with identical transcripts or hook_lines and report unique pairs without double counting.

    Reports:
    - Unique pairs (deduplicated across transcript and hook_line matches)
    - Match type ('transcript', 'hook_line', or 'both')
    - Spend, ROAS, link clicks, purchases, CVR, and launch/stop dates per ad.
    """
    # Group by transcript
    t_pairs: Dict[Tuple[str, ...], str] = {}
    for transcript, grp in ads.groupby("transcript"):
        if len(grp) > 1 and pd.notna(transcript) and str(transcript).strip():
            ad_ids = tuple(sorted(grp["ad_id"].tolist()))
            t_pairs[ad_ids] = str(transcript)

    # Group by hook_line
    h_pairs: Dict[Tuple[str, ...], str] = {}
    for hook, grp in ads.groupby("hook_line"):
        if len(grp) > 1 and pd.notna(hook) and str(hook).strip():
            ad_ids = tuple(sorted(grp["ad_id"].tolist()))
            h_pairs[ad_ids] = str(hook)

    all_pairs = sorted(set(t_pairs.keys()) | set(h_pairs.keys()))

    records = []
    for pair in all_pairs:
        in_t = pair in t_pairs
        in_h = pair in h_pairs
        if in_t and in_h:
            match_type = "both"
        elif in_t:
            match_type = "transcript"
        else:
            match_type = "hook_line"

        pair_id_str = f"PAIR-{'-'.join(pair)}"
        grp = ads[ads["ad_id"].isin(pair)].sort_values("ad_id")
        for _, row in grp.iterrows():
            spend = float(row["spend_inr"]) if pd.notna(row["spend_inr"]) else 0.0
            rev = float(row["revenue_inr"]) if pd.notna(row["revenue_inr"]) else 0.0
            clicks = int(row["link_clicks"]) if pd.notna(row["link_clicks"]) else 0
            purchases = int(row["purchases"]) if pd.notna(row["purchases"]) else 0
            roas = (rev / spend) if spend > 0 else 0.0
            cvr = (purchases / clicks) if clicks > 0 else 0.0
            records.append({
                "pair_id": pair_id_str,
                "match_type": match_type,
                "ad_id": row["ad_id"],
                "launch_date": str(row["launch_date"].date()) if pd.notna(row["launch_date"]) else "",
                "stopped_date": str(row["stopped_date"].date()) if pd.notna(row["stopped_date"]) else "",
                "days_live": int(row["days_live"]) if pd.notna(row["days_live"]) else 0,
                "spend_inr": spend,
                "revenue_inr": rev,
                "roas": round(roas, 4),
                "link_clicks": clicks,
                "purchases": purchases,
                "cvr": round(cvr, 6),
                "hook_line": str(row.get("hook_line", ""))[:80],
                "transcript_preview": str(row.get("transcript", ""))[:100],
            })

    return pd.DataFrame(records)


def audit_funnel_violations(ads: pd.DataFrame) -> pd.DataFrame:
    """Identify impossible marketing funnel values in ads.csv."""
    records = []
    checks = [
        ("purchases_gt_add_to_carts", "purchases", "add_to_carts"),
        ("clicks_gt_impressions", "link_clicks", "impressions"),
        ("thruplays_gt_video_3s_views", "thruplays", "video_3s_views"),
        ("add_to_carts_gt_link_clicks", "add_to_carts", "link_clicks"),
    ]
    for _, row in ads.iterrows():
        ad_id = row["ad_id"]
        for check_name, col_a, col_b in checks:
            val_a = row[col_a]
            val_b = row[col_b]
            if pd.notna(val_a) and pd.notna(val_b) and val_a > val_b:
                records.append({
                    "ad_id": ad_id,
                    "violation_type": check_name,
                    "metric_a": col_a,
                    "val_a": val_a,
                    "metric_b": col_b,
                    "val_b": val_b,
                })
    if not records:
        return pd.DataFrame(columns=["ad_id", "violation_type", "metric_a", "val_a", "metric_b", "val_b"])
    return pd.DataFrame(records)


def audit_days_live(ads: pd.DataFrame, data_as_of: str = DATA_AS_OF) -> pd.DataFrame:
    """Audit reported days_live vs calendar duration calculated against stopped_date or data_as_of.

    Computes difference = days_live - calculated_days.
    Reports the full distribution of differences and flags only ads where abs(difference) > 1.
    """
    as_of = pd.to_datetime(data_as_of)
    diffs = []
    ad_ids = []

    for _, row in ads.iterrows():
        launch = pd.to_datetime(row["launch_date"]) if pd.notna(row["launch_date"]) else None
        stopped = pd.to_datetime(row["stopped_date"]) if pd.notna(row["stopped_date"]) else None
        end_date = stopped if stopped is not None else as_of

        calc_days = int((end_date - launch).days) if launch is not None else None
        reported = int(row["days_live"]) if pd.notna(row["days_live"]) else None
        diff = (reported - calc_days) if (reported is not None and calc_days is not None) else None

        diffs.append(diff)
        ad_ids.append(row["ad_id"])

    df_detail = pd.DataFrame({"ad_id": ad_ids, "difference_days": diffs})
    total_ads = len(df_detail)

    dist_records = []
    for diff_val, grp in df_detail.groupby("difference_days", dropna=False):
        cnt = len(grp)
        pct = round(cnt / total_ads * 100, 2) if total_ads > 0 else 0.0
        # Flag only ads where the absolute difference is greater than 1
        is_flagged = bool(abs(diff_val) > 1) if pd.notna(diff_val) else True

        if diff_val == 0:
            interpretation = "Exact match: days_live equals calendar duration (inclusive boundary)"
        elif diff_val == -1:
            interpretation = "One-day convention: days_live equals calendar duration minus 1 (exclusive boundary)"
        elif diff_val == 1:
            interpretation = "One-day convention: days_live equals calendar duration plus 1"
        else:
            interpretation = f"ANOMALY: discrepancy of {diff_val} days exceeds 1-day convention"

        dist_records.append({
            "difference_days": diff_val,
            "ad_count": cnt,
            "pct_share": pct,
            "is_flagged": is_flagged,
            "interpretation": interpretation,
            "sample_ad_ids": "; ".join(grp["ad_id"].head(5).tolist()),
        })

    df_dist = pd.DataFrame(dist_records).sort_values("difference_days", ascending=False)
    return df_dist


def audit_concentration(ads: pd.DataFrame) -> pd.DataFrame:
    """Calculate spend and revenue concentration for top 1, 3, 5, 10 ads."""
    total_spend = float(ads["spend_inr"].sum())
    total_revenue = float(ads["revenue_inr"].sum())

    records = []
    for k in [1, 3, 5, 10]:
        top_spend_df = ads.nlargest(k, "spend_inr")
        top_rev_df = ads.nlargest(k, "revenue_inr")

        k_spend = float(top_spend_df["spend_inr"].sum())
        k_rev = float(top_rev_df["revenue_inr"].sum())

        records.append({
            "top_k": k,
            "spend_sum_inr": k_spend,
            "spend_share": round(k_spend / total_spend, 4) if total_spend > 0 else 0.0,
            "top_spend_ad_ids": "; ".join(top_spend_df["ad_id"].tolist()),
            "revenue_sum_inr": k_rev,
            "revenue_share": round(k_rev / total_revenue, 4) if total_revenue > 0 else 0.0,
            "top_revenue_ad_ids": "; ".join(top_rev_df["ad_id"].tolist()),
        })
    return pd.DataFrame(records)


def audit_spend_flags(ads: pd.DataFrame, config: Dict[str, Any] = CONFIG) -> pd.DataFrame:
    """Flag ads with extreme spend anomalies (zero-purchase high spend, below min spend)."""
    ads_cfg = config.get("ads", {})
    zero_purchase_thresh = float(ads_cfg.get("zero_purchase_spend_flag_inr", 100000))
    min_spend = float(ads_cfg.get("min_spend_inr", 10000))

    records = []
    for _, row in ads.iterrows():
        ad_id = row["ad_id"]
        spend = float(row["spend_inr"]) if pd.notna(row["spend_inr"]) else 0.0
        purchases = int(row["purchases"]) if pd.notna(row["purchases"]) else 0
        atc = int(row["add_to_carts"]) if pd.notna(row["add_to_carts"]) else 0
        rev = float(row["revenue_inr"]) if pd.notna(row["revenue_inr"]) else 0.0
        roas = (rev / spend) if spend > 0 else 0.0

        if spend >= zero_purchase_thresh and purchases == 0:
            records.append({
                "ad_id": ad_id,
                "flag_type": "zero_purchase_high_spend",
                "spend_inr": spend,
                "revenue_inr": rev,
                "purchases": purchases,
                "add_to_carts": atc,
                "roas": round(roas, 4),
                "threshold_inr": zero_purchase_thresh,
                "note": f"Spend ₹{spend:,.0f} >= ₹{zero_purchase_thresh:,.0f} but 0 purchases ({atc} add-to-carts); suspected tracking failure",
            })

        if spend < min_spend:
            records.append({
                "ad_id": ad_id,
                "flag_type": "below_min_spend",
                "spend_inr": spend,
                "revenue_inr": rev,
                "purchases": purchases,
                "add_to_carts": atc,
                "roas": round(roas, 4),
                "threshold_inr": min_spend,
                "note": f"Spend ₹{spend:,.0f} < ₹{min_spend:,.0f}; volatile / small sample creative",
            })

    return pd.DataFrame(records)


def audit_creator_data_quality(
    creators: pd.DataFrame,
    posts: pd.DataFrame,
    data_as_of: str = DATA_AS_OF,
    config: Dict[str, Any] = CONFIG,
) -> pd.DataFrame:
    """Audit creator data quality: post volume, hidden likes, sponsored saturation, future dates."""
    as_of = pd.to_datetime(data_as_of)
    cr_cfg = config.get("creators", {})
    hidden_likes_thresh = int(cr_cfg.get("hidden_likes_threshold", 5))
    hidden_likes_flag_pct = float(cr_cfg.get("hidden_likes_share_flag", 0.25))
    spon_flag_pct = float(cr_cfg.get("sponsored_share_flag", 0.70))
    inactive_days_thresh = int(cr_cfg.get("inactive_days_flag", 45))

    records = []
    for _, cr in creators.iterrows():
        c_id = cr["creator_id"]
        handle = cr["handle"]
        c_posts = posts[posts["creator_id"] == c_id]
        n_posts = len(c_posts)

        # Future posts after data_as_of
        future_posts = int((c_posts["posted_on"] > as_of).sum())

        # Hidden likes
        hidden_likes_cnt = int((c_posts["likes"] <= hidden_likes_thresh).sum())
        hidden_likes_share = (hidden_likes_cnt / n_posts) if n_posts > 0 else 0.0

        # Sponsored posts
        spon_cnt = int((c_posts["is_sponsored"]).sum())
        spon_share = (spon_cnt / n_posts) if n_posts > 0 else 0.0

        # Transcripts available
        transcripts_cnt = int(c_posts["transcript"].apply(lambda x: pd.notna(x) and len(str(x).strip()) > 0).sum())

        # Inactivity
        last_post_date = c_posts["posted_on"].max() if n_posts > 0 else pd.NaT
        inactive_days = int((as_of - last_post_date).days) if pd.notna(last_post_date) else None

        # Build flags
        flags = []
        if hidden_likes_share >= hidden_likes_flag_pct:
            flags.append(f"hidden_likes_{hidden_likes_share:.0%}")
        if spon_share >= spon_flag_pct:
            flags.append(f"sponsored_saturation_{spon_share:.0%}")
        if inactive_days is not None and inactive_days > inactive_days_thresh:
            flags.append(f"inactive_{inactive_days}d")
        if future_posts > 0:
            flags.append(f"future_posts_{future_posts}")
        if n_posts < int(config.get("gates", {}).get("min_posts", 8)):
            flags.append("too_few_posts")

        records.append({
            "creator_id": c_id,
            "handle": handle,
            "posts_available": n_posts,
            "posts_in_file_profile": int(cr["posts_in_file"]) if pd.notna(cr["posts_in_file"]) else n_posts,
            "future_posts_after_as_of": future_posts,
            "hidden_likes_count": hidden_likes_cnt,
            "hidden_likes_share": round(hidden_likes_share, 4),
            "sponsored_posts_count": spon_cnt,
            "sponsored_share": round(spon_share, 4),
            "transcripts_available": transcripts_cnt,
            "last_post_date": str(last_post_date.date()) if pd.notna(last_post_date) else "",
            "inactive_days": inactive_days,
            "flags": "; ".join(flags),
        })

    return pd.DataFrame(records)


def audit_brands_visible(
    posts: pd.DataFrame,
    config: Dict[str, Any] = CONFIG,
) -> pd.DataFrame:
    """Extract every distinct brand visible per creator and classify by config brand categories."""
    categories: Dict[str, List[str]] = config.get("brand_categories", {})

    records = []
    for c_id in sorted(posts["creator_id"].unique()):
        c_posts = posts[posts["creator_id"] == c_id]
        brands = set()
        for b_list in c_posts["brands_visible"]:
            if isinstance(b_list, list):
                for b in b_list:
                    if b.strip():
                        brands.add(b.strip())

        for brand in sorted(brands):
            # Check match against config categories
            matched_category = "uncategorised"
            is_known = False
            for cat_name, cat_brands in categories.items():
                if isinstance(cat_brands, list):
                    for cb in cat_brands:
                        if cb.lower() in brand.lower() or brand.lower() in cb.lower():
                            matched_category = cat_name
                            is_known = True
                            break
                if is_known:
                    break

            records.append({
                "creator_id": c_id,
                "brand": brand,
                "category": matched_category,
                "is_known_in_config": is_known,
            })

    return pd.DataFrame(records)


def audit_distinct_labels(
    ads: pd.DataFrame,
    posts: pd.DataFrame,
) -> pd.DataFrame:
    """Extract distinct values of ad labels and post labels needed for downstream mapping."""
    records = []

    # Ad labels to inspect
    ad_fields = ["hook_type", "ad_format", "language", "child_on_screen"]
    for field in ad_fields:
        if field in ads.columns:
            series = ads[field].dropna()
            val_counts = series.value_counts()
            for val, count in val_counts.items():
                records.append({
                    "source": "ads",
                    "field": field,
                    "distinct_value": str(val),
                    "count": int(count),
                })

    # Post labels to inspect
    post_fields = ["hook_style", "content_form", "topic", "language", "children_on_camera"]
    for field in post_fields:
        if field in posts.columns:
            series = posts[field].dropna()
            val_counts = series.value_counts()
            for val, count in val_counts.items():
                records.append({
                    "source": "posts",
                    "field": field,
                    "distinct_value": str(val),
                    "count": int(count),
                })

    return pd.DataFrame(records)


def audit_audience(
    creators: pd.DataFrame,
    audience: pd.DataFrame,
    config: Dict[str, Any] = CONFIG,
) -> pd.DataFrame:
    """Audit audience dataset coverage, geography, gender, and past brand relationships."""
    partner_brand = config.get("gates", {}).get("already_partner_brand", "Little Joys").lower()
    min_women = float(config.get("gates", {}).get("min_women_share_known", 0.50))
    min_india = float(config.get("gates", {}).get("min_india_share_known", 0.80))

    aud_map = {row["creator_id"]: row for _, row in audience.iterrows()}

    records = []
    for _, cr in creators.iterrows():
        c_id = cr["creator_id"]
        handle = cr["handle"]
        if c_id in aud_map:
            aud = aud_map[c_id]
            w_pct = float(aud["women_pct"]) if pd.notna(aud["women_pct"]) else None
            m_pct = float(aud["men_pct"]) if pd.notna(aud["men_pct"]) else None
            platform = str(aud["platform"])

            top_countries = aud["top_countries"] if isinstance(aud["top_countries"], list) else []
            india_share = None
            for c_entry in top_countries:
                if "india" in str(c_entry).lower():
                    parts = str(c_entry).split()
                    for p in parts:
                        if "%" in p:
                            try:
                                india_share = float(p.replace("%", ""))
                            except ValueError:
                                pass

            outside_india = (100.0 - india_share) if india_share is not None else None
            past_brands = aud["brands_in_past_year"] if isinstance(aud["brands_in_past_year"], list) else []

            flags = []
            if w_pct is not None and (w_pct / 100.0) < min_women:
                flags.append(f"low_women_share_{w_pct:.1f}%")
            if india_share is not None and (india_share / 100.0) < min_india:
                flags.append(f"low_india_share_{india_share:.1f}%")
            if platform != "instagram":
                flags.append(f"foreign_platform_{platform}")
            if any(partner_brand in str(b).lower() for b in past_brands):
                flags.append("past_little_joys_partner")

            records.append({
                "creator_id": c_id,
                "handle": handle,
                "audience_known": True,
                "platform": platform,
                "women_pct": w_pct,
                "men_pct": m_pct,
                "india_share_pct": india_share,
                "outside_india_pct": outside_india,
                "past_brands": "; ".join(past_brands),
                "flags": "; ".join(flags),
            })
        else:
            records.append({
                "creator_id": c_id,
                "handle": handle,
                "audience_known": False,
                "platform": "unknown",
                "women_pct": None,
                "men_pct": None,
                "india_share_pct": None,
                "outside_india_pct": None,
                "past_brands": "",
                "flags": "audience_inferred",
            })

    return pd.DataFrame(records)


def run_audit(
    output_dir: Optional[Path | str] = None,
    config: Dict[str, Any] = CONFIG,
) -> Dict[str, Any]:
    """Execute all audit checks and save tables to output_dir."""
    out_dir = Path(output_dir) if output_dir is not None else TABLES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    ads = load_ads()
    creators = load_creators()
    posts = load_posts()
    audience = load_audience()

    # 1. Missing values
    df_missing = audit_missing_values(ads, creators, posts, audience)
    df_missing.to_csv(out_dir / "audit_missing_values.csv", index=False)

    # 2. Duplicates (deduplicated across transcript and hook_line)
    df_dup = audit_duplicates(ads)
    df_dup.to_csv(out_dir / "audit_duplicates.csv", index=False)

    # 3. Funnel violations
    df_funnel = audit_funnel_violations(ads)
    df_funnel.to_csv(out_dir / "audit_funnel_violations.csv", index=False)

    # 4. Days live distribution
    df_days = audit_days_live(ads)
    df_days.to_csv(out_dir / "audit_days_live.csv", index=False)

    # 5. Concentration
    df_conc = audit_concentration(ads)
    df_conc.to_csv(out_dir / "audit_concentration.csv", index=False)

    # 6. Spend flags
    df_spend = audit_spend_flags(ads, config)
    df_spend.to_csv(out_dir / "audit_spend_flags.csv", index=False)

    # 7. Creator data quality
    df_cdq = audit_creator_data_quality(creators, posts, config=config)
    df_cdq.to_csv(out_dir / "audit_creator_data_quality.csv", index=False)

    # 8. Brands visible
    df_brands = audit_brands_visible(posts, config)
    df_brands.to_csv(out_dir / "audit_brands_visible.csv", index=False)

    # 9. Distinct labels
    df_labels = audit_distinct_labels(ads, posts)
    df_labels.to_csv(out_dir / "audit_distinct_labels.csv", index=False)

    # 10. Audience
    df_aud = audit_audience(creators, audience, config)
    df_aud.to_csv(out_dir / "audit_audience.csv", index=False)

    # LJ-004 concentration metric
    lj004_rev = float(ads[ads["ad_id"] == "LJ-004"]["revenue_inr"].iloc[0])
    total_rev = float(ads["revenue_inr"].sum())
    lj004_share = lj004_rev / total_rev if total_rev > 0 else 0.0

    unique_pair_ids = df_dup["pair_id"].unique().tolist()
    flagged_days_ads = int(df_days[df_days["is_flagged"]]["ad_count"].sum())

    summary = {
        "total_ads": len(ads),
        "total_creators": len(creators),
        "total_posts": len(posts),
        "total_audience_known": len(audience),
        "total_spend_inr": float(ads["spend_inr"].sum()),
        "total_revenue_inr": total_rev,
        "lj004_revenue_share": lj004_share,
        "zero_purchase_high_spend_ads": df_spend[df_spend["flag_type"] == "zero_purchase_high_spend"]["ad_id"].tolist(),
        "below_min_spend_ads_count": len(df_spend[df_spend["flag_type"] == "below_min_spend"]),
        "duplicate_pairs_count": len(unique_pair_ids),
        "duplicate_pairs": unique_pair_ids,
        "funnel_violations_count": len(df_funnel),
        "days_live_distribution": dict(zip(df_days["difference_days"], df_days["ad_count"])),
        "days_live_flagged_count": flagged_days_ads,
    }
    return summary


if __name__ == "__main__":
    res = run_audit()
    print("=== Little Joys Data Audit Complete ===")
    for k, v in res.items():
        print(f"  {k}: {v}")
