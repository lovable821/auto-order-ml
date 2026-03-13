"""Stage 5: train model."""

import logging
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.features.engineer import get_feature_columns
from src.models.lightgbm_forecaster import LightGBMForecaster
from src.models.metrics import evaluate_forecast
from src.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


def run_training_stage(ctx: PipelineContext) -> PipelineContext:
    """Train LightGBM on sales_with_features. Time split, eval on test. Seed from config."""
    sales = ctx.sales_with_features
    if sales is None or sales.empty or len(sales) < 10:
        logger.warning("Insufficient data for training; skipping")
        return ctx

    _apply_seed(ctx)

    models_cfg = ctx.config.get("models", {})
    train_test_split = ctx.train_test_split or models_cfg.get("train_test_split", 0.8)
    lgb_params = models_cfg.get("lightgbm", {})
    feat_cols = ctx.feature_columns or get_feature_columns()

    sales = sales.sort_values("date")
    split_idx = int(len(sales) * train_test_split)
    train = sales.iloc[:split_idx]
    test = sales.iloc[split_idx:]

    # Default LightGBM params
    defaults = {
        "n_estimators": 100,
        "max_depth": 4,
        "min_child_samples": 2,
        "min_data_in_leaf": 2,
        "verbosity": -1,
        "random_state": _get_seed(ctx),
    }
    params = {**defaults, **lgb_params}

    model = LightGBMForecaster(feature_cols=feat_cols, lgb_params=params)
    model.fit(train, target="demand")

    preds = model.predict(test)
    metrics = evaluate_forecast(test["demand"].values, preds)

    ctx.model = model
    ctx.metrics = metrics
    ctx.test_actual = test["demand"].values
    ctx.test_predictions = preds
    logger.info(
        "Training complete: WAPE=%.4f, Bias=%.4f",
        metrics["wape"],
        metrics["bias"],
    )
    return ctx


def _apply_seed(ctx: PipelineContext) -> None:
    """Set random seeds from config."""
    seed = _get_seed(ctx)
    if seed is not None:
        np.random.seed(seed)
        try:
            import random
            random.seed(seed)
        except Exception:
            pass


def _get_seed(ctx: PipelineContext) -> Optional[int]:
    """Read seed from config.reproducibility.random_seed."""
    return ctx.config.get("reproducibility", {}).get("random_seed")
