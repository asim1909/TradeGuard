# API Documentation

## Trade Reconciliation & Control Automation Engine

---

## 1. `config.py` - Configuration Module

Centralizes application settings, file system paths, database locations, logging formats, and domain tolerance parameters.

### Key Constants:
- `PROJECT_ROOT`: Absolute `Path` to project root directory.
- `RAW_DATA_DIR`: Path to `data/raw/` directory.
- `DEFAULT_DB_PATH`: Path to `database/trade_reconciliation.db`.
- `RECONCILIATION_THRESHOLD`: Price tolerance difference threshold (`float = 0.01`).
- `SUPPORTED_CURRENCIES`: Supported ISO currency codes (`List[str]`).
- `SUPPORTED_STATUS_VALUES`: Valid reconciliation status codes (`List[str]`).

### Functions:
- `ensure_project_directories() -> None`: Ensures all required data, report, and log directories exist.

---

## 2. `src/models/trade.py` - Trade Domain Model

Encapsulates trade data attributes and notional calculations.

### `Trade` (Dataclass)
```python
class Trade:
    trade_id: str
    counterparty: str
    asset_class: str
    quantity: float
    price: float
    currency: str
    trade_date: str
    settlement_date: str
    trader_id_or_book: str = "DEFAULT_DESK"
    source_system: str = "FRONT_OFFICE"
    notional_amount: float
    status: str = "NEW"
```

#### Methods:
- `calculate_notional() -> float`: Calculates `round(quantity * price, 4)`.
- `to_dict() -> Dict[str, Any]`: Serializes Trade object into a Python dictionary.
- `@classmethod from_dict(data: Dict[str, Any]) -> Trade`: Instantiates a Trade object from dictionary payload.
- `validate() -> bool`: Evaluates internal data validity.

---

## 3. `src/database/database_manager.py` - Database Manager

Manages SQLite connection lifecycle, schema initialization, and SQL query execution.

### `DatabaseManager`
```python
class DatabaseManager:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH, schema_path: Path = SCHEMA_PATH) -> None: ...
```

#### Methods:
- `connect() -> sqlite3.Connection`: Establishes database connection.
- `disconnect() -> None`: Closes active database handle.
- `initialize_schema() -> bool`: Executes DDL commands from `database/schema.sql`.
- `load_csv_to_table(csv_path: Path, table_name: str) -> int`: Ingests CSV trade records into staging table.
- `fetch_front_office_trades() -> List[Dict[str, Any]]`: Queries staged front-office trade records.
- `fetch_back_office_trades() -> List[Dict[str, Any]]`: Queries staged back-office trade records.
- `save_reconciliation_breaks(breaks_data: List[Dict[str, Any]]) -> int`: Inserts break records into database.

---

## 4. `src/reconciliation/reconciliation_engine.py` - Reconciliation Engine

Executes trade matching algorithms and break classification.

### `ReconciliationEngine`
```python
class ReconciliationEngine:
    def __init__(self, threshold: float = RECONCILIATION_THRESHOLD) -> None: ...
```

#### Methods:
- `load_data(fo_trades: List[Dict[str, Any]], bo_trades: List[Dict[str, Any]]) -> None`: Loads datasets into engine memory.
- `execute_reconciliation() -> Dict[str, Any]`: Executes reconciliation algorithm between FO and BO trades.
- `identify_discrepancies() -> List[Dict[str, Any]]`: Categorizes identified trade breaks.
- `calculate_break_statistics() -> Dict[str, Any]`: Calculates summary break statistics and exposure at risk.

---

## 5. `src/reporting/report_generator.py` - Report Generator

Generates executive break reports in Excel, CSV, and JSON formats.

### `ReportGenerator`
```python
class ReportGenerator:
    def __init__(self, output_name: str = DEFAULT_REPORT_NAME, excel_dir: Path = EXCEL_REPORTS_DIR, csv_dir: Path = CSV_REPORTS_DIR, json_dir: Path = JSON_REPORTS_DIR) -> None: ...
```

#### Methods:
- `generate_excel_report(reconciliation_summary: Dict, breaks_data: List, output_path: Optional[Path] = None) -> Path`: Exports OpenPyXL Excel workbook.
- `generate_csv_report(breaks_data: List, output_path: Optional[Path] = None) -> Path`: Exports raw CSV break report.
- `generate_json_report(reconciliation_summary: Dict, breaks_data: List, output_path: Optional[Path] = None) -> Path`: Exports structured JSON audit breakdown.
- `generate_all_reports(reconciliation_summary: Dict, breaks_data: List) -> Dict[str, Path]`: Triggers multi-format export.

---

## 6. `src/visualization/charts.py` - Chart Generator

Renders Matplotlib charts for visual dashboards.

### `ChartGenerator`
```python
class ChartGenerator:
    def __init__(self, output_dir: Path = CHARTS_DIR, dpi: int = CHART_DPI) -> None: ...
```

#### Methods:
- `generate_break_by_asset_class_chart(breaks_data: List, filename: str = "breaks_by_asset_class.png") -> Path`: Generates asset class bar plot.
- `generate_break_by_type_chart(breaks_data: List, filename: str = "breaks_by_type.png") -> Path`: Generates break type pie plot.
- `generate_break_exposure_chart(breaks_data: List, filename: str = "break_financial_exposure.png") -> Path`: Generates financial exposure bar plot.
- `generate_all_charts(breaks_data: List) -> List[Path]`: Renders full chart suite.

---

## 7. `src/utils/` - Utilities Suite

### Exception Classes (`src/utils/exceptions.py`):
- `TradeEngineError(Exception)`: Base domain exception.
- `TradeValidationError`: Trade payload schema validation failures.
- `DatabaseConnectionError`: Database connection and SQL execution errors.
- `CSVFormatError`: CSV feed parsing and header validation errors.
- `ReportGenerationError`: Report export failures.
- `ConfigurationError`: Invalid path or parameter settings.
- `ReconciliationError`: Reconciliation processing exceptions.

### Logger (`src/utils/logger.py`):
- `setup_logger(name: str, log_file: Optional[Path], level: int) -> logging.Logger`: Configures stream & rotating file logger.
- `get_logger(name: str) -> logging.Logger`: Retrieves logger instance.

### Validators (`src/utils/validators.py`):
- `ValidationHelper`: Validation class exposing `validate_trade_dict`, `validate_csv_file`, `validate_db_path`, `validate_config`, and `validate_date_string`.

### Helpers (`src/utils/helpers.py`):
- `@time_it`: Function execution timing decorator.
- `format_date(dt: Optional[datetime], format_str: str) -> str`: Formats datetime instances.
- `ensure_directory_exists(path: Path) -> Path`: Guarantees directory path exists.
- `read_json_file(file_path: Path)` / `write_json_file(data: Any, file_path: Path)`: JSON file I/O helpers.
