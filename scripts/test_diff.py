import pandas as pd
import numpy as np
from lj.load import load_ads
from lj.metrics import compute_ad_metrics
from lj.ad_model import build_analysis_set
from lj.stats import weighted_ratio, bh_correct

ads = compute_ad_metrics(load_ads())
df = build_analysis_set(ads, min_spend=10000)

print(f"Analysis set ads: {len(df)}")
top5 = df.sort_values("spend_inr", ascending=False).head(5)["ad_id"].tolist()
print(f"Top 5 spend ads: {top5}")

# Function to compute bootstrap CI and p-value on difference
def bootstrap_diff(df_data, feature, level, num_col, den_col, n_boot=5000, seed=42):
    rng = np.random.default_rng(seed)
    grp_mask = (df_data[feature] == level).to_numpy()
    nums = df_data[num_col].to_numpy(dtype=float)
    dens = df_data[den_col].to_numpy(dtype=float)
    n = len(df_data)
    
    grp_num = nums[grp_mask]
    grp_den = dens[grp_mask]
    rest_num = nums[~grp_mask]
    rest_den = dens[~grp_mask]
    
    pt_grp = np.sum(grp_num) / np.sum(grp_den) if np.sum(grp_den) > 0 else np.nan
    pt_rest = np.sum(rest_num) / np.sum(rest_den) if np.sum(rest_den) > 0 else np.nan
    pt_diff = pt_grp - pt_rest
    
    n_grp = len(grp_num)
    n_rest = len(rest_num)
    
    # Resample grp and rest
    grp_idx = rng.integers(0, n_grp, size=(n_boot, n_grp))
    rest_idx = rng.integers(0, n_rest, size=(n_boot, n_rest))
    
    grp_boot_num = np.sum(grp_num[grp_idx], axis=1)
    grp_boot_den = np.sum(grp_den[grp_idx], axis=1)
    rest_boot_num = np.sum(rest_num[rest_idx], axis=1)
    rest_boot_den = np.sum(rest_den[rest_idx], axis=1)
    
    valid = (grp_boot_den > 0) & (rest_boot_den > 0)
    grp_ratios = grp_boot_num[valid] / grp_boot_den[valid]
    rest_ratios = rest_boot_num[valid] / rest_boot_den[valid]
    diffs = grp_ratios - rest_ratios
    
    ci_low = float(np.percentile(diffs, 2.5))
    ci_high = float(np.percentile(diffs, 97.5))
    
    # Empirical p-value
    if pt_diff > 0:
        p_val = 2.0 * float(np.mean(diffs <= 0))
    else:
        p_val = 2.0 * float(np.mean(diffs >= 0))
    p_val = min(1.0, max(1.0 / n_boot, p_val))
    
    return pt_diff, ci_low, ci_high, p_val

print("Test bootstrap_diff on Hindi hook_rate:")
pt, lo, hi, p = bootstrap_diff(df, "language", "Hindi", "video_3s_views", "impressions", n_boot=2000)
print(f"Hindi Hook diff: {pt:.4f}, 95% CI: [{lo:.4f}, {hi:.4f}], p={p:.4f}")

