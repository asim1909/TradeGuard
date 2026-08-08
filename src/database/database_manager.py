"""
Database Manager Module for Trade Reconciliation & Control Automation Engine.

Manages SQLite database connection lifecycle, DDL schema creation, CSV staging ingestion,
data validation, query execution, transactions, and database health audits.
"""

from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional

import pandas as pd

from config import (
    BACK_OFFICE_CSV_PATH,
    CURRENCIES,
    DEFAULT_DB_PATH,
    FRONT_OFFICE_CSV_PATH,
    SCHEMA_PATH,
    TRADE_STATUSES,
)
from src.utils.exceptions import (
    CSVFormatError,
    DatabaseConnectionError,
    TradeValidationError,
)
from src.utils.logger import get_logger

logger = get_logger("DatabaseManager")


class DatabaseManager:
    """
    Manages relational SQLite database interactions, CSV loading, and query execution.

    Attributes:
        db_path: Path to SQLite database file.
        schema_path: Path to database initialization DDL script.
        connection: Active sqlite3 connection handle.
    """

    REQUIRED_COLUMNS = [
        "Trade_ID",
        "Trade_Date",
        "Settlement_Date",
        "Trader",
        "Desk",
        "Portfolio",
        "Counterparty",
        "Asset_Class",
        "Symbol",
        "Buy_Sell",
        "Quantity",
        "Price",
        "Currency",
        "Trade_Status",
    ]

    def __init__(
        self,
        db_path: Path = DEFAULT_DB_PATH,
        schema_path: Path = SCHEMA_PATH,
    ) -> None:
        """Initializes DatabaseManager with database and schema paths."""
        self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
        self.schema_path = Path(schema_path) if isinstance(schema_path, str) else schema_path
        self.connection: Optional[sqlite3.Connection] = None
        logger.info(f"Initialized DatabaseManager target: {self.db_path}")

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry point."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit point."""
        self.close()

    def connect(self) -> sqlite3.Connection:
        """Establishes connection to SQLite database."""
        if self.connection is not None:
            return self.connection

        logger.info(f"Connecting to database at: {self.db_path}")
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            logger.info("Successfully connected to SQLite database.")
            return self.connection
        except (sqlite3.Error, OSError) as e:
            logger.error(f"Failed connecting to database: {e}")
            raise DatabaseConnectionError(
                message=f"Database connection error for path: {self.db_path}",
                details=str(e),
            )

    def close(self) -> None:
        """Closes active database connection."""
        if self.connection:
            logger.info("Closing SQLite database connection.")
            self.connection.close()
            self.connection = None

    def disconnect(self) -> None:
        """Alias for close()."""
        self.close()

    def create_database(self) -> bool:
        """Ensures database file exists and is accessible."""
        conn = self.connect()
        return conn is not None

    def create_tables(self) -> bool:
        """Executes DDL script from schema.sql to create tables and indexes."""
        logger.info(f"Loading schema DDL from: {self.schema_path}")
        if not self.schema_path.exists():
            raise DatabaseConnectionError(f"Schema script not found at: {self.schema_path}")

        try:
            conn = self.connect()
            # If reconciliation_summary exists with old schema, drop it to recreate with expanded columns
            if self.table_exists("reconciliation_summary"):
                cols = [row[1] for row in self.execute_query("PRAGMA table_info(reconciliation_summary)")]
                if "Matched_Count" not in cols:
                    logger.info("Updating reconciliation_summary table schema...")
                    conn.execute("DROP TABLE reconciliation_summary")

            if self.table_exists("reconciliation_breaks"):
                cols = [row[1] for row in self.execute_query("PRAGMA table_info(reconciliation_breaks)")]
                if "Run_ID" not in cols:
                    logger.info("Updating reconciliation_breaks table schema...")
                    conn.execute("DROP TABLE reconciliation_breaks")

            with open(self.schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            conn.commit()
            logger.info("Database schema tables and indexes successfully created.")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed creating database tables: {e}")
            raise DatabaseConnectionError(message="Failed executing schema.sql", details=str(e))

    def validate_dataframe(self, df: pd.DataFrame, source_name: str = "CSV") -> None:
        """Validates input DataFrame schema and business rules prior to ingestion."""
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise TradeValidationError(f"Missing required columns in {source_name}: {missing_cols}")

        if df["Trade_ID"].isnull().any() or (df["Trade_ID"].astype(str).str.strip() == "").any():
            raise TradeValidationError(f"Missing or empty Trade_ID detected in {source_name}")

        if (df["Quantity"] <= 0).any():
            raise TradeValidationError(f"Non-positive Quantity detected in {source_name}")

        if (df["Price"] <= 0).any():
            raise TradeValidationError(f"Non-positive Price detected in {source_name}")

        invalid_currencies = set(df["Currency"]) - set(CURRENCIES)
        if invalid_currencies:
            raise TradeValidationError(f"Invalid currency codes in {source_name}: {invalid_currencies}")

        invalid_statuses = set(df["Trade_Status"]) - set(TRADE_STATUSES)
        if invalid_statuses:
            raise TradeValidationError(f"Invalid status values in {source_name}: {invalid_statuses}")

    def insert_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: str = "append",
    ) -> int:
        """Inserts DataFrame records into specified table using transaction batching."""
        self.validate_dataframe(df, source_name=table_name)
        conn = self.connect()

        try:
            start_time = time.perf_counter()
            df.to_sql(
                name=table_name,
                con=conn,
                if_exists=if_exists,
                index=False,
                method="multi",
                chunksize=500,
            )
            conn.commit()
            elapsed = round(time.perf_counter() - start_time, 4)
            inserted_count = len(df)
            logger.info(f"Inserted {inserted_count} rows into table '{table_name}' in {elapsed}s.")
            return inserted_count
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error inserting DataFrame into '{table_name}': {e}")
            raise DatabaseConnectionError(message=f"Failed inserting into {table_name}", details=str(e))

    def load_front_office_csv(self, csv_path: Optional[Path] = None) -> int:
        """Ingests Front Office raw CSV feed into front_office_trades table."""
        target_path = Path(csv_path) if csv_path else FRONT_OFFICE_CSV_PATH
        logger.info(f"Loading Front Office CSV from: {target_path}")

        if not target_path.exists():
            raise CSVFormatError(f"Front Office CSV file missing at: {target_path}")

        try:
            df = pd.read_csv(target_path)
            self.execute_delete("DELETE FROM front_office_trades")
            return self.insert_dataframe(df, "front_office_trades", if_exists="append")
        except Exception as e:
            if isinstance(e, (CSVFormatError, TradeValidationError, DatabaseConnectionError)):
                raise
            raise CSVFormatError(message=f"Failed reading FO CSV: {target_path}", details=str(e))

    def load_back_office_csv(self, csv_path: Optional[Path] = None) -> int:
        """Ingests Back Office raw CSV feed into back_office_trades table."""
        target_path = Path(csv_path) if csv_path else BACK_OFFICE_CSV_PATH
        logger.info(f"Loading Back Office CSV from: {target_path}")

        if not target_path.exists():
            raise CSVFormatError(f"Back Office CSV file missing at: {target_path}")

        try:
            df = pd.read_csv(target_path)
            self.execute_delete("DELETE FROM back_office_trades")
            return self.insert_dataframe(df, "back_office_trades", if_exists="append")
        except Exception as e:
            if isinstance(e, (CSVFormatError, TradeValidationError, DatabaseConnectionError)):
                raise
            raise CSVFormatError(message=f"Failed reading BO CSV: {target_path}", details=str(e))

    def fetch_dataframe(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """Executes SELECT query and returns result as a pandas DataFrame."""
        conn = self.connect()
        try:
            return pd.read_sql_query(query, conn, params=params)
        except sqlite3.Error as e:
            logger.error(f"Failed executing fetch_dataframe query: {e}")
            raise DatabaseConnectionError(message="Query execution failure", details=str(e))

    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Executes SQL statement and returns sqlite3.Row results."""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            q_type = query.strip().upper()
            if q_type.startswith("SELECT") or q_type.startswith("PRAGMA") or q_type.startswith("SHOW"):
                return cursor.fetchall()
            conn.commit()
            return []
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Database query execution error: {e}")
            raise DatabaseConnectionError(message=f"Failed executing SQL query", details=str(e))

    def execute_many(self, query: str, param_list: List[tuple]) -> int:
        """Executes parameterized query against a list of parameter tuples."""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.executemany(query, param_list)
            conn.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Database execute_many error: {e}")
            raise DatabaseConnectionError(message="Failed executing batch SQL query", details=str(e))

    def execute_select(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Executes SELECT query returning list of dictionaries."""
        rows = self.execute_query(query, params)
        return [dict(row) for row in rows]

    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Executes INSERT query returning last rowid."""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid or 0
        except sqlite3.Error as e:
            conn.rollback()
            raise DatabaseConnectionError(message="Failed executing INSERT", details=str(e))

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Executes UPDATE statement returning affected row count."""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            conn.rollback()
            raise DatabaseConnectionError(message="Failed executing UPDATE", details=str(e))

    def execute_delete(self, query: str, params: tuple = ()) -> int:
        """Executes DELETE statement returning deleted row count."""
        return self.execute_update(query, params)

    def get_trade_by_id(
        self,
        trade_id: str,
        table_name: str = "front_office_trades",
    ) -> Optional[Dict[str, Any]]:
        """Queries single trade record by Trade_ID."""
        query = f"SELECT * FROM {table_name} WHERE Trade_ID = ? LIMIT 1"
        results = self.execute_select(query, (trade_id,))
        return results[0] if results else None

    def get_all_front_office(self) -> pd.DataFrame:
        """Returns entire front_office_trades table as a DataFrame."""
        return self.fetch_dataframe("SELECT * FROM front_office_trades")

    def get_all_back_office(self) -> pd.DataFrame:
        """Returns entire back_office_trades table as a DataFrame."""
        return self.fetch_dataframe("SELECT * FROM back_office_trades")

    def table_exists(self, table_name: str) -> bool:
        """Checks if specified table exists in the database."""
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        rows = self.execute_query(query, (table_name,))
        return len(rows) > 0

    def record_count(self, table_name: str) -> int:
        """Returns total row count for specified table."""
        if not self.table_exists(table_name):
            return 0
        rows = self.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
        return rows[0]["count"] if rows else 0

    def count_rows(self, table_name: str) -> int:
        """Alias for record_count."""
        return self.record_count(table_name)

    def clear_tables(self) -> None:
        """Truncates all trade and reconciliation tables."""
        tables = [
            "front_office_trades",
            "back_office_trades",
            "reconciliation_breaks",
            "reconciliation_summary",
        ]
        for table in tables:
            if self.table_exists(table):
                self.execute_delete(f"DELETE FROM {table}")
        logger.info("Cleared all database tables.")

    def database_health_check(self) -> Dict[str, Any]:
        """Performs database connection, table integrity, and row count health checks."""
        conn = self.connect()
        tables = [
            "front_office_trades",
            "back_office_trades",
            "reconciliation_breaks",
            "reconciliation_summary",
        ]
        table_counts = {t: self.record_count(t) for t in tables}
        
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()[0]
        except sqlite3.Error as e:
            integrity = f"FAILED: {e}"

        return {
            "status": "HEALTHY" if integrity == "ok" else "UNHEALTHY",
            "db_path": str(self.db_path),
            "integrity_check": integrity,
            "table_counts": table_counts,
        }
