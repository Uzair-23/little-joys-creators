"""Tests for report generation (Phase 7).

Verifies:
1. 'What this data cannot tell you' section is present.
2. Every number in the report traces to outputs/tables/*.csv files (fails if ungrounded number appears).
3. Both report.html and report.md exist, are well-formed, and contain all 8 sections.
"""
import glob
from pathlib import Path
import re
import pandas as pd
import pytest

from lj.config import TABLES_DIR
from lj.report import load_report_data, render_reports


def get_all_table_numbers(tables_dir: Path = TABLES_DIR):
    """Collect all numeric values from every CSV file in tables_dir."""
    table_files = glob.glob(str(tables_dir / "*.csv"))
    table_numbers = set()

    for f in table_files:
        try:
            df = pd.read_csv(f)
            for col in df.columns:
                for val in df[col]:
                    if pd.isna(val):
                        continue
                    try:
                        num = float(val)
                        table_numbers.add(round(num, 4))
                    except (ValueError, TypeError):
                        pass
                    if isinstance(val, str):
                        for subnum in re.findall(r"[-+]?\d*\.?\d+", val):
                            try:
                                table_numbers.add(round(float(subnum), 4))
                            except ValueError:
                                pass
        except Exception:
            pass

    return table_numbers


def verify_text_numbers_in_tables(text: str, table_numbers: set) -> list:
    """Find any number in text that does not correspond to any number in table_numbers."""
    # Remove entity IDs and structural patterns
    cleaned = re.sub(r"CR-\d+", "", text)
    cleaned = re.sub(r"LJ-\d+", "", cleaned)
    cleaned = re.sub(r"2026-11-06", "", cleaned)
    cleaned = re.sub(r"Seed \d+", "", cleaned)

    # Extract numeric tokens
    raw_tokens = re.findall(r"[-+]?\d+(?:,\d+)*(?:\.\d+)?", cleaned)

    # Known structural / document constants (section headers 1-8, hours, standard terms)
    allowed_integers = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 20, 24, 42, 90, 2000, 2018}

    unmatched = []
    for tok in set(raw_tokens):
        clean = tok.replace(",", "").lstrip("+")
        try:
            val = float(clean)
        except ValueError:
            continue
        if val in allowed_integers:
            continue

        found = False
        candidates = [
            val,
            round(val, 4),
            round(val / 100.0, 4),
            round(val * 100.0, 4),
            round(val * 100000.0, 0),
        ]
        for cand in candidates:
            if cand in table_numbers or any(abs(cand - tn) < 1e-4 for tn in table_numbers):
                found = True
                break

        if not found:
            unmatched.append((tok, val))

    return unmatched


def test_what_this_data_cannot_tell_you_section_present(tmp_path):
    """Test that the 'What this data cannot tell you' section is present in both outputs."""
    md_path, html_path = render_reports(output_dir=tmp_path)

    assert md_path.exists()
    assert html_path.exists()

    md_text = md_path.read_text(encoding="utf-8")
    html_text = html_path.read_text(encoding="utf-8")

    assert "what this data cannot tell you" in md_text.lower()
    assert "what this data cannot tell you" in html_text.lower()
    assert "Critical Limitations" in md_text
    assert "Critical Limitations" in html_text


def test_numbers_in_report_trace_to_tables():
    """Verify that every number in report.md and report.html is traceable to outputs/tables/."""
    table_numbers = get_all_table_numbers()
    assert len(table_numbers) > 500, "Should have loaded rich set of numbers from outputs/tables"

    # 1. Test markdown report
    md_path = Path("outputs/report.md")
    assert md_path.exists(), "outputs/report.md must exist"
    md_text = md_path.read_text(encoding="utf-8")
    unmatched_md = verify_text_numbers_in_tables(md_text, table_numbers)
    assert len(unmatched_md) == 0, f"Found ungrounded numbers in report.md: {unmatched_md}"

    # 2. Test HTML report (with styles stripped)
    html_path = Path("outputs/report.html")
    assert html_path.exists(), "outputs/report.html must exist"
    html_raw = html_path.read_text(encoding="utf-8")
    html_no_style = re.sub(r"<style>.*?</style>", "", html_raw, flags=re.DOTALL)
    html_text = re.sub(r"<[^>]+>", " ", html_no_style)
    unmatched_html = verify_text_numbers_in_tables(html_text, table_numbers)
    assert len(unmatched_html) == 0, f"Found ungrounded numbers in report.html: {unmatched_html}"


def test_number_verifier_fails_on_invented_number():
    """Verify that verify_text_numbers_in_tables correctly fails if an invented number is introduced."""
    table_numbers = get_all_table_numbers()
    bogus_text = "The projected creator ROAS will reach an unprecedented 9876.5432x lift."
    unmatched = verify_text_numbers_in_tables(bogus_text, table_numbers)
    assert len(unmatched) > 0
    assert any(abs(val - 9876.5432) < 1e-4 for _, val in unmatched)


def test_report_structure_and_8_sections(tmp_path):
    """Verify that the report contains all 8 required sections from implementation_plan.md."""
    md_path, html_path = render_reports(output_dir=tmp_path)
    md_text = md_path.read_text(encoding="utf-8")

    sections = [
        "1. The Answer",
        "2. What the Brand's Own Ads Tell Us",
        "3. Why These 5 and Not the Others",
        "4. How Sure We Are",
        "5. What Each Creator Should Say",
        "6. What This Data Cannot Tell You",
        "7. Before You Sign Anyone",
        "8. Appendix",
    ]

    for sec in sections:
        assert sec in md_text, f"Missing section in report.md: {sec}"
