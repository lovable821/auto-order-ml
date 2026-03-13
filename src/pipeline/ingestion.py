"""
Data ingestion module - load and clean data from CSV or API.

Loads data via CSV files or ForecastoClient, normalizes column names to English,
parses dates, unifies SKU field, and removes duplicates.
Uses ForecastAPIClient (forecastapi.com) for real forecasts.
"""

import logging
from pathlib import Path
from typing import TypedDict

import pandas as pd

from src.api.forecasto_client import ForecastoClient

logger = logging.getLogger(__name__)

# Column name mappings: non-English / variant -> English
# Forecasto API (api.forecasto.ru) Russian fields included
COLUMN_MAPPINGS: dict[str, str] = {
    # Date
    "datum": "date",
    "dat": "date",
    "дата": "date",
    "data": "date",
    "период": "date",
    "period": "date",
    # Product identifier / SKU
    "produkt_id": "product_id",
    "artikelnummer": "product_id",
    "art_id": "product_id",
    "artikel": "product_id",
    "artnr": "product_id",
    "код": "product_id",
    "code": "product_id",
    # Product name
    "produktname": "name",
    "название": "name",
    "номенклатура": "name",
    # Quantity
    "menge": "quantity",
    "qty": "quantity",
    "количество": "quantity",
    "balance": "quantity",
    # Amount / Revenue
    "betrag": "amount",
    "sum": "amount",
    "сумма": "amount",
    "revenue": "amount",
    "totalloss": "amount",
    # Category / Product group
    "kategorie": "category",
    "категория": "category",
    "группа": "category",
    "product_group": "category",
    # SKU (unified)
    "sku": "sku",
    # Warehouse
    "lager_id": "warehouse_id",
    # Reason (losses)
    "grund": "reason",
    "причина": "reason",
    "reason": "reason",
    # Loss quantity
    "loss": "quantity",
    # Product properties
    "expirationdays": "expiration_days",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to English using mapping."""
    if df.empty:
        return df
    rename = {}
    for col in df.columns:
        col_lower = str(col).strip().lower().replace(" ", "_")
        if col_lower in COLUMN_MAPPINGS:
            rename[col] = COLUMN_MAPPINGS[col_lower]
        else:
            # Normalize to snake_case (lowercase, spaces -> underscores)
            normalized = col_lower
            if normalized and col != normalized:
                rename[col] = normalized
    result = df.rename(columns=rename) if rename else df
    # Ensure all columns lowercase
    result.columns = [str(c).lower().replace(" ", "_") for c in result.columns]
    return result


def _parse_dates(df: pd.DataFrame, date_columns: list[str]) -> pd.DataFrame:
    """Convert date columns to datetime."""
    if df.empty:
        return df
    for col in date_columns:
        if col in df.columns:
            try:
                df = df.copy()
                df[col] = pd.to_datetime(df[col], format="mixed", errors="coerce")
            except Exception as e:
                logger.warning("Failed to parse column %s as datetime: %s", col, e)
    return df


def _unify_sku(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """
    Unify SKU field across tables.
    Ensures 'sku' column exists; uses product_id if sku is missing.
    """
    if df.empty:
        return df
    df = df.copy()
    if "sku" not in df.columns and "product_id" in df.columns:
        df["sku"] = df["product_id"].astype(str)
        logger.debug("%s: created sku from product_id", table)
    elif "product_id" not in df.columns and "sku" in df.columns:
        df["product_id"] = df["sku"]
        logger.debug("%s: created product_id from sku", table)
    elif "sku" not in df.columns and "product_id" not in df.columns:
        logger.warning("%s: no sku or product_id column found", table)
    else:
        # Both exist - ensure sku is string, fill missing from product_id
        df["sku"] = df["sku"].fillna(df.get("product_id")).astype(str)
    return df


def _remove_duplicates(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """Remove duplicate rows."""
    if df.empty:
        return df
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    if removed > 0:
        logger.info("%s: removed %d duplicate rows", table, removed)
    return df


def _clean_sales(df: pd.DataFrame) -> pd.DataFrame:
    """Clean sales DataFrame."""
    df = _normalize_columns(df)
    df = _parse_dates(df, ["date"])
    df = _unify_sku(df, "sales")
    df = _remove_duplicates(df, "sales")
    return df


def _clean_inventory(df: pd.DataFrame) -> pd.DataFrame:
    """Clean inventory DataFrame."""
    df = _normalize_columns(df)
    df = _unify_sku(df, "inventory")
    df = _remove_duplicates(df, "inventory")
    return df


def _clean_products(df: pd.DataFrame) -> pd.DataFrame:
    """Clean products DataFrame. Unify sku/product_id."""
    df = _normalize_columns(df)
    # Products: product_id or artikelnummer may be the SKU
    if "product_id" in df.columns and "sku" not in df.columns:
        df["sku"] = df["product_id"].astype(str)
    elif "sku" in df.columns and "product_id" not in df.columns:
        df["product_id"] = df["sku"]
    else:
        df = _unify_sku(df, "products")
    df = _remove_duplicates(df, "products")
    return df


def _clean_losses(df: pd.DataFrame) -> pd.DataFrame:
    """Clean losses DataFrame."""
    df = _normalize_columns(df)
    df = _parse_dates(df, ["date"])
    df = _unify_sku(df, "losses")
    df = _remove_duplicates(df, "losses")
    return df


class IngestedData(TypedDict):
    """Typed dict for load_all_data return value."""

    sales: pd.DataFrame
    inventory: pd.DataFrame
    products: pd.DataFrame
    losses: pd.DataFrame


def load_all_data_from_csv(data_path: str | Path) -> IngestedData:
    """
    Load and clean all data from CSV files.

    Expects: sales.csv, inventory.csv, products.csv, losses.csv in data_path.

    Args:
        data_path: Directory containing CSV files.

    Returns:
        Dict with keys: sales, inventory, products, losses.
    """
    path = Path(data_path)
    logger.info("Loading data from CSV: %s", path)

    def _read_csv(name: str, default_cols: list[str]) -> pd.DataFrame:
        f = path / name
        if not f.exists():
            logger.warning("File not found: %s, returning empty DataFrame", f)
            return pd.DataFrame(columns=default_cols)
        return pd.read_csv(f)

    sales_raw = _read_csv("sales.csv", ["date", "product_id", "quantity", "amount"])
    inventory_raw = _read_csv("inventory.csv", ["product_id", "quantity", "warehouse_id"])
    products_raw = _read_csv("products.csv", ["product_id", "name", "category", "sku"])
    losses_raw = _read_csv("losses.csv", ["product_id", "quantity", "reason", "date"])

    return IngestedData(
        sales=_clean_sales(sales_raw),
        inventory=_clean_inventory(inventory_raw),
        products=_clean_products(products_raw),
        losses=_clean_losses(losses_raw),
    )


def load_all_data(
    token: str | None = None,
    start_date: str = "",
    end_date: str = "",
    *,
    base_url: str | None = None,
    data_source: str = "csv",
    data_path: str | Path | None = None,
) -> IngestedData:
    """
    Load and clean all data from CSV or Forecasto API.

    Args:
        token: API token (required when data_source="api"). Loads from .env when None.
        start_date: Start date for sales (required when data_source="api").
        end_date: End date for sales (required when data_source="api").
        base_url: Optional API base URL override.
        data_source: "csv" (default) or "api".
        data_path: Path to CSV directory. Default: data_sample/ or data/.

    Returns:
        Dict with keys: sales, inventory, products, losses.
    """
    if data_source == "csv":
        root = Path(__file__).resolve().parent.parent.parent
        path = Path(data_path) if data_path else root / "data_sample"
        if not path.exists():
            path = root / "data"
        return load_all_data_from_csv(path)

    # data_source == "api"
    if not token:
        try:
            from src.api.forecastapi_client import get_forecast_token
            token = get_forecast_token()
        except Exception:
            raise ValueError("Token required for data_source='api'. Set FORECAST_API_TOKEN or AUTHORIZATION in .env")
    if not start_date or not end_date:
        raise ValueError("start_date and end_date required for data_source='api'")

    client_kwargs: dict = {"token": token}
    if base_url is not None:
        client_kwargs["base_url"] = base_url

    client = ForecastoClient(**client_kwargs)
    logger.info("Loading data from API: %s to %s", start_date, end_date)

    sales_raw = client.get_sales(start_date, end_date)
    inventory_raw = client.get_inventory(end_date)
    products_raw = client.get_products()
    losses_raw = client.get_losses(end_date)

    return IngestedData(
        sales=_clean_sales(sales_raw),
        inventory=_clean_inventory(inventory_raw),
        products=_clean_products(products_raw),
        losses=_clean_losses(losses_raw),
    )
