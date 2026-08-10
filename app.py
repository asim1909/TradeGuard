"""
Flask REST API Web Server for Trade Reconciliation & Control Automation Engine (TradeGuard).

Serves the interactive web dashboard frontend and exposes REST API endpoints for triggering
data generation, SQL reconciliation, historical simulation, report downloads, and analytics queries.
"""

from datetime import datetime
from pathlib import Path
import os
from typing import Any, Dict, List

from flask import Flask, jsonify, request, send_from_directory

from config import (
    CSV_REPORTS_DIR, DEFAULT_DB_PATH, EXCEL_REPORTS_DIR, JSON_REPORTS_DIR,
    POWERBI_REPORTS_DIR, PROJECT_ROOT, REPORTS_DIR,
)
from src.database.database_manager import DatabaseManager
from src.data_generator import DataGenerator
from src.reconciliation.reconciliation_engine import ReconciliationEngine
from src.reporting.powerbi_exporter import PowerBIExporter
from src.reporting.report_generator import ReportGenerator
from src.utils.helpers import ensure_project_directories
from src.utils.history_simulator import simulate_historical_runs
from src.utils.logger import get_logger

logger = get_logger("TradeGuardWebApp")

ensure_project_directories()

app = Flask(__name__, static_folder="static", static_url_path="/static")


def get_db() -> DatabaseManager:
    """Returns a DatabaseManager instance for request handling."""
    db = DatabaseManager(db_path=DEFAULT_DB_PATH)
    db.connect()
    db.create_tables()
    return db


def rows_to_dicts(rows: List[Any]) -> List[Dict[str, Any]]:
    """Converts a list of SQLite Row objects or tuples/dicts into standard JSON-serializable dicts."""
    result = []
    for r in rows:
        if hasattr(r, "keys"):
            result.append(dict(r))
        elif isinstance(r, dict):
            result.append(r)
        else:
            result.append(r)
    return result


@app.route("/")
def index():
    """Serves the main single-page web dashboard."""
    index_path = PROJECT_ROOT / "static" / "index.html"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "TradeGuard Dashboard Loading...", 200


@app.route("/api/status", methods=["GET"])
def get_status():
    """Returns database status, connection metrics, and record counts."""
    db = get_db()
    try:
        summary_cnt = db.record_count("reconciliation_summary")
        breaks_cnt = db.record_count("reconciliation_breaks")
        fo_cnt = db.record_count("front_office_trades")
        bo_cnt = db.record_count("back_office_trades")

        latest_run = None
        if summary_cnt > 0:
            latest = db.execute_select(
                "SELECT Run_ID, Match_Percentage, Created_At FROM reconciliation_summary ORDER BY Created_At DESC LIMIT 1"
            )
            if latest:
                latest_run = rows_to_dicts(latest)[0]

        return jsonify({
            "status": "online",
            "db_path": str(DEFAULT_DB_PATH),
            "historical_runs_count": summary_cnt,
            "total_breaks_count": breaks_cnt,
            "front_office_count": fo_cnt,
            "back_office_count": bo_cnt,
            "latest_run": latest_run,
        })
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.disconnect()


@app.route("/api/summary", methods=["GET"])
def get_summary():
    """Returns latest run summary metrics and historical run trend series."""
    db = get_db()
    try:
        latest = db.execute_select(
            "SELECT * FROM reconciliation_summary ORDER BY Created_At DESC LIMIT 1"
        )
        latest_dict = rows_to_dicts(latest)[0] if latest else {}

        history = db.execute_select(
            "SELECT Run_ID, Created_At, Front_Count, Back_Count, Matched_Count, Match_Percentage, "
            "(Critical_Breaks + High_Breaks + Medium_Breaks + Low_Breaks) AS Total_Breaks, "
            "Critical_Breaks, High_Breaks, Medium_Breaks, Low_Breaks, Execution_Time "
            "FROM reconciliation_summary ORDER BY Created_At ASC"
        )

        return jsonify({
            "latest": latest_dict,
            "history": rows_to_dicts(history),
        })
    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.disconnect()


