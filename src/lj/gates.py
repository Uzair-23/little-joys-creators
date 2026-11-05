"""Hard gate evaluation and soft-flag detection for creators (Phase 4).

Evaluates 5 hard disqualification gates:
1. already_partner: past partner of Little Joys in audience or sponsored posts.
2. audience_mismatch: known audience with women share < 50% or India share < 80%.
3. direct_competitor: sponsored partnership with competitor_kids_nutrition (Gritzo).
4. no_family_content: kids or family/food topic share < 15%.
5. too_little_evidence: posts available < 8.

Also records non-disqualifying soft flags:
- child_performer_flag
- sponsored_saturation (> 70% sponsored)
- hidden_metrics (> 25% hidden likes)
- inactive (> 45 days since last post)
- medical_authority_persona (doctor / pediatrician)
"""
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from lj.config import CONFIG, TABLES_DIR
from lj.load import load_audience, load_posts

FOOD_FAMILY_TOPIC_PATTERN = re.compile(
    r"\b(food|nutrition|nutritional|diet|eating|eats|meal|meals|snack|snacks|recipe|recipes|"
    r"milk|feeding|cook|cooking|breakfast|dinner|lunch|puree|biscuit|biscuits|drink|weight gain|"
    r"growth|supplement|supplementation|fruits|vegetables|protein|family|routine|tantrum|"
    r"parenting|baby|child|children|toddler|infant|pediatric|teething)\b",
    re.IGNORECASE,
)


def gate_already_partner(
    creator_id: str,
    brands_in_past_year: str,
    sponsored_brands: List[str],
    config: Dict[str, Any] = CONFIG,
) -> Tuple[bool, str]:
    """Check if creator was previously a partner for the target brand."""
    target_brand = config.get("gates", {}).get("already_partner_brand", "Little Joys").lower().strip()
    
    # Check audience past brands
    if pd.notna(brands_in_past_year) and target_brand in str(brands_in_past_year).lower():
        return False, f"already_partner (audience historical partner: '{brands_in_past_year}')"
    
    # Check visible brands on sponsored posts
    for b in sponsored_brands:
        if pd.notna(b) and target_brand in str(b).lower():
            return False, f"already_partner (sponsored post with brand: '{b}')"

    return True, "ok"


def gate_audience_mismatch(
    audience_known: bool,
    women_share: Optional[float],
    india_share: Optional[float],
    config: Dict[str, Any] = CONFIG,
) -> Tuple[bool, str]:
    """Check if audience demographics match target parent profile (women >= 50%, India >= 80%)."""
    if not audience_known:
        return True, "ok (audience_inferred)"

    min_w = float(config.get("gates", {}).get("min_women_share_known", 0.50))
    min_ind = float(config.get("gates", {}).get("min_india_share_known", 0.80))

    w_val = float(women_share) if pd.notna(women_share) else 0.0
    ind_val = float(india_share) if pd.notna(india_share) else 0.0

    failures = []
    if w_val < min_w:
        failures.append(f"women_share={w_val:.1%} < {min_w:.0%}")
    if ind_val < min_ind:
        failures.append(f"india_share={ind_val:.1%} < {min_ind:.0%}")

    if failures:
        return False, f"audience_mismatch ({', '.join(failures)})"
    return True, "ok"


def gate_direct_competitor(
    competitor_brands_str: str,
    config: Dict[str, Any] = CONFIG,
) -> Tuple[bool, str]:
    """Check if creator worked with direct competitor kids' nutrition brand."""
    comp_list = config.get("brand_categories", {}).get("competitor_kids_nutrition", ["Gritzo"])
    comp_set = set(b.lower().strip() for b in comp_list)

    if pd.notna(competitor_brands_str) and competitor_brands_str.strip().lower() != "none":
        brands = [b.strip() for b in str(competitor_brands_str).split(";") if b.strip()]
        for b in brands:
            if b.lower() in comp_set:
                return False, f"direct_competitor (active partnership with: '{b}')"

    return True, "ok"


def gate_no_family_content(
    creator_posts: pd.DataFrame,
    config: Dict[str, Any] = CONFIG,
) -> Tuple[bool, str]:
    """Check if creator posts sufficient child/family/nutrition content (>= 15%)."""
    min_share = float(config.get("gates", {}).get("min_child_family_share", 0.15))
    if len(creator_posts) == 0:
        return False, "no_family_content (0 posts)"

    has_kids = creator_posts["children_on_camera"].fillna("").str.lower() == "yes"
    has_fam_topic = creator_posts["topic"].fillna("").apply(lambda t: bool(FOOD_FAMILY_TOPIC_PATTERN.search(t)))

    qualifying_posts = has_kids | has_fam_topic
    actual_share = float(qualifying_posts.mean())

    if actual_share < min_share:
        return False, f"no_family_content (child/family content share {actual_share:.1%} < {min_share:.0%})"
    return True, "ok"


def gate_too_little_evidence(
    posts_available: int,
    config: Dict[str, Any] = CONFIG,
) -> Tuple[bool, str]:
    """Check if minimum post count requirement is met."""
    min_p = int(config.get("gates", {}).get("min_posts", 8))
    if posts_available < min_p:
        return False, f"too_little_evidence (posts {posts_available} < {min_p})"
    return True, "ok"


