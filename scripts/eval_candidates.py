import pandas as pd
df = pd.read_csv('outputs/tables/ad_59_patterns_check.csv')

# Check attention candidates: hook > 0 and hold > 0, n_ads >= 8
att = df[(df['n_ads'] >= 8) & (df['hook_eff_with'] > 0) & (df['hold_eff_with'] > 0)].copy()
att['hold_share'] = att['hold_eff_no'] / att['hold_eff_with']
att['att_pass_50'] = (att['hook_share'] >= 0.50) & (att['hold_eff_no'] > 0)
print('=== ATTENTION CANDIDATES (hook > 0, hold > 0, n >= 8) ===')
for idx, r in att.iterrows():
    print(f"{r['feature']}={r['level']} (n={r['n_ads']}):")
    print(f"   Hook with={r['hook_eff_with']}, without={r['hook_eff_no']}, share={r['hook_share']}")
    print(f"   Hold with={r['hold_eff_with']}, without={r['hold_eff_no']}, share={r['hold_share']}")
    print(f"   Pass 50% rule: {r['att_pass_50']}")

# Check conversion candidates: roas > 0 and cvr > 0, n_ads >= 8
conv = df[(df['n_ads'] >= 8) & (df['roas_eff_with'] > 0) & (df['cvr_eff_with'] > 0)].copy()
conv['cvr_share'] = conv['cvr_eff_no'] / conv['cvr_eff_with']
conv['conv_pass_50'] = (conv['roas_share'] >= 0.50) & (conv['cvr_eff_no'] > 0)
print('\n=== CONVERSION CANDIDATES (roas > 0, cvr > 0, n >= 8) ===')
for idx, r in conv.iterrows():
    print(f"{r['feature']}={r['level']} (n={r['n_ads']}):")
    print(f"   ROAS with={r['roas_eff_with']}, without={r['roas_eff_no']}, share={r['roas_share']}")
    print(f"   CVR with={r['cvr_eff_with']}, without={r['cvr_eff_no']}, share={r['cvr_share']}")
    print(f"   Pass 50% rule: {r['conv_pass_50']}")

