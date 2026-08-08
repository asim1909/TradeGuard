# Architecture Specification

## Trade Reconciliation & Control Automation Engine

---

## 1. Executive Summary & Design Goals

The **Trade Reconciliation & Control Automation Engine** is architected to process, validate, reconcile, and audit financial trade datasets originating from heterogeneous trade execution systems (Front Office) and operational accounting/settlement systems (Back Office).

### Primary Architectural Pillars:
- **Clean Architecture & Separation of Concerns**: Complete isolation between domain models, database persistence, core reconciliation algorithms, presentation/reporting, and cross-cutting utilities.
- **Extensibility**: Modular design allowing future upgrades to enterprise databases (e.g., PostgreSQL, Snowflake), messaging queues (Kafka/RabbitMQ), and REST APIs without rewriting domain logic.
- **Operational Auditability**: Every execution run produces structured audit logs, database snapshots, and immutable report artifacts.
- **Fail-Safe Robustness**: Strict exception handling preventing silent data corruption or swallowed execution failures.

---

## 2. Layered Architectural Decomposition

```
+-----------------------------------------------------------------------+
|                         CLI / Orchestration Layer                     |
|                                (main.py)                              |
+-----------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
|                         Presentation & Reporting                      |
|            (src/reporting/report_generator.py, src/visualization)     |
+-----------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
|                         Core Reconciliation Engine                    |
|                   (src/reconciliation/reconciliation_engine.py)       |
+-----------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
|                           Domain & Data Models                        |
|                     (src/models/trade.py, src/utils)                  |
+-----------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
|                         Data Access & Staging Layer                   |
|                  (src/database/database_manager.py, SQLite)           |
+-----------------------------------------------------------------------+
```

### Module Responsibilities:

1. **CLI / Orchestration (`main.py`)**:
   - Parses CLI flags via `argparse`.
   - Bootstraps application logger and checks folder prerequisites.
   - Routes command execution to target workflow controllers.

2. **Domain Models (`src/models/trade.py`)**:
   - Encapsulates trade entities (`Trade` dataclass) with strict type hints.
   - Implements attribute normalization, dictionary serialization, and notional exposure calculation (`price * quantity`).

3. **Data Access Layer (`src/database/database_manager.py`)**:
   - Manages SQLite connection lifecycle (`connect`, `disconnect`).
   - Executes table creation DDL (`database/schema.sql`).
   - Handles batch CSV staging and parameterized SQL queries.

4. **Reconciliation Engine (`src/reconciliation/reconciliation_engine.py`)**:
   - Performs dataset alignment and key-based trade pairing (`trade_id`).
   - Evaluates tolerance thresholds on prices and quantities.
   - Categorizes trade exceptions (`PRICE_MISMATCH`, `QTY_MISMATCH`, `MISSING_IN_BO`).

5. **Reporting & Visualization Layer (`src/reporting/`, `src/visualization/`)**:
   - Formats reconciliation break tables into OpenPyXL Excel workbooks with custom styles.
   - Generates raw CSV datasets and JSON audit payloads.
   - Renders Matplotlib charts (bar charts, pie charts, exposure at risk).

6. **Cross-Cutting Utilities (`src/utils/`)**:
   - `logger.py`: Centralized rotating file and colored console logger.
   - `exceptions.py`: Custom domain exception hierarchy.
   - `validators.py`: Structural CSV, schema, date, and config validators.
   - `helpers.py`: Execution timing decorator (`@time_it`), date formatters, and file helpers.

---

## 3. SOLID Principles Application

| Principle | Application in Architecture |
| :--- | :--- |
| **Single Responsibility (SRP)** | `Trade` models data; `DatabaseManager` handles SQL; `ReconciliationEngine` matches trades; `ReportGenerator` creates workbooks. |
| **Open/Closed (OCP)** | New reporting formats (e.g. PDF/HTML) can be added by extending `ReportGenerator` without modifying reconciliation logic. |
| **Liskov Substitution (LSP)** | Exception hierarchy (`TradeEngineError`) allows catching specific or base errors cleanly without breaking call sites. |
| **Interface Segregation (ISP)** | Modules expose focused, explicit methods (e.g. `generate_excel_report`, `fetch_front_office_trades`). |
| **Dependency Inversion (DIP)** | High-level engine accepts generic trade record lists, remaining decoupled from underlying CSV/SQL source implementations. |

---

## 4. Enterprise Scalability Roadmap

The Phase 1 foundation prepares the architecture for future enterprise scaling:

1. **Database Migration**:
   - Abstract database operations so SQLite can be swapped for **PostgreSQL**, **Snowflake**, or **AWS Redshift** by updating `DatabaseManager`.
2. **REST API Integration**:
   - Wrap `ReconciliationEngine` and `ReportGenerator` inside **FastAPI** or **Flask** endpoints for web portal integration.
3. **Containerization & Cloud**:
   - Package application using **Docker** and schedule automated daily runs via **Apache Airflow** or **AWS Lambda**.
4. **CI/CD & Automated Testing**:
   - Integrate **GitHub Actions** for linting (`ruff`), formatting (`black`), type checking (`mypy`), and test coverage (`pytest-cov`).
