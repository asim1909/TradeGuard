"""
Main Command Line Interface (CLI) Entry Point for Trade Reconciliation & Control Automation Engine.

Provides CLI subcommands for triggering synthetic data generation, database staging,
reconciliation runs, multi-format break reporting, visualization generation, and interactive guidance.
"""

import argparse
import sys
from typing import List, Optional

from config import (
    DEFAULT_DB_PATH,
    DEFAULT_REPORT_NAME,
    RECONCILIATION_THRESHOLD,
    ensure_project_directories,
)
from src.database.database_manager import DatabaseManager
from src.data_generator import DataGenerator
from src.reconciliation.reconciliation_engine import ReconciliationEngine
from src.reporting.powerbi_exporter import PowerBIExporter
from src.reporting.report_generator import ReportGenerator
from src.utils.exceptions import TradeEngineError
from src.utils.helpers import ensure_project_directories
from src.utils.history_simulator import simulate_historical_runs
from src.utils.logger import get_logger, setup_logger
from src.visualization.charts import ChartGenerator

# Initialize main CLI logger
logger = setup_logger("TradeEngineCLI")


def handle_generate_data(args: argparse.Namespace) -> None:
    """CLI handler for 'generate-data' subcommand."""
    logger.info(f"CLI Command Invoked: generate-data [Count={args.count}, Seed={args.seed}, Break Rate={args.break_rate}]")
    generator = DataGenerator(
        num_trades=args.count,
        random_seed=args.seed,
        break_rate=args.break_rate,
    )
    fo_df, bo_df, metrics = generator.run()

    summary_str = f"""
----------------------------------------

Trade Generation Completed

Front Office Trades : {metrics.get('Front Office Trades', 0)}

Back Office Trades : {metrics.get('Back Office Trades', 0)}

Missing Trades : {metrics.get('Missing Trades', 0)}

Unexpected Trades : {metrics.get('Unexpected Trades', 0)}

Price Mismatches : {metrics.get('Price Mismatches', 0)}

Quantity Mismatches : {metrics.get('Quantity Mismatches', 0)}

Status Mismatches : {metrics.get('Status Mismatches', 0)}

Trade Date Mismatches : {metrics.get('Trade Date Mismatches', 0)}

Settlement Date Mismatches : {metrics.get('Settlement Date Mismatches', 0)}

Currency Mismatches : {metrics.get('Currency Mismatches', 0)}

Duplicate Trades : {metrics.get('Duplicate Trades', 0)}

CSV Files Saved

----------------------------------------"""
    print(summary_str)
    logger.info("Trade generation process finished successfully.")


def handle_load_data(args: argparse.Namespace) -> None:
    """CLI handler for 'load-data' subcommand."""
    logger.info(f"CLI Command Invoked: load-data [DB Path={args.db_path}, FO CSV={args.fo_csv}, BO CSV={args.bo_csv}]")
    db_manager = DatabaseManager(db_path=args.db_path)
    db_manager.connect()
    db_manager.create_tables()

    fo_loaded = db_manager.load_front_office_csv(csv_path=args.fo_csv)
    bo_loaded = db_manager.load_back_office_csv(csv_path=args.bo_csv)
    db_manager.disconnect()

    summary_str = f"""
----------------------------------------

Database Created

Schema Loaded

Front Office Rows Loaded : {fo_loaded}

Back Office Rows Loaded : {bo_loaded}

Indexes Created

Load Completed Successfully

----------------------------------------"""
    print(summary_str)
    logger.info("Data loading process completed successfully.")


