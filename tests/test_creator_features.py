"""Tests for Phase 3 creator features computation."""
import numpy as np
import pandas as pd
import pytest

from lj.config import CONFIG, PROCESSED_DIR
from lj.creator_features import compute_creator_features


@pytest.fixture
def synthetic_data():
    """Build a minimal synthetic dataset of 2 creators and posts."""
    creators_df = pd.DataFrame([
        {
            "creator_id": "CR-SYN-01",
            "handle": "test_creator_normal",
            "followers": 10000,
            "persona": "Relatable Mom",
            "verified": False,
        },
        {
            "creator_id": "CR-SYN-02",
            "handle": "test_creator_hidden_likes",
            "followers": 20000,
            "persona": "precocious child performer",
            "verified": True,
        },
    ])

    # Posts for CR-SYN-01:
    # 4 organic, 3 sponsored -> ratio should be calculated
    # Likes are visible (e.g. 100, 200) -> engagement_basis == 'full'
    # Plays: [1000, 2000, 3000, 4000] organic; [1000, 2000, 3000] sponsored
    posts_syn_01 = [
        # Organic
        {
            "creator_id": "CR-SYN-01",
            "post_url": f"http://test.com/1_{i}",
            "posted_on": f"2026-10-1{i}",
            "plays": p,
            "likes": 100,
            "comments": 10,
            "reshares": 5,
            "is_sponsored": False,
            "children_on_camera": "yes",
            "product_shown": "no",
            "topic": "morning routine with toddler breakfast",
            "language": "Hindi",
            "content_form": "piece_to_camera",
            "brands_visible": np.nan,
            "transcript": "hello",
        }
        for i, p in enumerate([1000, 2000, 3000, 4000], start=1)
    ] + [
        # Sponsored
        {
            "creator_id": "CR-SYN-01",
            "post_url": f"http://test.com/s_{i}",
            "posted_on": f"2026-10-2{i}",
            "plays": p,
            "likes": 100,
            "comments": 10,
            "reshares": 5,
            "is_sponsored": True,
            "children_on_camera": "yes",
            "product_shown": "yes",
            "topic": "baby nutrition tips",
            "language": "Hindi",
            "content_form": "piece_to_camera",
            "brands_visible": "Gritzo; BrandXUnknown",  # Gritzo is competitor, BrandXUnknown uncategorised
            "transcript": "sponsored content",
        }
        for i, p in enumerate([2000, 4000, 6000], start=1)
    ]

    # Posts for CR-SYN-02:
    # 2 organic, 1 sponsored -> ratio should be WITHHELD (<3 posts)
    # Likes are hidden (likes <= 5 or nan) on all posts -> engagement_basis == 'comments_reshares_only'
    posts_syn_02 = [
        {
            "creator_id": "CR-SYN-02",
            "post_url": "http://test.com/2_1",
            "posted_on": "2026-10-15",
            "plays": 10000,
            "likes": 2,  # Hidden like count
            "comments": 50,
            "reshares": 20,
            "is_sponsored": False,
            "children_on_camera": "yes",
            "product_shown": "no",
            "topic": "acting skit with child",
            "language": "English",
            "content_form": "skit",
            "brands_visible": np.nan,
            "transcript": "skit",
        },
        {
            "creator_id": "CR-SYN-02",
            "post_url": "http://test.com/2_2",
            "posted_on": "2026-10-16",
            "plays": 20000,
            "likes": np.nan,  # Hidden like count
            "comments": 80,
            "reshares": 30,
            "is_sponsored": False,
            "children_on_camera": "yes",
            "product_shown": "no",
            "topic": "school prep comedy",
            "language": "English",
            "content_form": "skit",
            "brands_visible": np.nan,
            "transcript": "skit 2",
        },
        {
            "creator_id": "CR-SYN-02",
            "post_url": "http://test.com/2_3",
            "posted_on": "2026-10-17",
            "plays": 30000,
            "likes": 0,  # Hidden like count
            "comments": 100,
            "reshares": 50,
            "is_sponsored": True,
            "children_on_camera": "yes",
            "product_shown": "yes",
            "topic": "snack review",
            "language": "English",
            "content_form": "demo_or_haul",
            "brands_visible": "Cadbury",  # Adjacent brand from config.yaml
            "transcript": "ad",
        },
    ]

    posts_df = pd.DataFrame(posts_syn_01 + posts_syn_02)

    # Audience table: CR-SYN-01 known, CR-SYN-02 unknown
    audience_df = pd.DataFrame([
        {
            "creator_id": "CR-SYN-01",
            "handle": "test_creator_normal",
            "platform": "instagram",
            "women_pct": 72.5,
            "top_countries": "India 85.0%, UAE 5.0%",
            "age_split": "25-34: 60%",
        }
    ])

    return creators_df, posts_df, audience_df


