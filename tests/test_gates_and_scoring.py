"""Tests for Phase 4 gates and creator scoring pipeline."""
import numpy as np
import pandas as pd
import pytest

from lj.config import CONFIG, TABLES_DIR
from lj.gates import evaluate_gates, gate_already_partner
from lj.scoring import (
    compute_audience_fit_score,
    compute_commercial_risk_score,
    score_and_rank_creators,
)


def test_cr20_fails_already_partner_gate():
    """Verify that CR-20 fails the already_partner gate due to past brand partnership."""
    features_df = pd.read_csv("data/processed/creator_features.csv")
    gates_df = evaluate_gates(features_df)

    cr20_row = gates_df[gates_df["creator_id"] == "CR-20"].iloc[0]
    assert bool(cr20_row["already_partner"]) is False
    assert bool(cr20_row["passed_all"]) is False
    assert "already_partner" in cr20_row["gate_reasons"]


def test_synthetic_creator_100pct_sponsored_risk_penalty():
    """Verify that a creator with 100% sponsored posts incurs the commercial risk penalty."""
    synthetic_row = pd.Series({
        "creator_id": "CR-SYN-SPON",
        "handle": "sponsored_heavy_creator",
        "adjacent_brands": "none",
        "sponsored_share": 1.00,  # 100% sponsored (> 70% threshold)
        "days_since_last_post": 10,
        "child_performer_flag": False,
    })

    risk_score, reasons = compute_commercial_risk_score(synthetic_row, config=CONFIG)
    # Saturation above 70% scaled up to 0.30 max penalty: (1.0 - 0.70) / (0.30) * 0.30 = 0.30 penalty
    assert np.isclose(risk_score, 0.70)
    assert any("sponsored_saturation" in r for r in reasons)


def test_unknown_audience_neutral_score_and_lower_confidence():
    """Verify that unknown audience receives neutral 0.50 score and lowers confidence point."""
    # 1. Unknown audience score check
    aud_score_unknown = compute_audience_fit_score(
        audience_known=False,
        women_share=np.nan,
        india_share=np.nan,
        age_split_str=None,
        config=CONFIG,
    )
    assert aud_score_unknown == 0.50

    # 2. Compare against known audience
    aud_score_known = compute_audience_fit_score(
        audience_known=True,
        women_share=0.834,
        india_share=0.883,
        age_split_str="25-34 71.9%; 35-44 19.6%",
        config=CONFIG,
    )
    assert aud_score_known > 0.50

    # 3. Confidence verification in ranking output
    ranking_df = score_and_rank_creators()
    # CR-15 has known audience -> receives audience point
    cr15 = ranking_df[ranking_df["creator_id"] == "CR-15"].iloc[0]
    assert "audience_known" in cr15["confidence_reasons"]
    assert cr15["confidence"] == "high"

    # CR-08 has unknown audience -> does not receive audience point
    cr08 = ranking_df[ranking_df["creator_id"] == "CR-08"].iloc[0]
    assert "audience_known" not in cr08["confidence_reasons"]
    assert cr08["confidence"] == "medium"


def test_creator_ranking_output_structure():
    """Verify creator_ranking.csv contains 20 creators, valid ranks 1-13, and all required columns."""
    ranking_df = score_and_rank_creators()

    assert len(ranking_df) == 20
    required_cols = [
        "creator_id",
        "handle",
        "passed_gates",
        "gate_reasons",
        "creative_fit",
        "reach_quality",
        "engagement_quality",
        "audience_fit",
        "commercial_risk",
        "total",
        "rank",
        "confidence",
        "confidence_reasons",
        "findings_used",
        "soft_flags",
    ]
    for col in required_cols:
        assert col in ranking_df.columns, f"Missing required column: {col}"

    passing = ranking_df[ranking_df["passed_gates"] == True]
    disqualified = ranking_df[ranking_df["passed_gates"] == False]

    assert len(passing) == 13
    assert len(disqualified) == 7

    # Passing creators have ranks 1 to 13
    assert sorted(passing["rank"].astype(int).tolist()) == list(range(1, 14))
    assert disqualified["rank"].isna().all()


def test_disqualified_creators_reasons():
    """Verify that each disqualified creator failed the expected gates."""
    gates_df = evaluate_gates(pd.read_csv("data/processed/creator_features.csv"))

    # CR-05, CR-10, CR-11 fail direct_competitor
    for cid in ["CR-05", "CR-10", "CR-11"]:
        row = gates_df[gates_df["creator_id"] == cid].iloc[0]
        assert bool(row["direct_competitor"]) is False

    # CR-06 fails no_family_content
    cr06 = gates_df[gates_df["creator_id"] == "CR-06"].iloc[0]
    assert bool(cr06["no_family_content"]) is False

    # CR-09 fails already_partner
    cr09 = gates_df[gates_df["creator_id"] == "CR-09"].iloc[0]
    assert bool(cr09["already_partner"]) is False

    # CR-14 fails audience_mismatch
    cr14 = gates_df[gates_df["creator_id"] == "CR-14"].iloc[0]
    assert bool(cr14["audience_mismatch"]) is False

    # CR-20 fails already_partner and audience_mismatch
    cr20 = gates_df[gates_df["creator_id"] == "CR-20"].iloc[0]
    assert bool(cr20["already_partner"]) is False
    assert bool(cr20["audience_mismatch"]) is False
