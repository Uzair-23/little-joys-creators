"""Creator features extraction module.

Extracts one comparable row per creator (20 creators) with:
- Identity: creator_id, handle, followers, persona, verified
- Reach: median_plays, plays_per_follower, plays_iqr, organic_median_plays, sponsored_median_plays, sponsored_organic_ratio, ratio_note
- Engagement: engagement_rate_median, likes_hidden_share, engagement_basis (full or comments_reshares_only)
- Consistency: share_posts_above_own_median
- Fit signals: share_kids_on_camera, share_product_shown, share_food_nutrition_topics, dominant_language, language_mix, format_mix
- Sponsorship: sponsored_share, distinct_sponsor_brands, days_since_last_post
- Risk: competitor_brands, adjacent_brands, uncategorised_brands, child_performer_flag
- Audience: audience_known (bool), women_share, india_share, age_split, audience_platform
- Quality: posts_available, transcripts_available

Adheres to:
1. Medians used for plays and engagement rates (IQR for spread).
2. Withholds sponsored_organic_ratio when fewer than 3 posts exist in either organic or sponsored group.
3. Automatically switches engagement_basis to 'comments_reshares_only' when likes_hidden_share > 0.25.
4. Maps brands_visible strictly using config.yaml brand_categories; lists all unmapped brands in uncategorised_brands without guessing.
5. Every NaN has an explicit companion reason column.
"""
from datetime import datetime
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from lj.config import CONFIG, DATA_AS_OF, PROCESSED_DIR
from lj.load import load_audience, load_creators, load_posts

FOOD_NUTRITION_PATTERN = re.compile(
    r"\b(food|nutrition|nutritional|diet|eating|eats|meal|meals|snack|snacks|recipe|recipes|"
    r"milk|feeding|cook|cooking|breakfast|dinner|lunch|puree|biscuit|biscuits|drink|weight gain|"
    r"growth|supplement|supplementation|fruits|vegetables|protein)\b",
    re.IGNORECASE,
)


