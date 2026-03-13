"""
Stage 9: Inventory simulation - run simulation with forecast and policy.
"""

import logging
from typing import Optional

import pandas as pd

from src.inventory.simulation import InventorySimulator, SimulationReport
from src.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


def run_simulation_stage(ctx: PipelineContext) -> PipelineContext:
    """
    Run inventory simulation using demand data and forecasts.

    Uses sales_cleaned (or sales_with_features) as demand, forecasts for
    ordering policy, and config for initial stock, expiration, lead time.
    When run as part of full pipeline, simulates a representative SKU.

    Args:
        ctx: Context with sales data, forecasts, policy, ingested_data.
            Uses config['inventory'] for expiration_days, lead_time_days.
            Uses config['simulation'] for enable, initial_stock.

    Returns:
        Updated context with simulation_report populated.
    """
    sim_cfg = ctx.config.get("simulation", {})
    if not sim_cfg.get("enable", True):
        logger.info("Simulation disabled in config")
        return ctx

    sales = ctx.sales_with_features if ctx.sales_with_features is not None else ctx.sales_cleaned
    if sales is None or (hasattr(sales, "empty") and sales.empty):
        logger.warning("No sales data; skipping simulation")
        return ctx

    inv_cfg = ctx.config.get("inventory", {})
    expiration_days = inv_cfg.get("expiration_days", 7)
    lead_time_days = inv_cfg.get("lead_time_days", 0)
    initial_stock = sim_cfg.get("initial_stock", 50)

    policy = ctx.policy
    if policy is None:
        from src.policy.rules import OrderPolicy, PolicyMode
        policy = OrderPolicy(policy_mode=PolicyMode.BALANCED)

    # Use first store×SKU as demo, or aggregate to single series
    group_cols = [c for c in ["store_id", "sku"] if c in sales.columns] or ["sku"]
    first_group = sales.groupby(group_cols).first().reset_index()
    if first_group.empty:
        logger.warning("No groups for simulation")
        return ctx

    # Build demand time series for first SKU
    first_sku = first_group.iloc[0]
    sku_filter = first_sku["sku"] if "sku" in first_sku else first_sku.get("product_id")
    store_filter = first_sku.get("store_id") if "store_id" in first_sku else None

    mask = sales["sku"] == sku_filter
    if store_filter:
        mask = mask & (sales["store_id"] == store_filter)
    demand_df = sales.loc[mask, ["date", "demand"]].sort_values("date")

    if len(demand_df) < 3:
        logger.warning("Insufficient demand history for simulation")
        return ctx

    # Forecast: use mean demand as constant forecast (simplified)
    forecast_val = float(demand_df["demand"].mean())

    sim = InventorySimulator(
        demand_ts=demand_df,
        forecast_demand=forecast_val,
        initial_stock=initial_stock,
        expiration_days=expiration_days,
        policy=policy,
        lead_time_days=lead_time_days,
    )
    report = sim.simulate()

    ctx.simulation_report = report
    logger.info(
        "Simulation complete: service_level=%.2f, waste=%.1f",
        report.metrics.get("service_level", 0),
        report.metrics.get("waste_quantity", 0),
    )
    return ctx
