"""Tests for Part A pipeline."""

import pytest
import numpy as np
from pathlib import Path

from src.pipeline.part_a_runner import run_part_a
from src.pipeline.data_ingestion_pipeline import DataIngestionConfig
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
    """Part A pipeline runs end-to-end."""
    cfg = DataIngestionConfig(data_source="csv", data_path=project_root / "data_sample")
    result = run_part_a(config=cfg, train_test_split=0.7)
    assert "model" in result
    assert "metrics" in result
    assert "predictions" in result
    if result["model"] is not None:
        assert "wape" in result["metrics"]
        assert "bias" in result["metrics"]
        assert not result["predictions"].empty
        # Different SKUs should get different predictions
        preds = result["predictions"]
        if len(preds) >= 2:
            assert preds["predicted_demand"].nunique() >= 2, "SKUs should have different forecasts"
