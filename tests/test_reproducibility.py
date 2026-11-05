"""Reproducibility test suite (Phase 8).

Runs the full Little Joys selection pipeline twice and asserts that all output
tables in outputs/tables/ are 100% identical across runs (bit-for-bit / numeric reproducibility).
"""
import glob
import os
from pathlib import Path
import pandas as pd
import pytest

from lj.config import TABLES_DIR
from lj.run_all import run_all_stages


def test_pipeline_reproducibility_across_two_runs():
    """Execute pipeline twice and verify all output tables match exactly."""
    # First execution
    success_1 = run_all_stages()
    assert success_1 is True, "Pipeline failed on first run"

    table_files_1 = glob.glob(str(TABLES_DIR / "*.csv"))
    assert len(table_files_1) >= 20, f"Expected >= 20 tables in outputs/tables, got {len(table_files_1)}"

    tables_run1 = {}
    for p in table_files_1:
        tables_run1[os.path.basename(p)] = pd.read_csv(p)

    # Second execution
    success_2 = run_all_stages()
    assert success_2 is True, "Pipeline failed on second run"

    table_files_2 = glob.glob(str(TABLES_DIR / "*.csv"))
    assert len(table_files_1) == len(table_files_2), "Table count differed between pipeline runs"

    # Verify every single table is identical
    for filename, df1 in tables_run1.items():
        file2_path = TABLES_DIR / filename
        assert file2_path.exists(), f"File {filename} missing in second run"
        df2 = pd.read_csv(file2_path)

        pd.testing.assert_frame_equal(
            df1,
            df2,
            check_exact=True,
            check_dtype=True,
            obj=f"Table mismatch in {filename}",
        )

