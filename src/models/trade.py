"""
Trade Domain Model for Trade Reconciliation & Control Automation Engine.

Defines the core data structures representing front-office and back-office trades
across asset classes (Equities, Fixed Income, FX, Derivatives, Commodities).
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Dict, Optional

from src.utils.logger import get_logger

logger = get_logger("TradeModel")


@dataclass
class Trade:
    """
    Core Trade domain model encapsulation.

    Attributes:
        trade_id: Unique identifier of the trade transaction.
        counterparty: Institution or counterparty involved in the trade.
        asset_class: Financial product classification (e.g. EQUITY, FX, FIXED_INCOME).
        quantity: Traded unit quantity or volume.
        price: Unit price at trade execution.
        currency: ISO currency code (e.g. USD, EUR, GBP).
        trade_date: ISO trade execution date (YYYY-MM-DD).
        settlement_date: Expected value/settlement date (YYYY-MM-DD).
        trader_id_or_book: Trader ID (Front Office) or Book/Account ID (Back Office).
        source_system: System feed origin (e.g. 'FRONT_OFFICE', 'BACK_OFFICE').
        notional_amount: Calculated total financial exposure (quantity * price).
        status: Transaction state (e.g. 'NEW', 'MATCHED', 'BREAK').
    """

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
    notional_amount: float = field(init=False)
    status: str = "NEW"
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def __post_init__(self) -> None:
        """Post-initialization calculations and type checks."""
        self.notional_amount = round(self.quantity * self.price, 4)
        logger.debug(f"Initialized Trade model for trade_id: {self.trade_id} with Notional: {self.notional_amount}")

    def calculate_notional(self) -> float:
        """
        Recalculates total trade notional exposure amount.

        :return: Notional monetary amount (quantity * price).
        """
        # TODO Phase 2: Add asset-class specific multiplier logic (e.g. FX pip scale, Bond face value factor)
        self.notional_amount = round(self.quantity * self.price, 4)
        return self.notional_amount

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the Trade instance into a Python dictionary payload.

        :return: Dictionary representation of the trade model.
        """
        # TODO Phase 2: Implement custom serialization formatting for database insertion
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trade":
        """
        Constructs a Trade model instance from a raw data dictionary.

        :param data: Input dictionary containing trade attributes.
        :return: Instantiated Trade object.
        """
        # TODO Phase 2: Add key mapping transformations for disparate FO/BO CSV schemas
        return cls(
            trade_id=str(data.get("trade_id", "")),
            counterparty=str(data.get("counterparty", "")),
            asset_class=str(data.get("asset_class", "")),
            quantity=float(data.get("quantity", 0.0)),
            price=float(data.get("price", 0.0)),
            currency=str(data.get("currency", "USD")),
            trade_date=str(data.get("trade_date", "")),
            settlement_date=str(data.get("settlement_date", "")),
            trader_id_or_book=str(data.get("trader_id_or_book", "DEFAULT_DESK")),
            source_system=str(data.get("source_system", "FRONT_OFFICE")),
            status=str(data.get("status", "NEW")),
        )

    def validate(self) -> bool:
        """
        Executes internal domain integrity checks on the trade instance.

        :return: True if valid.
        """
        # TODO Phase 2: Implement full domain validation check (non-empty ID, positive price/qty)
        logger.debug(f"Performing internal validation on trade_id: {self.trade_id}")
        return len(self.trade_id.strip()) > 0 and self.quantity > 0 and self.price > 0
