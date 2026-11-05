"""Tests for the data audit module (src/lj/audit.py and src/lj/labels_check.py)."""
import pandas as pd
from lj.audit import audit_days_live, run_audit
from lj.config import TABLES_DIR
from lj.labels_check import compute_label_error_rate, generate_labels_sample


def test_audit_runs_and_writes_tables(tmp_path):
    summary = run_audit(output_dir=tmp_path)
    assert summary["total_ads"] == 100
    assert summary["total_creators"] == 20
    assert summary["total_posts"] == 392
    assert summary["total_audience_known"] == 3

    expected_tables = [
        "audit_missing_values.csv",
        "audit_duplicates.csv",
        "audit_funnel_violations.csv",
        "audit_days_live.csv",
        "audit_concentration.csv",
        "audit_spend_flags.csv",
        "audit_creator_data_quality.csv",
        "audit_brands_visible.csv",
        "audit_distinct_labels.csv",
        "audit_audience.csv",
    ]
    for table_name in expected_tables:
        assert (tmp_path / table_name).exists(), f"Missing table {table_name}"


def test_lj089_flagged_as_zero_purchase_high_spend():
    run_audit()
    df_flags = pd.read_csv(TABLES_DIR / "audit_spend_flags.csv")
    zero_purchase_flags = df_flags[df_flags["flag_type"] == "zero_purchase_high_spend"]

    assert "LJ-089" in zero_purchase_flags["ad_id"].values
    lj089_row = zero_purchase_flags[zero_purchase_flags["ad_id"] == "LJ-089"].iloc[0]
    assert lj089_row["purchases"] == 0
    assert lj089_row["spend_inr"] >= 100000
    assert lj089_row["add_to_carts"] > 0


def test_lj004_flagged_as_concentration_outlier():
    run_audit()
    df_conc = pd.read_csv(TABLES_DIR / "audit_concentration.csv")
    top_1 = df_conc[df_conc["top_k"] == 1].iloc[0]

    assert "LJ-004" in top_1["top_revenue_ad_ids"]
    assert "LJ-004" in top_1["top_spend_ad_ids"]
    assert top_1["revenue_share"] > 0.25  # LJ-004 is ~30.3% of total revenue


def test_duplicate_pairs_unique_count_and_detection():
    summary = run_audit()
    assert summary["duplicate_pairs_count"] == 3

    df_dup = pd.read_csv(TABLES_DIR / "audit_duplicates.csv")
    assert df_dup["pair_id"].nunique() == 3
    expected_pairs = {"PAIR-LJ-003-LJ-059", "PAIR-LJ-036-LJ-056", "PAIR-LJ-073-LJ-093"}
    assert set(df_dup["pair_id"].unique()) == expected_pairs
    # Check that each was matched across both transcript and hook_line
    assert set(df_dup["match_type"].unique()) == {"both"}

    ad_ids_in_dups = set(df_dup["ad_id"].tolist())
    assert {"LJ-003", "LJ-059"}.issubset(ad_ids_in_dups)
    assert {"LJ-036", "LJ-056"}.issubset(ad_ids_in_dups)
    assert {"LJ-073", "LJ-093"}.issubset(ad_ids_in_dups)


def test_days_live_synthetic_flagging():
    """Synthetic check that a 2-day difference is flagged but a 1-day difference is not."""
    synthetic_ads = pd.DataFrame([
        {"ad_id": "AD-EXACT", "launch_date": "2026-09-01", "stopped_date": "2026-09-05", "days_live": 4},   # diff = 0
        {"ad_id": "AD-MINUS1", "launch_date": "2026-09-01", "stopped_date": "2026-09-05", "days_live": 3},  # diff = -1
        {"ad_id": "AD-PLUS1", "launch_date": "2026-09-01", "stopped_date": "2026-09-05", "days_live": 5},   # diff = +1
        {"ad_id": "AD-MINUS2", "launch_date": "2026-09-01", "stopped_date": "2026-09-05", "days_live": 2},  # diff = -2 (FLAG)
        {"ad_id": "AD-PLUS2", "launch_date": "2026-09-01", "stopped_date": "2026-09-05", "days_live": 6},   # diff = +2 (FLAG)
    ])

    df_dist = audit_days_live(synthetic_ads)

    # Convert difference_days to is_flagged mapping
    flag_map = dict(zip(df_dist["difference_days"], df_dist["is_flagged"]))

    assert flag_map[0] is False, "0-day difference should not be flagged"
    assert flag_map[-1] is False, "-1-day difference should not be flagged (1-day convention)"
    assert flag_map[1] is False, "+1-day difference should not be flagged (1-day convention)"
    assert flag_map[-2] is True, "-2-day difference must be flagged as anomaly"
    assert flag_map[2] is True, "+2-day difference must be flagged as anomaly"


def test_labels_sample_and_error_rate_calculation(tmp_path):
    sample_file = tmp_path / "audit_labels_sample.csv"
    sample = generate_labels_sample(output_path=sample_file, seed=42, n=12)

    assert len(sample) == 12
    assert "human_label" in sample.columns
    assert "agree" in sample.columns

    # Test error rate computation on synthetic filled data
    sample_copy = sample.copy()
    sample_copy["agree_hook_type"] = ["yes"] * 10 + ["no"] * 2
    sample_copy["agree_language"] = ["yes"] * 12

    report = compute_label_error_rate(sample_copy)
    assert report["total_ads_sampled"] == 12
    assert report["columns"]["hook_type"]["evaluated"] == 12
    assert report["columns"]["hook_type"]["errors"] == 2
    assert abs(report["columns"]["hook_type"]["error_rate"] - (2 / 12)) < 1e-3
    assert report["columns"]["language"]["errors"] == 0
