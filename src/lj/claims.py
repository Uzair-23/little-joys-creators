"""Claims whitelist builder module (Phase 6).

Builds outputs/tables/claims_whitelist.csv and docs/claims_whitelist.md from unique
entries in ads.claims_made, computing spend-weighted ROAS and assigning a
needs_compliance_review flag for regulated health outcomes.

Note on Regulatory Compliance:
Advertising children's nutrition is regulated in India under the ASCI Code for
Food and Beverages and FSSAI Advertising and Claims Regulations (2018).
Any claim referencing growth, protein quantities, immunity, or brain development
requires substantiation and prior approval from the brand's legal and regulatory counsel.
This system provides empirical data from past ads and does NOT constitute legal advice.
"""
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import pandas as pd

from lj.config import CONFIG, RAW_DIR, TABLES_DIR
from lj.load import load_ads

COMPLIANCE_PATTERNS = re.compile(
    r"\b(protein|\d+g|growth|height|weight|immunity|immune|brain|focus|memory|"
    r"development|digestion|gut|bones|calcium|teeth|absorption|deficiency|vitamin|"
    r"mineral|iron|zinc|dha|pediatrician|doctor|clinically)\b",
    re.IGNORECASE,
)


def build_claims_whitelist(
    ads_df: Optional[pd.DataFrame] = None,
    output_csv_path: Optional[Path | str] = None,
    output_doc_path: Optional[Path | str] = None,
) -> pd.DataFrame:
    """Build empirical claims whitelist from ads.claims_made."""
    if ads_df is None:
        ads_df = load_ads()

    csv_out = Path(output_csv_path) if output_csv_path is not None else TABLES_DIR / "claims_whitelist.csv"
    doc_out = Path(output_doc_path) if output_doc_path is not None else Path("docs/claims_whitelist.md")
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    doc_out.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for _, row in ads_df.iterrows():
        c_raw = row.get("claims_made")
        if c_raw is None:
            continue
        if isinstance(c_raw, float) and pd.isna(c_raw):
            continue

        claims_list = []
        if isinstance(c_raw, list):
            claims_list = [str(x).strip() for x in c_raw if str(x).strip()]
        elif isinstance(c_raw, str):
            claims_list = [x.strip() for x in c_raw.split(";") if x.strip()]

        ad_id = str(row["ad_id"])
        spend = float(row.get("spend_inr", row.get("spend", 0.0)))
        rev = float(row.get("revenue_inr", row.get("revenue", 0.0)))

        for claim in claims_list:
            records.append({
                "claim": claim,
                "ad_id": ad_id,
                "spend": spend,
                "revenue": rev,
            })

    if not records:
        df_empty = pd.DataFrame(columns=[
            "claim", "n_ads", "supporting_ad_ids", "total_spend_inr",
            "total_revenue_inr", "spend_weighted_roas", "needs_compliance_review"
        ])
        df_empty.to_csv(csv_out, index=False)
        return df_empty

    df_raw = pd.DataFrame(records)

    # Group by claim text
    grouped = df_raw.groupby("claim").agg(
        n_ads=("ad_id", "nunique"),
        supporting_ad_ids=("ad_id", lambda s: "; ".join(sorted(set(s)))),
        total_spend_inr=("spend", "sum"),
        total_revenue_inr=("revenue", "sum"),
    ).reset_index()

    grouped["spend_weighted_roas"] = (
        grouped["total_revenue_inr"] / grouped["total_spend_inr"]
    ).fillna(0.0).round(2)

    # Compliance review flag
    grouped["needs_compliance_review"] = grouped["claim"].apply(
        lambda c: bool(COMPLIANCE_PATTERNS.search(c))
    )

    # Sort by spend descending
    df_sorted = grouped.sort_values(by="total_spend_inr", ascending=False).reset_index(drop=True)
    df_sorted.to_csv(csv_out, index=False)

    # Generate Markdown documentation
    write_claims_markdown(df_sorted, doc_out)

    return df_sorted


def write_claims_markdown(df_claims: pd.DataFrame, doc_path: Path) -> None:
    """Generate docs/claims_whitelist.md report."""
    md = [
        "# Empirical Claims Whitelist (Phase 6 Reference)",
        "",
        "**Date:** 2026-11-05  ",
        "**Source Data:** `data/raw/ads.csv` (`claims_made`)  ",
        "**Generated File:** `outputs/tables/claims_whitelist.csv`  ",
        "",
        "---",
        "",
        "## 1. Compliance & Legal Notice (Rule 11 & ASCI/FSSAI Guidance)",
        "",
        "> [!IMPORTANT]",
        "> **Rule 11 Compliance:** Creator briefs may **only** cite claims that exist in `ads.claims_made`. No invented health outcomes, medical cures, or unsubstantiated statistics may be used in any brief.",
        "> ",
        "> **Regulatory Warning:** Advertising children's nutrition products in India is subject to strict regulatory oversight under the **Advertising Standards Council of India (ASCI) Code** and the **Food Safety and Standards Authority of India (FSSAI) Advertising and Claims Regulations (2018)**. Claims referencing specific nutrient quantities (e.g. `12g protein`), developmental milestones (`growth`, `height`), brain functions (`focus`, `memory`), or immunity require certified laboratory validation. The Little Joys marketing and legal teams must review all creator scripts prior to recording. **This document and code do not constitute legal advice.**",
        "",
        "---",
        "",
        "## 2. Top Whitelisted Claims by Ad Spend & ROAS",
        "",
        "| Claim Text | Supporting Ads Count | Total Spend (₹) | Spend-Weighted ROAS | Needs Legal Review? | Supporting Ad IDs |",
        "|---|---|---|---|---|---|",
    ]

    # Show top 25 claims by spend
    for _, r in df_claims.head(30).iterrows():
        rev_flag = "⚠️ **YES**" if r["needs_compliance_review"] else "No"
        ads_preview = r["supporting_ad_ids"]
        if len(ads_preview) > 35:
            ads_preview = ads_preview[:32] + "..."
        md.append(
            f"| {r['claim']} | {r['n_ads']} | ₹{r['total_spend_inr']:,.0f} | "
            f"{r['spend_weighted_roas']:.2f}x | {rev_flag} | `{ads_preview}` |"
        )

    md.extend([
        "",
        f"*(Full catalog of {len(df_claims)} unique claims saved to `outputs/tables/claims_whitelist.csv`)*",
        "",
        "---",
        "",
        "## 3. Compliance Classification Summary",
        f"- **Total Unique Claims Extracted:** {len(df_claims)}",
        f"- **Claims Requiring Legal Review:** {df_claims['needs_compliance_review'].sum()} ({df_claims['needs_compliance_review'].mean():.1%})",
        f"- **General / Sensory / Routine Claims:** {(~df_claims['needs_compliance_review']).sum()}",
        "",
    ])

    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")


def main() -> None:
    """CLI runner for claims whitelist."""
    print("=== Building Claims Whitelist (Phase 6) ===")
    df = build_claims_whitelist()
    print(f"Claims whitelist built: {len(df)} unique claims written to outputs/tables/claims_whitelist.csv")
    print(f"Legal review flagged for {df['needs_compliance_review'].sum()} claims.")


if __name__ == "__main__":
    main()
