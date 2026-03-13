"""
Order optimization logic - Part B.

Computes recommended order_qty for tomorrow given:
- Demand forecast
- Current stock
- Expiration days (shelf life)

Balances OOS (out-of-stock) vs waste (overstock/expiry).
"""

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from src.policy.rules import OrderPolicy, apply_policy

logger = logging.getLogger(__name__)


@dataclass
class OrderRecommendation:
    """Order recommendation for a store×SKU."""

    store_id: str
    sku: str
    forecast_demand: float
    current_stock: float
    expiration_days: float
    order_qty: int
    reason: str  # "cover_forecast", "sufficient_stock", "capped_by_expiry"


def compute_order_qty(
    forecast_demand: float,
    current_stock: float,
    expiration_days: float,
    *,
    min_order: int = 1,
    max_order: int = 1000,
    policy: Optional[OrderPolicy] = None,
) -> int:
    """
    Compute recommended order quantity for tomorrow.

    Logic:
    - Order to cover forecast: need = forecast - stock
    - Cap by expiration: don't order more than we can sell before expiry
      (stock + order <= expiration_days * forecast)
    - Apply min/max policy

    Args:
        forecast_demand: Predicted demand for tomorrow.
        current_stock: Current inventory balance.
        expiration_days: Shelf life in days (from product properties).
        min_order: Minimum order quantity.
        max_order: Maximum order quantity.
        policy: Optional OrderPolicy for rounding.

    Returns:
        Recommended order quantity (int).
    """
    need = forecast_demand - current_stock

    if need <= 0:
        return 0

    # Cap by expiration: avoid overstock that would expire
    # Max stock we want = expiration_days * daily_demand (approx)
    max_stock_after_order = expiration_days * forecast_demand
    waste_cap = max(0, max_stock_after_order - current_stock)

    raw_qty = min(need, waste_cap) if expiration_days > 0 else need
    raw_qty = max(0, raw_qty)

    if policy:
        qty = apply_policy(raw_qty, policy)
    else:
        qty = max(min_order, min(max_order, int(round(raw_qty))))

    return qty


def compute_order_recommendations(
    forecasts: pd.DataFrame,
    inventory: pd.DataFrame,
    products: pd.DataFrame,
    *,
    policy: Optional[OrderPolicy] = None,
) -> pd.DataFrame:
    """
    Compute order_qty for each store×SKU.

    Args:
        forecasts: DataFrame with store_id, sku, predicted_demand.
        inventory: DataFrame with Code/sku, balance.
        products: DataFrame with item_code/sku, ExpirationDays.

    Returns:
        DataFrame with store_id, sku, forecast_demand, current_stock,
        expiration_days, order_qty.
    """
    if forecasts.empty:
        return pd.DataFrame()

    inv_sku = "code" if "code" in inventory.columns else ("sku" if "sku" in inventory.columns else "product_id")
    inv_balance = "balance" if "balance" in inventory.columns else "quantity"
    prod_sku = "item_code" if "item_code" in products.columns else ("sku" if "sku" in products.columns else "product_id")
    exp_col = "ExpirationDays" if "ExpirationDays" in products.columns else "expiration_days"

    inv_cols = [c for c in [inv_sku, inv_balance] if c in inventory.columns]
    if len(inv_cols) < 2:
        logger.warning("Inventory missing required columns (sku/code, balance/quantity)")
        return pd.DataFrame()

    inv = inventory[inv_cols].rename(columns={inv_sku: "sku", inv_balance: "stock"})

    prod_cols = [c for c in [prod_sku, exp_col] if c in products.columns]
    if prod_sku not in prod_cols:
        logger.warning("Products missing SKU column")
        return pd.DataFrame()
    prod = products[[prod_sku]].copy()
    prod = prod.rename(columns={prod_sku: "sku"})
    if exp_col in products.columns:
        prod["expiration_days"] = pd.to_numeric(products[exp_col], errors="coerce").fillna(7)
    else:
        prod["expiration_days"] = 7  # default when missing

    merged = forecasts.merge(inv, on="sku", how="left")
    merged = merged.merge(prod, on="sku", how="left")
    merged["stock"] = merged["stock"].fillna(0)
    merged["expiration_days"] = merged["expiration_days"].fillna(7)

    pol = policy or OrderPolicy()

    rows = []
    for _, row in merged.iterrows():
        qty = compute_order_qty(
            forecast_demand=row["predicted_demand"],
            current_stock=row["stock"],
            expiration_days=row["expiration_days"],
            min_order=pol.min_order_quantity,
            max_order=pol.max_order_quantity,
            policy=pol,
        )
        rows.append({
            "store_id": row.get("store_id", "ALL"),
            "sku": row["sku"],
            "forecast_demand": row["predicted_demand"],
            "current_stock": row["stock"],
            "expiration_days": row["expiration_days"],
            "order_qty": qty,
        })

    return pd.DataFrame(rows)