@app.route("/api/breaks", methods=["GET"])
def get_breaks():
    """Returns reconciliation breaks enriched with trade metadata, severity tags, and resolution status."""
    db = get_db()
    try:
        query = """
            SELECT 
                b.ID, b.Run_ID, b.Trade_ID, b.Break_Type, b.Expected_Value, b.Actual_Value, b.Severity,
                COALESCE(b.Resolution_Status, 'UNRESOLVED') AS Resolution_Status,
                b.Resolution_Reason, b.Resolved_By, b.Resolved_At, b.Detected_At,
                COALESCE(f.Trader, bo.Trader, 'N/A') AS Trader,
                COALESCE(f.Desk, bo.Desk, 'Unassigned') AS Desk,
                COALESCE(f.Portfolio, bo.Portfolio, 'Unassigned') AS Portfolio,
                COALESCE(f.Counterparty, bo.Counterparty, 'Unassigned') AS Counterparty,
                COALESCE(f.Asset_Class, bo.Asset_Class, 'Unassigned') AS Asset_Class,
                COALESCE(f.Symbol, bo.Symbol, 'N/A') AS Symbol,
                COALESCE(f.Currency, bo.Currency, 'USD') AS Currency
            FROM reconciliation_breaks b
            LEFT JOIN front_office_trades f ON b.Trade_ID = f.Trade_ID
            LEFT JOIN back_office_trades bo ON b.Trade_ID = bo.Trade_ID
            ORDER BY b.Detected_At DESC, b.ID DESC
            LIMIT 500
        """
        rows = db.execute_select(query)
        return jsonify({"breaks": rows_to_dicts(rows)})
    except Exception as e:
        logger.error(f"Error fetching breaks: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.disconnect()


@app.route("/api/breaks/resolve", methods=["POST"])
def resolve_break_api():
    """Updates resolution status of a break and logs audit trail record."""
    db = get_db()
    try:
        data = request.get_json() or {}
        break_id = data.get("break_id")
        new_status = (data.get("status") or "RESOLVED").upper()
        reason = data.get("reason", "Approved by Product Control")
        user = data.get("user", "Product Controller")
        notes = data.get("notes", "")

        if not break_id:
            return jsonify({"status": "error", "message": "Missing break_id"}), 400

        valid_statuses = ["UNRESOLVED", "RESOLVED", "ESCALATED", "UNDER_REVIEW"]
        if new_status not in valid_statuses:
            return jsonify({"status": "error", "message": f"Invalid status. Must be one of {valid_statuses}"}), 400

        current = db.execute_select("SELECT Trade_ID, Resolution_Status FROM reconciliation_breaks WHERE ID = ?", (break_id,))
        if not current:
            return jsonify({"status": "error", "message": f"Break ID {break_id} not found"}), 404

        trade_id = current[0]["Trade_ID"] if hasattr(current[0], "keys") else current[0][0]
        prev_status = (current[0]["Resolution_Status"] if hasattr(current[0], "keys") else current[0][1]) or "UNRESOLVED"

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.execute_query(
            "UPDATE reconciliation_breaks SET Resolution_Status = ?, Resolution_Reason = ?, Resolved_By = ?, Resolved_At = ? WHERE ID = ?",
            (new_status, reason, user, now_str, break_id)
        )

        db.execute_query(
            "INSERT INTO break_resolutions_history (Break_ID, Trade_ID, Previous_Status, New_Status, Reason, Action_By, Notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (break_id, trade_id, prev_status, new_status, reason, user, notes)
        )

        return jsonify({
            "status": "success",
            "message": f"Break #{break_id} for Trade {trade_id} marked as {new_status}.",
            "break_id": break_id,
            "new_status": new_status,
            "resolved_at": now_str
        })
    except Exception as e:
        logger.error(f"Error resolving break: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.disconnect()


@app.route("/api/trades", methods=["GET"])
def get_trades():
    """Returns Front Office trade population with calculated notionals."""
    db = get_db()
    try:
        query = """
            SELECT 
                Trade_ID, Trade_Date, Settlement_Date, Trader, Desk, Portfolio, Counterparty,
                Asset_Class, Symbol, Buy_Sell, Quantity, Price, Currency, Trade_Status,
                ROUND(ABS(Quantity * Price), 2) AS Trade_Notional
            FROM front_office_trades
            ORDER BY Trade_ID ASC
            LIMIT 500
        """
        rows = db.execute_select(query)
        return jsonify({"trades": rows_to_dicts(rows)})
    except Exception as e:
        logger.error(f"Error fetching trades: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.disconnect()


@app.route("/api/risk-summary", methods=["GET"])
def get_risk_summary():
    """Returns aggregated desk, portfolio, counterparty, asset class, and severity risk metrics."""
    db = get_db()
    try:
        desks = db.execute_select("""
            WITH FO_Desk AS (
                SELECT Desk, COUNT(DISTINCT Trade_ID) AS Total_Trades, SUM(ABS(Quantity * Price)) AS Total_Notional
                FROM front_office_trades GROUP BY Desk
            ),
            Breaks_Desk AS (
                SELECT COALESCE(f.Desk, bo.Desk) AS Desk, COUNT(b.ID) AS Total_Breaks, COUNT(DISTINCT b.Trade_ID) AS Affected_Trades,
                SUM(CASE WHEN b.Severity = 'CRITICAL' THEN 1 ELSE 0 END) AS Critical_Breaks
                FROM reconciliation_breaks b
                LEFT JOIN front_office_trades f ON b.Trade_ID = f.Trade_ID
                LEFT JOIN back_office_trades bo ON b.Trade_ID = bo.Trade_ID
                GROUP BY COALESCE(f.Desk, bo.Desk)
            )
            SELECT d.Desk, d.Total_Trades, ROUND(d.Total_Notional, 2) AS Total_Notional,
                   COALESCE(b.Total_Breaks, 0) AS Total_Breaks, COALESCE(b.Critical_Breaks, 0) AS Critical_Breaks,
                   ROUND(CASE WHEN d.Total_Trades > 0 THEN (CAST(COALESCE(b.Affected_Trades, 0) AS FLOAT) / d.Total_Trades) * 100 ELSE 0 END, 2) AS Exception_Rate
            FROM FO_Desk d LEFT JOIN Breaks_Desk b ON d.Desk = b.Desk ORDER BY Exception_Rate DESC
        """)

        severities = db.execute_select("""
            SELECT Severity, COUNT(*) AS Break_Count,
                   ROUND((CAST(COUNT(*) AS FLOAT) / (SELECT COUNT(*) FROM reconciliation_breaks)) * 100, 2) AS Percentage
            FROM reconciliation_breaks GROUP BY Severity
        """)

        break_types = db.execute_select("""
            SELECT Break_Type, COUNT(*) AS Break_Count,
                   ROUND((CAST(COUNT(*) AS FLOAT) / (SELECT COUNT(*) FROM reconciliation_breaks)) * 100, 2) AS Percentage
            FROM reconciliation_breaks GROUP BY Break_Type ORDER BY Break_Count DESC
        """)

        return jsonify({
            "desks": rows_to_dicts(desks),
            "severities": rows_to_dicts(severities),
            "break_types": rows_to_dicts(break_types),
        })
    except Exception as e:
        logger.error(f"Error fetching risk summary: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.disconnect()


@app.route("/api/generate-data", methods=["POST"])
def generate_data_api():
    """Triggers synthetic trade data generation and ingests feeds into SQLite staging tables."""
    db = get_db()
    try:
        data = request.get_json() or {}
        count = int(data.get("count", 1000))
        seed = int(data.get("seed", 42))

        generator = DataGenerator(num_trades=count, random_seed=seed)
        fo_df, bo_df, stats = generator.run()

        conn = db.connect()
        fo_df.to_sql("front_office_trades", conn, if_exists="replace", index=False)
        bo_df.to_sql("back_office_trades", conn, if_exists="replace", index=False)

        return jsonify({
            "status": "success",
            "message": f"Successfully generated and loaded {len(fo_df)} FO trades and {len(bo_df)} BO trades.",
            "stats": stats,
        })
    except Exception as e:
        logger.error(f"Error generating data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.disconnect()


@app.route("/api/reconcile", methods=["POST"])
def reconcile_api():
    """Triggers the SQL reconciliation engine and updates database audit tables."""
    db = get_db()
    try:
        engine = ReconciliationEngine(db_manager=db, threshold=0.01)
        metrics = engine.run()
        return jsonify({
            "status": "success",
            "message": f"Reconciliation completed in {metrics['Execution_Time']}s with Match Rate: {metrics['Match_Percentage']}%.",
            "metrics": metrics,
        })
    except Exception as e:
        logger.error(f"Error running reconciliation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.disconnect()


@app.route("/api/simulate-history", methods=["POST"])
def simulate_history_api():
    """Simulates reproducible historical reconciliation runs over the past 30 days."""
    db = get_db()
    try:
        data = request.get_json() or {}
        runs = int(data.get("runs", 30))
        seed = int(data.get("seed", 42))

        total_runs = simulate_historical_runs(num_runs=runs, base_seed=seed, db_manager=db)
        return jsonify({
            "status": "success",
            "message": f"Successfully simulated {runs} historical runs. Total historical runs in DB: {total_runs}.",
            "total_runs": total_runs,
        })
    except Exception as e:
        logger.error(f"Error simulating history: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.disconnect()


@app.route("/api/export-powerbi", methods=["POST"])
def export_powerbi_api():
    """Generates all 9 Power BI analytics CSV datasets in reports/powerbi/."""
    db = get_db()
    try:
        exporter = PowerBIExporter(db_manager=db)
        files = exporter.run()
        file_names = {k: v.name for k, v in files.items()}
        return jsonify({
            "status": "success",
            "message": "Successfully exported 9 Power BI analytics CSV datasets.",
            "files": file_names,
        })
    except Exception as e:
        logger.error(f"Error exporting Power BI datasets: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.disconnect()


@app.route("/api/reports/list", methods=["GET"])
def list_reports():
    """Lists available Excel, CSV, JSON, and Power BI report files ready for download."""
    try:
        files = []
        for cat_name, cat_dir in [("excel", EXCEL_REPORTS_DIR), ("csv", CSV_REPORTS_DIR),
                                 ("json", JSON_REPORTS_DIR), ("powerbi", POWERBI_REPORTS_DIR)]:
            if cat_dir.exists():
                for p in cat_dir.glob("*"):
                    if p.is_file():
                        files.append({
                            "category": cat_name,
                            "filename": p.name,
                            "size_bytes": p.stat().st_size,
                            "modified": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        })
        return jsonify({"reports": files})
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/download/<category>/<filename>", methods=["GET"])
def download_report(category: str, filename: str):
    """Serves report file for browser download."""
    category_map = {
        "excel": EXCEL_REPORTS_DIR,
        "csv": CSV_REPORTS_DIR,
        "json": JSON_REPORTS_DIR,
        "powerbi": POWERBI_REPORTS_DIR,
    }
    target_dir = category_map.get(category.lower())
    if not target_dir or not target_dir.exists():
        return jsonify({"error": "Invalid category"}), 404
    return send_from_directory(target_dir, filename, as_attachment=True)


def run_web_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = False) -> None:
    """Launches the Flask development web server."""
    logger.info(f"Starting TradeGuard Web Dashboard at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_web_server()
