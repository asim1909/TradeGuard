"""
Custom Exception Classes for Trade Reconciliation & Control Automation Engine.

Defines a clean, domain-specific exception hierarchy for error handling
across validation, data ingestion, database management, reconciliation, and reporting.
"""


class TradeEngineError(Exception):
    """Base exception for all Trade Reconciliation Engine errors."""

    def __init__(self, message: str, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class TradeValidationError(TradeEngineError):
    """Raised when trade data fails domain schema or validation checks."""

    pass


class DatabaseConnectionError(TradeEngineError):
    """Raised when database connection, initialization, or query execution fails."""

    pass


class CSVFormatError(TradeEngineError):
    """Raised when CSV trade files are malformed, missing headers, or unparseable."""

    pass


class ReportGenerationError(TradeEngineError):
    """Raised when Excel, CSV, or JSON report generation fails."""

    pass


class ConfigurationError(TradeEngineError):
    """Raised when application configuration or path parameters are invalid."""

    pass


class ReconciliationError(TradeEngineError):
    """Raised when trade reconciliation logic encounters breaking data conditions."""

    pass
