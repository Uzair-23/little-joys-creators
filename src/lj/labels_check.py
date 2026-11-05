"""Label spot-check sampling and error rate calculation module.

Draws a fixed random sample of 12 ads (seed from config.yaml) and writes
outputs/tables/audit_labels_sample.csv with empty verification columns for human review.
Provides a function to read the reviewed file and calculate the error rate per label column.
"""
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
import pandas as pd

from lj.config import SEED, TABLES_DIR
from lj.load import load_ads

LABEL_COLUMNS = [
    "hook_type",
    "language",
    "child_on_screen",
    "creator_type",
    "ad_format",
]


def generate_labels_sample(
    output_path: Optional[Path | str] = None,
    seed: Optional[int] = None,
    n: int = 12,
) -> pd.DataFrame:
    """Draw a reproducible random sample of ads for human spot-checking of AI labels.

    Parameters
    ----------
    output_path : Optional[Path | str]
        Where to save audit_labels_sample.csv. Defaults to TABLES_DIR / "audit_labels_sample.csv".
    seed : Optional[int]
        Random seed. Defaults to SEED from config.yaml.
    n : int
        Number of ads to sample. Defaults to 12.

    Returns
    -------
    pd.DataFrame
        Sampled ads with empty human review columns.
    """
    out_file = Path(output_path) if output_path is not None else TABLES_DIR / "audit_labels_sample.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    random_seed = seed if seed is not None else SEED
    ads = load_ads()

    sample = ads.sample(n=n, random_state=random_seed).sort_values("ad_id").copy()

    # Base columns
    base_cols = ["ad_id", "hook_line", "transcript"] + LABEL_COLUMNS
    sample_df = sample[base_cols].copy()

    # Empty user-facing agree/label columns
    sample_df["human_label"] = ""
    sample_df["agree"] = ""

    # Per-column verification columns for granular evaluation
    for col in LABEL_COLUMNS:
        sample_df[f"human_{col}"] = ""
        sample_df[f"agree_{col}"] = ""

    sample_df.to_csv(out_file, index=False)
    return sample_df


def _is_truthy(val: Any) -> Optional[bool]:
    """Parse common boolean representations (yes, no, true, false, 1, 0)."""
    if pd.isna(val) or val is None:
        return None
    s = str(val).strip().lower()
    if s in ["yes", "y", "true", "1", "agree"]:
        return True
    if s in ["no", "n", "false", "0", "disagree"]:
        return False
    return None


def compute_label_error_rate(
    sample_path_or_df: Optional[Path | str | pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Read human-reviewed sample and compute the label error rate per column.

    Supports per-column agree (agree_<col>), per-column human correction (human_<col>),
    or overall agree column.

    Parameters
    ----------
    sample_path_or_df : Optional[Path | str | pd.DataFrame]
        Path to CSV or loaded DataFrame. Defaults to TABLES_DIR / "audit_labels_sample.csv".

    Returns
    -------
    Dict[str, Any]
        Dictionary with per-column error rate, overall error rate, and counts.
    """
    if isinstance(sample_path_or_df, pd.DataFrame):
        df = sample_path_or_df.copy()
    else:
        file_path = (
            Path(sample_path_or_df)
            if sample_path_or_df is not None
            else TABLES_DIR / "audit_labels_sample.csv"
        )
        if not file_path.exists():
            raise FileNotFoundError(f"Label sample file not found at {file_path}. Run generate_labels_sample() first.")
        df = pd.read_csv(file_path)

    col_results: Dict[str, Dict[str, Any]] = {}
    total_evaluated = 0
    total_errors = 0

    for col in LABEL_COLUMNS:
        eval_count = 0
        err_count = 0

        agree_col = f"agree_{col}"
        human_col = f"human_{col}"

        for _, row in df.iterrows():
            ai_val = row.get(col)

            # 1. Check explicit agree_<col>
            if agree_col in row and pd.notna(row[agree_col]) and str(row[agree_col]).strip():
                bool_val = _is_truthy(row[agree_col])
                if bool_val is not None:
                    eval_count += 1
                    if not bool_val:
                        err_count += 1
                    continue

            # 2. Check explicit human_<col>
            if human_col in row and pd.notna(row[human_col]) and str(row[human_col]).strip():
                human_val = str(row[human_col]).strip().lower()
                ai_str = str(ai_val).strip().lower() if pd.notna(ai_val) else ""
                eval_count += 1
                if human_val != ai_str:
                    err_count += 1
                continue

            # 3. If global agree column is filled and no per-col info exists
            if "agree" in row and pd.notna(row["agree"]) and str(row["agree"]).strip():
                bool_val = _is_truthy(row["agree"])
                if bool_val is not None:
                    eval_count += 1
                    if not bool_val:
                        err_count += 1

        err_rate = (err_count / eval_count) if eval_count > 0 else 0.0
        col_results[col] = {
            "evaluated": eval_count,
            "errors": err_count,
            "error_rate": round(err_rate, 4),
            "agreement_rate": round(1.0 - err_rate, 4),
        }
        total_evaluated += eval_count
        total_errors += err_count

    overall_error_rate = (total_errors / total_evaluated) if total_evaluated > 0 else 0.0

    report = {
        "total_ads_sampled": len(df),
        "total_labels_evaluated": total_evaluated,
        "total_errors_found": total_errors,
        "overall_error_rate": round(overall_error_rate, 4),
        "columns": col_results,
    }
    return report


if __name__ == "__main__":
    sample_file = TABLES_DIR / "audit_labels_sample.csv"
    regenerate = "--regenerate" in sys.argv

    if not sample_file.exists() or regenerate:
        sample_df = generate_labels_sample(sample_file)
        print(f"Generated new label sample of {len(sample_df)} ads at {sample_file}")
    else:
        sample_df = pd.read_csv(sample_file)
        print(f"Loaded existing label sample from {sample_file}")

    report = compute_label_error_rate(sample_df)

    print("\n" + "=" * 65)
    print("                 AI LABEL SPOT-CHECK ERROR REPORT")
    print("=" * 65)
    print(f"{'Label Column':<20} {'Evaluated':<10} {'Errors':<8} {'Error Rate':<12} {'Agree Rate':<10}")
    print("-" * 65)
    for col, metrics in report["columns"].items():
        err_pct = f"{metrics['error_rate']:.2%}"
        agr_pct = f"{metrics['agreement_rate']:.2%}"
        print(f"{col:<20} {metrics['evaluated']:<10} {metrics['errors']:<8} {err_pct:<12} {agr_pct:<10}")
    print("-" * 65)
    tot_eval = report["total_labels_evaluated"]
    tot_err = report["total_errors_found"]
    ovr_err = f"{report['overall_error_rate']:.2%}"
    ovr_agr = f"{1.0 - report['overall_error_rate']:.2%}"
    print(f"{'OVERALL':<20} {tot_eval:<10} {tot_err:<8} {ovr_err:<12} {ovr_agr:<10}")
    print("=" * 65)
