"""
Unit test suite for Break Resolution & Audit Lifecycle Workflow in TradeGuard.
"""

import json
import tempfile
import unittest
from pathlib import Path

from app import app
from src.database.database_manager import DatabaseManager
from src.data_generator import DataGenerator
from src.reconciliation.reconciliation_engine import ReconciliationEngine


class TestBreakResolution(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_resolution.db"
        
        self.db_manager = DatabaseManager(db_path=self.db_path)
        self.db_manager.connect()
        self.db_manager.create_tables()

        # Seed data & run reconciliation to generate break records
        generator = DataGenerator(num_trades=50, random_seed=42, break_rate=0.1)
        fo_df, bo_df, _ = generator.run()
        self.db_manager.insert_dataframe(fo_df, "front_office_trades", if_exists="replace")
        self.db_manager.insert_dataframe(bo_df, "back_office_trades", if_exists="replace")

        engine = ReconciliationEngine(db_manager=self.db_manager)
        engine.run()

        # Flask test client setup
        app.config["TESTING"] = True
        self.client = app.test_client()

    def tearDown(self):
        self.db_manager.close()
        self.temp_dir.cleanup()

    def test_break_resolution_workflow(self):
        """Test resolving a break via API endpoint and verifying SQLite audit logs."""
        breaks = self.db_manager.execute_select("SELECT ID, Trade_ID, Resolution_Status FROM reconciliation_breaks LIMIT 1")
        self.assertTrue(len(breaks) > 0, "Should have generated break records")
        
        break_id = breaks[0]["ID"] if hasattr(breaks[0], "keys") else breaks[0][0]
        trade_id = breaks[0]["Trade_ID"] if hasattr(breaks[0], "keys") else breaks[0][1]

        # Call POST /api/breaks/resolve
        payload = {
            "break_id": break_id,
            "status": "RESOLVED",
            "reason": "Price variance approved by Trading Desk",
            "user": "Lead Product Controller",
            "notes": "Verified against Bloomberg pricing tick data."
        }

        # Override default DB path in app module temporarily
        from app import DEFAULT_DB_PATH
        import app as app_module
        orig_path = app_module.DEFAULT_DB_PATH
        app_module.DEFAULT_DB_PATH = self.db_path

        try:
            response = self.client.post(
                "/api/breaks/resolve",
                data=json.dumps(payload),
                content_type="application/json"
            )
            data = response.get_json()

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["new_status"], "RESOLVED")

            # Verify reconciliation_breaks table update
            updated = self.db_manager.execute_select(
                "SELECT Resolution_Status, Resolution_Reason, Resolved_By FROM reconciliation_breaks WHERE ID = ?",
                (break_id,)
            )
            res_status = updated[0]["Resolution_Status"] if hasattr(updated[0], "keys") else updated[0][0]
            self.assertEqual(res_status, "RESOLVED")

            # Verify break_resolutions_history audit table
            history = self.db_manager.execute_select(
                "SELECT Break_ID, Trade_ID, New_Status, Action_By FROM break_resolutions_history WHERE Break_ID = ?",
                (break_id,)
            )
            self.assertTrue(len(history) > 0, "Audit log record should be created")
            action_by = history[0]["Action_By"] if hasattr(history[0], "keys") else history[0][3]
            self.assertEqual(action_by, "Lead Product Controller")

        finally:
            app_module.DEFAULT_DB_PATH = orig_path


if __name__ == "__main__":
    unittest.main()
