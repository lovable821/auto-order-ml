"""
Forecast pipeline - load data, call ForecastAPI for real forecasts.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from src.pipeline.ingestion import load_all_data, load_all_data_from_csv
from src.api.forecastapi_client import ForecastAPIClient, get_forecast_token

logger = logging.getLogger(__name__)


def _sales_to_forecast_format(sales: pd.DataFrame, sku_col: str = "sku") -> dict[str, list[dict]]:
    """Aggregate sales by product into ForecastAPI format {identifier: [{date, value}, ...]}."""
    if sales.empty:
        return {}
    sku_col = sku_col if sku_col in sales.columns else "product_id"
    if sku_col not in sales.columns:
        return {}
    if "date" not in sales.columns:
        return {}

    sales = sales.copy()
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    sales = sales.dropna(subset=["date"])
    sales["date"] = sales["date"].dt.strftime("%Y-%m-%d")

    value_col = "quantity" if "quantity" in sales.columns else "amount"
    if value_col not in sales.columns:
        return {}

    grouped = sales.groupby([sku_col, "date"])[value_col].sum().reset_index()
    grouped = grouped.rename(columns={value_col: "value"})

    by_product: dict[str, list[dict]] = {}
    for sku, g in grouped.groupby(sku_col):
        by_product[sku] = g[["date", "value"]].to_dict("records")
    return by_product


def run_forecast_pipeline(
    data_path: str | Path | None = None,
    periods: int = 6,
    frequency: str = "M",
    token: str | None = None,
    data_source: str = "api",
    start_date: str = "",
    end_date: str = "",
) -> dict[str, Any]:
    """
    Run full pipeline: load data (API or CSV) -> ForecastAPI (real) -> return forecasts.

    Args:
        data_path: Path to CSV directory (when data_source="csv"). Default: data_sample/
        periods: Forecast periods to request.
        frequency: D, W, M, Q, Y.
        token: API token. Loads from .env if None.
        data_source: "api" (api.forecasto.ru) or "csv".
        start_date: Start date for API (e.g. "01.01.2025").
        end_date: End date for API (e.g. "01.03.2026").

    Returns:
        Dict with product forecasts from ForecastAPI.
    """
    if data_source == "api":
        try:
            data = load_all_data(
                token=token,
                start_date=start_date or "01.01.2024",
                end_date=end_date or "31.12.2024",
                data_source="api",
            )
        except (ValueError, Exception) as e:
            logger.warning("API load failed (%s), falling back to CSV", e)
            root = Path(__file__).resolve().parent.parent.parent
            path = Path(data_path) if data_path else root / "data_sample"
            data = load_all_data_from_csv(path)
    else:
        root = Path(__file__).resolve().parent.parent.parent
        path = Path(data_path) if data_path else root / "data_sample"
        if not path.exists():
            path = root / "data"
        data = load_all_data_from_csv(path)
    sales = data["sales"]

    if sales.empty:
        logger.warning("No sales data found")
        return {}

    by_product = _sales_to_forecast_format(sales)
    if not by_product:
        logger.warning("Could not aggregate sales by product")
        return {}

    client = ForecastAPIClient(token=token or get_forecast_token())
    results: dict[str, Any] = {}

    for sku, series in by_product.items():
        if len(series) < 3:
            logger.debug("Skipping %s: need at least 3 data points", sku)
            continue
        try:
            result = client.get_forecast(
                identifier=sku,
                data=series,
                periods=periods,
                frequency=frequency,
                data_type="sales",
            )
            results[sku] = result
        except Exception as e:
            logger.error("Forecast failed for %s: %s", sku, e)

    return results
