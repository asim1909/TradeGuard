"""
Historical Reconciliation Data Simulator for Trade Reconciliation & Control Automation Engine.

Generates realistic historical reconciliation runs spanning a multi-day timeline, preserving
all run summaries and break records in SQLite database to support trend analysis and Power BI reporting.
"""

from datetime import datetime, timedelta
import random
import time
from typing import Optional

from config import DEFAULT_DB_PATH
from src.database.database_manager import DatabaseManager
from src.data_generator import DataGenerator
from src.reconciliation.reconciliation_engine import ReconciliationEngine
from src.utils.logger import get_logger

logger = get_logger("HistorySimulator")


def simulate_historical_runs(
    num_runs: int = 30,
    base_seed: int = 42,
    db_manager: Optional[DatabaseManager] = None,
) -> int:
    """
    Simulates reproducible historical reconciliation runs over past N days without overwriting existing data.

    Args:
        num_runs: Number of historical reconciliation runs to generate (default: 30).
        base_seed: Base random seed for reproducibility (default: 42).
        db_manager: Optional DatabaseManager instance.

    Returns:
        int: Total number of reconciliation runs stored in database.
    """
    start_time = time.perf_counter()
    logger.info(f"Starting historical simulation generating {num_runs} reconciliation runs [Seed={base_seed}]...")

    db = db_manager or DatabaseManager(db_path=DEFAULT_DB_PATH)
    db.connect()
    db.create_tables()

    now = datetime.now()

    for i in range(num_runs, 0, -1):
        run_seed = base_seed + i
        random.seed(run_seed)
        trade_count = 950 + random.randint(0, 100)
        break_rate = round(random.uniform(0.03, 0.07), 3)

        # Generate synthetic FO & BO datasets
        generator = DataGenerator(num_trades=trade_count, random_seed=run_seed, break_rate=break_rate)
        fo_df, bo_df, _ = generator.run()

        # Ingest into SQLite staging tables
        conn = db.connect()
        fo_df.to_sql("front_office_trades", conn, if_exists="replace", index=False)
        bo_df.to_sql("back_office_trades", conn, if_exists="replace", index=False)

        # Run reconciliation engine
        engine = ReconciliationEngine(db_manager=db, threshold=0.01)
        metrics = engine.run()
        run_id = metrics["Run_ID"]

        # Calculate simulated timestamp (i days ago)
        simulated_date = (now - timedelta(days=i)).strftime("%Y-%m-%d %H:%M:%S")

        # Backdate Created_At in reconciliation_summary and Detected_At in reconciliation_breaks for this Run_ID
        db.execute_insert(
            "UPDATE reconciliation_summary SET Created_At = ? WHERE Run_ID = ?",
            (simulated_date, run_id),
        )
        db.execute_insert(
            "UPDATE reconciliation_breaks SET Detected_At = ? WHERE Run_ID = ?",
            (simulated_date, run_id),
        )

        logger.info(f"Simulated Run {num_runs - i + 1}/{num_runs} [Run_ID={run_id}, Date={simulated_date}, Trades={trade_count}, Match={metrics['Match_Percentage']}%]")

    total_runs = db.record_count("reconciliation_summary")
    db.disconnect()

    elapsed = round(time.perf_counter() - start_time, 4)
    logger.info(f"Historical simulation completed in {elapsed} seconds. Total historical runs in DB: {total_runs}")
    return total_runs
