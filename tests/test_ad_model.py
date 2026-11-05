"""Unit tests for ad_model: analysis set, noise calibration, and finding rule."""

import numpy as np
import pandas as pd
import pytest

from lj.ad_model import (
    build_analysis_set,
    calibrate_duplicate_noise,
    evaluate_finding_rule,
)
from lj.load import load_ads


def test_analysis_set_exclusions():
    """Verify analysis set excludes LJ-089 and ads with spend < 10,000 INR."""
    raw_ads = load_ads()
    analysis_df, excl_df = build_analysis_set(raw_ads, return_exclusions=True)

    # LJ-089 excluded
    assert "LJ-089" not in analysis_df["ad_id"].values
    assert "LJ-089" in excl_df["ad_id"].values

    # No ads in analysis set with spend < 10,000
    assert (analysis_df["spend_inr"] < 10000.0).sum() == 0

    # Total row counts: 79 included, 21 excluded (1 tracking fault + 20 low spend)
    assert len(analysis_df) == 79
    assert len(excl_df) == 21


def test_duplicate_noise_calibration():
    """Verify duplicate creative noise table has 3 unique pairs and positive deltas."""
    raw_ads = load_ads()
    noise_df, summary = calibrate_duplicate_noise(raw_ads)

    assert len(noise_df) == 3
    assert "roas_diff_abs" in noise_df.columns
    assert (noise_df["roas_diff_abs"] > 0).all()
    # Median ROAS difference is approximately 0.49
    median_roas_diff = noise_df["roas_diff_abs"].median()
    assert median_roas_diff == pytest.approx(0.4915, rel=1e-2)


def test_pattern_keeping_under_50_pct_without_lj004_rejected_synthetic():
    """Verify that a candidate pattern retaining under 50% of its effect without LJ-004 is rejected.
    
    Construct a synthetic group of 8 ads:
    - 7 ads have spend 10k, rev 14k (ROAS = 1.4)
    - 1 ad ('LJ-004') has spend 100k, rev 300k (ROAS = 3.0)
    Combined group ROAS = 398k / 170k = 2.3412.
    Rest of ads (8 ads) have spend 10k, rev 10k each (ROAS = 1.0).
    Baseline group effect = 2.3412 - 1.0 = +1.3412.
    
    Without 'LJ-004':
    Group ROAS = 98k / 70k = 1.4. Rest ROAS = 1.0.
    Without-LJ004 effect = 1.4 - 1.0 = +0.40.
    Share retained = 0.40 / 1.3412 = 29.8% (< 50% threshold).
    Must be rejected with reason depends_on_lj004!
    """
    group_ads = pd.DataFrame({
        "ad_id": [f"GRP-{i}" for i in range(1, 8)] + ["LJ-004"],
        "spend": [10000.0] * 7 + [100000.0],
        "revenue": [14000.0] * 7 + [300000.0],
        "link_clicks": [500] * 7 + [5000],
        "purchases": [20] * 7 + [300],
        "video_views_3s": [2000] * 7 + [20000],
        "thruplays": [500] * 7 + [5000],
        "impressions": [6000] * 7 + [60000],
        "category": ["A"] * 8,
    })

    rest_ads = pd.DataFrame({
        "ad_id": [f"REST-{i}" for i in range(1, 9)],
        "spend": [10000.0] * 8,
        "revenue": [10000.0] * 8,
        "link_clicks": [500] * 8,
        "purchases": [15] * 8,
        "video_views_3s": [2000] * 8,
        "thruplays": [500] * 8,
        "impressions": [6000] * 8,
        "category": ["B"] * 8,
    })

    synthetic_analysis = pd.concat([group_ads, rest_ads], ignore_index=True)

    survives, reason, details = evaluate_finding_rule(
        analysis_df=synthetic_analysis,
        feature="category",
        level="A",
        min_ads=8,
        outlier_ad_id="LJ-004",
        min_retention_ratio=0.50,
    )

    assert survives is False
    assert "depends_on_lj004" in reason
    assert details["roas_share"] < 0.50


def test_real_lj004_dependent_patterns_rejected():
    """Verify that in the real Little Joys data, child_led, curiosity_gap, and protein_intake are rejected."""
    not_concluded = pd.read_csv("outputs/tables/ad_not_concluded.csv")

    for feat, lvl in [("ad_format", "child_led"), ("hook_driver", "curiosity_gap"), ("main_benefit", "protein_intake"), ("production", "semi_pro")]:
        row = not_concluded[(not_concluded["feature"] == feat) & (not_concluded["level"] == lvl)]
        assert len(row) == 1, f"Missing {feat}={lvl} in ad_not_concluded.csv"
        assert bool(row.iloc[0]["depends_on_lj004"]) is True
        assert "depends_on_lj004" in row.iloc[0]["reason"]


def test_findings_table_required_columns():
    """Confirm findings table has all required audit and methodology columns."""
    df_findings = pd.read_csv("outputs/tables/ad_findings.csv")
    required_cols = [
        "tier",
        "metric_family",
        "ci_diff_low",
        "ci_diff_high",
        "adj_p_value",
        "label_error_rate",
        "depends_on_lj004",
    ]
    for col in required_cols:
        assert col in df_findings.columns, f"Column {col} missing from ad_findings.csv"

    # All surviving findings must have depends_on_lj004 == False
    assert (df_findings["depends_on_lj004"] == False).all() or (df_findings["depends_on_lj004"] == "False").all()


def test_lj004_traits_table_accuracy():
    """Verify ad_lj004_traits.csv lists 10 traits and all depend on LJ-004."""
    df_traits = pd.read_csv("outputs/tables/ad_lj004_traits.csv")
    assert len(df_traits) == 10
    assert "share_retained" in df_traits.columns
    assert "depends_on_lj004" in df_traits.columns
    assert (df_traits["depends_on_lj004"] == True).all() or (df_traits["depends_on_lj004"] == "True").all()
