"""Data loading utilities for Little Joys creator selection pipeline.

Never modifies data/raw/.
Parses dates, coerces numeric dtypes, splits list-columns on '; ', and normalises booleans.
"""
from pathlib import Path
from typing import Any, List, Optional
import pandas as pd

from lj.config import RAW_DIR


def _split_list_cell(val: Any) -> List[str]:
    """Split string cell on '; ' into a list of strings, stripping whitespace.

    Returns an empty list for NaN/None/empty values.
    """
    if pd.isna(val) or val is None:
        return []
    if isinstance(val, list):
        return val
    s = str(val).strip()
    if not s:
        return []
    return [item.strip() for item in s.split("; ") if item.strip()]


def load_ads(path: Optional[Path | str] = None) -> pd.DataFrame:
    """Load ads.csv with parsed dates, numeric types, and split list-columns.

    Parameters
    ----------
    path : Optional[Path | str]
        Path to ads.csv. Defaults to RAW_DIR / "ads.csv".

    Returns
    -------
    pd.DataFrame
        Cleanly typed ads DataFrame (100 rows).
    """
    file_path = Path(path) if path is not None else RAW_DIR / "ads.csv"
    df = pd.read_csv(file_path)

    # Dates
    df["launch_date"] = pd.to_datetime(df["launch_date"])
    df["stopped_date"] = pd.to_datetime(df["stopped_date"])

    # Numeric columns
    int_cols = [
        "days_live",
        "impressions",
        "video_3s_views",
        "thruplays",
        "link_clicks",
        "add_to_carts",
        "purchases",
    ]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    float_cols = ["duration_s", "spend_inr", "revenue_inr"]
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    # List columns
    list_cols = [
        "claims_made",
        "child_role",
        "demo_shown",
        "proof_used",
        "persuasion",
        "narratives",
        "ad_categories",
    ]
    for col in list_cols:
        if col in df.columns:
            df[col] = df[col].apply(_split_list_cell)

    return df


def load_creators(path: Optional[Path | str] = None) -> pd.DataFrame:
    """Load creators.csv with parsed types and split list-columns.

    Parameters
    ----------
    path : Optional[Path | str]
        Path to creators.csv. Defaults to RAW_DIR / "creators.csv".

    Returns
    -------
    pd.DataFrame
        Cleanly typed creators DataFrame (20 rows).
    """
    file_path = Path(path) if path is not None else RAW_DIR / "creators.csv"
    df = pd.read_csv(file_path)

    # Numeric columns
    int_cols = ["followers", "following", "total_posts", "posts_in_file"]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # Boolean columns
    if "verified" in df.columns:
        df["verified"] = df["verified"].astype(str).str.lower().str.strip() == "yes"

    # List columns
    list_cols = ["catchphrases", "themes", "format_habits"]
    for col in list_cols:
        if col in df.columns:
            df[col] = df[col].apply(_split_list_cell)

    return df


def load_posts(path: Optional[Path | str] = None) -> pd.DataFrame:
    """Load creator_posts.csv with parsed dates, boolean is_sponsored, and split list-columns.

    Parameters
    ----------
    path : Optional[Path | str]
        Path to creator_posts.csv. Defaults to RAW_DIR / "creator_posts.csv".

    Returns
    -------
    pd.DataFrame
        Cleanly typed creator posts DataFrame (392 rows).
    """
    file_path = Path(path) if path is not None else RAW_DIR / "creator_posts.csv"
    df = pd.read_csv(file_path)

    # Dates
    df["posted_on"] = pd.to_datetime(df["posted_on"])

    # Numeric columns
    int_cols = ["likes", "comments", "reshares", "production_quality_1to5"]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    float_cols = ["duration_s", "plays"]
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    # is_sponsored normalised to boolean
    if "is_sponsored" in df.columns:
        df["is_sponsored_raw"] = df["is_sponsored"]
        df["is_sponsored"] = df["is_sponsored"].astype(str).str.lower().str.strip() == "yes"

    # List columns
    list_cols = ["child_ages", "brands_visible"]
    for col in list_cols:
        if col in df.columns:
            df[col] = df[col].apply(_split_list_cell)

    return df


def load_audience(path: Optional[Path | str] = None) -> pd.DataFrame:
    """Load creator_audience.csv with parsed dates, normalised platform and brand lists.

    Parameters
    ----------
    path : Optional[Path | str]
        Path to creator_audience.csv. Defaults to RAW_DIR / "creator_audience.csv".

    Returns
    -------
    pd.DataFrame
        Cleanly typed creator audience DataFrame (3 rows).
    """
    file_path = Path(path) if path is not None else RAW_DIR / "creator_audience.csv"
    df = pd.read_csv(file_path)

    # Dates
    if "as_of" in df.columns:
        df["as_of"] = pd.to_datetime(df["as_of"])

    # Platform normalised
    if "platform" in df.columns:
        df["platform"] = df["platform"].astype(str).str.lower().str.strip()

    # Numeric columns
    float_cols = ["women_pct", "men_pct"]
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    # List columns
    list_cols = ["age_split", "top_cities", "top_countries", "brands_in_past_year"]
    for col in list_cols:
        if col in df.columns:
            df[col] = df[col].apply(_split_list_cell)

    return df
