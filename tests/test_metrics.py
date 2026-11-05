"""Unit tests for funnel metrics in lj.metrics."""

import numpy as np
import pandas as pd
import pytest

from lj.load import load_ads
from lj.metrics import _safe_divide, compute_ad_metrics


def test_safe_divide_zeros_and_negatives():
    """Verify safe divide returns np.nan on zero or negative denominators."""
    num = pd.Series([10.0, 20.0, 30.0, 40.0])
    den = pd.Series([2.0, 0.0, -5.0, np.nan])

    res = _safe_divide(num, den)

    assert res.iloc[0] == pytest.approx(5.0)
    assert np.isnan(res.iloc[1])
    assert np.isnan(res.iloc[2])
    assert np.isnan(res.iloc[3])


def test_compute_ad_metrics_structure():
    """Verify compute_ad_metrics produces all 8 funnel metrics."""
    ads_df = load_ads()
    metrics_df = compute_ad_metrics(ads_df)

    expected_cols = [
        "roas",
        "cpa",
        "cvr",
        "ctr",
        "hook_rate",
        "hold_rate",
        "atc_rate",
        "aov",
    ]
    for col in expected_cols:
        assert col in metrics_df.columns
        assert len(metrics_df[col]) == 100


def test_zero_purchase_ad_cpa_aov():
    """Verify zero purchases results in NaN for CPA and AOV (e.g. LJ-089)."""
    ads_df = load_ads()
    metrics_df = compute_ad_metrics(ads_df)

    lj_089 = metrics_df[metrics_df["ad_id"] == "LJ-089"].iloc[0]
    assert lj_089["purchases"] == 0
    assert np.isnan(lj_089["cpa"])
    assert np.isnan(lj_089["aov"])
    assert lj_089["cvr"] == pytest.approx(0.0)
    assert lj_089["roas"] == pytest.approx(0.0)

