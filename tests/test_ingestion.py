"""Tests for data ingestion module."""

import pandas as pd
import pytest
from unittest.mock import Mock, patch

from src.pipeline.ingestion import (
    load_all_data,
    _normalize_columns,
    _parse_dates,
    _unify_sku,
    _remove_duplicates,
)


def test_normalize_columns_renames_foreign():
    """Columns are renamed from foreign to English."""
    df = pd.DataFrame({"datum": [1], "menge": [10], "produkt_id": ["P1"]})
    result = _normalize_columns(df)
    assert "date" in result.columns
    assert "quantity" in result.columns
    assert "product_id" in result.columns
    assert "datum" not in result.columns


def test_normalize_columns_lowercase():
    """Column names are lowercased."""
    df = pd.DataFrame({"Product_ID": [1], "Quantity": [2]})
    result = _normalize_columns(df)
    assert list(result.columns) == ["product_id", "quantity"]


def test_parse_dates():
    """Date columns are parsed to datetime."""
    df = pd.DataFrame({"date": ["01.01.2025", "15.03.2026"]})
    result = _parse_dates(df, ["date"])
    assert pd.api.types.is_datetime64_any_dtype(result["date"])
    assert result["date"].iloc[0].year == 2025


def test_unify_sku_from_product_id():
    """SKU created from product_id when missing."""
    df = pd.DataFrame({"product_id": ["P1", "P2"], "quantity": [1, 2]})
    result = _unify_sku(df, "test")
    assert "sku" in result.columns
    assert list(result["sku"]) == ["P1", "P2"]


def test_unify_sku_from_sku():
    """product_id created from sku when missing."""
    df = pd.DataFrame({"sku": ["S1", "S2"], "qty": [1, 2]})
    result = _unify_sku(df, "test")
    assert "product_id" in result.columns
    assert list(result["product_id"]) == ["S1", "S2"]


def test_remove_duplicates():
    """Duplicate rows are removed."""
    df = pd.DataFrame({"a": [1, 1, 2], "b": [10, 10, 20]})
    result = _remove_duplicates(df, "test")
    assert len(result) == 2


def test_load_all_data_from_csv_returns_dict(project_root):
    """load_all_data (csv) returns dict with sales, inventory, products, losses."""
    result = load_all_data(data_source="csv", data_path=project_root / "data_sample")
    assert "sales" in result
    assert "inventory" in result
    assert "products" in result
    assert "losses" in result
    assert all(isinstance(v, pd.DataFrame) for v in result.values())
    assert len(result["sales"]) > 0


@patch("src.pipeline.ingestion.ForecastoClient")
def test_load_all_data_api_returns_dict(mock_client_class):
    """load_all_data (api) returns dict with sales, inventory, products, losses."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_client.get_sales.return_value = pd.DataFrame({"date": ["01.01.2025"], "product_id": ["P1"], "quantity": [1]})
    mock_client.get_inventory.return_value = pd.DataFrame({"product_id": ["P1"], "quantity": [10]})
    mock_client.get_products.return_value = pd.DataFrame({"product_id": ["P1"], "name": ["Prod1"]})
    mock_client.get_losses.return_value = pd.DataFrame({"product_id": ["P1"], "quantity": [0], "date": ["01.03.2026"]})

    result = load_all_data(
        token="token", start_date="01.01.2025", end_date="01.03.2026", data_source="api"
    )

    assert "sales" in result
    assert "inventory" in result
    assert "products" in result
    assert "losses" in result
    assert all(isinstance(v, pd.DataFrame) for v in result.values())


def test_load_all_data_csv_columns_renamed(project_root):
    """load_all_data (csv) normalizes column names to English."""
    result = load_all_data(data_source="csv", data_path=project_root / "data_sample")
    assert "date" in result["sales"].columns
    assert "product_id" in result["sales"].columns
    assert "quantity" in result["sales"].columns
    assert "sku" in result["sales"].columns


def test_load_all_data_csv_datetime_parsed(project_root):
    """load_all_data (csv) parses date columns to datetime."""
    result = load_all_data(data_source="csv", data_path=project_root / "data_sample")
    assert pd.api.types.is_datetime64_any_dtype(result["sales"]["date"])
    if not result["losses"].empty and "date" in result["losses"].columns:
        assert pd.api.types.is_datetime64_any_dtype(result["losses"]["date"])


def test_load_all_data_csv_sku_unified(project_root):
    """load_all_data (csv) unifies SKU field across tables."""
    result = load_all_data(data_source="csv", data_path=project_root / "data_sample")
    assert "sku" in result["sales"].columns
    assert "sku" in result["inventory"].columns
    assert "sku" in result["products"].columns
    assert "sku" in result["losses"].columns


@patch("src.pipeline.ingestion.ForecastoClient")
def test_load_all_data_api_duplicates_removed(mock_client_class):
    """load_all_data (api) removes duplicate rows."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    dup_sales = pd.DataFrame({
        "date": ["01.01.2025", "01.01.2025"],
        "product_id": ["P1", "P1"],
        "quantity": [1, 1],
    })
    mock_client.get_sales.return_value = dup_sales
    mock_client.get_inventory.return_value = pd.DataFrame({"product_id": ["P1"], "quantity": [10]})
    mock_client.get_products.return_value = pd.DataFrame({"product_id": ["P1"], "name": ["Prod1"]})
    mock_client.get_losses.return_value = pd.DataFrame({"product_id": ["P1"], "quantity": [0], "date": ["01.03.2026"]})

    result = load_all_data(
        token="token", start_date="01.01.2025", end_date="01.03.2026", data_source="api"
    )

    assert len(result["sales"]) == 1
