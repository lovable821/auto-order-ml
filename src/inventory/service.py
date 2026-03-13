"""Inventory service - stock levels and reorder logic."""

from dataclasses import dataclass
from typing import List


@dataclass
class StockLevel:
    """Current stock for a product."""

    product_id: str
    quantity: float
    safety_stock: float


def compute_reorder_point(
    forecast_demand: float,
    lead_time_days: int,
    safety_stock_days: int,
    multiplier: float = 1.2,
) -> float:
    """Compute reorder point from forecast and policy."""
    return forecast_demand * (lead_time_days + safety_stock_days) * multiplier
