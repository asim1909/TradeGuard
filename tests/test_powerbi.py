"""
Unit Test Suite for Power BI Exporter and History Simulator (Phase 6).

Verifies unique Run_ID generation, historical run preservation, Power BI CSV export
file creation, required columns, Trade_Notional calculations, non-inflated aggregation math,
and historical simulation execution.
Compatible with standard library unittest and pytest.
"""

from pathlib import Path
import tempfile
import unittest

import pandas as pd

from src.database.database_manager import DatabaseManager
from src.data_generator import DataGenerator
from src.reconciliation.reconciliation_engine import ReconciliationEngine
from src.reporting.powerbi_exporter import PowerBIExporter
from src.utils.history_simulator import simulate_historical_runs


class TestPowerBIExporterAndSimulator(unittest.TestCase):
    """Test suite verifying Power BI exporter and historical simulator."""

    def setUp(self):
        """Set up temporary database, run synthetic data generation, database load, and reconciliation."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.db_path = self.tmp_path / "test_powerbi.db"
        self.output_dir = self.tmp_path / "powerbi"

        # Generate sample trade feeds & load into SQLite
        self.generator = DataGenerator(num_trades=100, random_seed=42, raw_dir=self.tmp_path)
        self.fo_df, self.bo_df, _ = self.generator.run()

        self.db_manager = DatabaseManager(db_path=self.db_path)
        self.db_manager.create_tables()
        self.db_manager.load_front_office_csv(csv_path=self.tmp_path / "front_office.csv")
        self.db_manager.load_back_office_csv(csv_path=self.tmp_path / "back_office.csv")

        # Run reconciliation engine
        self.engine = ReconciliationEngine(db_manager=self.db_manager, threshold=0.01)
        self.metrics = self.engine.run()

        # Initialize PowerBI exporter
        self.exporter = PowerBIExporter(db_manager=self.db_manager, output_dir=self.output_dir)

    def tearDown(self):
        """Clean up database connection and temporary directory."""
        self.db_manager.close()
        self.temp_dir.cleanup()

    def test_unique_run_id_generation_and_preservation(self):
        """Verifies that multiple reconciliation runs generate unique Run_IDs and preserve history."""
        initial_count = self.db_manager.record_count("reconciliation_summary")
        self.assertEqual(initial_count, 1)

        # Run second reconciliation
        engine2 = ReconciliationEngine(db_manager=self.db_manager, threshold=0.01)
        metrics2 = engine2.run()

        second_count = self.db_manager.record_count("reconciliation_summary")
        self.assertEqual(second_count, 2)
        self.assertNotEqual(self.metrics["Run_ID"], metrics2["Run_ID"])

        # Check break records are tagged with correct Run_IDs
        breaks = self.db_manager.fetch_dataframe("SELECT DISTINCT Run_ID FROM reconciliation_breaks")
        run_ids = set(breaks["Run_ID"].tolist())
        self.assertIn(self.metrics["Run_ID"], run_ids)
        self.assertIn(metrics2["Run_ID"], run_ids)

    def test_powerbi_export_files_and_columns_created(self):
        """Verifies that all 9 Power BI CSV datasets are created with required column headers."""
        exported = self.exporter.run()

        expected_files_and_columns = {
            "reconciliation_runs.csv": [
                "Run_ID", "Created_At", "Front_Count", "Back_Count", "Matched_Count",
                "Match_Percentage", "Total_Breaks", "Critical_Breaks", "High_Breaks",
                "Medium_Breaks", "Low_Breaks", "Execution_Time"
            ],
            "reconciliation_breaks.csv": [
                "Run_ID", "Trade_ID", "Break_Type", "Expected_Value", "Actual_Value",
                "Severity", "Detected_At", "Trader", "Desk", "Portfolio",
                "Counterparty", "Asset_Class", "Symbol", "Buy_Sell", "Currency"
            ],
            "trade_details.csv": [
                "Trade_ID", "Trade_Date", "Settlement_Date", "Trader", "Desk",
                "Portfolio", "Counterparty", "Asset_Class", "Symbol", "Buy_Sell",
                "Quantity", "Price", "Currency", "Trade_Status", "Trade_Notional"
            ],
            "desk_summary.csv": [
                "Desk", "Total_Trades", "Total_Notional", "Total_Breaks",
                "Critical_Breaks", "High_Breaks", "Medium_Breaks", "Low_Breaks", "Exception_Rate"
            ],
            "portfolio_summary.csv": [
                "Portfolio", "Total_Trades", "Total_Notional", "Total_Breaks", "Exception_Rate"
            ],
            "counterparty_summary.csv": [
                "Counterparty", "Total_Trades", "Total_Notional", "Total_Breaks", "Critical_Breaks", "Exception_Rate"
            ],
            "asset_class_summary.csv": [
                "Asset_Class", "Total_Trades", "Total_Notional", "Total_Breaks", "Exception_Rate"
            ],
            "severity_summary.csv": [
                "Severity", "Break_Count", "Percentage"
            ],
            "break_type_summary.csv": [
                "Break_Type", "Break_Count", "Percentage"
            ],
        }

        for filename, expected_cols in expected_files_and_columns.items():
            target_path = self.output_dir / filename
            self.assertTrue(target_path.exists(), f"Power BI CSV '{filename}' missing on disk")
            df = pd.read_csv(target_path)
            for col in expected_cols:
                self.assertIn(col, df.columns, f"Column '{col}' missing from '{filename}'")

    def test_trade_notional_calculation(self):
        """Verifies calculation of Trade_Notional (Quantity * Price) in trade_details.csv."""
        self.exporter.run()
        trade_df = pd.read_csv(self.output_dir / "trade_details.csv")
        self.assertFalse(trade_df.empty)

        # Check notional math
        for _, row in trade_df.iterrows():
            expected_notional = round(abs(row["Quantity"] * row["Price"]), 2)
            self.assertAlmostEqual(row["Trade_Notional"], expected_notional, places=2)
            self.assertGreaterEqual(row["Trade_Notional"], 0.0)

    def test_no_inflated_trade_counts_in_desk_summary(self):
        """Verifies that JOINs between breaks and trades do not inflate Total_Trades in desk_summary.csv."""
        self.exporter.run()
        desk_df = pd.read_csv(self.output_dir / "desk_summary.csv")
        fo_count_by_desk = self.fo_df.groupby("Desk")["Trade_ID"].nunique().to_dict()

        for _, row in desk_df.iterrows():
            desk_name = row["Desk"]
            self.assertEqual(row["Total_Trades"], fo_count_by_desk[desk_name])
            self.assertGreaterEqual(row["Exception_Rate"], 0.0)
            self.assertLessEqual(row["Exception_Rate"], 100.0)

    def test_simulate_history_preserves_runs(self):
        """Verifies that simulate_historical_runs populates historical runs and preserves pre-existing runs."""
        initial_runs = self.db_manager.record_count("reconciliation_summary")
        self.assertEqual(initial_runs, 1)

        total_runs = simulate_historical_runs(num_runs=5, base_seed=100, db_manager=self.db_manager)
        self.assertEqual(total_runs, 6)

        runs_df = self.db_manager.fetch_dataframe("SELECT * FROM reconciliation_summary")
        self.assertEqual(len(runs_df), 6)


if __name__ == "__main__":
    unittest.main()
