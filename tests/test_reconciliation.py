"""
Unit Test Suite for ReconciliationEngine module (Phase 4).

Verifies SQL-based detection of missing trades, unexpected trades, duplicate trades,
price/quantity mismatches, status mismatches, trade/settlement date mismatches,
currency mismatches, severity assignment, break persistence, and summary generation.
Compatible with standard library unittest and pytest.
"""

from pathlib import Path
import tempfile
import unittest

from src.database.database_manager import DatabaseManager
from src.data_generator import DataGenerator
from src.reconciliation.reconciliation_engine import ReconciliationEngine


class TestReconciliationEngine(unittest.TestCase):
    """Test suite verifying ReconciliationEngine functionality."""

    def setUp(self):
        """Set up temporary database, generate trade feeds, and load staging tables."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.db_path = self.tmp_path / "test_reconciliation.db"

        # Generate sample trade feeds (100 trades with injected breaks)
        self.generator = DataGenerator(num_trades=100, random_seed=42, raw_dir=self.tmp_path)
        self.fo_df, self.bo_df, self.gen_metrics = self.generator.run()

        self.fo_csv = self.tmp_path / "front_office.csv"
        self.bo_csv = self.tmp_path / "back_office.csv"

        # Initialize database and load tables
        self.db_manager = DatabaseManager(db_path=self.db_path)
        self.db_manager.create_tables()
        self.db_manager.load_front_office_csv(csv_path=self.fo_csv)
        self.db_manager.load_back_office_csv(csv_path=self.bo_csv)

        # Initialize reconciliation engine
        self.engine = ReconciliationEngine(db_manager=self.db_manager, threshold=0.01)

    def tearDown(self):
        """Clean up database connection and temporary directory."""
        self.db_manager.close()
        self.temp_dir.cleanup()

    def test_find_missing_trades(self):
        """Verifies detection of trades present in FO but missing in BO."""
        missing = self.engine.find_missing_trades()
        self.assertGreater(len(missing), 0, "Failed to detect missing trades")
        for break_rec in missing:
            self.assertEqual(break_rec["Break_Type"], "Missing Trade")
            self.assertEqual(break_rec["Severity"], "CRITICAL")

    def test_find_unexpected_trades(self):
        """Verifies detection of trades present in BO but missing in FO."""
        unexpected = self.engine.find_unexpected_trades()
        self.assertGreater(len(unexpected), 0, "Failed to detect unexpected trades")
        for break_rec in unexpected:
            self.assertEqual(break_rec["Break_Type"], "Unexpected Trade")
            self.assertEqual(break_rec["Severity"], "CRITICAL")

    def test_find_duplicate_trades(self):
        """Verifies detection of duplicate Trade_IDs in BO."""
        duplicates = self.engine.find_duplicate_trades()
        self.assertGreater(len(duplicates), 0, "Failed to detect duplicate trades")
        for break_rec in duplicates:
            self.assertEqual(break_rec["Break_Type"], "Duplicate Trade")
            self.assertEqual(break_rec["Severity"], "HIGH")

    def test_find_price_mismatches(self):
        """Verifies detection of price mismatches exceeding tolerance threshold."""
        prices = self.engine.find_price_mismatches()
        self.assertGreater(len(prices), 0, "Failed to detect price mismatches")
        for break_rec in prices:
            self.assertEqual(break_rec["Break_Type"], "Price Mismatch")
            self.assertEqual(break_rec["Severity"], "MEDIUM")

    def test_find_quantity_mismatches(self):
        """Verifies detection of unit quantity mismatches."""
        quantities = self.engine.find_quantity_mismatches()
        self.assertGreater(len(quantities), 0, "Failed to detect quantity mismatches")
        for break_rec in quantities:
            self.assertEqual(break_rec["Break_Type"], "Quantity Mismatch")
            self.assertEqual(break_rec["Severity"], "HIGH")

    def test_find_status_mismatches(self):
        """Verifies detection of trade status mismatches."""
        statuses = self.engine.find_status_mismatches()
        self.assertGreater(len(statuses), 0, "Failed to detect status mismatches")
        for break_rec in statuses:
            self.assertEqual(break_rec["Break_Type"], "Status Mismatch")
            self.assertEqual(break_rec["Severity"], "LOW")

    def test_find_date_and_currency_mismatches(self):
        """Verifies detection of trade date, settlement date, and currency mismatches."""
        trade_dates = self.engine.find_trade_date_mismatches()
        settle_dates = self.engine.find_settlement_date_mismatches()
        currencies = self.engine.find_currency_mismatches()

        self.assertGreater(len(trade_dates), 0, "Failed to detect trade date mismatches")
        self.assertGreater(len(settle_dates), 0, "Failed to detect settlement date mismatches")
        self.assertGreater(len(currencies), 0, "Failed to detect currency mismatches")

    def test_severity_assignment(self):
        """Verifies severity rule mapping logic."""
        self.assertEqual(self.engine.assign_severity("Missing Trade"), "CRITICAL")
        self.assertEqual(self.engine.assign_severity("Unexpected Trade"), "CRITICAL")
        self.assertEqual(self.engine.assign_severity("Duplicate Trade"), "HIGH")
        self.assertEqual(self.engine.assign_severity("Quantity Mismatch"), "HIGH")
        self.assertEqual(self.engine.assign_severity("Price Mismatch"), "MEDIUM")
        self.assertEqual(self.engine.assign_severity("Currency Mismatch"), "MEDIUM")
        self.assertEqual(self.engine.assign_severity("Status Mismatch"), "LOW")

    def test_full_reconciliation_workflow_and_persistence(self):
        """Verifies end-to-end reconciliation execution, break persistence, and summary calculation."""
        metrics = self.engine.run()

        self.assertIn("Run_ID", metrics)
        self.assertGreater(metrics["Front_Count"], 0)
        self.assertGreater(metrics["Back_Count"], 0)
        self.assertGreater(metrics["Match_Percentage"], 0.0)

        # Check breaks persisted in SQLite table
        break_count = self.db_manager.record_count("reconciliation_breaks")
        self.assertEqual(break_count, len(self.engine.all_breaks))

        # Check summary persisted in SQLite table
        summary_count = self.db_manager.record_count("reconciliation_summary")
        self.assertEqual(summary_count, 1)


if __name__ == "__main__":
    unittest.main()