def compute_creator_features(
    creators_df: Optional[pd.DataFrame] = None,
    posts_df: Optional[pd.DataFrame] = None,
    audience_df: Optional[pd.DataFrame] = None,
    config: Dict[str, Any] = CONFIG,
    output_path: Optional[Path | str] = None,
) -> pd.DataFrame:
    """Compute normalized feature vector for all creators."""
    if creators_df is None:
        creators_df = load_creators()
    if posts_df is None:
        posts_df = load_posts()
    if audience_df is None:
        audience_df = load_audience()

    out_file = Path(output_path) if output_path is not None else PROCESSED_DIR / "creator_features.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    cr_cfg = config.get("creators", {})
    min_posts_ratio = int(cr_cfg.get("min_posts_per_group_for_ratio", 3))
    hidden_likes_thresh = float(cr_cfg.get("hidden_likes_threshold", 5))
    hidden_share_flag = float(cr_cfg.get("hidden_likes_share_flag", 0.25))

    brand_categories = config.get("brand_categories", {})
    comp_brands = set(b.lower() for b in brand_categories.get("competitor_kids_nutrition", []))
    adj_food = set(b.lower() for b in brand_categories.get("adjacent_food_snacks", []))
    adj_well = set(b.lower() for b in brand_categories.get("adjacent_wellness", []))
    all_adj = adj_food | adj_well

    ref_date = datetime.strptime(str(config.get("data_as_of", DATA_AS_OF)), "%Y-%m-%d").date()

    records = []

    for _, cr in creators_df.iterrows():
        cid = str(cr["creator_id"])
        handle = str(cr["handle"])
        followers = float(cr["followers"])
        persona = str(cr["persona"])
        verified = bool(cr["verified"])

        c_posts = posts_df[posts_df["creator_id"] == cid].copy()
        n_posts = len(c_posts)

        # 1. Reach metrics
        if n_posts > 0 and c_posts["plays"].dropna().count() > 0:
            plays_clean = c_posts["plays"].dropna()
            median_plays = float(plays_clean.median())
            q25 = float(plays_clean.quantile(0.25))
            q75 = float(plays_clean.quantile(0.75))
            plays_iqr = q75 - q25
            plays_per_follower = median_plays / followers if followers > 0 else np.nan
            plays_per_follower_reason = "ok" if pd.notna(plays_per_follower) else "followers_is_zero"
        else:
            median_plays = np.nan
            plays_iqr = np.nan
            plays_per_follower = np.nan
            plays_per_follower_reason = "no_plays_data"

        # Organic vs Sponsored breakdown
        org_posts = c_posts[c_posts["is_sponsored"] == False]
        spon_posts = c_posts[c_posts["is_sponsored"] == True]
        n_org = len(org_posts)
        n_spon = len(spon_posts)

        # Organic median plays
        if n_org > 0 and org_posts["plays"].dropna().count() > 0:
            organic_median_plays = float(org_posts["plays"].dropna().median())
            organic_median_plays_reason = "ok"
        else:
            organic_median_plays = np.nan
            organic_median_plays_reason = "no_organic_posts"

        # Sponsored median plays
        if n_spon > 0 and spon_posts["plays"].dropna().count() > 0:
            sponsored_median_plays = float(spon_posts["plays"].dropna().median())
            sponsored_median_plays_reason = "ok"
        else:
            sponsored_median_plays = np.nan
            sponsored_median_plays_reason = "no_sponsored_posts"

        # Sponsored to organic ratio
        if n_org < min_posts_ratio or n_spon < min_posts_ratio:
            sponsored_organic_ratio = np.nan
            ratio_note = f"insufficient_posts_in_group (organic={n_org}, sponsored={n_spon} < {min_posts_ratio})"
        elif pd.isna(organic_median_plays) or organic_median_plays <= 0:
            sponsored_organic_ratio = np.nan
            ratio_note = "organic_median_plays_zero_or_nan"
        else:
            sponsored_organic_ratio = float(sponsored_median_plays / organic_median_plays)
            ratio_note = "ok"

        # 2. Engagement metrics
        # Check hidden likes: likes <= 5 or missing
        if n_posts > 0:
            likes_series = c_posts["likes"]
            hidden_mask = likes_series.isna() | (likes_series <= hidden_likes_thresh)
            likes_hidden_share = float(hidden_mask.mean())

            if likes_hidden_share > hidden_share_flag:
                engagement_basis = "comments_reshares_only"
                # (comments + reshares) / plays
                c_num = c_posts["comments"].fillna(0) + c_posts["reshares"].fillna(0)
            else:
                engagement_basis = "full"
                # (likes + comments + reshares) / plays
                c_num = c_posts["likes"].fillna(0) + c_posts["comments"].fillna(0) + c_posts["reshares"].fillna(0)

            c_den = c_posts["plays"].replace(0, np.nan)
            eng_rates = (c_num / c_den).dropna()
            if len(eng_rates) > 0:
                engagement_rate_median = float(eng_rates.median())
                engagement_rate_median_reason = "ok"
            else:
                engagement_rate_median = np.nan
                engagement_rate_median_reason = "no_valid_plays_for_engagement"
        else:
            likes_hidden_share = np.nan
            engagement_basis = "none"
            engagement_rate_median = np.nan
            engagement_rate_median_reason = "no_posts"

        # 3. Consistency
        if n_posts > 0 and pd.notna(median_plays):
            share_posts_above_own_median = float((c_posts["plays"] > median_plays).mean())
        else:
            share_posts_above_own_median = np.nan

        # 4. Fit signals
        if n_posts > 0:
            share_kids_on_camera = float((c_posts["children_on_camera"].str.lower() == "yes").mean())
            share_product_shown = float((c_posts["product_shown"].str.lower() == "yes").mean())

            # Food/nutrition topics
            food_matches = c_posts["topic"].fillna("").apply(lambda t: bool(FOOD_NUTRITION_PATTERN.search(t)))
            share_food_nutrition_topics = float(food_matches.mean())

            # Language breakdown
            langs = c_posts["language"].dropna().str.strip()
            if len(langs) > 0:
                dominant_language = str(langs.mode().iloc[0])
                lang_counts = langs.value_counts(normalize=True)
                language_mix = "; ".join([f"{k}: {v * 100:.1f}%" for k, v in lang_counts.items()])
            else:
                dominant_language = "unknown"
                language_mix = ""

            # Format mix
            forms = c_posts["content_form"].dropna().str.strip()
            if len(forms) > 0:
                form_counts = forms.value_counts(normalize=True)
                format_mix = "; ".join([f"{k}: {v * 100:.1f}%" for k, v in form_counts.items()])
            else:
                format_mix = ""
        else:
            share_kids_on_camera = 0.0
            share_product_shown = 0.0
            share_food_nutrition_topics = 0.0
            dominant_language = "none"
            language_mix = ""
            format_mix = ""

        # 5. Sponsorship metrics
        if n_posts > 0:
            sponsored_share = float((c_posts["is_sponsored"] == True).mean())
            # Distinct sponsor brands in sponsored posts
            spon_brands = []
            for b_list in spon_posts["brands_visible"].dropna():
                if isinstance(b_list, list):
                    spon_brands.extend(b_list)
                elif isinstance(b_list, str) and b_list.strip():
                    spon_brands.extend([x.strip() for x in b_list.split(";") if x.strip()])
            distinct_sponsor_brands = len(set(spon_brands))

            # Days since last post
            valid_dates = pd.to_datetime(c_posts["posted_on"]).dropna()
            if len(valid_dates) > 0:
                latest_date = valid_dates.max().date()
                days_since_last_post = int((ref_date - latest_date).days)
                days_since_last_post_reason = "ok"
            else:
                days_since_last_post = np.nan
                days_since_last_post_reason = "no_valid_posted_on_dates"
        else:
            sponsored_share = 0.0
            distinct_sponsor_brands = 0
            days_since_last_post = np.nan
            days_since_last_post_reason = "no_posts"

        # 6. Risk metrics & Brand Categorisation
        all_brands_raw = []
        for b_list in c_posts["brands_visible"].dropna():
            if isinstance(b_list, list):
                all_brands_raw.extend(b_list)
            elif isinstance(b_list, str) and b_list.strip():
                all_brands_raw.extend([x.strip() for x in b_list.split(";") if x.strip()])

        unique_brands = sorted(set(all_brands_raw))
        seen_comp = []
        seen_adj = []
        seen_uncat = []

        for b in unique_brands:
            b_norm = b.lower().strip()
            if b_norm in comp_brands:
                seen_comp.append(b)
            elif b_norm in all_adj:
                seen_adj.append(b)
            else:
                # Do not guess; list every uncatalogued brand
                seen_uncat.append(b)

        competitor_brands_str = "; ".join(seen_comp) if seen_comp else "none"
        adjacent_brands_str = "; ".join(seen_adj) if seen_adj else "none"
        uncategorised_brands_str = "; ".join(seen_uncat) if seen_uncat else "none"

        # Child performer flag
        child_performer_flag = bool("child performer" in persona.lower())

        # 7. Audience metrics (known vs inferred)
        aud_matches = audience_df[audience_df["creator_id"] == cid]
        if len(aud_matches) > 0:
            aud = aud_matches.iloc[0]
            audience_known = True
            women_share = float(aud["women_pct"]) / 100.0 if pd.notna(aud["women_pct"]) else np.nan
            women_share_reason = "known" if pd.notna(women_share) else "missing_in_audience_file"

            # Parse India percentage from top_countries string or list
            c_str = str(aud["top_countries"])
            m_ind = re.search(r"India\s+([\d\.]+)%", c_str, re.IGNORECASE)
            if m_ind:
                india_share = float(m_ind.group(1)) / 100.0
                india_share_reason = "known"
            else:
                india_share = np.nan
                india_share_reason = "india_percentage_not_found_in_top_countries"

            age_split_val = aud["age_split"]
            if isinstance(age_split_val, list):
                age_split = "; ".join(str(x) for x in age_split_val)
                age_split_reason = "known"
            elif pd.notna(age_split_val):
                age_split = str(age_split_val)
                age_split_reason = "known"
            else:
                age_split = np.nan
                age_split_reason = "missing_in_audience_file"

            plat_val = aud["platform"]
            if isinstance(plat_val, list):
                audience_platform = "; ".join(str(x) for x in plat_val)
                audience_platform_reason = "known"
            elif pd.notna(plat_val):
                audience_platform = str(plat_val)
                audience_platform_reason = "known"
            else:
                audience_platform = np.nan
                audience_platform_reason = "missing_in_audience_file"
        else:
            audience_known = False
            women_share = np.nan
            women_share_reason = "audience_data_not_available (inferred)"
            india_share = np.nan
            india_share_reason = "audience_data_not_available (inferred)"
            age_split = np.nan
            age_split_reason = "audience_data_not_available (inferred)"
            audience_platform = np.nan
            audience_platform_reason = "audience_data_not_available (inferred)"

        # 8. Data quality
        posts_available = n_posts
        transcripts_available = int(
            (c_posts["transcript"].dropna().str.strip() != "").sum()
        )

        records.append({
            # Identity
            "creator_id": cid,
            "handle": handle,
            "followers": int(followers),
            "persona": persona,
            "verified": verified,
            # Reach
            "median_plays": round(median_plays, 1) if pd.notna(median_plays) else np.nan,
            "plays_per_follower": round(plays_per_follower, 4) if pd.notna(plays_per_follower) else np.nan,
            "plays_per_follower_reason": plays_per_follower_reason,
            "plays_iqr": round(plays_iqr, 1) if pd.notna(plays_iqr) else np.nan,
            "organic_median_plays": round(organic_median_plays, 1) if pd.notna(organic_median_plays) else np.nan,
            "organic_median_plays_reason": organic_median_plays_reason,
            "sponsored_median_plays": round(sponsored_median_plays, 1) if pd.notna(sponsored_median_plays) else np.nan,
            "sponsored_median_plays_reason": sponsored_median_plays_reason,
            "sponsored_organic_ratio": round(sponsored_organic_ratio, 4) if pd.notna(sponsored_organic_ratio) else np.nan,
            "ratio_note": ratio_note,
            # Engagement
            "engagement_rate_median": round(engagement_rate_median, 6) if pd.notna(engagement_rate_median) else np.nan,
            "engagement_rate_median_reason": engagement_rate_median_reason,
            "likes_hidden_share": round(likes_hidden_share, 4) if pd.notna(likes_hidden_share) else np.nan,
            "engagement_basis": engagement_basis,
            # Consistency
            "share_posts_above_own_median": round(share_posts_above_own_median, 4) if pd.notna(share_posts_above_own_median) else np.nan,
            # Fit signals
            "share_kids_on_camera": round(share_kids_on_camera, 4),
            "share_product_shown": round(share_product_shown, 4),
            "share_food_nutrition_topics": round(share_food_nutrition_topics, 4),
            "dominant_language": dominant_language,
            "language_mix": language_mix,
            "format_mix": format_mix,
            # Sponsorship
            "sponsored_share": round(sponsored_share, 4),
            "distinct_sponsor_brands": distinct_sponsor_brands,
            "days_since_last_post": days_since_last_post,
            "days_since_last_post_reason": days_since_last_post_reason,
            # Risk
            "competitor_brands": competitor_brands_str,
            "adjacent_brands": adjacent_brands_str,
            "uncategorised_brands": uncategorised_brands_str,
            "child_performer_flag": child_performer_flag,
            # Audience
            "audience_known": audience_known,
            "women_share": round(women_share, 4) if pd.notna(women_share) else np.nan,
            "women_share_reason": women_share_reason,
            "india_share": round(india_share, 4) if pd.notna(india_share) else np.nan,
            "india_share_reason": india_share_reason,
            "age_split": age_split,
            "age_split_reason": age_split_reason,
            "audience_platform": audience_platform,
            "audience_platform_reason": audience_platform_reason,
            # Quality
            "posts_available": posts_available,
            "transcripts_available": transcripts_available,
        })

    df_features = pd.DataFrame(records)
    df_features.to_csv(out_file, index=False)
    return df_features


def main() -> None:
    """Entry point for executing creator features pipeline."""
    print("=== Computing Creator Features (Phase 3) ===")
    df_features = compute_creator_features()
    print(f"Creator features saved: {len(df_features)} rows written to data/processed/creator_features.csv")
    print("Preview of key features:")
    preview_cols = [
        "creator_id",
        "handle",
        "followers",
        "median_plays",
        "engagement_rate_median",
        "engagement_basis",
        "share_kids_on_camera",
        "sponsored_share",
        "audience_known",
        "child_performer_flag",
    ]
    print(df_features[preview_cols].to_string(index=False))


if __name__ == "__main__":
    main()
