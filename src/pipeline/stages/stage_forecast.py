"""Stage 6: predict tomorrow."""

import logging
from typing import Optional

import pandas as pd

from src.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


def run_forecast_stage(ctx: PipelineContext) -> PipelineContext:
    """Predict tomorrow per store×SKU. Uses last row per group from sales_with_features."""
    model = ctx.model
    sales = ctx.sales_with_features
    if model is None or sales is None or sales.empty:
        logger.warning("No model or data; skipping forecast stage")
        ctx.forecasts = pd.DataFrame()
        return ctx

    try:
        tomorrow = model.predict_next_day(sales, target="demand")
        ctx.forecasts = tomorrow
        logger.info("Forecast complete: %d store-SKU predictions", len(tomorrow))
    except Exception as e:
        logger.error("Forecast failed: %s", e)
        ctx.forecasts = pd.DataFrame()

    return ctx
