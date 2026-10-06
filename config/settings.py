"""
Central configuration for the GATE CSE Exam Pattern Forecasting System.
"""
import logging
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
EXTRACTED_DIR = DATA_DIR / "extracted"
CLEANED_DIR = DATA_DIR / "cleaned"
STRUCTURED_DIR = DATA_DIR / "structured"
DB_DIR = DATA_DIR / "db"

RAW_GO_DIR = RAW_DIR / "go"
RAW_OFFICIAL_DIR = RAW_DIR / "official"

# Create directories if they don't exist
for dir_path in [
    DATA_DIR, RAW_DIR, EXTRACTED_DIR, CLEANED_DIR, STRUCTURED_DIR, DB_DIR,
    RAW_GO_DIR, RAW_OFFICIAL_DIR
]:
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

# File paths
DB_PATH = DB_DIR / "gate_forecasting.db"
PROVENANCE_PATH = DATA_DIR / "provenance.json"

# Year ranges
START_YEAR = 1987
END_YEAR = 2026
HOLDOUT_YEAR = 2027

# Era definitions
ERA_DEFINITIONS = {
    "Era 1 (Early)": (1987, 2000),
    "Era 2 (Mid)": (2001, 2012),
    "Era 3 (Modern)": (2013, 2026)
}

# GATE CSE paper codes
PAPER_CODES = ["CS", "CS1", "CS2"]

# GO Release tags
GO_RELEASES = [
    {
        "tag": "gatecse-2027",
        "url": "https://api.github.com/repos/GATEOverflow/GO-PDFs/releases/tags/gatecse-2027"
    },
    {
        "tag": "gatecse-2026",
        "url": "https://api.github.com/repos/GATEOverflow/GO-PDFs/releases/tags/gatecse-2026"
    },
    {
        "tag": "gatecse-2025",
        "url": "https://api.github.com/repos/GATEOverflow/GO-PDFs/releases/tags/gatecse-2025"
    },
    {
        "tag": "gatecse-2024",
        "url": "https://api.github.com/repos/GATEOverflow/GO-PDFs/releases/tags/gatecse-2024"
    },
    {
        "tag": "gatecse-2022-vol1",
        "url": "https://api.github.com/repos/GATEOverflow/GO-PDFs/releases/tags/gatecse-2022-vol1"
    },
    {
        "tag": "gatecse-2022-vol2",
        "url": "https://api.github.com/repos/GATEOverflow/GO-PDFs/releases/tags/gatecse-2022-vol2"
    },
    {
        "tag": "gate-2026-common",
        "url": "https://api.github.com/repos/GATEOverflow/GO-PDFs/releases/tags/gate-2026-common"
    },
    {
        "tag": "engineering-mathematics",
        "url": "https://api.github.com/repos/GATEOverflow/GO-PDFs/releases/tags/engineering-mathematics"
    },
    {
        "tag": "aptitude",
        "url": "https://api.github.com/repos/GATEOverflow/GO-PDFs/releases/tags/aptitude"
    }
]

def setup_logging(log_level: int = logging.INFO) -> None:
    """Sets up the central logging configuration."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=log_level, format=log_format)
