"""
Power BI Analytics Exporter for Trade Reconciliation & Control Automation Engine.

Queries SQLite database to generate analytics-ready CSV datasets specifically tailored for
Power BI Desktop reports, executive dashboards, exception analytics, and risk/control monitoring.
"""

from pathlib import Path
import time
from typing import Any, Dict, List, Optional

import pandas as pd

from config import DEFAULT_DB_PATH, POWERBI_REPORTS_DIR
from src.database.database_manager import DatabaseManager
from src.utils.exceptions import DatabaseConnectionError, ReportGenerationError
from src.utils.logger import get_logger

logger = get_logger("PowerBIExporter")


class PowerBIExporter:
    """
    Generates structured, aggregated, and enriched Power BI CSV feeds from SQLite database tables.

    Attributes:
        db_manager: DatabaseManager instance for querying SQLite data.
        output_dir: Target directory path for exported Power BI CSV files.
    """

    VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        output_dir: Path = POWERBI_REPORTS_DIR,
    ) -> None:
        """Initializes PowerBIExporter with database manager and target directory."""
        self.db_manager = db_manager or DatabaseManager(db_path=DEFAULT_DB_PATH)
        self.output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized PowerBIExporter targeting directory: {self.output_dir}")

    def export_reconciliation_runs(self) -> Path:
        """Exports reconciliation_runs.csv containing historical KPI run metrics."""
        query = """
            SELECT 
                Run_ID,
                Created_At,
                Front_Count,
                Back_Count,
                Matched_Count,
                Match_Percentage,
                (Critical_Breaks + High_Breaks + Medium_Breaks + Low_Breaks) AS Total_Breaks,
                Critical_Breaks,
                High_Breaks,
                Medium_Breaks,
                Low_Breaks,
                Execution_Time
            FROM reconciliation_summary
            ORDER BY Created_At ASC
        """
        df = self.db_manager.fetch_dataframe(query)
        target_path = self.output_dir / "reconciliation_runs.csv"
        df.to_csv(target_path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} rows to reconciliation_runs.csv")
        return target_path

    def export_reconciliation_breaks(self) -> Path:
        """Exports reconciliation_breaks.csv enriched with FO/BO trade metadata."""
        query = """
            SELECT 
                b.Run_ID,
                b.Trade_ID,
                b.Break_Type,
                b.Expected_Value,
                b.Actual_Value,
                b.Severity,
                b.Detected_At,
                COALESCE(f.Trader, bo.Trader, 'N/A') AS Trader,
                COALESCE(f.Desk, bo.Desk, 'Unassigned') AS Desk,
                COALESCE(f.Portfolio, bo.Portfolio, 'Unassigned') AS Portfolio,
                COALESCE(f.Counterparty, bo.Counterparty, 'Unassigned') AS Counterparty,
                COALESCE(f.Asset_Class, bo.Asset_Class, 'Unassigned') AS Asset_Class,
                COALESCE(f.Symbol, bo.Symbol, 'N/A') AS Symbol,
                COALESCE(f.Buy_Sell, bo.Buy_Sell, 'N/A') AS Buy_Sell,
                COALESCE(f.Currency, bo.Currency, 'USD') AS Currency
            FROM reconciliation_breaks b
            LEFT JOIN front_office_trades f ON b.Trade_ID = f.Trade_ID
            LEFT JOIN back_office_trades bo ON b.Trade_ID = bo.Trade_ID
            ORDER BY b.Detected_At ASC, b.ID ASC
        """
        df = self.db_manager.fetch_dataframe(query)
        target_path = self.output_dir / "reconciliation_breaks.csv"
        df.to_csv(target_path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} rows to reconciliation_breaks.csv")
        return target_path

    def export_trade_details(self) -> Path:
        """Exports trade_details.csv from Front Office feed with calculated Trade_Notional."""
        query = """
            SELECT 
                Trade_ID,
                Trade_Date,
                Settlement_Date,
                Trader,
                Desk,
                Portfolio,
                Counterparty,
                Asset_Class,
                Symbol,
                Buy_Sell,
                Quantity,
                Price,
                Currency,
                Trade_Status,
                ROUND(ABS(Quantity * Price), 2) AS Trade_Notional
            FROM front_office_trades
            ORDER BY Trade_ID ASC
        """
        df = self.db_manager.fetch_dataframe(query)
        target_path = self.output_dir / "trade_details.csv"
        df.to_csv(target_path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} rows to trade_details.csv")
        return target_path

    def export_desk_summary(self) -> Path:
        """Exports desk_summary.csv with aggregated metrics and exception rates by Desk."""
        query = """
            WITH FO_Desk AS (
                SELECT 
                    Desk,
                    COUNT(DISTINCT Trade_ID) AS Total_Trades,
                    SUM(ABS(Quantity * Price)) AS Total_Notional
                FROM front_office_trades
                GROUP BY Desk
            ),
            Breaks_Desk AS (
                SELECT 
                    COALESCE(f.Desk, bo.Desk) AS Desk,
                    COUNT(b.ID) AS Total_Breaks,
                    COUNT(DISTINCT b.Trade_ID) AS Affected_Trades,
                    SUM(CASE WHEN b.Severity = 'CRITICAL' THEN 1 ELSE 0 END) AS Critical_Breaks,
                    SUM(CASE WHEN b.Severity = 'HIGH' THEN 1 ELSE 0 END) AS High_Breaks,
                    SUM(CASE WHEN b.Severity = 'MEDIUM' THEN 1 ELSE 0 END) AS Medium_Breaks,
                    SUM(CASE WHEN b.Severity = 'LOW' THEN 1 ELSE 0 END) AS Low_Breaks
                FROM reconciliation_breaks b
                LEFT JOIN front_office_trades f ON b.Trade_ID = f.Trade_ID
                LEFT JOIN back_office_trades bo ON b.Trade_ID = bo.Trade_ID
                GROUP BY COALESCE(f.Desk, bo.Desk)
            )
            SELECT 
                d.Desk,
                d.Total_Trades,
                ROUND(d.Total_Notional, 2) AS Total_Notional,
                COALESCE(b.Total_Breaks, 0) AS Total_Breaks,
                COALESCE(b.Critical_Breaks, 0) AS Critical_Breaks,
                COALESCE(b.High_Breaks, 0) AS High_Breaks,
                COALESCE(b.Medium_Breaks, 0) AS Medium_Breaks,
                COALESCE(b.Low_Breaks, 0) AS Low_Breaks,
                ROUND(CASE WHEN d.Total_Trades > 0 THEN (CAST(COALESCE(b.Affected_Trades, 0) AS FLOAT) / d.Total_Trades) * 100 ELSE 0 END, 2) AS Exception_Rate
            FROM FO_Desk d
            LEFT JOIN Breaks_Desk b ON d.Desk = b.Desk
            ORDER BY d.Desk ASC
        """
        df = self.db_manager.fetch_dataframe(query)
        target_path = self.output_dir / "desk_summary.csv"
        df.to_csv(target_path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} rows to desk_summary.csv")
        return target_path

    def export_portfolio_summary(self) -> Path:
        """Exports portfolio_summary.csv with aggregated metrics by Portfolio."""
        query = """
            WITH FO_Port AS (
                SELECT 
                    Portfolio,
                    COUNT(DISTINCT Trade_ID) AS Total_Trades,
                    SUM(ABS(Quantity * Price)) AS Total_Notional
                FROM front_office_trades
                GROUP BY Portfolio
            ),
            Breaks_Port AS (
                SELECT 
                    COALESCE(f.Portfolio, bo.Portfolio) AS Portfolio,
                    COUNT(b.ID) AS Total_Breaks,
                    COUNT(DISTINCT b.Trade_ID) AS Affected_Trades
                FROM reconciliation_breaks b
                LEFT JOIN front_office_trades f ON b.Trade_ID = f.Trade_ID
                LEFT JOIN back_office_trades bo ON b.Trade_ID = bo.Trade_ID
                GROUP BY COALESCE(f.Portfolio, bo.Portfolio)
            )
            SELECT 
                p.Portfolio,
                p.Total_Trades,
                ROUND(p.Total_Notional, 2) AS Total_Notional,
                COALESCE(b.Total_Breaks, 0) AS Total_Breaks,
                ROUND(CASE WHEN p.Total_Trades > 0 THEN (CAST(COALESCE(b.Affected_Trades, 0) AS FLOAT) / p.Total_Trades) * 100 ELSE 0 END, 2) AS Exception_Rate
            FROM FO_Port p
            LEFT JOIN Breaks_Port b ON p.Portfolio = b.Portfolio
            ORDER BY p.Portfolio ASC
        """
        df = self.db_manager.fetch_dataframe(query)
        target_path = self.output_dir / "portfolio_summary.csv"
        df.to_csv(target_path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} rows to portfolio_summary.csv")
        return target_path

    def export_counterparty_summary(self) -> Path:
        """Exports counterparty_summary.csv with aggregated metrics by Counterparty."""
        query = """
            WITH FO_Cpty AS (
                SELECT 
                    Counterparty,
                    COUNT(DISTINCT Trade_ID) AS Total_Trades,
                    SUM(ABS(Quantity * Price)) AS Total_Notional
                FROM front_office_trades
                GROUP BY Counterparty
            ),
            Breaks_Cpty AS (
                SELECT 
                    COALESCE(f.Counterparty, bo.Counterparty) AS Counterparty,
                    COUNT(b.ID) AS Total_Breaks,
                    COUNT(DISTINCT b.Trade_ID) AS Affected_Trades,
                    SUM(CASE WHEN b.Severity = 'CRITICAL' THEN 1 ELSE 0 END) AS Critical_Breaks
                FROM reconciliation_breaks b
                LEFT JOIN front_office_trades f ON b.Trade_ID = f.Trade_ID
                LEFT JOIN back_office_trades bo ON b.Trade_ID = bo.Trade_ID
                GROUP BY COALESCE(f.Counterparty, bo.Counterparty)
            )
            SELECT 
                c.Counterparty,
                c.Total_Trades,
                ROUND(c.Total_Notional, 2) AS Total_Notional,
                COALESCE(b.Total_Breaks, 0) AS Total_Breaks,
                COALESCE(b.Critical_Breaks, 0) AS Critical_Breaks,
                ROUND(CASE WHEN c.Total_Trades > 0 THEN (CAST(COALESCE(b.Affected_Trades, 0) AS FLOAT) / c.Total_Trades) * 100 ELSE 0 END, 2) AS Exception_Rate
            FROM FO_Cpty c
            LEFT JOIN Breaks_Cpty b ON c.Counterparty = b.Counterparty
            ORDER BY c.Counterparty ASC
        """
        df = self.db_manager.fetch_dataframe(query)
        target_path = self.output_dir / "counterparty_summary.csv"
        df.to_csv(target_path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} rows to counterparty_summary.csv")
        return target_path

    def export_asset_class_summary(self) -> Path:
        """Exports asset_class_summary.csv with aggregated metrics by Asset_Class."""
        query = """
            WITH FO_Asset AS (
                SELECT 
                    Asset_Class,
                    COUNT(DISTINCT Trade_ID) AS Total_Trades,
                    SUM(ABS(Quantity * Price)) AS Total_Notional
                FROM front_office_trades
                GROUP BY Asset_Class
            ),
            Breaks_Asset AS (
                SELECT 
                    COALESCE(f.Asset_Class, bo.Asset_Class) AS Asset_Class,
                    COUNT(b.ID) AS Total_Breaks,
                    COUNT(DISTINCT b.Trade_ID) AS Affected_Trades
                FROM reconciliation_breaks b
                LEFT JOIN front_office_trades f ON b.Trade_ID = f.Trade_ID
                LEFT JOIN back_office_trades bo ON b.Trade_ID = bo.Trade_ID
                GROUP BY COALESCE(f.Asset_Class, bo.Asset_Class)
            )
            SELECT 
                a.Asset_Class,
                a.Total_Trades,
                ROUND(a.Total_Notional, 2) AS Total_Notional,
                COALESCE(b.Total_Breaks, 0) AS Total_Breaks,
                ROUND(CASE WHEN a.Total_Trades > 0 THEN (CAST(COALESCE(b.Affected_Trades, 0) AS FLOAT) / a.Total_Trades) * 100 ELSE 0 END, 2) AS Exception_Rate
            FROM FO_Asset a
            LEFT JOIN Breaks_Asset b ON a.Asset_Class = b.Asset_Class
            ORDER BY a.Asset_Class ASC
        """
        df = self.db_manager.fetch_dataframe(query)
        target_path = self.output_dir / "asset_class_summary.csv"
        df.to_csv(target_path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} rows to asset_class_summary.csv")
        return target_path

    def export_severity_summary(self) -> Path:
        """Exports severity_summary.csv containing break counts and percentages by Severity."""
        query = """
            SELECT 
                Severity,
                COUNT(*) AS Break_Count,
                ROUND((CAST(COUNT(*) AS FLOAT) / (SELECT COUNT(*) FROM reconciliation_breaks)) * 100, 2) AS Percentage
            FROM reconciliation_breaks
            GROUP BY Severity
            ORDER BY CASE Severity 
                WHEN 'CRITICAL' THEN 1 
                WHEN 'HIGH' THEN 2 
                WHEN 'MEDIUM' THEN 3 
                WHEN 'LOW' THEN 4 
                ELSE 5 END
        """
        df = self.db_manager.fetch_dataframe(query)
        target_path = self.output_dir / "severity_summary.csv"
        df.to_csv(target_path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} rows to severity_summary.csv")
        return target_path

    def export_break_type_summary(self) -> Path:
        """Exports break_type_summary.csv containing break counts and percentages by Break_Type."""
        query = """
            SELECT 
                Break_Type,
                COUNT(*) AS Break_Count,
                ROUND((CAST(COUNT(*) AS FLOAT) / (SELECT COUNT(*) FROM reconciliation_breaks)) * 100, 2) AS Percentage
            FROM reconciliation_breaks
            GROUP BY Break_Type
            ORDER BY Break_Count DESC
        """
        df = self.db_manager.fetch_dataframe(query)
        target_path = self.output_dir / "break_type_summary.csv"
        df.to_csv(target_path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} rows to break_type_summary.csv")
        return target_path

    def validate_datasets(self) -> bool:
        """Validates database integrity and reconciliation records prior to export."""
        self.db_manager.connect()
        if not self.db_manager.table_exists("reconciliation_summary"):
            raise ReportGenerationError("Database missing 'reconciliation_summary' table. Run 'reconcile' first.")
        if not self.db_manager.table_exists("reconciliation_breaks"):
            raise ReportGenerationError("Database missing 'reconciliation_breaks' table. Run 'reconcile' first.")

        rec_count = self.db_manager.record_count("reconciliation_summary")
        if rec_count == 0:
            raise ReportGenerationError("No reconciliation run history found in database.")

        return True

    def run(self) -> Dict[str, Path]:
        """Executes full Power BI dataset export pipeline."""
        start_time = time.perf_counter()
        logger.info("Starting Power BI analytics dataset export workflow...")

        self.validate_datasets()

        exported_files = {
            "reconciliation_runs": self.export_reconciliation_runs(),
            "reconciliation_breaks": self.export_reconciliation_breaks(),
            "trade_details": self.export_trade_details(),
            "desk_summary": self.export_desk_summary(),
            "portfolio_summary": self.export_portfolio_summary(),
            "counterparty_summary": self.export_counterparty_summary(),
            "asset_class_summary": self.export_asset_class_summary(),
            "severity_summary": self.export_severity_summary(),
            "break_type_summary": self.export_break_type_summary(),
        }

        elapsed = round(time.perf_counter() - start_time, 4)
        logger.info(f"Power BI export workflow completed in {elapsed} seconds. Output path: {self.output_dir}")
        return exported_files
