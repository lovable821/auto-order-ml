"""Pipeline orchestrator - runs all stages in sequence."""

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

from src.pipeline.context import PipelineContext
from src.pipeline.stages import (
    run_ingestion_stage,
    run_cleaning_stage,
    run_censoring_stage,
    run_features_stage,
    run_training_stage,
    run_forecast_stage,
    run_policy_stage,
    run_order_optimization_stage,
    run_simulation_stage,
)

logger = logging.getLogger(__name__)


def load_config(config_path: str | Path) -> dict[str, Any]:
    """Load config from YAML. Falls back to defaults if file missing."""
    path = Path(config_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent.parent / path
    if not path.exists():
        logger.warning("Config file not found: %s; using defaults", path)
        return _default_config()

    with open(path) as f:
        config = yaml.safe_load(f) or {}
    return {**_default_config(), **config}


def _default_config() -> dict[str, Any]:
    """Return default configuration."""
    return {
        "data_source": "csv",
        "pipeline": {
            "data_path": "data_sample",
            "output_path": "data/processed",
            "batch_size": 1000,
        },
        "preprocessing": {
            "remove_outliers": True,
            "fill_missing_dates": False,
            "outlier_method": "iqr",
            "outlier_factor": 1.5,
        },
        "censoring": {
            "enable": True,
            "correction_method": "flag_only",
        },
        "features": {
            "lookback_days": 30,
            "lag_days": [1, 2, 3],
            "rolling_windows": [3, 6],
        },
        "models": {
            "train_test_split": 0.8,
            "lightgbm": {},
        },
        "inventory": {
            "expiration_days": 7,
            "lead_time_days": 0,
        },
        "policy": {
            "policy_mode": "balanced",
            "min_order_quantity": 1,
            "max_order_quantity": 1000,
        },
        "simulation": {
            "enable": True,
            "initial_stock": 50,
        },
        "reproducibility": {
            "random_seed": 42,
        },
    }


def run_pipeline(
    config_path: str | Path = "configs/default.yaml",
    config_overrides: Optional[dict[str, Any]] = None,
) -> PipelineContext:
    """Run the full pipeline. Returns context with model, forecasts, orders, etc."""
    config = load_config(config_path)
    if config_overrides:
        config = _deep_merge(config, config_overrides)

    ctx = PipelineContext(config=config)
    ctx.train_test_split = config.get("models", {}).get("train_test_split", 0.8)

    stages = [
        ("ingestion", run_ingestion_stage),
        ("cleaning", run_cleaning_stage),
        ("censoring", run_censoring_stage),
        ("features", run_features_stage),
        ("training", run_training_stage),
        ("forecast", run_forecast_stage),
        ("policy", run_policy_stage),
        ("order_optimization", run_order_optimization_stage),
        ("simulation", run_simulation_stage),
    ]

    for name, stage_fn in stages:
        logger.info("Running stage: %s", name)
        try:
            ctx = stage_fn(ctx)
        except Exception as e:
            logger.exception("Stage %s failed: %s", name, e)
            raise

    logger.info("Pipeline complete")
    return ctx


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result
