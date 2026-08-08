"""
Synthetic Financial Trade Data Generator for Trade Reconciliation & Control Automation Engine.

Generates realistic Front Office (Trading Desk) and Back Office (Operations) trade datasets,
intentionally injecting operational reconciliation breaks (missing trades, price mismatches,
quantity mismatches, date mismatches, currency mismatches, status mismatches, and duplicates).
"""

from datetime import datetime, timedelta
from pathlib import Path
import random
import time
from typing import Any, Dict, List, Tuple

import pandas as pd

from config import (
    ASSET_CLASSES,
    BACK_OFFICE_CSV_PATH,
    BUY_SELL_SIDES,
    COUNTERPARTIES,
    CURRENCIES,
    DEFAULT_BREAK_RATE,
    DEFAULT_NUM_TRADES,
    DEFAULT_RANDOM_SEED,
    DESKS,
    FRONT_OFFICE_CSV_PATH,
    PORTFOLIOS,
    RAW_DATA_DIR,
    SYMBOLS,
    TRADE_STATUSES,
    TRADERS,
)
from src.utils.exceptions import CSVFormatError, ConfigurationError, TradeEngineError
from src.utils.logger import get_logger

logger = get_logger("DataGenerator")


class DataGenerator:
    """
    Simulates investment bank front-office and back-office trade message streams with injected breaks.

    Attributes:
        num_trades: Number of Front Office trade records to generate.
        random_seed: Seed for reproducible random numbers.
        break_rate: Ratio of break injection.
        raw_dir: Destination folder for output CSVs.
        breaks_df: Internal pandas DataFrame tracking all injected breaks.
    """

    def __init__(
        self,
        num_trades: int = DEFAULT_NUM_TRADES,
        random_seed: int = DEFAULT_RANDOM_SEED,
        break_rate: float = DEFAULT_BREAK_RATE,
        raw_dir: Path = RAW_DATA_DIR,
    ) -> None:
        """Initializes DataGenerator with parameters and seed."""
        if num_trades <= 0:
            raise ConfigurationError(f"num_trades must be > 0, got: {num_trades}")

        self.num_trades = num_trades
        self.random_seed = random_seed
        self.break_rate = break_rate
        self.raw_dir = Path(raw_dir) if isinstance(raw_dir, str) else raw_dir

        # Initialize seed for reproducibility
        random.seed(self.random_seed)

        self.break_records: List[Dict[str, Any]] = []
        self.breaks_df: pd.DataFrame = pd.DataFrame(
            columns=["Trade_ID", "Break_Type", "Expected_Value", "Actual_Value", "Severity"]
        )
        self.metrics: Dict[str, int] = {}
        logger.info(
            f"Initialized DataGenerator [Trades={self.num_trades}, Seed={self.random_seed}, BreakRate={self.break_rate}]"
        )

    def generate_front_office_data(self) -> pd.DataFrame:
        """Generates clean Front Office trade executions dataset."""
        logger.info(f"Generating {self.num_trades} Front Office trade records...")
        base_date = datetime.now() - timedelta(days=10)
        trades: List[Dict[str, Any]] = []

        for i in range(1, self.num_trades + 1):
            trade_id = f"TRD_{100000 + i}"
            trade_dt = base_date + timedelta(days=random.randint(0, 5), hours=random.randint(0, 8))
            settle_dt = trade_dt + timedelta(days=random.randint(1, 3))
            
            qty = random.randint(1, 500) * 10
            price = round(random.uniform(15.0, 850.0), 2)

            trade = {
                "Trade_ID": trade_id,
                "Trade_Date": trade_dt.strftime("%Y-%m-%d"),
                "Settlement_Date": settle_dt.strftime("%Y-%m-%d"),
                "Trader": random.choice(TRADERS),
                "Desk": random.choice(DESKS),
                "Portfolio": random.choice(PORTFOLIOS),
                "Counterparty": random.choice(COUNTERPARTIES),
                "Asset_Class": random.choice(ASSET_CLASSES),
                "Symbol": random.choice(SYMBOLS),
                "Buy_Sell": random.choice(BUY_SELL_SIDES),
                "Quantity": qty,
                "Price": price,
                "Currency": random.choice(CURRENCIES),
                "Trade_Status": random.choice(TRADE_STATUSES),
            }
            trades.append(trade)

        df = pd.DataFrame(trades)
        self._validate_dataset(df, "Front Office")
        logger.info(f"Successfully generated Front Office dataset with {len(df)} rows.")
        return df

    def generate_back_office_data(self, fo_df: pd.DataFrame) -> pd.DataFrame:
        """Clones FO dataset and injects controlled reconciliation breaks."""
        logger.info("Generating Back Office trade feed with injected breaks...")
        bo_df = fo_df.copy()
        self.break_records.clear()

        # Fixed count allocations to match exact target ratios
        missing_cnt = max(1, int(self.num_trades * 0.018))      # ~18
        unexpected_cnt = max(1, int(self.num_trades * 0.012))   # ~12
        price_cnt = max(1, int(self.num_trades * 0.016))        # ~16
        qty_cnt = max(1, int(self.num_trades * 0.010))          # ~10
        status_cnt = max(1, int(self.num_trades * 0.009))       # ~9
        tdate_cnt = max(1, int(self.num_trades * 0.007))        # ~7
        sdate_cnt = max(1, int(self.num_trades * 0.005))        # ~5
        curr_cnt = max(1, int(self.num_trades * 0.008))         # ~8
        dup_cnt = max(1, int(self.num_trades * 0.004))          # ~4

        # Sequential break injections
        bo_df = self.inject_missing_trades(bo_df, missing_cnt)
        bo_df = self.inject_unexpected_trades(bo_df, unexpected_cnt)
        bo_df = self.inject_price_mismatches(bo_df, price_cnt)
        bo_df = self.inject_quantity_mismatches(bo_df, qty_cnt)
        bo_df = self.inject_status_mismatches(bo_df, status_cnt)
        bo_df = self.inject_trade_date_mismatches(bo_df, tdate_cnt)
        bo_df = self.inject_settlement_date_mismatches(bo_df, sdate_cnt)
        bo_df = self.inject_currency_mismatches(bo_df, curr_cnt)
        bo_df = self.inject_duplicate_trades(bo_df, dup_cnt)

        # Store break records internally in DataFrame
        self.breaks_df = pd.DataFrame(self.break_records)
        self._validate_dataset(bo_df, "Back Office", check_unique_id=False)

        # Save metrics count
        self.metrics = {
            "Front Office Trades": len(fo_df),
            "Back Office Trades": len(bo_df),
            "Missing Trades": missing_cnt,
            "Unexpected Trades": unexpected_cnt,
            "Price Mismatches": price_cnt,
            "Quantity Mismatches": qty_cnt,
            "Status Mismatches": status_cnt,
            "Trade Date Mismatches": tdate_cnt,
            "Settlement Date Mismatches": sdate_cnt,
            "Currency Mismatches": curr_cnt,
            "Duplicate Trades": dup_cnt,
        }
        logger.info(f"Back Office generation complete. Total BO rows: {len(bo_df)}.")
        return bo_df

    def inject_missing_trades(self, df: pd.DataFrame, count: int) -> pd.DataFrame:
        """Removes specified count of trades from Back Office."""
        drop_indices = random.sample(list(df.index), min(count, len(df)))
        for idx in drop_indices:
            trade_id = df.loc[idx, "Trade_ID"]
            self._record_break(trade_id, "Missing Trades", "Present in BO", "Missing in BO", "CRITICAL")
        df = df.drop(index=drop_indices).reset_index(drop=True)
        return df

    def inject_unexpected_trades(self, df: pd.DataFrame, count: int) -> pd.DataFrame:
        """Adds new trades existing only in Back Office."""
        base_date = datetime.now() - timedelta(days=5)
        new_rows = []
        for i in range(1, count + 1):
            trade_id = f"TRD_BO_UNX_{i:04d}"
            trade_dt = base_date + timedelta(days=random.randint(0, 3))
            row = {
                "Trade_ID": trade_id,
                "Trade_Date": trade_dt.strftime("%Y-%m-%d"),
                "Settlement_Date": (trade_dt + timedelta(days=2)).strftime("%Y-%m-%d"),
                "Trader": random.choice(TRADERS),
                "Desk": random.choice(DESKS),
                "Portfolio": random.choice(PORTFOLIOS),
                "Counterparty": random.choice(COUNTERPARTIES),
                "Asset_Class": random.choice(ASSET_CLASSES),
                "Symbol": random.choice(SYMBOLS),
                "Buy_Sell": random.choice(BUY_SELL_SIDES),
                "Quantity": random.randint(5, 100) * 10,
                "Price": round(random.uniform(50.0, 300.0), 2),
                "Currency": random.choice(CURRENCIES),
                "Trade_Status": "BOOKED",
            }
            new_rows.append(row)
            self._record_break(trade_id, "Unexpected Trades", "Absent in BO", "Present in BO", "HIGH")
        return pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

    def inject_price_mismatches(self, df: pd.DataFrame, count: int) -> pd.DataFrame:
        """Modifies trade prices beyond reconciliation tolerance."""
        indices = random.sample(list(df.index), min(count, len(df)))
        for idx in indices:
            old_val = df.loc[idx, "Price"]
            new_val = round(old_val * random.choice([1.08, 0.92, 1.15]), 2)
            trade_id = df.loc[idx, "Trade_ID"]
            df.loc[idx, "Price"] = new_val
            self._record_break(trade_id, "Price Mismatch", f"{old_val}", f"{new_val}", "HIGH")
        return df

    def inject_quantity_mismatches(self, df: pd.DataFrame, count: int) -> pd.DataFrame:
        """Modifies trade quantities."""
        indices = random.sample(list(df.index), min(count, len(df)))
        for idx in indices:
            old_val = df.loc[idx, "Quantity"]
            new_val = old_val + random.choice([100, -50, 500])
            trade_id = df.loc[idx, "Trade_ID"]
            df.loc[idx, "Quantity"] = max(10, new_val)
            self._record_break(trade_id, "Quantity Mismatch", f"{old_val}", f"{df.loc[idx, 'Quantity']}", "MEDIUM")
        return df

    def inject_status_mismatches(self, df: pd.DataFrame, count: int) -> pd.DataFrame:
        """Modifies trade statuses."""
        indices = random.sample(list(df.index), min(count, len(df)))
        for idx in indices:
            old_val = df.loc[idx, "Trade_Status"]
            choices = [s for s in TRADE_STATUSES if s != old_val]
            new_val = random.choice(choices)
            trade_id = df.loc[idx, "Trade_ID"]
            df.loc[idx, "Trade_Status"] = new_val
            self._record_break(trade_id, "Status Mismatch", f"{old_val}", f"{new_val}", "LOW")
        return df

    def inject_trade_date_mismatches(self, df: pd.DataFrame, count: int) -> pd.DataFrame:
        """Modifies trade dates."""
        indices = random.sample(list(df.index), min(count, len(df)))
        for idx in indices:
            old_val = df.loc[idx, "Trade_Date"]
            dt = datetime.strptime(old_val, "%Y-%m-%d") - timedelta(days=random.randint(1, 3))
            new_val = dt.strftime("%Y-%m-%d")
            trade_id = df.loc[idx, "Trade_ID"]
            df.loc[idx, "Trade_Date"] = new_val
            self._record_break(trade_id, "Trade Date Mismatch", f"{old_val}", f"{new_val}", "MEDIUM")
        return df

    def inject_settlement_date_mismatches(self, df: pd.DataFrame, count: int) -> pd.DataFrame:
        """Modifies settlement dates."""
        indices = random.sample(list(df.index), min(count, len(df)))
        for idx in indices:
            old_val = df.loc[idx, "Settlement_Date"]
            dt = datetime.strptime(old_val, "%Y-%m-%d") + timedelta(days=random.randint(2, 5))
            new_val = dt.strftime("%Y-%m-%d")
            trade_id = df.loc[idx, "Trade_ID"]
            df.loc[idx, "Settlement_Date"] = new_val
            self._record_break(trade_id, "Settlement Date Mismatch", f"{old_val}", f"{new_val}", "LOW")
        return df

    def inject_currency_mismatches(self, df: pd.DataFrame, count: int) -> pd.DataFrame:
        """Modifies trade currencies."""
        indices = random.sample(list(df.index), min(count, len(df)))
        for idx in indices:
            old_val = df.loc[idx, "Currency"]
            choices = [c for c in CURRENCIES if c != old_val]
            new_val = random.choice(choices)
            trade_id = df.loc[idx, "Trade_ID"]
            df.loc[idx, "Currency"] = new_val
            self._record_break(trade_id, "Currency Mismatch", f"{old_val}", f"{new_val}", "HIGH")
        return df

    def inject_duplicate_trades(self, df: pd.DataFrame, count: int) -> pd.DataFrame:
        """Duplicates existing trades in Back Office."""
        indices = random.sample(list(df.index), min(count, len(df)))
        dup_rows = []
        for idx in indices:
            row = df.loc[idx].to_dict()
            dup_rows.append(row)
            self._record_break(row["Trade_ID"], "Duplicate Trades", "Single Trade", "Duplicate Entry in BO", "HIGH")
        return pd.concat([df, pd.DataFrame(dup_rows)], ignore_index=True)

    def save_to_csv(
        self,
        fo_df: pd.DataFrame,
        bo_df: pd.DataFrame,
        fo_path: Any = None,
        bo_path: Any = None,
    ) -> Tuple[Path, Path]:
        """Saves FO and BO DataFrames into CSV files safely."""
        fo_target = Path(fo_path) if fo_path else (self.raw_dir / "front_office.csv")
        bo_target = Path(bo_path) if bo_path else (self.raw_dir / "back_office.csv")

        try:
            fo_target.parent.mkdir(parents=True, exist_ok=True)
            bo_target.parent.mkdir(parents=True, exist_ok=True)

            fo_df.to_csv(fo_target, index=False, encoding="utf-8")
            bo_df.to_csv(bo_target, index=False, encoding="utf-8")

            logger.info(f"Successfully saved FO CSV -> {fo_target} and BO CSV -> {bo_target}")
            return fo_target, bo_target
        except (PermissionError, OSError) as e:
            logger.error(f"Failed to write CSV datasets: {e}")
            raise CSVFormatError(message="Failed writing trade CSV datasets to disk.", details=str(e))
        except Exception as e:
            logger.error(f"Unexpected error during CSV export: {e}")
            raise TradeEngineError(message="Unexpected exception during CSV export.", details=str(e))

    def run(self) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """Executes complete synthetic data generation workflow."""
        start_time = time.perf_counter()
        logger.info("Starting synthetic trade data generation workflow...")

        fo_df = self.generate_front_office_data()
        bo_df = self.generate_back_office_data(fo_df)
        self.save_to_csv(fo_df, bo_df)

        elapsed = round(time.perf_counter() - start_time, 4)
        logger.info(f"Trade data generation completed in {elapsed} seconds.")
        return fo_df, bo_df, self.metrics

    def _record_break(
        self,
        trade_id: str,
        break_type: str,
        expected: Any,
        actual: Any,
        severity: str,
    ) -> None:
        """Helper to append an internal break tracking record."""
        self.break_records.append(
            {
                "Trade_ID": trade_id,
                "Break_Type": break_type,
                "Expected_Value": str(expected),
                "Actual_Value": str(actual),
                "Severity": severity,
            }
        )

    def _validate_dataset(
        self,
        df: pd.DataFrame,
        dataset_name: str,
        check_unique_id: bool = True,
    ) -> None:
        """Internal data quality validation helper."""
        if df.empty:
            raise TradeEngineError(f"{dataset_name} dataset is empty.")

        if check_unique_id and df["Trade_ID"].duplicated().any():
            raise TradeEngineError(f"Duplicate Trade_IDs detected in {dataset_name}.")

        if (df["Quantity"] <= 0).any():
            raise TradeEngineError(f"Non-positive Quantity detected in {dataset_name}.")

        if (df["Price"] <= 0).any():
            raise TradeEngineError(f"Non-positive Price detected in {dataset_name}.")

        invalid_currencies = set(df["Currency"]) - set(CURRENCIES)
        if invalid_currencies:
            raise TradeEngineError(f"Invalid currency codes detected in {dataset_name}: {invalid_currencies}")

        invalid_statuses = set(df["Trade_Status"]) - set(TRADE_STATUSES)
        if invalid_statuses:
            raise TradeEngineError(f"Invalid trade status values detected in {dataset_name}: {invalid_statuses}")
