"""Stage 7: compute order qty."""

import logging
from typing import Optional

import pandas as pd

from src.inventory.order_optimizer import compute_order_recommendations
from src.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


def run_order_optimization_stage(ctx: PipelineContext) -> PipelineContext:
    """Compute order qty per store×SKU from forecasts, inventory, products, policy."""
    forecasts = ctx.forecasts
    if forecasts is None or forecasts.empty:
        logger.warning("No forecasts; skipping order optimization")
        ctx.orders = pd.DataFrame()
        return ctx

    data = ctx.ingested_data
    if not data:
        logger.warning("No ingested data; skipping order optimization")
        ctx.orders = pd.DataFrame()
        return ctx

    inv = data["inventory"].copy()
    if "code" in inv.columns and "sku" not in inv.columns:
        inv["sku"] = inv["code"]
    prod = data["products"].copy()
    if "item_code" in prod.columns and "sku" not in prod.columns:
        prod["sku"] = prod["item_code"]

    policy = ctx.policy
    if policy is None:
        from src.policy.rules import OrderPolicy, PolicyMode
        policy = OrderPolicy(policy_mode=PolicyMode.BALANCED)

    orders = compute_order_recommendations(
        forecasts=forecasts,
        inventory=inv,
        products=prod,
        policy=policy,
    )

    ctx.orders = orders
    total_qty = int(orders["order_qty"].sum()) if not orders.empty else 0
    logger.info(
        "Order optimization complete: %d recommendations, total order_qty=%d",
        len(orders),
        total_qty,
    )
    return ctx