def handle_reconcile(args: argparse.Namespace) -> None:
    """CLI handler for 'reconcile' subcommand."""
    logger.info(f"CLI Command Invoked: reconcile [Threshold={args.threshold}, DB Path={args.db_path}]")
    db_manager = DatabaseManager(db_path=args.db_path)
    db_manager.connect()

    engine = ReconciliationEngine(db_manager=db_manager, threshold=args.threshold)
    metrics = engine.run()

    db_manager.disconnect()

    summary_str = f"""
----------------------------------------

Reconciliation Completed

Front Office Trades : {metrics.get('Front_Count', 0)}

Back Office Trades : {metrics.get('Back_Count', 0)}

Matched Trades : {metrics.get('Matched_Count', 0)}

Missing Trades : {metrics.get('Missing_Count', 0)}

Unexpected Trades : {metrics.get('Unexpected_Count', 0)}

Price Mismatches : {metrics.get('Price_Mismatch_Count', 0)}

Quantity Mismatches : {metrics.get('Quantity_Mismatch_Count', 0)}

Status Mismatches : {metrics.get('Status_Mismatch_Count', 0)}

Trade Date Mismatches : {metrics.get('Trade_Date_Mismatch_Count', 0)}

Settlement Date Mismatches : {metrics.get('Settlement_Date_Mismatch_Count', 0)}

Currency Mismatches : {metrics.get('Currency_Mismatch_Count', 0)}

Duplicate Trades : {metrics.get('Duplicate_Count', 0)}

Critical Issues : {metrics.get('Critical_Breaks', 0)}

Match Percentage : {metrics.get('Match_Percentage', 0.0):.2f}%

Execution Time : {metrics.get('Execution_Time', 0.0):.4f}s

Results stored successfully.

----------------------------------------"""
    print(summary_str)
    logger.info("Trade reconciliation run completed successfully.")


def handle_report(args: argparse.Namespace) -> None:
    """CLI handler for 'report' subcommand."""
    logger.info(f"CLI Command Invoked: report [DB Path={args.db_path}]")
    db_manager = DatabaseManager(db_path=args.db_path)
    db_manager.connect()

    report_gen = ReportGenerator(db_manager=db_manager)
    results = report_gen.run()

    db_manager.disconnect()

    summary_str = """
---------------------------------------

Generating Reports...

Excel Report Created

CSV Reports Created

JSON Reports Created

Reports Saved

Location

reports/

Completed Successfully

---------------------------------------"""
    print(summary_str)
    logger.info("Report generation process completed successfully.")


def handle_charts(args: argparse.Namespace) -> None:
    """CLI handler for 'charts' subcommand."""
    logger.info("CLI Command Invoked: charts")
    chart_gen = ChartGenerator()
    chart_paths = chart_gen.generate_all_charts(breaks_data=[])
    logger.info(f"[SUCCESS] Chart visualization placeholder executed. Rendered charts: {chart_paths}")


def handle_powerbi_export(args: argparse.Namespace) -> None:
    """CLI handler for 'powerbi-export' subcommand."""
    logger.info(f"CLI Command Invoked: powerbi-export [DB Path={args.db_path}]")
    db_manager = DatabaseManager(db_path=args.db_path)
    exporter = PowerBIExporter(db_manager=db_manager)
    exporter.run()
    db_manager.disconnect()

    summary_str = """
----------------------------------------

Power BI Export Completed

Reconciliation Runs Exported

Reconciliation Breaks Exported

Trade Details Exported

Desk Summary Exported

Portfolio Summary Exported

Counterparty Summary Exported

Asset Class Summary Exported

Severity Summary Exported

Break Type Summary Exported

Location:
reports/powerbi/

----------------------------------------"""
    print(summary_str)
    logger.info("Power BI export process completed successfully.")


def handle_simulate_history(args: argparse.Namespace) -> None:
    """CLI handler for 'simulate-history' subcommand."""
    logger.info(f"CLI Command Invoked: simulate-history [Runs={args.runs}, Seed={args.seed}, DB Path={args.db_path}]")
    db_manager = DatabaseManager(db_path=args.db_path)
    total = simulate_historical_runs(num_runs=args.runs, base_seed=args.seed, db_manager=db_manager)
    print(f"\nSuccessfully simulated {args.runs} historical reconciliation runs. Total database runs: {total}.\n")


def handle_dashboard(args: argparse.Namespace) -> None:
    """CLI handler for 'dashboard' subcommand."""
    logger.info(f"CLI Command Invoked: dashboard [Host={args.host}, Port={args.port}]")
    from app import run_web_server
    run_web_server(host=args.host, port=args.port, debug=args.debug)


def handle_help(args: argparse.Namespace) -> None:
    """CLI handler for 'help' subcommand."""
    logger.info("=========================================================================")
    logger.info("   Trade Reconciliation & Control Automation Engine - CLI Guide          ")
    logger.info("=========================================================================")
    logger.info("Available Commands:")
    logger.info("  python main.py generate-data  - Generate synthetic FO & BO trade datasets")
    logger.info("  python main.py load-data       - Ingest raw CSV trade feeds into database")
    logger.info("  python main.py reconcile       - Execute FO vs BO trade reconciliation engine")
    logger.info("  python main.py report          - Export Excel, CSV, and JSON break reports")
    logger.info("  python main.py charts          - Render visualization charts for break metrics")
    logger.info("  python main.py help            - Display this CLI usage and command reference")
    logger.info("=========================================================================")


