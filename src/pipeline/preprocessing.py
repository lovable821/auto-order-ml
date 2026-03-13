"""
Cleaning and preprocessing for demand forecasting.

Part A Step 2: Handles censoring, outliers, missing values.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def handle_demand_censoring(
    df: pd.DataFrame,
    inventory: pd.DataFrame,
    demand_col: str = "demand",
    sku_col: str = "sku",
    date_col: str = "date",
    store_col: str = "store_id",
) -> pd.DataFrame:
    """
    Flag demand censoring when stock was zero (stockouts).

    When balance=0, observed sales <= true demand. Adds 'censored' column.
    """
    if df.empty or inventory.empty:
        return df

    df = df.copy()
    inv = inventory.copy()
    inv["date"] = pd.to_datetime(inv.get("date", inv.get("Date")), errors="coerce")

    inv_sku = "code" if "code" in inv.columns else "sku" if "sku" in inv.columns else "product_id"
    inv_balance = "balance" if "balance" in inv.columns else "quantity"

    if inv_sku not in inv.columns or inv_balance not in inv.columns:
        logger.warning("Inventory missing code/balance, skipping censoring")
        df["censored"] = False
        return df

    inv_agg = inv.groupby([inv_sku, "date"])[inv_balance].sum().reset_index()
    inv_agg = inv_agg.rename(columns={inv_sku: sku_col})
    inv_agg["was_stockout"] = inv_agg[inv_balance] <= 0

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    inv_agg = inv_agg.rename(columns={"date": date_col})
    df = df.merge(
        inv_agg[[sku_col, date_col, "was_stockout"]],
        on=[sku_col, date_col],
        how="left",
    )
    df["censored"] = df["was_stockout"].fillna(False)
    df = df.drop(columns=["was_stockout"], errors="ignore")
    return df


def remove_outliers(
    df: pd.DataFrame,
    demand_col: str = "demand",
    method: str = "iqr",
    factor: float = 1.5,
) -> pd.DataFrame:
    """
    Remove or cap outliers in demand.

    method: "iqr" (interquartile range) or "zscore"
    """
    if df.empty or demand_col not in df.columns:
        return df

    df = df.copy()
    q = df[demand_col].quantile([0.25, 0.75])
    q1, q3 = q.iloc[0], q.iloc[1]
    iqr = q3 - q1

    if method == "iqr":
        low = q1 - factor * iqr
        high = q3 + factor * iqr
    else:  # zscore
        mean = df[demand_col].mean()
        std = df[demand_col].std()
        if std == 0:
            return df
        low = mean - factor * std
        high = mean + factor * std

    before = len(df)
    df = df[(df[demand_col] >= low) & (df[demand_col] <= high)]
    removed = before - len(df)
    if removed > 0:
        logger.info("Removed %d outlier rows (method=%s)", removed, method)
    return df


def fill_missing_dates(
    df: pd.DataFrame,
    sku_col: str = "sku",
    date_col: str = "date",
    demand_col: str = "demand",
    store_col: Optional[str] = "store_id",
    fill_value: float = 0,
) -> pd.DataFrame:
    """
    Fill missing (store, sku, date) combinations with fill_value (e.g. 0 for no sale).
    """
    if df.empty:
        return df

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    min_date = df[date_col].min()
    max_date = df[date_col].max()
    all_dates = pd.date_range(min_date, max_date, freq="D")

    group_cols = [c for c in [store_col, sku_col] if c and c in df.columns]
    if not group_cols:
        group_cols = [sku_col]

    groups = df[group_cols].drop_duplicates()
    full = groups.merge(
        pd.DataFrame({date_col: all_dates}),
        how="cross",
    )
    out = full.merge(
        df[[*group_cols, date_col, demand_col]],
        on=group_cols + [date_col],
        how="left",
    )
    out[demand_col] = out[demand_col].fillna(fill_value)
    return out


def preprocess_sales(
    df: pd.DataFrame,
    inventory: Optional[pd.DataFrame] = None,
    handle_censoring: bool = True,
    remove_outliers_flag: bool = True,
    fill_missing: bool = False,
) -> pd.DataFrame:
    """
    Full preprocessing pipeline for sales/demand data.

    Args:
        df: Sales with store_id, sku, date, demand.
        inventory: Optional inventory for censoring.
        handle_censoring: Add censored flag from stockouts.
        remove_outliers_flag: Remove IQR outliers.
        fill_missing: Fill missing dates with 0.
    """
    if df.empty:
        return df

    out = df.copy()

    if handle_censoring and inventory is not None and not inventory.empty:
        out = handle_demand_censoring(out, inventory)

    if remove_outliers_flag:
        out = remove_outliers(out)

    if fill_missing:
        out = fill_missing_dates(out)

    return out
