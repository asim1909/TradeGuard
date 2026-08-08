# Operational Workflow & Data Lifecycle Guide

## Trade Reconciliation & Control Automation Engine

---

## 1. End-to-End Operational Lifecycle

The operational lifecycle simulates a real-world investment banking middle-office trade control cycle across 5 distinct phases:

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ 1. Data Ingestion│ ────> │ 2. Database     │ ────> │ 3. Reconciliation│
│   (Raw Feeds)   │       │    Staging      │       │    Engine       │
└─────────────────┘       └─────────────────┘       └────────┬────────┘
                                                             │
                                                             ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ 5. Audit &      │ <──── │ 4. Multi-Format │ <───────┘                 │
│    Archival     │       │    Reporting    │                         │
└─────────────────┘       └─────────────────┘                         │
```

---

## 2. Detailed Phase Breakdown

### Phase 1: Trade Feed Generation & Ingestion
- **Input**: Raw Front Office trading desk feeds (`data/raw/front_office_trades.csv`) and Back Office settlement feeds (`data/raw/back_office_trades.csv`).
- **Processing**:
  - `DataGenerator` generates synthetic datasets with realistic field distributions.
  - `ValidationHelper.validate_csv_file()` verifies file existence, non-zero file sizes, and expected header columns.
- **Output**: Verified CSV trade feed files.

### Phase 2: Database Staging & Normalization
- **Processing**:
  - `DatabaseManager.connect()` opens a connection to `database/trade_reconciliation.db`.
  - `DatabaseManager.initialize_schema()` executes `database/schema.sql` to create `front_office_trades` and `back_office_trades` tables.
  - Raw CSV records are parsed into `Trade` model instances and batch-inserted into staging tables.
- **Output**: Relational staging tables containing normalized trade records.

### Phase 3: Trade Reconciliation Engine Execution
- **Processing**:
  - `ReconciliationEngine.load_data()` fetches staged trade records.
  - `ReconciliationEngine.execute_reconciliation()` performs trade matching:
    1. **Exact Key Matching**: Align FO and BO records on `trade_id`.
    2. **Price Tolerance Check**: Calculate `abs(fo_price - bo_price)`. If `> RECONCILIATION_THRESHOLD` (e.g. 0.01), flag as `PRICE_MISMATCH`.
    3. **Quantity Matching**: Check unit volume alignment. Flag mismatches as `QTY_MISMATCH`.
    4. **Unmatched Record Detection**: Flag trades present only in FO as `MISSING_IN_BO` and trades present only in BO as `MISSING_IN_FO`.
- **Output**: Structured break records and reconciliation summary metrics.

### Phase 4: Multi-Format Executive Reporting & Visualization
- **Processing**:
  - `ReportGenerator` exports break datasets to:
    - **Excel (`reports/excel/`)**: Formatted multi-tab workbook with summary KPIs, styled headers, and conditional formatting.
    - **CSV (`reports/csv/`)**: Raw break table for downstream ingestion.
    - **JSON (`reports/json/`)**: Structured audit breakdown payload.
  - `ChartGenerator` renders visual analytics charts to `reports/charts/`:
    - `breaks_by_asset_class.png`: Bar chart of breaks per asset class.
    - `breaks_by_type.png`: Pie chart of break types.
    - `break_financial_exposure.png`: Exposure at risk per counterparty.
- **Output**: Exported report workbooks and visualization images.

### Phase 5: Exception Management & Audit Archival
- **Processing**:
  - Break records are persisted to the `reconciliation_breaks` table in SQLite with severity levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
  - Execution summary is recorded in `reconciliation_summary` table.
  - Rotating log files (`logs/trade_reconciliation.log`) preserve execution timestamps and audit records.
