# Power BI Trade Reconciliation & Control Dashboard Specification

This document provides complete instructions, data model architecture, and DAX measure specifications for manually building the **Power BI Trade Reconciliation & Control Dashboard** using the CSV datasets exported by the `TradeGuard` engine.

---

## 1. Data Source Files & Location

Import the 9 analytics-ready CSV files exported to `reports/powerbi/`:

1. `reconciliation_runs.csv` (Historical KPI run metrics)
2. `reconciliation_breaks.csv` (Enriched exception records with trade metadata)
3. `trade_details.csv` (Front Office trade population with calculated `Trade_Notional`)
4. `desk_summary.csv` (Desk-level aggregations)
5. `portfolio_summary.csv` (Portfolio-level aggregations)
6. `counterparty_summary.csv` (Counterparty-level aggregations)
7. `asset_class_summary.csv` (Asset Class-level aggregations)
8. `severity_summary.csv` (Severity distribution)
9. `break_type_summary.csv` (Break Type distribution)

---

## 2. Power BI Data Model Architecture (Star Schema)

Configure relationships in Power BI Desktop under the **Model View**:

### Core Analytical Model

```
                    ┌─────────────────────────┐
                    │   reconciliation_runs   │
                    └────────────┬────────────┘
                                 │ 1
                                 │
                                 │ *
                    ┌────────────┴────────────┐
                    │  reconciliation_breaks  │
                    └────────────┬────────────┘
                                 │ *
                                 │
                                 │ 1
                    ┌────────────┴────────────┐
                    │      trade_details      │
                    └─────────────────────────┘
```

### Relationship Definitions

| Primary Table | Key Column | Foreign Table | Key Column | Cardinality | Filter Direction |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `reconciliation_runs` | `Run_ID` | `reconciliation_breaks` | `Run_ID` | 1-to-Many (`1:*`) | Single (`reconciliation_runs` filters `reconciliation_breaks`) |
| `trade_details` | `Trade_ID` | `reconciliation_breaks` | `Trade_ID` | 1-to-Many (`1:*`) | Single (`trade_details` filters `reconciliation_breaks`) |
| `desk_summary` | `Desk` | `trade_details` | `Desk` | 1-to-Many (`1:*`) | Single |
| `portfolio_summary` | `Portfolio` | `trade_details` | `Portfolio` | 1-to-Many (`1:*`) | Single |
| `counterparty_summary` | `Counterparty` | `trade_details` | `Counterparty` | 1-to-Many (`1:*`) | Single |
| `asset_class_summary` | `Asset_Class` | `trade_details` | `Asset_Class` | 1-to-Many (`1:*`) | Single |

---

## 3. DAX Measures Repository

Create a dedicated DAX measure table named `_Measures`:

```dax
// 1. Total Trades
Total Trades = SUM(reconciliation_runs[Front_Count])

// 2. Matched Trades
Matched Trades = SUM(reconciliation_runs[Matched_Count])

// 3. Total Breaks
Total Breaks = COUNT(reconciliation_breaks[Run_ID])

// 4. Affected Trades Count (Distinct Trades with Breaks)
Affected Trades = DISTINCTCOUNT(reconciliation_breaks[Trade_ID])

// 5. Match Rate (%)
Match Rate = 
DIVIDE(
    [Matched Trades],
    [Total Trades],
    0
) * 100

// 6. Exception Rate (%)
Exception Rate = 
DIVIDE(
    [Affected Trades],
    [Total Trades],
    0
) * 100

// 7. Critical Breaks Count
Critical Breaks = 
CALCULATE(
    COUNT(reconciliation_breaks[Run_ID]),
    reconciliation_breaks[Severity] = "CRITICAL"
)

// 8. High Breaks Count
High Breaks = 
CALCULATE(
    COUNT(reconciliation_breaks[Run_ID]),
    reconciliation_breaks[Severity] = "HIGH"
)

// 9. Medium Breaks Count
Medium Breaks = 
CALCULATE(
    COUNT(reconciliation_breaks[Run_ID]),
    reconciliation_breaks[Severity] = "MEDIUM"
)

// 10. Low Breaks Count
Low Breaks = 
CALCULATE(
    COUNT(reconciliation_breaks[Run_ID]),
    reconciliation_breaks[Severity] = "LOW"
)

// 11. Total Trade Notional ($)
Total Notional = SUM(trade_details[Trade_Notional])

// 12. Average Processing Time (seconds)
Average Processing Time = AVERAGE(reconciliation_runs[Execution_Time])

// 13. Previous Run Match Rate
Previous Run Match Rate = 
CALCULATE(
    [Match Rate],
    OFFSET(
        -1,
        ORDERBY(reconciliation_runs[Created_At], ASC)
    )
)

// 14. Match Rate Change
Match Rate Change = [Match Rate] - [Previous Run Match Rate]
```

