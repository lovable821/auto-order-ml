"""
Part A: Demand forecast for tomorrow (store×SKU).

Orchestrates: ingestion -> preprocessing -> features -> LightGBM -> evaluation.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from src.pipeline.data_ingestion_pipeline import DataIngestionConfig, DataIngestionPipeline
from src.pipeline.preprocessing import preprocess_sales
from src.features.engineer import build_features, get_feature_columns

FEAT_LAG_DAYS = (1, 2, 3)
FEAT_ROLLING = (3, 6)
from src.models.lightgbm_forecaster import LightGBMForecaster
from src.models.metrics import evaluate_forecast

logger = logging.getLogger(__name__)


def run_part_a(
    config: DataIngestionConfig | None = None,
    data_path: str | Path | None = None,
    train_test_split: float = 0.8,
) -> dict[str, Any]:
    """
    Run Part A pipeline: forecast tomorrow's demand per store×SKU.

    Returns:
        Dict with model, metrics (WAPE, Bias), predictions, test_data.
    """
    cfg = config or DataIngestionConfig(data_source="csv", data_path=data_path)
    pipeline = DataIngestionPipeline(cfg)
    data = pipeline.run()

    sales = pipeline.get_sales_for_forecasting(data)
    if sales.empty:
        logger.warning("No sales data")
        return {"model": None, "metrics": {}, "predictions": pd.DataFrame()}

    # Preprocess
    sales = preprocess_sales(
        sales,
        inventory=data.get("inventory"),
        handle_censoring=bool(not data["inventory"].empty),
        remove_outliers_flag=True,
        fill_missing=False,
    )

    # Label-encode sku for model (LightGBM needs numeric)
    if "sku" in sales.columns:
        sales["sku_code"] = pd.Categorical(sales["sku"]).codes

    # Features (use smaller lags for sparse/monthly data)
    sales = build_features(
        sales,
        lookback_days=30,
        lag_days=FEAT_LAG_DAYS,
        rolling_windows=FEAT_ROLLING,
    )

    # Drop rows with NaN from lags (start of series)
    feat_cols = get_feature_columns(lag_days=FEAT_LAG_DAYS, rolling_windows=FEAT_ROLLING)
    if "sku_code" in sales.columns:
        feat_cols = ["sku_code"] + feat_cols
    sales = sales.dropna(subset=[c for c in feat_cols if c in sales.columns])

    if sales.empty or len(sales) < 10:
        logger.warning("Insufficient data after feature engineering")
        return {"model": None, "metrics": {}, "predictions": pd.DataFrame()}

    # Train/test split by time
    sales = sales.sort_values("date")
    split_idx = int(len(sales) * train_test_split)
    train = sales.iloc[:split_idx]
    test = sales.iloc[split_idx:]

    # Single model with sku_code for product differentiation
    lgb_params = {
        "n_estimators": 100,
        "max_depth": 4,
        "min_child_samples": 2,
        "min_data_in_leaf": 2,
    }
    model = LightGBMForecaster(feature_cols=feat_cols, lgb_params=lgb_params)
    model.fit(train, target="demand")

    preds = model.predict(test)
    metrics = evaluate_forecast(test["demand"].values, preds)

    # Predict tomorrow for each store×SKU (use last row)
    tomorrow = model.predict_next_day(sales, target="demand")

    logger.info("Part A complete. WAPE=%.4f, Bias=%.4f", metrics["wape"], metrics["bias"])

    return {
        "model": model,
        "metrics": metrics,
        "predictions": tomorrow,
        "test_predictions": preds,
        "test_actual": test["demand"].values,
    }