def test_synthetic_creator_features_calculation(synthetic_data, tmp_path):
    """Test reach medians, hidden likes, ratio withholding, brand categorisation on synthetic data."""
    creators_df, posts_df, audience_df = synthetic_data
    out_csv = tmp_path / "test_features.csv"

    features_df = compute_creator_features(
        creators_df=creators_df,
        posts_df=posts_df,
        audience_df=audience_df,
        config=CONFIG,
        output_path=out_csv,
    )

    assert len(features_df) == 2

    # --- Check Creator 1 ---
    r1 = features_df[features_df["creator_id"] == "CR-SYN-01"].iloc[0]
    # Organic plays: 1000, 2000, 3000, 4000 -> median is 2500
    assert r1["organic_median_plays"] == 2500.0
    # Sponsored plays: 2000, 4000, 6000 -> median is 4000
    assert r1["sponsored_median_plays"] == 4000.0
    # Both counts >= 3 -> ratio calculated (4000 / 2500 = 1.6)
    assert np.isclose(r1["sponsored_organic_ratio"], 1.6)
    assert r1["ratio_note"] == "ok"

    # Engagement basis: visible likes -> 'full'
    assert r1["engagement_basis"] == "full"
    assert r1["likes_hidden_share"] == 0.0

    # Brands categorisation:
    # Gritzo in competitor_kids_nutrition
    # BrandXUnknown in uncategorised_brands
    assert "Gritzo" in r1["competitor_brands"]
    assert "BrandXUnknown" in r1["uncategorised_brands"]

    # Child performer flag
    assert bool(r1["child_performer_flag"]) is False

    # Audience known
    assert bool(r1["audience_known"]) is True
    assert np.isclose(r1["women_share"], 0.725)
    assert np.isclose(r1["india_share"], 0.85)

    # --- Check Creator 2 ---
    r2 = features_df[features_df["creator_id"] == "CR-SYN-02"].iloc[0]
    # Organic count = 2 (< 3) and sponsored count = 1 (< 3) -> ratio WITHHELD
    assert pd.isna(r2["sponsored_organic_ratio"])
    assert "insufficient_posts_in_group" in r2["ratio_note"]

    # Hidden likes share = 1.0 > 0.25 -> engagement basis switches to comments_reshares_only
    assert r2["likes_hidden_share"] == 1.0
    assert r2["engagement_basis"] == "comments_reshares_only"

    # Brand categorisation: Cadbury in adjacent_brands
    assert "Cadbury" in r2["adjacent_brands"]
    assert r2["competitor_brands"] == "none"

    # Child performer flag from persona "precocious child performer"
    assert bool(r2["child_performer_flag"]) is True

    # Audience inferred
    assert bool(r2["audience_known"]) is False
    assert pd.isna(r2["women_share"])
    assert "inferred" in r2["women_share_reason"]


def test_companion_reasons_for_all_nans(synthetic_data, tmp_path):
    """Ensure every NaN value in creator_features has a companion reason column."""
    creators_df, posts_df, audience_df = synthetic_data
    out_csv = tmp_path / "test_nans.csv"

    features_df = compute_creator_features(
        creators_df=creators_df,
        posts_df=posts_df,
        audience_df=audience_df,
        config=CONFIG,
        output_path=out_csv,
    )

    # Check companion reason columns for columns that can have NaNs
    nan_reason_map = {
        "plays_per_follower": "plays_per_follower_reason",
        "organic_median_plays": "organic_median_plays_reason",
        "sponsored_median_plays": "sponsored_median_plays_reason",
        "sponsored_organic_ratio": "ratio_note",
        "engagement_rate_median": "engagement_rate_median_reason",
        "days_since_last_post": "days_since_last_post_reason",
        "women_share": "women_share_reason",
        "india_share": "india_share_reason",
        "age_split": "age_split_reason",
        "audience_platform": "audience_platform_reason",
    }

    for col, reason_col in nan_reason_map.items():
        nan_mask = features_df[col].isna()
        if nan_mask.any():
            # For every row where col is NaN, reason_col must NOT be NaN or empty
            assert features_df.loc[nan_mask, reason_col].notna().all(), f"Missing companion reason for {col}"
            assert (features_df.loc[nan_mask, reason_col].str.strip() != "").all(), f"Empty companion reason for {col}"


def test_real_creator_features_output():
    """Verify production creator_features.csv has 20 rows and matches raw creator IDs."""
    features_df = compute_creator_features()

    assert len(features_df) == 20
    assert features_df["creator_id"].nunique() == 20

    # Ensure hidden likes creator CR-17 is handled correctly
    cr17 = features_df[features_df["creator_id"] == "CR-17"].iloc[0]
    assert cr17["likes_hidden_share"] > 0.25
    assert cr17["engagement_basis"] == "comments_reshares_only"
    assert cr17["sponsored_share"] == 1.0
    assert pd.isna(cr17["organic_median_plays"])
    assert cr17["organic_median_plays_reason"] == "no_organic_posts"

    # Ensure audience known only for CR-14, CR-15, CR-20
    known_creators = set(features_df[features_df["audience_known"] == True]["creator_id"])
    assert known_creators == {"CR-14", "CR-15", "CR-20"}
