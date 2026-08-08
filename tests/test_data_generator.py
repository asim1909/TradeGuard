"""
Unit Test Suite for DataGenerator module (Phase 2).

Verifies synthetic trade generation, break injection, CSV file creation,
data quality constraints, uniqueness rules, and currency/status validity.
Compatible with standard library unittest and pytest.
"""

from pathlib import Path
import tempfile
import unittest
import pandas as pd

from config import CURRENCIES, TRADE_STATUSES
from src.data_generator import DataGenerator


class TestDataGenerator(unittest.TestCase):
    """Test suite verifying DataGenerator functionality."""

    def setUp(self):
        """Set up temporary directory and run generator instance."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.generator = DataGenerator(num_trades=100, random_seed=42, raw_dir=self.tmp_path)
        self.fo_df, self.bo_df, self.metrics = self.generator.run()

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_csv_files_generated(self):
        """Verifies that front_office.csv and back_office.csv files are successfully generated."""
        fo_csv = self.tmp_path / "front_office.csv"
        bo_csv = self.tmp_path / "back_office.csv"

        self.assertTrue(fo_csv.exists(), "front_office.csv was not created")
        self.assertTrue(bo_csv.exists(), "back_office.csv was not created")
        self.assertGreater(fo_csv.stat().st_size, 0, "front_office.csv is empty")
        self.assertGreater(bo_csv.stat().st_size, 0, "back_office.csv is empty")

    def test_trade_count_and_uniqueness(self):
        """Verifies Front Office trade count and uniqueness of Trade_ID."""
        self.assertEqual(len(self.fo_df), 100, f"Expected 100 Front Office trades, got {len(self.fo_df)}")
        self.assertEqual(self.fo_df["Trade_ID"].nunique(), 100, "Front Office Trade_IDs are not completely unique")

    def test_data_quality_constraints(self):
        """Verifies positive price, positive quantity, and Settlement_Date >= Trade_Date."""
        self.assertTrue((self.fo_df["Quantity"] > 0).all(), "Front Office contains non-positive Quantity")
        self.assertTrue((self.fo_df["Price"] > 0).all(), "Front Office contains non-positive Price")

        trade_dates = pd.to_datetime(self.fo_df["Trade_Date"])
        settlement_dates = pd.to_datetime(self.fo_df["Settlement_Date"])
        self.assertTrue((settlement_dates >= trade_dates).all(), "Settlement_Date is earlier than Trade_Date")

    def test_valid_currencies_and_statuses(self):
        """Verifies all generated currencies and trade statuses are within valid domain lists."""
        invalid_fo_currencies = set(self.fo_df["Currency"]) - set(CURRENCIES)
        self.assertFalse(invalid_fo_currencies, f"Invalid currencies found in FO: {invalid_fo_currencies}")

        invalid_fo_statuses = set(self.fo_df["Trade_Status"]) - set(TRADE_STATUSES)
        self.assertFalse(invalid_fo_statuses, f"Invalid statuses found in FO: {invalid_fo_statuses}")

        invalid_bo_currencies = set(self.bo_df["Currency"]) - set(CURRENCIES)
        self.assertFalse(invalid_bo_currencies, f"Invalid currencies found in BO: {invalid_bo_currencies}")

        invalid_bo_statuses = set(self.bo_df["Trade_Status"]) - set(TRADE_STATUSES)
        self.assertFalse(invalid_bo_statuses, f"Invalid statuses found in BO: {invalid_bo_statuses}")

    def test_break_tracking_dataframe(self):
        """Verifies internal break tracking dataframe structure and populated records."""
        self.assertTrue(hasattr(self.generator, "breaks_df"), "DataGenerator missing breaks_df attribute")
        self.assertIsInstance(self.generator.breaks_df, pd.DataFrame, "breaks_df is not a pandas DataFrame")
        self.assertFalse(self.generator.breaks_df.empty, "breaks_df should contain injected break tracking records")

        expected_cols = {"Trade_ID", "Break_Type", "Expected_Value", "Actual_Value", "Severity"}
        self.assertTrue(expected_cols.issubset(set(self.generator.breaks_df.columns)), "breaks_df missing required columns")


if __name__ == "__main__":
    unittest.main()
