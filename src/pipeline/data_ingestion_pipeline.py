"""Load from API or CSV. Returns sales, inventory, products, losses."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd
import yaml

from src.pipeline.ingestion import (
    IngestedData,
    load_all_data,
    load_all_data_from_csv,
)

logger = logging.getLogger(__name__)


@dataclass
class DataIngestionConfig:
    """data_source, data_path, dates, token."""

    data_source: Literal["api", "csv"] = "csv"
    data_path: str | Path | None = None
    start_date: str = "01.01.2024"
    end_date: str = "31.12.2024"
    token: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "DataIngestionConfig":
        """Load from config dict."""
        pipeline = d.get("pipeline", {})
        return cls(
            data_source=d.get("data_source", "csv"),
            data_path=pipeline.get("data_path"),
            start_date=d.get("start_date", "01.01.2024"),
            end_date=d.get("end_date", "31.12.2024"),
            token=d.get("token"),
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> "DataIngestionConfig":
        """Load from YAML file."""
        with open(path) as f:
            config = yaml.safe_load(f) or {}
        return cls.from_dict(config)


class DataIngestionPipeline:
    """Load from API or CSV. Falls back to CSV if API fails."""

    def __init__(self, config: DataIngestionConfig | None = None):
        self.config = config or DataIngestionConfig()

    def run(self) -> IngestedData:
        """Load and return sales, inventory, products, losses."""
        logger.info("Running data ingestion pipeline (source=%s)", self.config.data_source)

        if self.config.data_source == "api":
            try:
                return load_all_data(
                    token=self.config.token,
                    start_date=self.config.start_date,
                    end_date=self.config.end_date,
                    data_source="api",
                )
            except Exception as e:
                logger.warning("API ingestion failed: %s. Falling back to CSV.", e)
                return self._load_csv()

        return self._load_csv()

    def _load_csv(self) -> IngestedData:
        """Load from CSV."""
        root = Path(__file__).resolve().parent.parent.parent
        path = Path(self.config.data_path) if self.config.data_path else root / "data_sample"
        if not path.exists():
            path = root / "data"
        return load_all_data_from_csv(path)

    def get_sales_for_forecasting(self, data: IngestedData) -> pd.DataFrame:
        """Aggregate by store×sku×date. Uses ALL if no store_id."""
        sales = data["sales"].copy()
        if sales.empty:
            return sales

        # Ensure required columns
        sku_col = "sku" if "sku" in sales.columns else "product_id"
        if sku_col not in sales.columns:
            logger.warning("No SKU column in sales")
            return pd.DataFrame()

        if "store_id" not in sales.columns:
            sales["store_id"] = "ALL"

        qty_col = "quantity" if "quantity" in sales.columns else "amount"
        if qty_col not in sales.columns:
            return pd.DataFrame()

        sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
        sales = sales.dropna(subset=["date", sku_col])

        agg = (
            sales.groupby(["store_id", sku_col, "date"])[qty_col]
            .sum()
            .reset_index()
            .rename(columns={qty_col: "demand", sku_col: "sku"})
        )
        return agg[["store_id", "sku", "date", "demand"]]
