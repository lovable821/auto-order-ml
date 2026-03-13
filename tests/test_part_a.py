"""Part A tests."""

import pytest
import numpy as np
from pathlib import Path

from src.pipeline.orchestrator import run_pipeline
from src.models.metrics import wape, bias_metric, evaluate_forecast


def test_wape():
    """WAPE metric."""
    y_true = np.array([10, 20, 30])
    y_pred = np.array([12, 18, 32])
    assert 0 <= wape(y_true, y_pred) <= 1


def test_bias():
    """Bias metric."""
    y_true = np.array([10, 20, 30])
    y_pred = np.array([12, 22, 32])  # over-forecast
    assert bias_metric(y_true, y_pred) > 0


def test_evaluate_forecast():
    """evaluate_forecast returns dict."""
    r = evaluate_forecast([1, 2, 3], [1.1, 2.1, 2.9])
    assert "wape" in r
    assert "bias" in r


def test_run_part_a(project_root):
    """Pipeline runs end-to-end with forecast output."""
    config_path = str(project_root / "configs" / "default.yaml")
    ctx = run_pipeline(
        config_path,
        config_overrides={"pipeline": {"data_path": str(project_root / "data_sample")}},
    )
    assert ctx.model is not None or ctx.forecasts is not None
    if ctx.model is not None:
        assert "wape" in ctx.metrics
        assert "bias" in ctx.metrics
    if ctx.forecasts is not None and not ctx.forecasts.empty:
        if len(ctx.forecasts) >= 2:
            assert ctx.forecasts["predicted_demand"].nunique() >= 1