def extract_soft_flags(
    row: pd.Series,
    config: Dict[str, Any] = CONFIG,
) -> List[str]:
    """Detect non-disqualifying soft flags for transparency."""
    cr_cfg = config.get("creators", {})
    spon_flag = float(cr_cfg.get("sponsored_share_flag", 0.70))
    hidden_flag = float(cr_cfg.get("hidden_likes_share_flag", 0.25))
    inactive_days = int(cr_cfg.get("inactive_days_flag", 45))

    flags = []
    if bool(row.get("child_performer_flag", False)):
        flags.append("child_performer_flag")
    if float(row.get("sponsored_share", 0.0)) > spon_flag:
        flags.append(f"sponsored_saturation ({row.get('sponsored_share', 0.0):.1%} > {spon_flag:.0%})")
    if float(row.get("likes_hidden_share", 0.0)) > hidden_flag:
        flags.append(f"hidden_metrics ({row.get('likes_hidden_share', 0.0):.1%} hidden likes)")
    if pd.notna(row.get("days_since_last_post")) and int(row.get("days_since_last_post")) > inactive_days:
        flags.append(f"inactive ({int(row.get('days_since_last_post'))} days > {inactive_days}d)")
    
    persona_str = str(row.get("persona", "")).lower()
    if any(k in persona_str for k in ["pediatric", "doctor", "clinical"]):
        flags.append("medical_authority_persona")

    return flags


def evaluate_gates(
    features_df: pd.DataFrame,
    posts_df: Optional[pd.DataFrame] = None,
    audience_df: Optional[pd.DataFrame] = None,
    config: Dict[str, Any] = CONFIG,
    output_path: Optional[Path | str] = None,
) -> pd.DataFrame:
    """Run all 5 hard gates on all creators and output gate_results.csv."""
    if posts_df is None:
        posts_df = load_posts()
    if audience_df is None:
        audience_df = load_audience()

    out_file = Path(output_path) if output_path is not None else TABLES_DIR / "gate_results.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    records = []

    for _, r in features_df.iterrows():
        cid = str(r["creator_id"])
        handle = str(r["handle"])

        # Creator posts and audience info
        c_posts = posts_df[posts_df["creator_id"] == cid].copy()
        spon_posts = c_posts[c_posts["is_sponsored"] == True]
        spon_brands = []
        for b_raw in spon_posts["brands_visible"].dropna():
            if isinstance(b_raw, list):
                spon_brands.extend(b_raw)
            elif isinstance(b_raw, str):
                spon_brands.extend([x.strip() for x in b_raw.split(";") if x.strip()])

        aud_match = audience_df[audience_df["creator_id"] == cid]
        past_brands_str = str(aud_match.iloc[0].get("brands_in_past_year", "")) if len(aud_match) > 0 else ""

        # Run gates
        p_already, r_already = gate_already_partner(cid, past_brands_str, spon_brands, config)
        p_aud, r_aud = gate_audience_mismatch(bool(r["audience_known"]), r.get("women_share"), r.get("india_share"), config)
        p_comp, r_comp = gate_direct_competitor(str(r.get("competitor_brands", "none")), config)
        p_fam, r_fam = gate_no_family_content(c_posts, config)
        p_evid, r_evid = gate_too_little_evidence(int(r.get("posts_available", 0)), config)

        passed_all = p_already and p_aud and p_comp and p_fam and p_evid

        fail_reasons = []
        if not p_already:
            fail_reasons.append(r_already)
        if not p_aud:
            fail_reasons.append(r_aud)
        if not p_comp:
            fail_reasons.append(r_comp)
        if not p_fam:
            fail_reasons.append(r_fam)
        if not p_evid:
            fail_reasons.append(r_evid)

        gate_reasons_str = "; ".join(fail_reasons) if fail_reasons else "all_gates_passed"

        # Soft flags
        soft_flags_list = extract_soft_flags(r, config)
        soft_flags_str = "; ".join(soft_flags_list) if soft_flags_list else "none"

        records.append({
            "creator_id": cid,
            "handle": handle,
            "passed_all": passed_all,
            "already_partner": p_already,
            "audience_mismatch": p_aud,
            "direct_competitor": p_comp,
            "no_family_content": p_fam,
            "too_little_evidence": p_evid,
            "gate_reasons": gate_reasons_str,
            "soft_flags": soft_flags_str,
        })

    df_gates = pd.DataFrame(records)
    df_gates.to_csv(out_file, index=False)
    return df_gates


def main() -> None:
    """CLI runner for gates evaluation."""
    from lj.config import PROCESSED_DIR
    feat_file = PROCESSED_DIR / "creator_features.csv"
    if not feat_file.exists():
        from lj.creator_features import compute_creator_features
        features_df = compute_creator_features()
    else:
        features_df = pd.read_csv(feat_file)

    df_gates = evaluate_gates(features_df)
    passed_cnt = df_gates["passed_all"].sum()
    total_cnt = len(df_gates)
    print(f"Gates evaluation complete: {passed_cnt}/{total_cnt} creators passed all hard gates.")
    print("Disqualified creators and reasons:")
    disq = df_gates[df_gates["passed_all"] == False]
    for _, r in disq.iterrows():
        print(f"  - {r['creator_id']} (@{r['handle']}): {r['gate_reasons']}")


if __name__ == "__main__":
    main()

