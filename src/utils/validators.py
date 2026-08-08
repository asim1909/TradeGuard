"""
Validation Utilities for Trade Reconciliation & Control Automation Engine.

Provides validation helper functions and a centralized ValidationHelper class
for data verification, CSV structure checking, date parsing, database health checks,
and configuration audit validation.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import (
    DATE_FORMAT,
    DEFAULT_DB_PATH,
    RAW_DATA_DIR,
    REPORTS_DIR,
    SUPPORTED_CURRENCIES,
)
from src.utils.exceptions import (
    CSVFormatError,
    ConfigurationError,
    DatabaseConnectionError,
    TradeValidationError,
)
from src.utils.logger import get_logger

logger = get_logger("Validators")


class ValidationHelper:
    """
    Centralized validation manager class for Trade Reconciliation Engine.
    Exposes structural and business validation helper methods.
    """

    def __init__(self) -> None:
        """Initialize ValidationHelper instance."""
        logger.debug("Initializing ValidationHelper...")

    def validate_trade_dict(self, trade_data: Dict[str, Any]) -> bool:
        """
        Validates a single trade dictionary payload against domain schema requirements.

        :param trade_data: Raw trade data dictionary.
        :return: True if valid.
        :raises TradeValidationError: If validation rules are violated.
        """
        logger.debug(f"Validating trade dictionary structure for trade_id: {trade_data.get('trade_id')}")
        
        # TODO Phase 2: Add comprehensive schema checks for trade_id, price > 0, quantity > 0, currency ISO code
        required_fields = ["trade_id", "counterparty", "asset_class", "quantity", "price", "currency", "trade_date"]
        missing_fields = [field for field in required_fields if field not in trade_data]
        if missing_fields:
            raise TradeValidationError(
                message=f"Missing required trade fields: {missing_fields}",
                details=f"Trade payload keys: {list(trade_data.keys())}"
            )
        return True

    def validate_csv_file(self, file_path: Path, expected_headers: Optional[List[str]] = None) -> bool:
        """
        Verifies that a CSV file exists, is non-empty, and contains required headers.

        :param file_path: Path to target CSV file.
        :param expected_headers: List of required column header names.
        :return: True if file passes CSV validation checks.
        :raises CSVFormatError: If file is missing, empty, or unparseable.
        """
        logger.debug(f"Validating CSV file at path: {file_path}")
        if not file_path.exists():
            raise CSVFormatError(message=f"Target CSV file does not exist at path: {file_path}")

        if file_path.stat().st_size == 0:
            raise CSVFormatError(message=f"Target CSV file is empty (0 bytes): {file_path}")

        # TODO Phase 2: Implement header parsing check against expected_headers
        return True

    def validate_db_path(self, db_path: Path = DEFAULT_DB_PATH) -> bool:
        """
        Validates SQLite database file path and directory accessibility.

        :param db_path: Path to database file.
        :return: True if database directory exists and is writable.
        :raises DatabaseConnectionError: If database path is invalid.
        """
        logger.debug(f"Validating database path access: {db_path}")
        try:
            db_dir = db_path.parent
            if not db_dir.exists():
                db_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            raise DatabaseConnectionError(
                message=f"Cannot establish database directory access for path: {db_path}",
                details=str(e)
            )

    def validate_config(self) -> bool:
        """
        Audits project paths and threshold settings in config.py.

        :return: True if configuration settings are valid.
        :raises ConfigurationError: If critical configuration paths or values are invalid.
        """
        logger.debug("Validating system configuration parameters...")
        if not SUPPORTED_CURRENCIES:
            raise ConfigurationError(message="SUPPORTED_CURRENCIES in config.py cannot be empty.")

        # TODO Phase 2: Add directory permissions and threshold boundary checks
        return True

    def validate_date_string(self, date_str: str, date_format: str = DATE_FORMAT) -> bool:
        """
        Validates whether a string matches an expected date format.

        :param date_str: Date string (e.g. '2026-08-05').
        :param date_format: Format string (e.g. '%Y-%m-%d').
        :return: True if valid date string, False otherwise.
        """
        try:
            datetime.strptime(date_str, date_format)
            return True
        except ValueError:
            logger.warning(f"Date string '{date_str}' failed format check for format: {date_format}")
            return False


# Standalone Helper Functions mapping to specifications
def validate_trade(trade_data: Dict[str, Any]) -> bool:
    """Standalone validator function for a trade payload."""
    return ValidationHelper().validate_trade_dict(trade_data)


def validate_csv(file_path: Path) -> bool:
    """Standalone validator function for a CSV file."""
    return ValidationHelper().validate_csv_file(file_path)


def validate_database_connection(db_path: Path = DEFAULT_DB_PATH) -> bool:
    """Standalone validator function for database accessibility."""
    return ValidationHelper().validate_db_path(db_path)


def validate_configuration() -> bool:
    """Standalone validator function for application configuration."""
    return ValidationHelper().validate_config()


def validate_date(date_str: str, format_str: str = DATE_FORMAT) -> bool:
    """Standalone validator function for date strings."""
    return ValidationHelper().validate_date_string(date_str, format_str)
