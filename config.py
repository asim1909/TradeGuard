"""
Configuration Module for Trade Reconciliation & Control Automation Engine.

Centralizes all project settings, directory paths, file formats, database locations,
logging rules, reconciliation tolerance thresholds, and synthetic generator parameters.

Uses pathlib for cross-platform compatibility across Windows, Linux, and macOS.
"""

from pathlib import Path
from typing import List

# =============================================================================
# PROJECT ROOT & DIRECTORY HIERARCHY
# =============================================================================

# Root directory of the repository
PROJECT_ROOT: Path = Path(__file__).resolve().parent

# Data directory structure
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
SAMPLE_OUTPUT_DIR: Path = DATA_DIR / "sample_output"

# Raw CSV File Destinations
FRONT_OFFICE_CSV_PATH: Path = RAW_DATA_DIR / "front_office.csv"
BACK_OFFICE_CSV_PATH: Path = RAW_DATA_DIR / "back_office.csv"

# Database directory & schema path
DATABASE_DIR: Path = PROJECT_ROOT / "database"
SCHEMA_PATH: Path = DATABASE_DIR / "schema.sql"
DEFAULT_DB_NAME: str = "trade_reconciliation.db"
DEFAULT_DB_PATH: Path = DATABASE_DIR / DEFAULT_DB_NAME

# Reports directory structure
REPORTS_DIR: Path = PROJECT_ROOT / "reports"
EXCEL_REPORTS_DIR: Path = REPORTS_DIR / "excel"
CSV_REPORTS_DIR: Path = REPORTS_DIR / "csv"
JSON_REPORTS_DIR: Path = REPORTS_DIR / "json"
CHARTS_DIR: Path = REPORTS_DIR / "charts"
POWERBI_REPORTS_DIR: Path = REPORTS_DIR / "powerbi"
PDF_REPORTS_DIR: Path = REPORTS_DIR / "pdf"

# Logs directory structure
LOGS_DIR: Path = PROJECT_ROOT / "logs"
DEFAULT_LOG_FILENAME: str = "trade_reconciliation.log"
LOG_FILE_PATH: Path = LOGS_DIR / DEFAULT_LOG_FILENAME

# Documentation and Assets
DOCS_DIR: Path = PROJECT_ROOT / "docs"
ASSETS_DIR: Path = PROJECT_ROOT / "assets"

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(module)s:%(lineno)d | %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB rotating size
LOG_BACKUP_COUNT: int = 5

# =============================================================================
# SYNTHETIC DATA GENERATOR CONFIGURATION
# =============================================================================

DEFAULT_NUM_TRADES: int = 1000
DEFAULT_RANDOM_SEED: int = 42
DEFAULT_BREAK_RATE: float = 0.04  # ~3-5% target break ratio
DEFAULT_RECONCILE_THRESHOLD: float = 0.01  # $0.01 price variance tolerance threshold

# Generator Domain Value Lists
TRADERS: List[str] = [
    "Rahul Sharma",
    "John Smith",
    "Priya Patel",
    "Amit Verma",
    "David Miller",
    "Sarah Jenkins",
]

DESKS: List[str] = [
    "Equities",
    "Fixed Income",
    "FX",
    "Commodities",
    "Derivatives",
]

PORTFOLIOS: List[str] = [
    "Global Alpha",
    "Income Growth",
    "Momentum",
    "Balanced",
    "Macro Hedge",
]

COUNTERPARTIES: List[str] = [
    "Goldman Sachs",
    "JP Morgan",
    "Morgan Stanley",
    "Citi",
    "Barclays",
    "HSBC",
]

ASSET_CLASSES: List[str] = [
    "Equity",
    "Bond",
    "ETF",
    "FX",
    "Commodity",
    "Derivative",
]

SYMBOLS: List[str] = [
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOG",
    "META",
    "TSLA",
    "AMZN",
    "NFLX",
    "IBM",
    "ORCL",
]

BUY_SELL_SIDES: List[str] = ["BUY", "SELL"]

CURRENCIES: List[str] = ["USD", "EUR", "GBP", "JPY", "INR"]

TRADE_STATUSES: List[str] = ["BOOKED", "CONFIRMED", "SETTLED", "PENDING"]

# =============================================================================
# RECONCILIATION & DOMAIN SETTINGS
# =============================================================================

# Monetary threshold difference tolerance (e.g., 0.01 currency unit)
RECONCILIATION_THRESHOLD: float = 0.01

# Quantity threshold difference tolerance (e.g., 0.0 for exact unit match)
QUANTITY_THRESHOLD: float = 0.0

# Standardized date formatting string
DATE_FORMAT: str = "%Y-%m-%d"
TIMESTAMP_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# Financial Domain Enums / Standard Lists
SUPPORTED_CURRENCIES: List[str] = CURRENCIES
SUPPORTED_ASSET_CLASSES: List[str] = ASSET_CLASSES
SUPPORTED_STATUS_VALUES: List[str] = TRADE_STATUSES

# Default system reporting options
DEFAULT_REPORT_NAME: str = "trade_reconciliation_break_report"
CHART_DPI: int = 300
CHART_STYLE: str = "ggplot"


def ensure_project_directories() -> None:
    """
    Utility function to ensure all required project directories exist on startup.
    Creates missing directories gracefully.
    """
    directories = [
        RAW_DATA_DIR,
        PROCESSED_DATA_DIR,
        SAMPLE_OUTPUT_DIR,
        DATABASE_DIR,
        EXCEL_REPORTS_DIR,
        CSV_REPORTS_DIR,
        JSON_REPORTS_DIR,
        CHARTS_DIR,
        LOGS_DIR,
        DOCS_DIR,
        ASSETS_DIR,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
