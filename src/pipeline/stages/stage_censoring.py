"""Stage 4: censored demand."""

import logging
from typing import Optional

import pandas as pd

from src.pipeline.context import PipelineContext
from src.pipeline.preprocessing import handle_demand_censoring

logger = logging.getLogger(__name__)


def run_censoring_stage(ctx: PipelineContext) -> PipelineContext:
    """Flag stockout days (balance=0). Can exclude or impute those rows."""
    sales = ctx.sales_cleaned
    if sales is None or sales.empty:
        logger.warning("No sales data; skipping censoring stage")
        return ctx

    censoring_cfg = ctx.config.get("censoring", {})
    if not censoring_cfg.get("enable", True):
        ctx.sales_corrected = sales.copy()
        return ctx

    inventory = ctx.ingested_data.get("inventory", pd.DataFrame()) if ctx.ingested_data else pd.DataFrame()
    if inventory.empty:
        logger.debug("No inventory data; skipping censoring (no stockout info)")
        ctx.sales_corrected = sales.copy()
        if "censored" not in ctx.sales_corrected.columns:
            ctx.sales_corrected["censored"] = False
        return ctx

    sales = handle_demand_censoring(
        sales,
        inventory=inventory,
        demand_col="demand",
        sku_col="sku",
        date_col="date",
        store_col="store_id",
    )

    correction_method = censoring_cfg.get("correction_method", "flag_only")
    if correction_method == "exclude_censored":
        before = len(sales)
        sales = sales[~sales["censored"]].copy()
        logger.info("Excluded %d censored rows", before - len(sales))
    elif correction_method == "impute_rolling":
        sales = _impute_censored_demand(sales)

    ctx.sales_corrected = sales
    n_censored = int(sales["censored"].sum()) if "censored" in sales.columns else 0
    logger.info("Censoring complete: %d censored rows flagged", n_censored)
    return ctx


def _impute_censored_demand(df: pd.DataFrame, window: int = 7) -> pd.DataFrame:
    """Replace censored demand with rolling mean of recent uncensored."""
    df = df.copy()
    group_cols = [c for c in ["store_id", "sku"] if c in df.columns] or ["sku"]
    for (_, group), idx in df.groupby(group_cols).groups.items():
        sub = df.loc[idx].sort_values("date")
        censored_mask = sub["censored"].fillna(False)
        if not censored_mask.any():
            continue
        rolling = sub["demand"].rolling(window, min_periods=1).mean()
        df.loc[idx[censored_mask], "demand"] = rolling[censored_mask].values
    return df
