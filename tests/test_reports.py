"""
Unit Test Suite for ReportGenerator module (Phase 5).

Verifies reading reconciliation results from SQLite database and generating
10-sheet styled Excel workbooks, individual CSV feeds, and JSON audit files.
Compatible with standard library unittest and pytest.
"""

from pathlib import Path
import tempfile
import unittest

import openpyxl

from src.database.database_manager import DatabaseManager
from src.data_generator import DataGenerator
from src.reconciliation.reconciliation_engine import ReconciliationEngine
from src.reporting.report_generator import ReportGenerator


class TestReportGenerator(unittest.TestCase):
    """Test suite verifying ReportGenerator functionality."""

    def setUp(self):
        """Set up temporary database, run synthetic data generation, reconciliation, and database load."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.db_path = self.tmp_path / "test_reporting.db"
        self.reports_dir = self.tmp_path / "reports"

        # Generate sample trade feeds & load into SQLite
        self.generator = DataGenerator(num_trades=100, random_seed=42, raw_dir=self.tmp_path)
        self.fo_df, self.bo_df, _ = self.generator.run()

        self.db_manager = DatabaseManager(db_path=self.db_path)
        self.db_manager.create_tables()
        self.db_manager.load_front_office_csv(csv_path=self.tmp_path / "front_office.csv")
        self.db_manager.load_back_office_csv(csv_path=self.tmp_path / "back_office.csv")

        # Run reconciliation engine so SQLite tables contain results
        self.engine = ReconciliationEngine(db_manager=self.db_manager, threshold=0.01)
        self.metrics = self.engine.run()

        # Initialize report generator
        self.report_gen = ReportGenerator(db_manager=self.db_manager, reports_dir=self.reports_dir)

    def tearDown(self):
        """Clean up database connection and temporary directory."""
        self.db_manager.close()
        self.temp_dir.cleanup()

    def test_generate_excel_report_sheets(self):
        """Verifies Excel report workbook creation with all 10 required worksheets."""
        results = self.report_gen.run()
        excel_path = results["excel"]

        self.assertTrue(excel_path.exists(), "Excel report file was not created")
        self.assertGreater(excel_path.stat().st_size, 0, "Excel report file is empty")

        # Inspect workbook sheet names
        wb = openpyxl.load_workbook(excel_path)
        expected_sheets = [
            "Executive Summary",
            "Missing Trades",
            "Unexpected Trades",
            "Price Mismatches",
            "Quantity Mismatches",
            "Currency Mismatches",
            "Status Mismatches",
            "Trade Date Mismatches",
            "Settlement Date Mismatches",
            "Duplicate Trades",
        ]
        for sheet_name in expected_sheets:
            self.assertIn(sheet_name, wb.sheetnames, f"Sheet '{sheet_name}' missing from Excel report workbook")

    def test_generate_csv_reports(self):
        """Verifies generation of summary and break category CSV files in reports/csv/."""
        results = self.report_gen.run()
        csv_paths = results["csv"]

        expected_files = [
            "summary.csv",
            "missing_trades.csv",
            "unexpected_trades.csv",
            "price_mismatches.csv",
            "quantity_mismatches.csv",
            "currency_mismatches.csv",
            "status_mismatches.csv",
            "duplicate_trades.csv",
        ]

        csv_filenames = [p.name for p in csv_paths]
        for fname in expected_files:
            self.assertIn(fname, csv_filenames, f"CSV report file '{fname}' was not generated")
            target = self.reports_dir / "csv" / fname
            self.assertTrue(target.exists(), f"CSV report '{fname}' missing from disk")

    def test_generate_json_reports(self):
        """Verifies generation of summary.json and breaks.json audit files in reports/json/."""
        results = self.report_gen.run()
        sum_json, breaks_json = results["json"]

        self.assertTrue(sum_json.exists(), "summary.json was not created")
        self.assertTrue(breaks_json.exists(), "breaks.json was not created")
        self.assertGreater(sum_json.stat().st_size, 0, "summary.json is empty")
        self.assertGreater(breaks_json.stat().st_size, 0, "breaks.json is empty")

    def test_summary_values_matching_database(self):
        """Verifies summary values read from SQLite match the database run metrics."""
        summary_dict, breaks_df = self.report_gen.read_reconciliation_data()

        self.assertEqual(summary_dict["Run_ID"], self.metrics["Run_ID"])
        self.assertEqual(summary_dict["Front_Count"], self.metrics["Front_Count"])
        self.assertEqual(summary_dict["Back_Count"], self.metrics["Back_Count"])
        self.assertEqual(summary_dict["Matched_Count"], self.metrics["Matched_Count"])
        self.assertEqual(len(breaks_df), len(self.engine.all_breaks))


if __name__ == "__main__":
    unittest.main()
