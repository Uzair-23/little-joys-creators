"""Tests for Phase 6 creator briefs generation and citation validity."""
from pathlib import Path
import re
import pandas as pd
import pytest

from lj.briefs import BRIEFS_METADATA, render_briefs
from lj.config import BRIEFS_DIR, RAW_DIR, TABLES_DIR
from lj.load import load_ads, load_posts


def test_briefs_generation_and_nine_sections():
    """Verify that all 5 briefs are generated and contain all 9 mandatory sections."""
    generated_files = render_briefs()
    assert len(generated_files) == 5

    required_sections = [
        "## 1. Creator and Why Them",
        "## 2. Creative Angle",
        "## 3. Format and Language",
        "## 4. Three Scripted Hook Lines",
        "## 5. Storyboard & Video Beats",
        "## 6. Whitelisted Proof Element",
        "## 7. Do's and Don'ts",
        "## 8. Risks and Compliance Checklist",
        "## 9. Confidence Level & Known Data Gaps",
    ]

    for fpath in generated_files:
        assert fpath.exists(), f"Missing brief file: {fpath}"
        content = fpath.read_text(encoding="utf-8")
        for sec in required_sections:
            assert sec in content, f"Section '{sec}' missing in {fpath.name}"


def test_all_cited_ad_ids_exist_in_ads_csv():
    """Verify that every ad ID cited across all 5 briefs exists in data/raw/ads.csv."""
    ads_df = load_ads()
    valid_ad_ids = set(ads_df["ad_id"])

    brief_files = list(BRIEFS_DIR.glob("*.md"))
    assert len(brief_files) >= 5

    ad_id_pattern = re.compile(r"\b(LJ-\d{3})\b")

    for fpath in brief_files:
        content = fpath.read_text(encoding="utf-8")
        cited_ads = set(ad_id_pattern.findall(content))
        assert len(cited_ads) > 0, f"No ad IDs cited in {fpath.name}"
        for ad_id in cited_ads:
            assert ad_id in valid_ad_ids, f"Invalid ad ID cited in {fpath.name}: {ad_id}"


def test_all_cited_post_urls_exist_in_creator_posts():
    """Verify that every creator post URL cited across all 5 briefs exists in data/raw/creator_posts.csv."""
    posts_df = load_posts()
    valid_urls = set(posts_df["post_url"].dropna().str.strip())

    brief_files = list(BRIEFS_DIR.glob("*.md"))
    url_pattern = re.compile(r"https://www\.instagram\.com/p/[\w-]+/?")

    for fpath in brief_files:
        content = fpath.read_text(encoding="utf-8")
        cited_urls = set(url_pattern.findall(content))
        assert len(cited_urls) >= 3, f"Fewer than 3 post URLs cited in {fpath.name}"
        for url in cited_urls:
            # Normalize trailing slash
            url_norm = url if url.endswith("/") else url + "/"
            found = (url in valid_urls) or (url_norm in valid_urls) or (url.rstrip("/") in valid_urls)
            assert found, f"Invalid post URL cited in {fpath.name}: {url}"


def test_all_brief_claims_exist_in_whitelist():
    """Verify that the proof element claim in each brief exists in outputs/tables/claims_whitelist.csv."""
    claims_df = pd.read_csv(TABLES_DIR / "claims_whitelist.csv")
    whitelist_claims = set(claims_df["claim"])

    for cid, meta in BRIEFS_METADATA.items():
        claim_used = meta["whitelisted_claim"]
        assert claim_used in whitelist_claims, f"Claim for {cid} is not in claims_whitelist: {claim_used}"

