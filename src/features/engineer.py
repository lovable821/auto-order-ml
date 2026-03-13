"""Lags, rolling mean/std, calendar features for store×SKU demand."""

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def build_features(
    df: pd.DataFrame,
    lookback_days: int = 30,
    target_column: str = "demand",
    sku_col: str = "sku",
    date_col: str = "date",
    store_col: Optional[str] = "store_id",
    lag_days: tuple[int, ...] = (1, 7, 14),
    rolling_windows: tuple[int, ...] = (7, 14),
) -> pd.DataFrame:
    """Lags, rolling mean/std, day_of_week, month, etc."""
    if df.empty:
        return df

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values([store_col or sku_col, sku_col, date_col])

    group_cols = [c for c in [store_col, sku_col] if c and c in df.columns]
    if not group_cols:
        group_cols = [sku_col]

    # Lag features
    for lag in lag_days:
        df[f"lag_{lag}"] = df.groupby(group_cols)[target_column].shift(lag)

    # Rolling stats
    for w in rolling_windows:
        df[f"rolling_mean_{w}"] = (
            df.groupby(group_cols)[target_column]
            .transform(lambda x: x.shift(1).rolling(w, min_periods=1).mean())
        )
        df[f"rolling_std_{w}"] = (
            df.groupby(group_cols)[target_column]
            .transform(lambda x: x.shift(1).rolling(w, min_periods=1).std())
        )

    # Calendar features
    df["day_of_week"] = df[date_col].dt.dayofweek
    df["month"] = df[date_col].dt.month
    df["day_of_month"] = df[date_col].dt.day
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    return df


def get_feature_columns(
    lag_days: tuple[int, ...] = (1, 7, 14),
    rolling_windows: tuple[int, ...] = (7, 14),
) -> list[str]:
    """Column names for model (must match build_features output)."""
    features = []
    for lag in lag_days:
        features.append(f"lag_{lag}")
    for w in rolling_windows:
        features.extend([f"rolling_mean_{w}", f"rolling_std_{w}"])
    features.extend(["day_of_week", "month", "day_of_month", "is_weekend"])
    return features
