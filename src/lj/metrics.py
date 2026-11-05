"""Ad-level funnel metrics calculation module.

Adds to each ad:
- roas: revenue_inr / spend_inr
- cpa: spend_inr / purchases
- cvr: purchases / link_clicks
- ctr: link_clicks / impressions
- hook_rate: video_3s_views / impressions
- hold_rate: thruplays / video_3s_views
- atc_rate: add_to_carts / link_clicks
- aov: revenue_inr / purchases

Division by zero yields np.nan, never 0.0 or infinity.
Writes outputs/tables/ad_metrics.csv.
"""
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd

from lj.config import TABLES_DIR
from lj.load import load_ads


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Safely divide two series, replacing zero or non-positive denominators with np.nan."""
    num = pd.to_numeric(numerator, errors="coerce")
    den = pd.to_numeric(denominator, errors="coerce")

    # Mask zero or negative or NaN denominators
    valid_mask = den.notna() & (den > 0)
    result = pd.Series(np.nan, index=num.index, dtype="float64")
    result[valid_mask] = num[valid_mask] / den[valid_mask]
    return result


def compute_ad_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-ad funnel metrics with strict zero-division protection.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame of ads (must contain spend_inr, revenue_inr, purchases, link_clicks,
        impressions, video_3s_views, thruplays, add_to_carts).

    Returns
    -------
    pd.DataFrame
        Copy of DataFrame with metric columns added.
    """
    out = df.copy()

    # Core funnel and efficiency metrics
    out["roas"] = _safe_divide(out["revenue_inr"], out["spend_inr"])
    out["cpa"] = _safe_divide(out["spend_inr"], out["purchases"])
    out["cvr"] = _safe_divide(out["purchases"], out["link_clicks"])
    out["ctr"] = _safe_divide(out["link_clicks"], out["impressions"])
    out["hook_rate"] = _safe_divide(out["video_3s_views"], out["impressions"])
    out["hold_rate"] = _safe_divide(out["thruplays"], out["video_3s_views"])
    out["atc_rate"] = _safe_divide(out["add_to_carts"], out["link_clicks"])
    out["aov"] = _safe_divide(out["revenue_inr"], out["purchases"])

    return out


def run_metrics(
    output_path: Optional[Path | str] = None,
) -> pd.DataFrame:
    """Load ads, calculate metrics, and save to output table."""
    out_file = Path(output_path) if output_path is not None else TABLES_DIR / "ad_metrics.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    ads = load_ads()
    metrics_df = compute_ad_metrics(ads)
    metrics_df.to_csv(out_file, index=False)
    return metrics_df


if __name__ == "__main__":
    df = run_metrics()
    print(f"Calculated metrics for {len(df)} ads at {TABLES_DIR / 'ad_metrics.csv'}")
    print("Sample metrics summary (medians):")
    cols = ["roas", "cvr", "ctr", "hook_rate", "hold_rate", "cpa", "aov"]
    print(df[cols].median())

