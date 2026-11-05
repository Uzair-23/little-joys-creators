"""Tests for Phase 6 claims whitelist module."""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from lj.claims import build_claims_whitelist
from lj.config import TABLES_DIR


def test_claims_whitelist_extraction(tmp_path):
    """Verify unique claims extraction and spend-weighted ROAS computation on synthetic ads."""
    synth_ads = pd.DataFrame([
        {
            "ad_id": "LJ-TEST-1",
            "spend_inr": 1000.0,
            "revenue_inr": 2000.0,
            "claims_made": "Zero added sugar; 12g protein per scoop",
        },
        {
            "ad_id": "LJ-TEST-2",
            "spend_inr": 2000.0,
            "revenue_inr": 1000.0,
            "claims_made": "12g protein per scoop; Boosts natural immunity",
        },
    ])

    csv_path = tmp_path / "test_claims.csv"
    doc_path = tmp_path / "test_claims.md"

    df_claims = build_claims_whitelist(
        ads_df=synth_ads,
        output_csv_path=csv_path,
        output_doc_path=doc_path,
    )

    assert len(df_claims) == 3
    claims_set = set(df_claims["claim"])
    assert "Zero added sugar" in claims_set
    assert "12g protein per scoop" in claims_set
    assert "Boosts natural immunity" in claims_set

    # Check 12g protein per scoop (used by both ads)
    prot_row = df_claims[df_claims["claim"] == "12g protein per scoop"].iloc[0]
    assert prot_row["n_ads"] == 2
    assert "LJ-TEST-1" in prot_row["supporting_ad_ids"]
    assert "LJ-TEST-2" in prot_row["supporting_ad_ids"]
    assert prot_row["total_spend_inr"] == 3000.0
    assert prot_row["total_revenue_inr"] == 3000.0
    assert np.isclose(prot_row["spend_weighted_roas"], 1.0)
    assert bool(prot_row["needs_compliance_review"]) is True

    # Immunity claim compliance check
    imm_row = df_claims[df_claims["claim"] == "Boosts natural immunity"].iloc[0]
    assert bool(imm_row["needs_compliance_review"]) is True


def test_real_claims_whitelist_outputs():
    """Verify production claims whitelist table and report exist and contain valid data."""
    csv_file = TABLES_DIR / "claims_whitelist.csv"
    doc_file = Path("docs/claims_whitelist.md")

    assert csv_file.exists()
    assert doc_file.exists()

    df = pd.read_csv(csv_file)
    assert len(df) > 100
    assert "claim" in df.columns
    assert "spend_weighted_roas" in df.columns
    assert "needs_compliance_review" in df.columns

    # Verify that protein and immunity claims are flagged
    prot_claims = df[df["claim"].str.contains(r"\bprotein\b", case=False, na=False)]
    assert prot_claims["needs_compliance_review"].all()
