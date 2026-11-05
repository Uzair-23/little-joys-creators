"""Configuration loader for the Little Joys creator selection pipeline."""
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def get_default_config_path() -> Path:
    """Return default path to config.yaml in repo root."""
    return REPO_ROOT / "config.yaml"


def load_config(config_path: Optional[Path | str] = None) -> Dict[str, Any]:
    """Load and parse configuration YAML file."""
    path = Path(config_path) if config_path is not None else get_default_config_path()
    if not path.is_absolute():
        path = REPO_ROOT / path
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


# Expose singleton and primary constants
CONFIG = load_config()
SEED: int = int(CONFIG.get("seed", 42))
DATA_AS_OF: str = str(CONFIG.get("data_as_of", "2026-10-26"))

# Expose resolved directories
RAW_DIR: Path = REPO_ROOT / CONFIG["paths"]["raw"]
PROCESSED_DIR: Path = REPO_ROOT / CONFIG["paths"]["processed"]
TABLES_DIR: Path = REPO_ROOT / CONFIG["paths"]["tables"]
FIGURES_DIR: Path = REPO_ROOT / CONFIG["paths"]["figures"]
BRIEFS_DIR: Path = REPO_ROOT / CONFIG["paths"]["briefs"]

