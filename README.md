# 🛡️ TradeGuard | Trade Reconciliation & Control Automation Engine

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Flask Web UI](https://img.shields.io/badge/Web%20UI-Flask%20%2B%20Chart.js-00f2fe.svg)](http://127.0.0.1:5000)
[![Power BI Ready](https://img.shields.io/badge/Analytics-Power%20BI-yellow.svg)](docs/powerbi_dashboard.md)
[![Tests Passing](https://img.shields.io/badge/tests-33%20passed-brightgreen.svg)]()
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **An enterprise-grade, high-performance financial software suite for investment banks and global trading desks.**
> Processes multi-asset Front Office vs. Back Office trade feeds, executes SQL-first automated break detection across 9 exception categories, generates multi-format executive audit reports, and serves an interactive web control dashboard.

---

## 📌 Executive Summary & Domain Context

In global investment banks and financial institutions, tens of thousands of trades execute daily across Equities, Fixed Income, Foreign Exchange (FX), Credit, and Derivatives. Discrepancies naturally occur between **Front Office execution feeds** (trading desk capture) and **Back Office settlement staging records** (operations & custody) due to timing latencies, price rounding errors, manual booking slips, or system mismatches.

Unreconciled trade breaks introduce severe operational risks:
- **PnL Leakage**: Unidentified price/quantity discrepancies impacting bank PnL.
- **Credit & Counterparty Risk**: Unmatched counterparty exposure during market volatility.
- **Regulatory Penalties**: Non-compliance with financial oversight mandates (SEC, FINRA, FCA, PRA).

**TradeGuard** provides a production-grade, modular solution designed according to **Clean Architecture** and **Product Control** best practices. It ingests trading feeds, persists records in SQLite, performs high-speed SQL-first reconciliation (`< 0.02s` execution time), exports multi-format reports (Excel, CSV, JSON), feeds Power BI analytics, and presents a real-time web dashboard.

---

## ⚡ Key Feature Highlights

### 🎯 1. SQL-First Reconciliation Engine
- **Field-Level Discrepancy Matching**: Compares Front Office and Back Office trades using ANSI SQL joins, Window functions, and CTEs.
- **9 Core Break Categories**:
  1. **Missing Trades** (`CRITICAL`): Trade in FO but missing in BO.
  2. **Unexpected Trades** (`CRITICAL`): Trade in BO but missing in FO.
  3. **Duplicate Trades** (`HIGH`): Multiple BO records matching a single FO Trade ID.
  4. **Price Mismatches** (`HIGH`): Price variance exceeding tolerance (e.g., `$0.01`).
  5. **Quantity Mismatches** (`HIGH`): Quantity differences between FO and BO.
  6. **Currency Mismatches** (`HIGH`): FX currency mismatches (e.g., USD vs. EUR).
  7. **Status Mismatches** (`MEDIUM`): Trade lifecycle status differences (`PENDING` vs. `SETTLED`).
  8. **Trade Date Mismatches** (`LOW`): Execution date discrepancies.
  9. **Settlement Date Mismatches** (`LOW`): Value date / settlement timing variance.
- **Severity Classification**: Automatically assigns risk levels (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) to every break record.
- **Historical Audit Tracking**: Tags every run and break with a unique `Run_ID` (e.g., `REC_20260805_225747_94a8ff`) to track historical resolution trends over time.

### 🌐 2. Interactive Web Control Dashboard
- **Modern Dark-Mode Web Interface**: Built with Flask, vanilla CSS glassmorphism (`backdrop-filter: blur(12px)`), electric cyan accents (`#00f2fe`), and Inter font.
- **Live Status & One-Click Workflows**: Trigger trade feed generation, SQL reconciliation runs, 30-day historical simulations, and Power BI exports directly from UI buttons.
- **Dynamic Visual Analytics**: Real-time line, doughnut, and bar charts powered by Chart.js for 30-day Match Rate trends, break severity distribution, exception categories, and desk risk exposure.
- **Granular Exception Explorer**: Client-side live search and multi-criteria filtering by Severity, Break Type, Desk, Counterparty, and Trader.
- **1-Click Download Center**: Direct browser downloads for generated Excel workbooks, CSV feeds, JSON audit files, and Power BI datasets.

### 📊 3. Executive Multi-Format Reporting Engine
- **OpenPyXL Excel Workbooks (`.xlsx`)**: 10 formatted worksheets including an **Executive KPI Summary Card** sheet and 9 exception category sheets. Styled with navy headers (`#1B365D`), freeze panes, zebra striping, auto-fit column widths, and conditional color fills.
- **Granular CSV Feeds (`.csv`)**: 8 independent CSV report files for downstream data pipelines.
- **JSON Audit Reports (`.json`)**: Machine-readable JSON summary and detailed break logs for automated compliance auditing.

### 📈 4. Power BI Analytics & Historical Simulator
- **9 Analytics-Ready CSV Feeds**: Exported directly into `reports/powerbi/` (`reconciliation_runs.csv`, `reconciliation_breaks.csv`, `trade_details.csv`, `desk_summary.csv`, `portfolio_summary.csv`, `counterparty_summary.csv`, `asset_class_summary.csv`, `severity_summary.csv`, `break_type_summary.csv`).
- **Star-Schema Data Model**: Fully documented data model, relationships, and 14 custom DAX measures in [`docs/powerbi_dashboard.md`](docs/powerbi_dashboard.md).
- **Historical Run Simulator**: Generates reproducible historical run data across 30 days to analyze reconciliation quality trends over time.

---

## 🏗 System Architecture & Data Flow

```
                      ┌──────────────────────────────────────────┐
                      │    TradeGuard Web Dashboard (Browser)    │
                      │         http://127.0.0.1:5000            │
                      └────────────────────┬─────────────────────┘
                                           │
                                           │  REST API (JSON)
                                           ▼
                      ┌──────────────────────────────────────────┐
                      │     CLI / Flask REST API Server          │
                      │         (main.py / app.py)               │
                      └────────────────────┬─────────────────────┘
                                           │
          ┌────────────────────────────────┼────────────────────────────────┐
          │                                │                                │
          ▼                                ▼                                ▼
┌──────────────────┐            ┌──────────────────┐            ┌───────────────────┐
│  DataGenerator   │            │ DatabaseManager  │            │  PowerBIExporter  │
│(data_generator.py│            │(database_manager)│            │(powerbi_exporter) │
└─────────┬────────┘            └──────────┬───────┘            └─────────┬─────────┘
          │                                │                              │
          ▼                                ▼                              ▼
┌──────────────────┐            ┌──────────────────┐            ┌───────────────────┐
│ Trade Feeds      │───────────>│ SQLite Database  │<───────────│ Power BI CSV Feeds│
│ (data/raw/*.csv) │            │ (schema.sql)     │            │(reports/powerbi/) │
└──────────────────┘            └──────────┬───────┘            └───────────────────┘
                                           │
                                           ▼
                                ┌─────────────────────┐
                                │ReconciliationEngine │
                                │(reconcil_engine.py) │
                                └──────────┬──────────┘
                                           │
                                           ▼
                                ┌─────────────────────┐
                                │  ReportGenerator    │
                                │(report_generator.py)│
                                └─────────────────────┘
```

---

## 📂 Project Directory Structure

```text
TradeGuard/
├── app.py                              # Flask REST API Web Server & Routes
├── config.py                           # Centralized System Configuration & Paths
├── main.py                             # Command Line Interface (CLI) Entrypoint
├── pyproject.toml                      # Build Specifications & Tooling Config
├── requirements.txt                    # Project Dependencies
├── README.md                           # Master Documentation & Setup Guide
├── LICENSE                             # MIT License
│
├── data/
│   ├── raw/                            # Front Office & Back Office trade CSV feeds
│   └── processed/                      # Staged data files
│
├── database/
│   ├── schema.sql                      # SQL DDL Schema (Tables, Indexes, Foreign Keys)
│   └── trade_reconciliation.db         # SQLite Persistence Database
│
├── docs/
│   ├── architecture.md                 # System Architecture & SOLID Patterns
│   ├── api.md                          # Python Module & API Reference
│   ├── workflow.md                     # Operational Workflow Guide
│   └── powerbi_dashboard.md            # Power BI Star-Schema & DAX Specification
│
├── reports/                            # Generated Output Artifacts
│   ├── excel/                          # OpenPyXL 10-Sheet Styled Workbooks (.xlsx)
│   ├── csv/                            # Granular Break Datasets (.csv)
│   ├── json/                           # Audit Logs (.json)
│   └── powerbi/                        # Analytics-Ready Feeds (.csv)
│
├── src/                                # Core Engine Source Code
│   ├── data_generator.py               # Trade Feed Engine & Break Generator
│   ├── database/
│   │   └── database_manager.py         # SQLite Connection & CRUD Manager
│   ├── models/
│   │   └── trade.py                    # Financial Trade Dataclass & Notional Math
│   ├── reconciliation/
│   │   └── reconciliation_engine.py    # SQL Matching & Exception Engine
│   ├── reporting/
│   │   ├── report_generator.py         # OpenPyXL Excel, CSV, JSON Generator
│   │   └── powerbi_exporter.py         # Power BI CSV Exporter
│   └── utils/
│       ├── helpers.py                  # Directory, File & Utility Helpers
│       ├── history_simulator.py        # 30-Day Historical Run Simulator
│       ├── logger.py                   # Rotating File & Colored Console Logger
│       └── validators.py               # Input Data Validation Suite
│
├── static/                             # Web Application Frontend Assets
│   ├── index.html                      # Glassmorphic Single-Page Web UI
│   ├── css/
│   │   └── styles.css                  # Modern Dark-Mode Design System
│   └── js/
│       └── app.js                      # REST API Client, Chart.js & UI Logic
│
└── tests/                              # Pytest / Unittest Automated Suite
    ├── test_database.py                # Database Manager Tests
    ├── test_trade.py                   # Domain Model Tests
    ├── test_reconciliation.py          # Reconciliation Engine Tests
    ├── test_reports.py                 # Report Generator Tests
    └── test_powerbi.py                 # Power BI Exporter Tests
```

---

## 🛠 Technology Stack

- **Core Language**: Python 3.12+
- **Database Engine**: SQLite 3 / ANSI SQL (CTEs, Window Functions, Indexes)
- **Web Backend Framework**: Flask (REST API)
- **Frontend Interface**: HTML5, Vanilla CSS3 (Glassmorphism, Dark Mode), JavaScript (ES6+)
- **Charting & Analytics**: Chart.js 4.4
- **Data Manipulation**: Pandas, NumPy
- **Excel Report Formatting**: OpenPyXL
- **Business Intelligence**: Power BI (Star-Schema, DAX Metrics)
- **Testing & Quality Assurance**: Python `unittest`, `py_compile`
- **CLI Framework**: Argparse

---

## 🚀 Getting Started & Installation

### Prerequisites
- **Python 3.12+** installed on your system.

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/TradeGuard.git
cd TradeGuard
```

### 2. Create & Activate Virtual Environment
```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 💻 CLI Command Reference

Execute the full pipeline or individual stages via `main.py`:

```bash
# 1. View all available CLI subcommands
python main.py help

# 2. Generate Front Office & Back Office trade feeds (1,000 trades, 4% break rate)
python main.py generate-data --count 1000 --seed 42

# 3. Load trade feeds into SQLite database
python main.py load-data

# 4. Run SQL Trade Reconciliation Engine
python main.py reconcile --threshold 0.01

# 5. Generate Excel, CSV, and JSON audit reports
python main.py report

# 6. Simulate 30 days of historical reconciliation runs
python main.py simulate-history --runs 30

# 7. Export Power BI analytics CSV datasets
python main.py powerbi-export

# 8. Launch the Interactive Web Control Dashboard
python main.py dashboard --port 5000
```

---

## 🌐 Web Dashboard Guide

Launch the web server:
```bash
python main.py dashboard
```
Open your browser and navigate to **`http://127.0.0.1:5000`**.

### Dashboard Views:
1. **Executive Overview**: Key performance indicators, 30-day match rate trend chart, break severity distribution doughnut, exception category breakdown, and desk risk exposure.
2. **Exception Explorer**: Complete filterable datatable of all reconciliation breaks with trade metadata, trader name, expected vs. actual values, and severity tags (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
3. **Trade Population**: Front Office trading feed viewer with calculated trade notionals ($).
4. **Control & Risk**: Product control risk summary table by Trading Desk, showing affected trade counts, total notionals, and exception rates (%).
5. **Reports Center**: One-click file download center for generated Excel workbooks, CSV feeds, JSON audit files, and Power BI datasets.

---

## 🧪 Testing & Verification

The project includes unit and integration tests covering data generation, schema creation, SQL matching rules, break persistence, Excel/CSV report rendering, and Power BI export validation.

Run the full test suite:
```bash
python -m unittest discover tests
```

**Test Output:**
```text
Ran 33 tests in 3.142s

OK
```

---

## 🛡 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

