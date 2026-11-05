"""Statistical aggregation and inference utilities for ad analysis.

Implements:
- weighted_ratio: spend-weighted ratio of sums (sum(num) / sum(den))
- bootstrap_ci: percentile bootstrap confidence intervals
- bh_correct: Benjamini-Hochberg false discovery rate correction
- percentile_rank: percentile rank scaling (0 to 1)
"""
from typing import List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd


def weighted_ratio(
    df: pd.DataFrame,
    num_col: str,
    den_col: str,
) -> float:
    """Compute spend-weighted ratio sum(num) / sum(den).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing numerator and denominator columns.
    num_col : str
        Name of numerator column.
    den_col : str
        Name of denominator column.

    Returns
    -------
    float
        The weighted ratio, or np.nan if denominator sum is 0, non-positive, or df is empty.
    """
    if df is None or len(df) == 0:
        return np.nan

    valid = df[[num_col, den_col]].dropna()
    if len(valid) == 0:
        return np.nan

    den_sum = float(valid[den_col].sum())
    if den_sum <= 0:
        return np.nan

    num_sum = float(valid[num_col].sum())
    return float(num_sum / den_sum)


def bootstrap_ci(
    df: pd.DataFrame,
    num_col: str,
    den_col: str,
    n_iterations: int = 5000,
    seed: int = 42,
    ci_level: float = 0.95,
    n_boot: Optional[int] = None,
) -> Tuple[float, float, float]:
    """Calculate point estimate and bootstrap confidence interval for weighted ratio.

    Resamples rows with replacement.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with ad records.
    num_col : str
        Numerator column.
    den_col : str
        Denominator column.
    n_iterations : int
        Number of bootstrap resamples (default 5000).
    seed : int
        Random seed for reproducibility.
    ci_level : float
        Confidence level, e.g. 0.95 for 95% CI.
    n_boot : Optional[int]
        Alias for n_iterations.

    Returns
    -------
    Tuple[float, float, float]
        (point_estimate, ci_low, ci_high)
    """
    if n_boot is not None:
        n_iterations = n_boot
    point_est = weighted_ratio(df, num_col, den_col)
    if np.isnan(point_est) or len(df) < 2:
        return (point_est, np.nan, np.nan)

    clean_df = df[[num_col, den_col]].dropna().reset_index(drop=True)
    n = len(clean_df)
    if n < 2:
        return (point_est, np.nan, np.nan)

    rng = np.random.default_rng(seed)
    nums = clean_df[num_col].to_numpy(dtype=float)
    dens = clean_df[den_col].to_numpy(dtype=float)

    # Vectorized bootstrap resampling
    indices = rng.integers(0, n, size=(n_iterations, n))
    resampled_num_sums = np.sum(nums[indices], axis=1)
    resampled_den_sums = np.sum(dens[indices], axis=1)

    # Filter out zero/negative denominators in resamples
    valid_mask = resampled_den_sums > 0
    if not np.any(valid_mask):
        return (point_est, np.nan, np.nan)

    bootstrap_ratios = resampled_num_sums[valid_mask] / resampled_den_sums[valid_mask]

    alpha = 1.0 - ci_level
    ci_low = float(np.percentile(bootstrap_ratios, 100 * (alpha / 2.0)))
    ci_high = float(np.percentile(bootstrap_ratios, 100 * (1.0 - alpha / 2.0)))

    return (point_est, ci_low, ci_high)


def bh_correct(
    pvalues: Union[Sequence[float], np.ndarray],
    alpha: Optional[float] = None,
) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
    """Apply Benjamini-Hochberg (FDR) adjustment to a collection of p-values.

    Parameters
    ----------
    pvalues : Sequence[float]
        Array or list of unadjusted p-values.
    alpha : Optional[float]
        If specified, also returns boolean array of rejections (p_adj <= alpha).

    Returns
    -------
    Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]
        Array of adjusted p-values, or (adjusted_p, reject_mask) if alpha is provided.
    """
    p_arr = np.asarray(pvalues, dtype=float)
    if len(p_arr) == 0:
        if alpha is not None:
            return np.array([]), np.array([], dtype=bool)
        return np.array([])

    n = len(p_arr)
    # Handle NaNs
    valid_mask = ~np.isnan(p_arr)
    valid_p = p_arr[valid_mask]
    m = len(valid_p)

    adjusted = np.full(n, np.nan, dtype=float)
    if m == 0:
        if alpha is not None:
            return adjusted, np.zeros(n, dtype=bool)
        return adjusted

    # Rank ascending
    sort_idx = np.argsort(valid_p)
    sorted_p = valid_p[sort_idx]

    # BH calculation: p_adj = min(1, p * m / rank)
    ranks = np.arange(1, m + 1)
    factors = m / ranks
    adj_values = sorted_p * factors

    # Ensure monotonicity from right to left
    adj_values = np.minimum.accumulate(adj_values[::-1])[::-1]
    adj_values = np.clip(adj_values, 0.0, 1.0)

    # Restore order
    valid_adjusted = np.empty(m, dtype=float)
    valid_adjusted[sort_idx] = adj_values
    adjusted[valid_mask] = valid_adjusted

    if alpha is not None:
        reject = (adjusted <= alpha) & (~np.isnan(adjusted))
        return adjusted, reject

    return adjusted


def percentile_rank(
    series: pd.Series,
    ascending: bool = True,
) -> pd.Series:
    """Compute percentile rank for a numeric Series, normalized 0 to 1.

    Parameters
    ----------
    series : pd.Series
        Numeric Series.
    ascending : bool
        Whether to rank ascending (lowest value gets lowest rank).

    Returns
    -------
    pd.Series
        Series with values ranked between 0.0 and 1.0 (mean rank on ties).
    """
    if series.empty or series.dropna().empty:
        return pd.Series(np.nan, index=series.index)
    # Using rank(pct=True) gives percentile rank in (0, 1]
    # For min/max scaling (0 to 1), if length > 1:
    valid = series.dropna()
    if len(valid) <= 1:
        return pd.Series(0.5, index=series.index)
    ranks = series.rank(ascending=ascending, method="min") - 1
    max_rank = len(valid) - 1
    return ranks / max_rank
