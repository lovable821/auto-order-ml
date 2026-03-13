"""Data ingestion pipeline tests."""

import pytest
from pathlib import Path

from src.pipeline.data_ingestion_pipeline import (
    DataIngestionConfig,
    DataIngestionPipeline,
)


def test_config_from_dict():
    """DataIngestionConfig loads from dict."""
    cfg = DataIngestionConfig.from_dict({"data_source": "csv"})
    assert cfg.data_source == "csv"


def test_pipeline_run_csv(project_root):
    """Pipeline runs with CSV source."""
    cfg = DataIngestionConfig(data_source="csv", data_path=project_root / "data_sample")
    pipeline = DataIngestionPipeline(cfg)
    data = pipeline.run()
    assert "sales" in data
    assert "inventory" in data
    assert not data["sales"].empty


def test_get_sales_for_forecasting(project_root):
    """get_sales_for_forecasting returns store×sku×date format."""
    cfg = DataIngestionConfig(data_source="csv", data_path=project_root / "data_sample")
    pipeline = DataIngestionPipeline(cfg)
    data = pipeline.run()
    df = pipeline.get_sales_for_forecasting(data)
    assert "store_id" in df.columns
    assert "sku" in df.columns
    assert "date" in df.columns
    assert "demand" in df.columns
