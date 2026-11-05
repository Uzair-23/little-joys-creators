"""Tests for data loading module (src/lj/load.py)."""
import pandas as pd
from lj.load import load_ads, load_creators, load_posts, load_audience


def test_row_counts():
    ads = load_ads()
    creators = load_creators()
    posts = load_posts()
    audience = load_audience()

    assert len(ads) == 100, f"Expected 100 ads, got {len(ads)}"
    assert len(creators) == 20, f"Expected 20 creators, got {len(creators)}"
    assert len(posts) == 392, f"Expected 392 posts, got {len(posts)}"
    assert len(audience) == 3, f"Expected 3 audience rows, got {len(audience)}"


def test_dates_parsed():
    ads = load_ads()
    posts = load_posts()
    audience = load_audience()

    assert pd.api.types.is_datetime64_any_dtype(ads["launch_date"])
    assert pd.api.types.is_datetime64_any_dtype(ads["stopped_date"])
    assert pd.api.types.is_datetime64_any_dtype(posts["posted_on"])
    assert pd.api.types.is_datetime64_any_dtype(audience["as_of"])


def test_list_columns_split():
    ads = load_ads()
    creators = load_creators()
    posts = load_posts()
    audience = load_audience()

    # ads list columns
    for col in ["claims_made", "child_role", "demo_shown", "proof_used", "persuasion", "narratives", "ad_categories"]:
        assert isinstance(ads[col].iloc[0], list)

    # creators list columns
    for col in ["catchphrases", "themes", "format_habits"]:
        assert isinstance(creators[col].iloc[0], list)

    # posts list columns
    for col in ["child_ages", "brands_visible"]:
        assert isinstance(posts[col].iloc[0], list)

    # audience list columns
    for col in ["age_split", "top_cities", "top_countries", "brands_in_past_year"]:
        assert isinstance(audience[col].iloc[0], list)


def test_is_sponsored_boolean():
    posts = load_posts()
    assert pd.api.types.is_bool_dtype(posts["is_sponsored"])
    assert set(posts["is_sponsored"].unique()).issubset({True, False})

