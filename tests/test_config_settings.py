"""
Unit test suite for Live Reconciliation & Generator Settings API controls in TradeGuard.
"""

import json
import tempfile
import unittest
from pathlib import Path

from app import app
import app as app_module
from src.database.database_manager import DatabaseManager


class TestConfigSettingsAPI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_config_api.db"

        self.db_manager = DatabaseManager(db_path=self.db_path)
        self.db_manager.connect()
        self.db_manager.create_tables()

        app.config["TESTING"] = True
        self.client = app.test_client()

        self.orig_db_path = app_module.DEFAULT_DB_PATH
        app_module.DEFAULT_DB_PATH = self.db_path

    def tearDown(self):
        app_module.DEFAULT_DB_PATH = self.orig_db_path
        self.db_manager.close()
        self.temp_dir.cleanup()

    def test_get_config_api(self):
        """Test GET /api/config returns default configuration parameters."""
        response = self.client.get("/api/config")
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["default_num_trades"], 1000)
        self.assertEqual(data["default_break_rate"], 0.04)
        self.assertEqual(data["default_reconcile_threshold"], 0.01)

    def test_dynamic_generate_and_reconcile_settings(self):
        """Test POST /api/generate-data and POST /api/reconcile with custom settings."""
        # 1. Custom generate data call
        gen_payload = {
            "count": 200,
            "seed": 99,
            "break_rate": 0.08
        }
        gen_resp = self.client.post(
            "/api/generate-data",
            data=json.dumps(gen_payload),
            content_type="application/json"
        )
        gen_data = gen_resp.get_json()
        self.assertEqual(gen_resp.status_code, 200)
        self.assertEqual(gen_data["status"], "success")

        # 2. Custom reconcile call with higher tolerance threshold ($0.50)
        rec_payload = {
            "threshold": 0.50
        }
        rec_resp = self.client.post(
            "/api/reconcile",
            data=json.dumps(rec_payload),
            content_type="application/json"
        )
        rec_data = rec_resp.get_json()
        self.assertEqual(rec_resp.status_code, 200)
        self.assertEqual(rec_data["status"], "success")
        self.assertIn("Tolerance: $0.50", rec_data["message"])


if __name__ == "__main__":
    unittest.main()
