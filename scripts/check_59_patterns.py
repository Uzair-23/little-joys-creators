import pandas as pd
import numpy as np
from lj.load import load_ads
from lj.metrics import compute_ad_metrics
from lj.ad_model import build_analysis_set
from lj.stats import weighted_ratio
from lj.config import CONFIG

ads = compute_ad_metrics(load_ads())
df = build_analysis_set(ads, min_spend=10000)

features = CONFIG["ads"]["features_to_test"]

results = []

for feat in features:
    if feat not in df.columns:
        continue
    for level, grp in df.groupby(feat, dropna=False):
        if pd.isna(level):
            continue
        n_ads = len(grp)
        rest = df[df[feat] != level]
        has_lj004 = "LJ-004" in grp["ad_id"].values
        
        grp_no = grp[grp["ad_id"] != "LJ-004"]
        rest_no = rest[rest["ad_id"] != "LJ-004"]
        
        # Conversion metrics
        roas_grp = weighted_ratio(grp, "revenue_inr", "spend_inr")
        roas_rest = weighted_ratio(rest, "revenue_inr", "spend_inr")
        roas_eff_with = roas_grp - roas_rest
        
        roas_grp_no = weighted_ratio(grp_no, "revenue_inr", "spend_inr") if len(grp_no) > 0 else np.nan
        roas_rest_no = weighted_ratio(rest_no, "revenue_inr", "spend_inr") if len(rest_no) > 0 else np.nan
        roas_eff_no = (roas_grp_no - roas_rest_no) if pd.notna(roas_grp_no) and pd.notna(roas_rest_no) else np.nan
        
        cvr_grp = weighted_ratio(grp, "purchases", "link_clicks")
        cvr_rest = weighted_ratio(rest, "purchases", "link_clicks")
        cvr_eff_with = cvr_grp - cvr_rest
        
        cvr_grp_no = weighted_ratio(grp_no, "purchases", "link_clicks") if len(grp_no) > 0 else np.nan
        cvr_rest_no = weighted_ratio(rest_no, "purchases", "link_clicks") if len(rest_no) > 0 else np.nan
        cvr_eff_no = (cvr_grp_no - cvr_rest_no) if pd.notna(cvr_grp_no) and pd.notna(cvr_rest_no) else np.nan
        
        # Attention metrics
        hook_grp = weighted_ratio(grp, "video_3s_views", "impressions")
        hook_rest = weighted_ratio(rest, "video_3s_views", "impressions")
        hook_eff_with = hook_grp - hook_rest
        
        hook_grp_no = weighted_ratio(grp_no, "video_3s_views", "impressions") if len(grp_no) > 0 else np.nan
        hook_rest_no = weighted_ratio(rest_no, "video_3s_views", "impressions") if len(rest_no) > 0 else np.nan
        hook_eff_no = (hook_grp_no - hook_rest_no) if pd.notna(hook_grp_no) and pd.notna(hook_rest_no) else np.nan
        
        hold_grp = weighted_ratio(grp, "thruplays", "video_3s_views")
        hold_rest = weighted_ratio(rest, "thruplays", "video_3s_views")
        hold_eff_with = hold_grp - hold_rest
        
        hold_grp_no = weighted_ratio(grp_no, "thruplays", "video_3s_views") if len(grp_no) > 0 else np.nan
        hold_rest_no = weighted_ratio(rest_no, "thruplays", "video_3s_views") if len(rest_no) > 0 else np.nan
        hold_eff_no = (hold_grp_no - hold_rest_no) if pd.notna(hold_grp_no) and pd.notna(hold_rest_no) else np.nan
        
        # Share retained for conversion (ROAS)
        if roas_eff_with > 0 and pd.notna(roas_eff_no):
            roas_share = roas_eff_no / roas_eff_with
            roas_pass_lj004 = (roas_share >= 0.50) and (roas_eff_no > 0)
        else:
            roas_share = np.nan
            roas_pass_lj004 = False
            
        # Share retained for attention (Hook)
        if hook_eff_with > 0 and pd.notna(hook_eff_no):
            hook_share = hook_eff_no / hook_eff_with
            hook_pass_lj004 = (hook_share >= 0.50) and (hook_eff_no > 0)
        else:
            hook_share = np.nan
            hook_pass_lj004 = False
            
        results.append({
            "feature": feat,
            "level": str(level),
            "n_ads": n_ads,
            "has_lj004": has_lj004,
            "roas_eff_with": round(roas_eff_with, 4),
            "roas_eff_no": round(roas_eff_no, 4) if pd.notna(roas_eff_no) else np.nan,
            "roas_share": round(roas_share, 4) if pd.notna(roas_share) else np.nan,
            "roas_pass_lj004": roas_pass_lj004,
            "cvr_eff_with": round(cvr_eff_with, 4),
            "cvr_eff_no": round(cvr_eff_no, 4) if pd.notna(cvr_eff_no) else np.nan,
            "hook_eff_with": round(hook_eff_with, 4),
            "hook_eff_no": round(hook_eff_no, 4) if pd.notna(hook_eff_no) else np.nan,
            "hook_share": round(hook_share, 4) if pd.notna(hook_share) else np.nan,
            "hook_pass_lj004": hook_pass_lj004,
            "hold_eff_with": round(hold_eff_with, 4),
            "hold_eff_no": round(hold_eff_no, 4) if pd.notna(hold_eff_no) else np.nan,
        })

res_df = pd.DataFrame(results)
res_df.to_csv("outputs/tables/ad_59_patterns_check.csv", index=False)
print(f"Total patterns evaluated: {len(res_df)}")
print("\nPatterns with has_lj004=True and their ROAS / Hook retention:")
for idx, r in res_df[res_df["has_lj004"]].iterrows():
    print(f"{r['feature']}={r['level']} (n={r['n_ads']}):")
    print(f"   ROAS with={r['roas_eff_with']}, without={r['roas_eff_no']}, share={r['roas_share']}, pass={r['roas_pass_lj004']}")
    print(f"   CVR with={r['cvr_eff_with']}, without={r['cvr_eff_no']}")
    print(f"   Hook with={r['hook_eff_with']}, without={r['hook_eff_no']}, share={r['hook_share']}, pass={r['hook_pass_lj004']}")
    print(f"   Hold with={r['hold_eff_with']}, without={r['hold_eff_no']}")
