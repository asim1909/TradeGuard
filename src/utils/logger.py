"""
Logging Module for Trade Reconciliation & Control Automation Engine.

Provides enterprise-grade, thread-safe logging infrastructure supporting:
- Console logging with optional colorization
- Rotating file handlers for audit history
- Timestamp, module, and log level metadata formatting
- Configurable log levels and output destinations
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
from typing import Optional

from config import (
    LOG_BACKUP_COUNT,
    LOG_DATE_FORMAT,
    LOG_FILE_PATH,
    LOG_FORMAT,
    LOG_MAX_BYTES,
    LOGS_DIR,
)

# Optional color formatting support for terminal output
try:
    import colorama
    colorama.init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False


class ColoredFormatter(logging.Formatter):
    """Custom logging formatter that adds ANSI color coding to console output."""

    COLOR_MAP = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[41m",  # Red Background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = LOG_FORMAT
        if HAS_COLORAMA and record.levelno in self.COLOR_MAP:
            color = self.COLOR_MAP[record.levelno]
            levelname_colored = f"{color}{record.levelname:<8}{self.RESET}"
            # Temporarily modify levelname for colored output
            original_levelname = record.levelname
            record.levelname = levelname_colored
            formatted = super().format(record)
            record.levelname = original_levelname
            return formatted
        return super().format(record)


def setup_logger(
    name: str = "TradeEngine",
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    console_output: bool = True,
) -> logging.Logger:
    """
    Initializes and configures a logger instance with console and file handlers.

    :param name: Name of the logger instance.
    :param log_file: Path to log file. Defaults to config.LOG_FILE_PATH.
    :param level: Logging level (e.g. logging.INFO, logging.DEBUG).
    :param console_output: Whether to enable stdout console logging.
    :return: Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if setup_logger is called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create logs directory if missing
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    target_log_file = log_file or LOG_FILE_PATH

    # 1. Rotating File Handler (Audit Log)
    file_formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    file_handler = RotatingFileHandler(
        filename=target_log_file,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # 2. Console Stream Handler
    if console_output:
        console_formatter = ColoredFormatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "TradeEngine") -> logging.Logger:
    """
    Retrieves an existing logger or initializes a new default logger.

    :param name: Logger name identifier.
    :return: logging.Logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name=name)
    return logger
