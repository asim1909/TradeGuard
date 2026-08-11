"""
Unit test suite for PDF Executive Summary Report Generator in TradeGuard.
"""

import tempfile
import unittest
from pathlib import Path

from app import app
import app as app_module
from src.database.database_manager import DatabaseManager
from src.data_generator import DataGenerator
from src.reconciliation.reconciliation_engine import ReconciliationEngine
from src.reporting.pdf_generator import PDFReportGenerator


class TestPDFReportGenerator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_pdf.db"
        self.pdf_dir = Path(self.temp_dir.name) / "pdf_reports"

        self.db_manager = DatabaseManager(db_path=self.db_path)
        self.db_manager.connect()
        self.db_manager.create_tables()

        # Seed trade data & run reconciliation engine
        generator = DataGenerator(num_trades=50, random_seed=42, break_rate=0.1)
        fo_df, bo_df, _ = generator.run()
        self.db_manager.insert_dataframe(fo_df, "front_office_trades", if_exists="replace")
        self.db_manager.insert_dataframe(bo_df, "back_office_trades", if_exists="replace")

        engine = ReconciliationEngine(db_manager=self.db_manager)
        self.metrics = engine.run()

        app.config["TESTING"] = True
        self.client = app.test_client()

        self.orig_db_path = app_module.DEFAULT_DB_PATH
        app_module.DEFAULT_DB_PATH = self.db_path

    def tearDown(self):
        app_module.DEFAULT_DB_PATH = self.orig_db_path
        self.db_manager.close()
        self.temp_dir.cleanup()

    def test_pdf_generation(self):
        """Test PDFReportGenerator generates a non-empty PDF document."""
        summary = self.db_manager.execute_select(
            "SELECT * FROM reconciliation_summary WHERE Run_ID = ?",
            (self.metrics["Run_ID"],)
        )[0]
        breaks = self.db_manager.execute_select(
            "SELECT * FROM reconciliation_breaks WHERE Run_ID = ?",
            (self.metrics["Run_ID"],)
        )

        pdf_gen = PDFReportGenerator(output_dir=self.pdf_dir)
        pdf_path = pdf_gen.generate(dict(summary), [dict(b) for b in breaks])

        self.assertTrue(pdf_path.exists())
        self.assertTrue(pdf_path.stat().st_size > 1000, "PDF file size should be > 1KB")

    def test_pdf_api_endpoint(self):
        """Test POST /api/reports/pdf generates and returns PDF metadata."""
        response = self.client.post("/api/reports/pdf")
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["category"], "pdf")
        self.assertTrue(data["filename"].endswith(".pdf"))


if __name__ == "__main__":
    unittest.main()
