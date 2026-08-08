"""
Unit Test Suite for DatabaseManager module (Phase 3).

Verifies database creation, connection lifecycle, schema initialization,
table creation, index presence, CSV loading, row count verification, and health check audits.
Compatible with standard library unittest and pytest.
"""

from pathlib import Path
import tempfile
import unittest
import pandas as pd

from src.database.database_manager import DatabaseManager
from src.data_generator import DataGenerator


class TestDatabaseManager(unittest.TestCase):
    """Test suite verifying DatabaseManager functionality."""

    def setUp(self):
        """Set up temporary directory, database, and sample CSV data."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.db_path = self.tmp_path / "test_trade_reconciliation.db"

        # Generate sample CSV datasets
        self.generator = DataGenerator(num_trades=50, random_seed=42, raw_dir=self.tmp_path)
        self.fo_df, self.bo_df, _ = self.generator.run()

        self.fo_csv = self.tmp_path / "front_office.csv"
        self.bo_csv = self.tmp_path / "back_office.csv"

        # Initialize database manager instance
        self.db_manager = DatabaseManager(db_path=self.db_path)

    def tearDown(self):
        """Clean up database connection and temporary directory."""
        self.db_manager.close()
        self.temp_dir.cleanup()

    def test_database_connection_and_creation(self):
        """Verifies database connection creation and file existence."""
        conn = self.db_manager.connect()
        self.assertIsNotNone(conn, "Database connection is None")
        self.assertTrue(self.db_path.exists(), "SQLite database file was not created on disk")

    def test_tables_creation(self):
        """Verifies all expected schema tables are created."""
        self.db_manager.create_tables()

        expected_tables = [
            "front_office_trades",
            "back_office_trades",
            "reconciliation_breaks",
            "reconciliation_summary",
        ]
        for table in expected_tables:
            self.assertTrue(
                self.db_manager.table_exists(table),
                f"Expected table '{table}' does not exist in database",
            )

    def test_indexes_creation(self):
        """Verifies performance indexes exist in the database schema."""
        self.db_manager.create_tables()
        rows = self.db_manager.execute_query("SELECT name FROM sqlite_master WHERE type='index'")
        index_names = [row["name"] for row in rows]

        expected_indexes = ["idx_fo_trade_id", "idx_bo_trade_id", "idx_fo_desk", "idx_bo_desk"]
        for idx in expected_indexes:
            self.assertIn(idx, index_names, f"Expected index '{idx}' missing from schema")

    def test_csv_loading_and_row_counts(self):
        """Verifies loading FO and BO CSV feeds into database staging tables."""
        self.db_manager.create_tables()

        fo_count = self.db_manager.load_front_office_csv(csv_path=self.fo_csv)
        bo_count = self.db_manager.load_back_office_csv(csv_path=self.bo_csv)

        self.assertEqual(fo_count, len(self.fo_df), "FO table row count does not match CSV")
        self.assertEqual(bo_count, len(self.bo_df), "BO table row count does not match CSV")
        self.assertEqual(self.db_manager.record_count("front_office_trades"), len(self.fo_df))
        self.assertEqual(self.db_manager.record_count("back_office_trades"), len(self.bo_df))

    def test_sql_utility_methods(self):
        """Verifies reusable query helper methods (get_trade_by_id, fetch_dataframe, get_all_front_office)."""
        self.db_manager.create_tables()
        self.db_manager.load_front_office_csv(csv_path=self.fo_csv)

        target_trade_id = self.fo_df.iloc[0]["Trade_ID"]
        trade = self.db_manager.get_trade_by_id(target_trade_id, "front_office_trades")

        self.assertIsNotNone(trade, f"Failed retrieving trade by ID: {target_trade_id}")
        self.assertEqual(trade["Trade_ID"], target_trade_id)

        df_fo = self.db_manager.get_all_front_office()
        self.assertEqual(len(df_fo), len(self.fo_df))

    def test_database_health_check(self):
        """Verifies database health check passes integrity check and table counts."""
        self.db_manager.create_tables()
        self.db_manager.load_front_office_csv(csv_path=self.fo_csv)
        self.db_manager.load_back_office_csv(csv_path=self.bo_csv)

        health = self.db_manager.database_health_check()
        self.assertEqual(health["status"], "HEALTHY")
        self.assertEqual(health["integrity_check"], "ok")
        self.assertEqual(health["table_counts"]["front_office_trades"], len(self.fo_df))
        self.assertEqual(health["table_counts"]["back_office_trades"], len(self.bo_df))


if __name__ == "__main__":
    unittest.main()
