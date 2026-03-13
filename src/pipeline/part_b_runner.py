"""
Part B: Order quantity for tomorrow.

Uses Part A forecast + inventory + product properties (expiration) -> order_qty.
"""

import logging

from pathlib import Path
from typing import Any

import pandas as pd

from src.pipeline.part_a_runner import run_part_a
from src.pipeline.data_ingestion_pipeline import DataIngestionConfig, DataIngestionPipeline
from src.inventory.order_optimizer import compute_order_recommendations
from src.policy.rules import OrderPolicy

logger = logging.getLogger(__name__)


def run_part_b(
    config: DataIngestionConfig | None = None,
    data_path: str | Path | None = None,
    **part_a_kwargs: Any,
) -> dict[str, Any]:
    """
    Run Part B: compute order_qty for tomorrow per store×SKU.

    Pipeline: Part A forecast -> merge inventory + products -> order optimization.

    Returns:
        Dict with forecasts, orders (DataFrame with order_qty), data.
    """
    cfg = config or DataIngestionConfig(data_source="csv", data_path=data_path)
    pipeline = DataIngestionPipeline(cfg)
    data = pipeline.run()

    # Run Part A for forecasts
    part_a_result = run_part_a(config=cfg, data_path=data_path, **part_a_kwargs)
    forecasts = part_a_result.get("predictions", pd.DataFrame())

    if forecasts.empty:
        logger.warning("No forecasts from Part A")
        return {"forecasts": pd.DataFrame(), "orders": pd.DataFrame(), "data": data}

    # Align inventory: ensure sku column matches (Code -> sku)
    inv = data["inventory"].copy()
    if "code" in inv.columns and "sku" not in inv.columns:
        inv["sku"] = inv["code"]

    # Products: item_code -> sku, ExpirationDays
    prod = data["products"].copy()
    if "item_code" in prod.columns and "sku" not in prod.columns:
        prod["sku"] = prod["item_code"]

    policy = OrderPolicy(min_order_quantity=1, max_order_quantity=1000)
    orders = compute_order_recommendations(
        forecasts=forecasts,
        inventory=inv,
        products=prod,
        policy=policy,
    )

    logger.info(
        "Part B order optimization: %d recommendations (total order_qty=%d)",
        len(orders),
        int(orders["order_qty"].sum()),
    )
    for _, row in orders.iterrows():
        if row["order_qty"] > 0:
            logger.info(
                "  %s/%s: forecast=%.1f stock=%.0f -> order_qty=%d",
                row["store_id"],
                row["sku"],
                row["forecast_demand"],
                row["current_stock"],
                row["order_qty"],
            )

    return {
        "forecasts": forecasts,
        "orders": orders,
        "data": data,
        "part_a_metrics": part_a_result.get("metrics", {}),
    }
