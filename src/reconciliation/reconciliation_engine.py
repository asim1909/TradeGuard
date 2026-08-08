"""
Reconciliation Engine Module for Trade Reconciliation & Control Automation Engine.

Executes SQL-first trade matching algorithms between Front Office and Back Office SQLite tables,
detects missing trades, unexpected trades, duplicates, price/qty mismatches, status mismatches,
date mismatches, and currency mismatches, assigns severity, and persists breaks and run summaries.
"""

from datetime import datetime
import time
import uuid
from typing import Any, Dict, List, Optional

from config import RECONCILIATION_THRESHOLD
from src.database.database_manager import DatabaseManager
from src.utils.exceptions import DatabaseConnectionError, ReconciliationError
from src.utils.logger import get_logger

logger = get_logger("ReconciliationEngine")


class ReconciliationEngine:
    """
    Core SQL-driven trade reconciliation engine.

    Attributes:
        db_manager: Instance of DatabaseManager.
        threshold: Allowed price monetary discrepancy tolerance.
        all_breaks: List of all detected break dictionaries.
    """

    SEVERITY_MAP = {
        "Missing Trade": "CRITICAL",
        "Unexpected Trade": "CRITICAL",
        "Duplicate Trade": "HIGH",
        "Quantity Mismatch": "HIGH",
        "Price Mismatch": "MEDIUM",
        "Currency Mismatch": "MEDIUM",
        "Status Mismatch": "LOW",
        "Trade Date Mismatch": "LOW",
        "Settlement Date Mismatch": "LOW",
    }

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        threshold: float = RECONCILIATION_THRESHOLD,
    ) -> None:
        """Initializes ReconciliationEngine with DatabaseManager and price tolerance."""
        self.db_manager = db_manager or DatabaseManager()
        self.threshold = threshold
        self.all_breaks: List[Dict[str, Any]] = []
        logger.info(f"Initialized ReconciliationEngine with threshold: {self.threshold}")

    def assign_severity(self, break_type: str) -> str:
        """Assigns risk severity level based on break category."""
        return self.SEVERITY_MAP.get(break_type, "MEDIUM")

    def find_missing_trades(self) -> List[Dict[str, Any]]:
        """Identifies trades present in Front Office but missing in Back Office."""
        sql = """
            SELECT fo.Trade_ID, 'Missing Trade' AS Break_Type,
                   'Present in BO' AS Expected_Value, 'Missing in BO' AS Actual_Value
            FROM front_office_trades fo
            LEFT JOIN back_office_trades bo ON fo.Trade_ID = bo.Trade_ID
            WHERE bo.Trade_ID IS NULL
        """
        logger.debug("Executing SQL: find_missing_trades")
        rows = self.db_manager.execute_select(sql)
        for r in rows:
            r["Severity"] = self.assign_severity(r["Break_Type"])
        logger.info(f"Detected {len(rows)} Missing Trades.")
        return rows

    def find_unexpected_trades(self) -> List[Dict[str, Any]]:
        """Identifies trades present in Back Office but missing in Front Office."""
        sql = """
            SELECT DISTINCT bo.Trade_ID, 'Unexpected Trade' AS Break_Type,
                   'Absent in BO' AS Expected_Value, 'Present in BO' AS Actual_Value
            FROM back_office_trades bo
            LEFT JOIN front_office_trades fo ON bo.Trade_ID = fo.Trade_ID
            WHERE fo.Trade_ID IS NULL
        """
        logger.debug("Executing SQL: find_unexpected_trades")
        rows = self.db_manager.execute_select(sql)
        for r in rows:
            r["Severity"] = self.assign_severity(r["Break_Type"])
        logger.info(f"Detected {len(rows)} Unexpected Trades.")
        return rows

    def find_duplicate_trades(self) -> List[Dict[str, Any]]:
        """Identifies duplicate Trade_IDs appearing multiple times in Back Office."""
        sql = """
            SELECT Trade_ID, 'Duplicate Trade' AS Break_Type,
                   'Single Trade' AS Expected_Value,
                   'Duplicate Entry in BO (' || COUNT(*) || ')' AS Actual_Value
            FROM back_office_trades
            GROUP BY Trade_ID
            HAVING COUNT(*) > 1
        """
        logger.debug("Executing SQL: find_duplicate_trades")
        rows = self.db_manager.execute_select(sql)
        for r in rows:
            r["Severity"] = self.assign_severity(r["Break_Type"])
        logger.info(f"Detected {len(rows)} Duplicate Trades.")
        return rows

    def find_price_mismatches(self) -> List[Dict[str, Any]]:
        """Identifies trades where price difference exceeds threshold tolerance."""
        sql = """
            SELECT DISTINCT fo.Trade_ID, 'Price Mismatch' AS Break_Type,
                   CAST(fo.Price AS TEXT) AS Expected_Value,
                   CAST(bo.Price AS TEXT) AS Actual_Value
            FROM front_office_trades fo
            INNER JOIN back_office_trades bo ON fo.Trade_ID = bo.Trade_ID
            WHERE ABS(fo.Price - bo.Price) > ?
        """
        logger.debug(f"Executing SQL: find_price_mismatches [Threshold={self.threshold}]")
        rows = self.db_manager.execute_select(sql, (self.threshold,))
        for r in rows:
            r["Severity"] = self.assign_severity(r["Break_Type"])
        logger.info(f"Detected {len(rows)} Price Mismatches.")
        return rows

    def find_quantity_mismatches(self) -> List[Dict[str, Any]]:
        """Identifies trades with different unit quantities."""
        sql = """
            SELECT DISTINCT fo.Trade_ID, 'Quantity Mismatch' AS Break_Type,
                   CAST(fo.Quantity AS TEXT) AS Expected_Value,
                   CAST(bo.Quantity AS TEXT) AS Actual_Value
            FROM front_office_trades fo
            INNER JOIN back_office_trades bo ON fo.Trade_ID = bo.Trade_ID
            WHERE fo.Quantity <> bo.Quantity
        """
        logger.debug("Executing SQL: find_quantity_mismatches")
        rows = self.db_manager.execute_select(sql)
        for r in rows:
            r["Severity"] = self.assign_severity(r["Break_Type"])
        logger.info(f"Detected {len(rows)} Quantity Mismatches.")
        return rows

    def find_status_mismatches(self) -> List[Dict[str, Any]]:
        """Identifies trades with different trade status codes."""
        sql = """
            SELECT DISTINCT fo.Trade_ID, 'Status Mismatch' AS Break_Type,
                   fo.Trade_Status AS Expected_Value,
                   bo.Trade_Status AS Actual_Value
            FROM front_office_trades fo
            INNER JOIN back_office_trades bo ON fo.Trade_ID = bo.Trade_ID
            WHERE fo.Trade_Status <> bo.Trade_Status
        """
        logger.debug("Executing SQL: find_status_mismatches")
        rows = self.db_manager.execute_select(sql)
        for r in rows:
            r["Severity"] = self.assign_severity(r["Break_Type"])
        logger.info(f"Detected {len(rows)} Status Mismatches.")
        return rows

    def find_trade_date_mismatches(self) -> List[Dict[str, Any]]:
        """Identifies trades with different trade execution dates."""
        sql = """
            SELECT DISTINCT fo.Trade_ID, 'Trade Date Mismatch' AS Break_Type,
                   fo.Trade_Date AS Expected_Value,
                   bo.Trade_Date AS Actual_Value
            FROM front_office_trades fo
            INNER JOIN back_office_trades bo ON fo.Trade_ID = bo.Trade_ID
            WHERE fo.Trade_Date <> bo.Trade_Date
        """
        logger.debug("Executing SQL: find_trade_date_mismatches")
        rows = self.db_manager.execute_select(sql)
        for r in rows:
            r["Severity"] = self.assign_severity(r["Break_Type"])
        logger.info(f"Detected {len(rows)} Trade Date Mismatches.")
        return rows

    def find_settlement_date_mismatches(self) -> List[Dict[str, Any]]:
        """Identifies trades with different settlement dates."""
        sql = """
            SELECT DISTINCT fo.Trade_ID, 'Settlement Date Mismatch' AS Break_Type,
                   fo.Settlement_Date AS Expected_Value,
                   bo.Settlement_Date AS Actual_Value
            FROM front_office_trades fo
            INNER JOIN back_office_trades bo ON fo.Trade_ID = bo.Trade_ID
            WHERE fo.Settlement_Date <> bo.Settlement_Date
        """
        logger.debug("Executing SQL: find_settlement_date_mismatches")
        rows = self.db_manager.execute_select(sql)
        for r in rows:
            r["Severity"] = self.assign_severity(r["Break_Type"])
        logger.info(f"Detected {len(rows)} Settlement Date Mismatches.")
        return rows

    def find_currency_mismatches(self) -> List[Dict[str, Any]]:
        """Identifies trades with different currency codes."""
        sql = """
            SELECT DISTINCT fo.Trade_ID, 'Currency Mismatch' AS Break_Type,
                   fo.Currency AS Expected_Value,
                   bo.Currency AS Actual_Value
            FROM front_office_trades fo
            INNER JOIN back_office_trades bo ON fo.Trade_ID = bo.Trade_ID
            WHERE fo.Currency <> bo.Currency
        """
        logger.debug("Executing SQL: find_currency_mismatches")
        rows = self.db_manager.execute_select(sql)
        for r in rows:
            r["Severity"] = self.assign_severity(r["Break_Type"])
        logger.info(f"Detected {len(rows)} Currency Mismatches.")
        return rows

    def store_breaks(self, run_id: str, breaks: List[Dict[str, Any]]) -> int:
        """Stores detected reconciliation breaks into reconciliation_breaks table preserving run history."""
        logger.info(f"Persisting {len(breaks)} break records into reconciliation_breaks for Run_ID '{run_id}'...")

        if not breaks:
            return 0

        sql = """
            INSERT INTO reconciliation_breaks (Run_ID, Trade_ID, Break_Type, Expected_Value, Actual_Value, Severity)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        param_list = [
            (run_id, b["Trade_ID"], b["Break_Type"], b.get("Expected_Value"), b.get("Actual_Value"), b["Severity"])
            for b in breaks
        ]
        return self.db_manager.execute_many(sql, param_list)

    def generate_summary(
        self,
        run_id: str,
        execution_time: float,
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generates and persists executive summary record into reconciliation_summary table."""
        sql = """
            INSERT INTO reconciliation_summary (
                Run_ID, Execution_Time, Front_Count, Back_Count, Matched_Count,
                Missing_Count, Unexpected_Count, Price_Mismatch_Count, Quantity_Mismatch_Count,
                Status_Mismatch_Count, Trade_Date_Mismatch_Count, Settlement_Date_Mismatch_Count,
                Currency_Mismatch_Count, Duplicate_Count, Critical_Breaks, High_Breaks,
                Medium_Breaks, Low_Breaks, Match_Percentage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            run_id,
            execution_time,
            metrics["Front_Count"],
            metrics["Back_Count"],
            metrics["Matched_Count"],
            metrics["Missing_Count"],
            metrics["Unexpected_Count"],
            metrics["Price_Mismatch_Count"],
            metrics["Quantity_Mismatch_Count"],
            metrics["Status_Mismatch_Count"],
            metrics["Trade_Date_Mismatch_Count"],
            metrics["Settlement_Date_Mismatch_Count"],
            metrics["Currency_Mismatch_Count"],
            metrics["Duplicate_Count"],
            metrics["Critical_Breaks"],
            metrics["High_Breaks"],
            metrics["Medium_Breaks"],
            metrics["Low_Breaks"],
            metrics["Match_Percentage"],
        )
        self.db_manager.execute_insert(sql, params)
        logger.info(f"Persisted summary run record {run_id} into reconciliation_summary.")
        return metrics

    def run(self) -> Dict[str, Any]:
        """Executes full trade reconciliation algorithm and records summary statistics."""
        start_time = time.perf_counter()
        logger.info("Starting trade reconciliation engine run...")

        # Ensure schema tables exist
        self.db_manager.create_tables()

        # Verify database tables exist and are non-empty
        fo_cnt = self.db_manager.record_count("front_office_trades")
        bo_cnt = self.db_manager.record_count("back_office_trades")
        if fo_cnt == 0 or bo_cnt == 0:
            raise ReconciliationError(
                f"Cannot run reconciliation. Tables empty (FO: {fo_cnt}, BO: {bo_cnt}). Run 'load-data' first."
            )

        # 1. Execute all SQL detection queries
        missing = self.find_missing_trades()
        unexpected = self.find_unexpected_trades()
        duplicates = self.find_duplicate_trades()
        prices = self.find_price_mismatches()
        quantities = self.find_quantity_mismatches()
        statuses = self.find_status_mismatches()
        trade_dates = self.find_trade_date_mismatches()
        settle_dates = self.find_settlement_date_mismatches()
        currencies = self.find_currency_mismatches()

        # Combine all breaks
        self.all_breaks = (
            missing + unexpected + duplicates + prices + quantities + statuses + trade_dates + settle_dates + currencies
        )

        run_id = f"REC_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        # 2. Persist breaks to database
        self.store_breaks(run_id, self.all_breaks)

        # 3. Calculate metrics & severity counts
        crit_cnt = sum(1 for b in self.all_breaks if b["Severity"] == "CRITICAL")
        high_cnt = sum(1 for b in self.all_breaks if b["Severity"] == "HIGH")
        med_cnt = sum(1 for b in self.all_breaks if b["Severity"] == "MEDIUM")
        low_cnt = sum(1 for b in self.all_breaks if b["Severity"] == "LOW")

        # Determine FO trades with breaks (excluding unexpected/duplicates which are BO-only)
        fo_break_trade_ids = {
            b["Trade_ID"] for b in (missing + prices + quantities + statuses + trade_dates + settle_dates + currencies)
        }
        matched_cnt = max(0, fo_cnt - len(fo_break_trade_ids))
        match_pct = round((matched_cnt / fo_cnt) * 100.0, 2) if fo_cnt > 0 else 0.0
        elapsed = round(time.perf_counter() - start_time, 4)

        metrics = {
            "Run_ID": run_id,
            "Execution_Time": elapsed,
            "Front_Count": fo_cnt,
            "Back_Count": bo_cnt,
            "Matched_Count": matched_cnt,
            "Missing_Count": len(missing),
            "Unexpected_Count": len(unexpected),
            "Price_Mismatch_Count": len(prices),
            "Quantity_Mismatch_Count": len(quantities),
            "Status_Mismatch_Count": len(statuses),
            "Trade_Date_Mismatch_Count": len(trade_dates),
            "Settlement_Date_Mismatch_Count": len(settle_dates),
            "Currency_Mismatch_Count": len(currencies),
            "Duplicate_Count": len(duplicates),
            "Critical_Breaks": crit_cnt,
            "High_Breaks": high_cnt,
            "Medium_Breaks": med_cnt,
            "Low_Breaks": low_cnt,
            "Match_Percentage": match_pct,
        }

        # 4. Save summary record
        self.generate_summary(metrics["Run_ID"], elapsed, metrics)
        logger.info(f"Reconciliation engine completed in {elapsed}s with Match Rate: {match_pct}%.")
        return metrics
