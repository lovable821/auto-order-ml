"""
Stage 2: Data cleaning - normalize, deduplicate, remove outliers, fill missing dates.
"""

import logging
from typing import Optional

import pandas as pd

from src.pipeline.context import PipelineContext
from src.pipeline.data_ingestion_pipeline import DataIngestionPipeline
from src.pipeline.preprocessing import fill_missing_dates, remove_outliers

logger = logging.getLogger(__name__)


def run_cleaning_stage(ctx: PipelineContext) -> PipelineContext:
    """
    Clean and normalize the sales dataset.

    Uses get_sales_for_forecasting for aggregation, then applies outlier removal
    and optional missing-date filling. Does NOT apply censoring (that is stage 4).

    Args:
        ctx: Context with ingested_data. Expects config['preprocessing'] for
            remove_outliers, fill_missing, etc.

    Returns:
        Updated context with sales_cleaned populated.
    """
    if not ctx.ingested_data:
        logger.warning("No ingested data; skipping cleaning stage")
        return ctx

    pipeline = DataIngestionPipeline(None)
    sales = pipeline.get_sales_for_forecasting(ctx.ingested_data)

    if sales.empty:
        logger.warning("No sales data for forecasting")
        ctx.sales_cleaned = sales
        return ctx

    preprocess_cfg = ctx.config.get("preprocessing", {})
    remove_outliers_flag = preprocess_cfg.get("remove_outliers", True)
    fill_missing = preprocess_cfg.get("fill_missing_dates", False)
    outlier_method = preprocess_cfg.get("outlier_method", "iqr")
    outlier_factor = preprocess_cfg.get("outlier_factor", 1.5)

    if remove_outliers_flag:
        sales = remove_outliers(
            sales,
            demand_col="demand",
            method=outlier_method,
            factor=outlier_factor,
        )

    if fill_missing:
        sales = fill_missing_dates(
            sales,
            sku_col="sku",
            date_col="date",
            demand_col="demand",
            store_col="store_id",
            fill_value=0,
        )

    ctx.sales_cleaned = sales
    logger.info("Cleaning complete: %d rows", len(sales))
    return ctx
