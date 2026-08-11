"""
Helper Utilities for Trade Reconciliation & Control Automation Engine.

Provides common utility functions for file handling, date formatting, JSON parsing,
CSV verification, path normalization, and execution timing analysis.
"""

from datetime import datetime
import functools
import json
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar

from config import DATE_FORMAT
from src.utils.logger import get_logger

logger = get_logger("Helpers")

F = TypeVar("F", bound=Callable[..., Any])


def time_it(func: F) -> F:
    """
    Decorator that measures and logs the execution time of a function.

    :param func: Function to be measured.
    :return: Wrapped function with timing log.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        logger.debug(f"Starting execution of '{func.__qualname__}'...")
        try:
            result = func(*args, **kwargs)
            elapsed_time = time.perf_counter() - start_time
            logger.info(f"Completed '{func.__qualname__}' in {elapsed_time:.4f} seconds.")
            return result
        except Exception as e:
            elapsed_time = time.perf_counter() - start_time
            logger.error(f"Failed '{func.__qualname__}' after {elapsed_time:.4f} seconds with error: {e}")
            raise

    return wrapper  # type: ignore[return-value]


def format_date(dt: Optional[datetime] = None, format_str: str = DATE_FORMAT) -> str:
    """
    Formats a datetime object or returns the current date string formatted.

    :param dt: Datetime object to format. Defaults to current datetime.
    :param format_str: Date formatting pattern.
    :return: Formatted date string.
    """
    target_dt = dt or datetime.now()
    return target_dt.strftime(format_str)


def ensure_directory_exists(path: Path) -> Path:
    """
    Ensures that a directory exists, creating parent directories if necessary.

    :param path: Path object of directory or file.
    :return: Absolute Path object guaranteed to exist.
    """
    target_dir = path if path.is_dir() or not path.suffix else path.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def ensure_project_directories() -> None:
    """Ensures all essential project directory structures exist on disk."""
    from config import (
        ASSETS_DIR, CHARTS_DIR, CSV_REPORTS_DIR, DATABASE_DIR, DOCS_DIR,
        EXCEL_REPORTS_DIR, JSON_REPORTS_DIR, LOGS_DIR, PDF_REPORTS_DIR, POWERBI_REPORTS_DIR, RAW_DATA_DIR,
    )
    for folder in [RAW_DATA_DIR, DATABASE_DIR, EXCEL_REPORTS_DIR, CSV_REPORTS_DIR,
                   JSON_REPORTS_DIR, CHARTS_DIR, POWERBI_REPORTS_DIR, PDF_REPORTS_DIR, LOGS_DIR, DOCS_DIR, ASSETS_DIR]:
        folder.mkdir(parents=True, exist_ok=True)


def get_file_extension(file_path: Path) -> str:
    """
    Extracts lower-case file extension without dot.

    :param file_path: Path to file.
    :return: Extension string (e.g. 'csv', 'xlsx', 'json').
    """
    return file_path.suffix.lstrip(".").lower()


def read_json_file(file_path: Path) -> Dict[str, Any] | List[Any]:
    """
    Helper to safely read and parse a JSON file.

    :param file_path: Path to JSON file.
    :return: Parsed JSON data structure (dict or list).
    """
    logger.debug(f"Reading JSON file from: {file_path}")
    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found at: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_file(data: Any, file_path: Path, indent: int = 4) -> Path:
    """
    Helper to safely write data structure to a formatted JSON file.

    :param data: Python dictionary or list structure.
    :param file_path: Path to save JSON output.
    :param indent: Formatting indent spacing.
    :return: Output Path object.
    """
    ensure_directory_exists(file_path)
    logger.debug(f"Writing JSON file to: {file_path}")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, default=str)
    return file_path
