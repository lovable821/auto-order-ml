"""Shared state passed between pipeline stages."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.pipeline.ingestion import IngestedData


@dataclass
class PipelineContext:
    """Holds intermediate results as each stage runs."""

    # Config
    config: dict[str, Any] = field(default_factory=dict)
    data_path: Optional[Path] = None

    # Stage 1: Ingestion
    ingested_data: Optional[IngestedData] = None

    # Stage 2: Cleaning
    sales_cleaned: Optional[pd.DataFrame] = None

    # Stage 3: Features (built on cleaned sales)
    sales_with_features: Optional[pd.DataFrame] = None

    # Stage 4: Censoring (adjustment applied)
    sales_corrected: Optional[pd.DataFrame] = None

    # Stage 5: Training
    model: Any = None
    train_test_split: float = 0.8
    metrics: dict[str, float] = field(default_factory=dict)
    test_actual: Optional[Any] = None
    test_predictions: Optional[Any] = None

    # Stage 6: Forecast
    forecasts: Optional[pd.DataFrame] = None

    # Stage 7: Order optimization
    orders: Optional[pd.DataFrame] = None

    # Stage 8: Policy (loaded from config)
    policy: Any = None

    # Stage 9: Simulation
    simulation_report: Any = None

    # Feature column names (for model)
    feature_columns: list[str] = field(default_factory=list)
