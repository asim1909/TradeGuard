-- =============================================================================
-- Trade Reconciliation & Control Automation Engine
-- Database DDL Schema (SQLite Compatible)
-- =============================================================================

-- 1. Front Office Trades Table (Trading Desk Capture Feed)
CREATE TABLE IF NOT EXISTS front_office_trades (
    Trade_ID TEXT PRIMARY KEY,
    Trade_Date TEXT NOT NULL,
    Settlement_Date TEXT NOT NULL,
    Trader TEXT NOT NULL,
    Desk TEXT NOT NULL,
    Portfolio TEXT NOT NULL,
    Counterparty TEXT NOT NULL,
    Asset_Class TEXT NOT NULL,
    Symbol TEXT NOT NULL,
    Buy_Sell TEXT NOT NULL,
    Quantity INTEGER NOT NULL,
    Price REAL NOT NULL,
    Currency TEXT NOT NULL,
    Trade_Status TEXT NOT NULL,
    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Back Office Trades Table (Settlements / Operations Feed)
-- Trade_ID is NOT UNIQUE to allow duplicate trades injected into Back Office.
CREATE TABLE IF NOT EXISTS back_office_trades (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Trade_ID TEXT NOT NULL,
    Trade_Date TEXT NOT NULL,
    Settlement_Date TEXT NOT NULL,
    Trader TEXT NOT NULL,
    Desk TEXT NOT NULL,
    Portfolio TEXT NOT NULL,
    Counterparty TEXT NOT NULL,
    Asset_Class TEXT NOT NULL,
    Symbol TEXT NOT NULL,
    Buy_Sell TEXT NOT NULL,
    Quantity INTEGER NOT NULL,
    Price REAL NOT NULL,
    Currency TEXT NOT NULL,
    Trade_Status TEXT NOT NULL,
    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Reconciliation Breaks Table (Auditing & Exception Tracking)
CREATE TABLE IF NOT EXISTS reconciliation_breaks (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Run_ID TEXT NOT NULL,
    Trade_ID TEXT NOT NULL,
    Break_Type TEXT NOT NULL,
    Expected_Value TEXT,
    Actual_Value TEXT,
    Severity TEXT DEFAULT 'MEDIUM',
    Detected_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Run_ID) REFERENCES reconciliation_summary(Run_ID)
);

-- 4. Reconciliation Summary Table (Execution Run Metrics & Control Audit)
CREATE TABLE IF NOT EXISTS reconciliation_summary (
    Run_ID TEXT PRIMARY KEY,
    Execution_Time REAL NOT NULL,
    Front_Count INTEGER NOT NULL,
    Back_Count INTEGER NOT NULL,
    Matched_Count INTEGER NOT NULL,
    Missing_Count INTEGER NOT NULL,
    Unexpected_Count INTEGER NOT NULL,
    Price_Mismatch_Count INTEGER NOT NULL,
    Quantity_Mismatch_Count INTEGER NOT NULL,
    Status_Mismatch_Count INTEGER NOT NULL,
    Trade_Date_Mismatch_Count INTEGER NOT NULL,
    Settlement_Date_Mismatch_Count INTEGER NOT NULL,
    Currency_Mismatch_Count INTEGER NOT NULL,
    Duplicate_Count INTEGER NOT NULL,
    Critical_Breaks INTEGER NOT NULL,
    High_Breaks INTEGER NOT NULL,
    Medium_Breaks INTEGER NOT NULL,
    Low_Breaks INTEGER NOT NULL,
    Match_Percentage REAL NOT NULL,
    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Front Office Trades
CREATE INDEX IF NOT EXISTS idx_fo_trade_id ON front_office_trades(Trade_ID);
CREATE INDEX IF NOT EXISTS idx_fo_trade_date ON front_office_trades(Trade_Date);
CREATE INDEX IF NOT EXISTS idx_fo_desk ON front_office_trades(Desk);
CREATE INDEX IF NOT EXISTS idx_fo_portfolio ON front_office_trades(Portfolio);
CREATE INDEX IF NOT EXISTS idx_fo_symbol ON front_office_trades(Symbol);
CREATE INDEX IF NOT EXISTS idx_fo_currency ON front_office_trades(Currency);
CREATE INDEX IF NOT EXISTS idx_fo_status ON front_office_trades(Trade_Status);

-- Indexes for Back Office Trades
CREATE INDEX IF NOT EXISTS idx_bo_trade_id ON back_office_trades(Trade_ID);
CREATE INDEX IF NOT EXISTS idx_bo_trade_date ON back_office_trades(Trade_Date);
CREATE INDEX IF NOT EXISTS idx_bo_desk ON back_office_trades(Desk);
CREATE INDEX IF NOT EXISTS idx_bo_portfolio ON back_office_trades(Portfolio);
CREATE INDEX IF NOT EXISTS idx_bo_symbol ON back_office_trades(Symbol);
CREATE INDEX IF NOT EXISTS idx_bo_currency ON back_office_trades(Currency);
CREATE INDEX IF NOT EXISTS idx_bo_status ON back_office_trades(Trade_Status);
