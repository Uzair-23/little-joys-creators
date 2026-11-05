"""Unit tests for statistical helpers in lj.stats."""

import numpy as np
import pandas as pd
import pytest
from statsmodels.stats.multitest import multipletests

from lj.stats import bh_correct, bootstrap_ci, percentile_rank, weighted_ratio


def test_weighted_ratio_hand_crafted():
    """Verify weighted_ratio on hand-crafted DataFrame where spend-weighted ROAS is known.
    
    Ad 1: spend = 100, rev = 200 (ROAS = 2.0)
    Ad 2: spend = 1000, rev = 5000 (ROAS = 5.0)
    Weighted ROAS = (200 + 5000) / (100 + 1000) = 5200 / 1100 = 4.72727...
    Unweighted mean of ratios = (2.0 + 5.0) / 2 = 3.5.
    """
    df = pd.DataFrame({
        "spend": [100.0, 1000.0],
        "revenue": [200.0, 5000.0],
    })
    expected_weighted = 5200.0 / 1100.0
    calc_weighted = weighted_ratio(df, "revenue", "spend")

    assert calc_weighted == pytest.approx(expected_weighted, rel=1e-6)
    assert calc_weighted != pytest.approx(3.5, rel=1e-3)


def test_weighted_ratio_zero_denominator():
    """Verify weighted_ratio returns np.nan when sum of denominator is zero."""
    df = pd.DataFrame({
        "num": [10.0, 20.0],
        "den": [0.0, 0.0],
    })
    result = weighted_ratio(df, "num", "den")
    assert np.isnan(result)


def test_weighted_ratio_empty_df():
    """Verify weighted_ratio returns np.nan for empty DataFrame."""
    df = pd.DataFrame({"num": [], "den": []})
    assert np.isnan(weighted_ratio(df, "num", "den"))


def test_bootstrap_ci_reproducible():
    """Verify bootstrap_ci returns identical results with fixed seed."""
    df = pd.DataFrame({
        "spend": [100.0, 200.0, 300.0, 400.0, 500.0],
        "revenue": [150.0, 310.0, 420.0, 600.0, 800.0],
    })
    ci1 = bootstrap_ci(df, "revenue", "spend", n_boot=200, seed=42)
    ci2 = bootstrap_ci(df, "revenue", "spend", n_boot=200, seed=42)

    assert ci1 == ci2
    # ci1 is (point_estimate, ci_low, ci_high)
    point_est, ci_low, ci_high = ci1
    assert ci_low <= ci_high
    assert ci_low <= point_est <= ci_high


def test_bh_correct_matches_statsmodels():
    """Verify Benjamini-Hochberg FDR correction matches statsmodels."""
    p_values = [0.001, 0.015, 0.035, 0.08, 0.25, 0.60]
    expected_reject, expected_p_adj, _, _ = multipletests(p_values, alpha=0.05, method="fdr_bh")

    calc_p_adj, calc_reject = bh_correct(p_values, alpha=0.05)

    np.testing.assert_allclose(calc_p_adj, expected_p_adj, rtol=1e-5)
    np.testing.assert_array_equal(calc_reject, expected_reject)


def test_percentile_rank():
    """Verify percentile ranking logic."""
    series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    ranks_asc = percentile_rank(series, ascending=True)
    assert ranks_asc.iloc[0] == 0.0
    assert ranks_asc.iloc[-1] == 1.0

    ranks_desc = percentile_rank(series, ascending=False)
    assert ranks_desc.iloc[0] == 1.0
    assert ranks_desc.iloc[-1] == 0.0