def build_parser() -> argparse.ArgumentParser:
    """Constructs the root argument parser and subcommands."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Trade Reconciliation & Control Automation Engine CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging output")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: generate-data
    p_gen = subparsers.add_parser("generate-data", help="Generate synthetic FO & BO trade feeds")
    p_gen.add_argument("--count", type=int, default=1000, help="Number of trades to generate (Default: 1000)")
    p_gen.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (Default: 42)")
    p_gen.add_argument("--break-rate", type=float, default=0.04, help="Target break ratio (Default: 0.04)")

    # Command: load-data
    p_load = subparsers.add_parser("load-data", help="Load raw CSV feeds into SQLite staging database")
    p_load.add_argument("--fo-csv", type=str, default="data/raw/front_office.csv", help="Path to FO CSV")
    p_load.add_argument("--bo-csv", type=str, default="data/raw/back_office.csv", help="Path to BO CSV")
    p_load.add_argument("--db-path", type=str, default=str(DEFAULT_DB_PATH), help="Target SQLite database path")

    # Command: reconcile
    p_rec = subparsers.add_parser("reconcile", help="Execute FO vs BO trade reconciliation engine")
    p_rec.add_argument("--threshold", type=float, default=RECONCILIATION_THRESHOLD, help="Price discrepancy tolerance")
    p_rec.add_argument("--db-path", type=str, default=str(DEFAULT_DB_PATH), help="SQLite database path")

    # Command: report
    p_rep = subparsers.add_parser("report", help="Export reconciliation break reports in Excel, CSV, and JSON formats")
    p_rep.add_argument("--name", type=str, default=DEFAULT_REPORT_NAME, help="Base output filename prefix")
    p_rep.add_argument("--formats", nargs="+", default=["excel", "csv", "json"], help="Output formats")
    p_rep.add_argument("--db-path", type=str, default=str(DEFAULT_DB_PATH), help="Target SQLite database path")

    # Command: charts
    subparsers.add_parser("charts", help="Render reconciliation break visualization charts")

    # Command: powerbi-export
    p_pbi = subparsers.add_parser("powerbi-export", help="Export analytics-ready CSV datasets for Power BI")
    p_pbi.add_argument("--db-path", type=str, default=str(DEFAULT_DB_PATH), help="SQLite database path")

    # Command: simulate-history
    p_sim = subparsers.add_parser("simulate-history", help="Simulate historical reconciliation runs over past N days")
    p_sim.add_argument("--runs", type=int, default=30, help="Number of historical runs to generate (Default: 30)")
    p_sim.add_argument("--seed", type=int, default=42, help="Base random seed (Default: 42)")
    p_sim.add_argument("--db-path", type=str, default=str(DEFAULT_DB_PATH), help="SQLite database path")

    # Command: dashboard
    p_dash = subparsers.add_parser("dashboard", help="Launch interactive web dashboard server")
    p_dash.add_argument("--host", type=str, default="127.0.0.1", help="Web server host IP (Default: 127.0.0.1)")
    p_dash.add_argument("--port", type=int, default=5000, help="Web server port (Default: 5000)")
    p_dash.add_argument("--debug", action="store_true", help="Enable Flask debug mode")

    # Command: help
    subparsers.add_parser("help", help="Display CLI command usage reference")

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """Main CLI execution routing function."""
    ensure_project_directories()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        setup_logger(level=10)  # DEBUG level

    if not args.command or args.command == "help":
        handle_help(args)
        return

    command_map = {
        "generate-data": handle_generate_data,
        "load-data": handle_load_data,
        "reconcile": handle_reconcile,
        "report": handle_report,
        "charts": handle_charts,
        "powerbi-export": handle_powerbi_export,
        "simulate-history": handle_simulate_history,
        "dashboard": handle_dashboard,
    }

    handler = command_map.get(args.command)
    if handler:
        handler(args)
    else:
        logger.error(f"Unknown command: '{args.command}'. Use 'python main.py help' for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