---

## 4. Dashboard Pages Structure & Visual Layout

### Page 1: Executive Overview

- **KPI Cards Top Banner**:
  - Total Trades (`[Total Trades]`)
  - Matched Trades (`[Matched Trades]`)
  - Match % (`[Match Rate]` formatted as `92.70%`)
  - Total Breaks (`[Total Breaks]`)
  - Critical Breaks (`[Critical Breaks]` highlighted in Red)
  - Processing Time (`[Average Processing Time]` in seconds)

- **Visuals**:
  - **Match % Trend** (Line Chart: X = `Created_At`, Y = `[Match Rate]`)
  - **Break Severity Distribution** (Donut Chart: Legend = `Severity`, Values = `[Total Breaks]`)
  - **Break Type Distribution** (Bar Chart: Y = `Break_Type`, X = `Break_Count`)
  - **Reconciliation Volume Trend** (Stacked Column Chart: X = `Created_At`, Y = `Matched_Count` vs `Total_Breaks`)

---

### Page 2: Exception Analysis

- **Top Global Slicers**:
  - `Run Date` / `Created_At` (Date Slider)
  - `Desk` (Dropdown)
  - `Portfolio` (Dropdown)
  - `Counterparty` (Dropdown)
  - `Asset Class` (Dropdown)
  - `Severity` (Multi-select)
  - `Break Type` (Multi-select)

- **Visuals**:
  - **Breaks by Type** (Horizontal Bar Chart)
  - **Breaks by Severity** (Pie Chart: Red/Orange/Yellow/Green color palette)
  - **Breaks by Desk** (Clustered Bar Chart)
  - **Breaks by Counterparty** (Top 10 Horizontal Bar Chart)
  - **Breaks by Asset Class** (Tree Map)
  - **Detailed Exception Data Table**:
    - Columns: `Run_ID`, `Trade_ID`, `Break_Type`, `Severity`, `Expected_Value`, `Actual_Value`, `Desk`, `Counterparty`, `Asset_Class`, `Detected_At`

---

### Page 3: Control & Risk Monitoring

- **Visuals**:
  - **Critical Issues by Desk** (Bar Chart filtered to `Severity = 'CRITICAL'`)
  - **Exception Rate by Desk** (Column Chart: X = `Desk`, Y = `Exception_Rate`)
  - **Exception Rate by Counterparty** (Bar Chart: X = `Counterparty`, Y = `Exception_Rate`)
  - **Exception Rate by Portfolio** (Column Chart: X = `Portfolio`, Y = `Exception_Rate`)
  - **Critical Break Trend** (Area Chart: X = `Created_At`, Y = `[Critical Breaks]`)
  - **Top 10 Entities by Exception Count** (Table: Entity, Total Trades, Total Breaks, Critical Breaks, Exception Rate %)

---

### Page 4: Historical Performance

- **Visuals**:
  - **Match % Over Time** (Line Chart with target benchmark line at 95%)
  - **Total Breaks Over Time** (Column Chart)
  - **Critical Breaks Over Time** (Line Chart in Red)
  - **Processing Time Over Time** (Line Chart in Blue)
  - **Trade Volume Over Time** (Area Chart: FO vs BO counts)
