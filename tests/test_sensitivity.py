"""Tests for Phase 5 sensitivity and robustness module."""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from lj.config import CONFIG, FIGURES_DIR, SEED, TABLES_DIR
from lj.sensitivity import run_scenario_variants, run_weight_perturbation


def test_sensitivity_seed_reproducibility():
    """Verify that sensitivity Dirichlet draws are completely reproducible with the same seed."""
    ranking_df = pd.read_csv(TABLES_DIR / "creator_ranking.csv")

    df1 = run_weight_perturbation(ranking_df, config=CONFIG, n_draws=500, seed=42)
    df2 = run_weight_perturbation(ranking_df, config=CONFIG, n_draws=500, seed=42)

    pd.testing.assert_frame_equal(df1, df2)


def test_sensitivity_top5_frequency_properties():
    """Verify top-5 frequencies sum properly and conform to probability bounds [0, 1]."""
    ranking_df = pd.read_csv(TABLES_DIR / "creator_ranking.csv")
    n_draws = 1000

    df_freq = run_weight_perturbation(ranking_df, config=CONFIG, n_draws=n_draws, seed=SEED)

    # Every frequency is in [0, 1]
    assert (df_freq["share_in_top5"] >= 0.0).all()
    assert (df_freq["share_in_top5"] <= 1.0).all()

    # The sum of all selections across creators must equal 5.0
    total_shares = df_freq["share_in_top5"].sum()
    assert np.isclose(total_shares, 5.0, atol=0.01)

    # Check classification categories
    valid_labels = {"robust", "likely", "marginal"}
    assert set(df_freq["label"]).issubset(valid_labels)


def test_sensitivity_outputs_exist():
    """Verify sensitivity outputs are generated in expected paths."""
    freq_file = TABLES_DIR / "sensitivity_top5_frequency.csv"
    variants_file = TABLES_DIR / "sensitivity_variants.csv"
    fig_file = FIGURES_DIR / "top5_stability.png"
    doc_file = Path("docs/robustness.md")

    assert freq_file.exists()
    assert variants_file.exists()
    assert fig_file.exists()
    assert doc_file.exists()

    df_var = pd.read_csv(variants_file)
    assert len(df_var) >= 5
    assert "top_5_creators" in df_var.columns

