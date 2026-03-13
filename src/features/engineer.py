"""Feature engineering - build features for demand forecasting."""

import pandas as pd
from typing import List


def build_features(
    df: pd.DataFrame,
    lookback_days: int = 30,
    target_column: str = "demand",
    categorical_cols: List[str] | None = None,
) -> pd.DataFrame:
    """Build forecasting features from raw data."""
    categorical_cols = categorical_cols or []
    # Placeholder - implement rolling stats, lags, etc.
    return df
