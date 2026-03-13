"""Stage 3: build features."""

import logging
from typing import Optional

import pandas as pd

from src.features.engineer import build_features, get_feature_columns
from src.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


def run_features_stage(ctx: PipelineContext) -> PipelineContext:
    """Add lags, rolling mean/std, calendar. Uses sales_cleaned or sales_corrected."""
    sales = ctx.sales_corrected if ctx.sales_corrected is not None else ctx.sales_cleaned
    if sales is None or sales.empty:
        logger.warning("No sales data; skipping feature engineering")
        return ctx

    feat_cfg = ctx.config.get("features", {})
    lookback_days = feat_cfg.get("lookback_days", 30)
    lag_days = tuple(feat_cfg.get("lag_days", [1, 2, 3]))
    rolling_windows = tuple(feat_cfg.get("rolling_windows", [3, 6]))

    sales = build_features(
        sales,
        lookback_days=lookback_days,
        target_column="demand",
        sku_col="sku",
        date_col="date",
        store_col="store_id",
        lag_days=lag_days,
        rolling_windows=rolling_windows,
    )

    feat_cols = list(
        get_feature_columns(lag_days=lag_days, rolling_windows=rolling_windows)
    )
    if "sku" in sales.columns:
        sales = sales.copy()
        sales["sku_code"] = pd.Categorical(sales["sku"]).codes
        feat_cols = ["sku_code"] + feat_cols

    sales = sales.dropna(subset=[c for c in feat_cols if c in sales.columns])

    ctx.sales_with_features = sales
    ctx.feature_columns = feat_cols
    logger.info("Feature engineering complete: %d rows, %d features", len(sales), len(feat_cols))
    return ctx
