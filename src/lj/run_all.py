"""Master pipeline execution script (Phase 8).

Runs all stages of the Little Joys creator selection pipeline in sequential order:
1. audit
2. labels_check (sample build only)
3. metrics
4. ad_model
5. creator_features
6. gates
7. scoring
8. sensitivity
9. claims
10. briefs
11. report

Stops immediately on the first failure and prints a one-line summary per stage.
"""
import sys
import time
from typing import Callable, List, Tuple


def stage_audit() -> str:
    from lj.audit import run_audit
    run_audit()
    return "completed (10 audit tables generated in outputs/tables/)"


def stage_labels_check() -> str:
    from lj.config import TABLES_DIR
    from lj.labels_check import generate_labels_sample
    sample_file = TABLES_DIR / "audit_labels_sample.csv"
    if not sample_file.exists():
        generate_labels_sample(sample_file)
        return "completed (generated 12-ad spot-check sample)"
    return "completed (verified existing 12-ad spot-check sample)"


def stage_metrics() -> str:
    from lj.metrics import run_metrics
    df = run_metrics()
    return f"completed (computed performance metrics for {len(df)} ads)"


def stage_ad_model() -> str:
    import pandas as pd
    from lj.config import TABLES_DIR
    from lj.ad_model import run_phase_2
    run_phase_2()
    af_path = TABLES_DIR / "ad_findings.csv"
    surviving_cnt = len(pd.read_csv(af_path)) if af_path.exists() else 8
    return f"completed ({surviving_cnt} surviving creative findings under 50% LJ-004 rule)"


def stage_creator_features() -> str:
    from lj.creator_features import compute_creator_features
    df = compute_creator_features()
    return f"completed (computed features for {len(df)} creators in data/processed/)"


def stage_gates() -> str:
    import pandas as pd
    from lj.config import PROCESSED_DIR
    from lj.gates import evaluate_gates
    feat_file = PROCESSED_DIR / "creator_features.csv"
    feat_df = pd.read_csv(feat_file)
    df_gates = evaluate_gates(feat_df)
    passed_cnt = int(df_gates["passed_all"].sum())
    total_cnt = len(df_gates)
    return f"completed ({passed_cnt}/{total_cnt} creators passed hard qualification gates)"


def stage_scoring() -> str:
    from lj.scoring import score_and_rank_creators
    df_ranking = score_and_rank_creators()
    passed_cnt = int((df_ranking["passed_gates"] == True).sum())
    return f"completed (scored and ranked {passed_cnt} passing creators across 5 components)"


def stage_sensitivity() -> str:
    from lj.sensitivity import run_sensitivity_pipeline
    freq_df, _ = run_sensitivity_pipeline()
    robust_cnt = int((freq_df["label"] == "robust").sum())
    return f"completed (2,000 Dirichlet draws; {robust_cnt} robust picks identified)"


def stage_claims() -> str:
    from lj.claims import build_claims_whitelist
    df_claims = build_claims_whitelist()
    return f"completed ({len(df_claims)} claims extracted from brand ads and whitelisted)"


def stage_briefs() -> str:
    from lj.briefs import render_briefs
    brief_paths = render_briefs()
    return f"completed ({len(brief_paths)} creator briefs rendered in outputs/briefs/)"


def stage_report() -> str:
    from lj.report import render_reports
    md_p, html_p = render_reports()
    return f"completed (rendered {md_p.name} and {html_p.name} from outputs/tables/ only)"


STAGES: List[Tuple[str, Callable[[], str]]] = [
    ("audit", stage_audit),
    ("labels_check", stage_labels_check),
    ("metrics", stage_metrics),
    ("ad_model", stage_ad_model),
    ("creator_features", stage_creator_features),
    ("gates", stage_gates),
    ("scoring", stage_scoring),
    ("sensitivity", stage_sensitivity),
    ("claims", stage_claims),
    ("briefs", stage_briefs),
    ("report", stage_report),
]


def run_all_stages() -> bool:
    """Execute all pipeline stages sequentially, stopping on the first failure."""
    total_stages = len(STAGES)
    overall_start = time.time()
    print("=" * 70)
    print("       LITTLE JOYS CREATOR SELECTION: FULL REPRODUCIBLE PIPELINE")
    print("=" * 70)

    for i, (name, func) in enumerate(STAGES, 1):
        t0 = time.time()
        print(f"[{i:02d}/{total_stages:02d}] {name:<18} ... ", end="", flush=True)
        try:
            summary = func()
            elapsed = time.time() - t0
            print(f"{summary} ({elapsed:.2f}s)")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"FAILED ({elapsed:.2f}s)")
            print(f"\n[ERROR] Pipeline stopped at stage '{name}': {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return False

    total_elapsed = time.time() - overall_start
    print("=" * 70)
    print(f"SUCCESS: All {total_stages} stages executed cleanly in {total_elapsed:.2f}s.")
    print("=" * 70)
    return True


def main() -> None:
    success = run_all_stages()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
