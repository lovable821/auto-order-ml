"""Stage 1: load data."""

import logging
from pathlib import Path
from typing import Any

from src.pipeline.context import PipelineContext
from src.pipeline.data_ingestion_pipeline import DataIngestionConfig, DataIngestionPipeline
from src.pipeline.ingestion import IngestedData

logger = logging.getLogger(__name__)


def run_ingestion_stage(ctx: PipelineContext) -> PipelineContext:
    """Load data from API or CSV, put in ctx.ingested_data."""
    cfg = _build_ingestion_config(ctx)
    pipeline = DataIngestionPipeline(cfg)
    data = pipeline.run()
    ctx.ingested_data = data
    logger.info(
        "Ingestion complete: sales=%d rows, inventory=%d, products=%d, losses=%d",
        len(data["sales"]),
        len(data["inventory"]),
        len(data["products"]),
        len(data["losses"]),
    )
    return ctx


def _build_ingestion_config(ctx: PipelineContext) -> DataIngestionConfig:
    """Config from ctx, resolve data path."""
    cfg = ctx.config
    # Project root: stages -> pipeline -> src -> project
    root = Path(__file__).resolve().parent.parent.parent.parent
    pipeline_cfg = cfg.get("pipeline") or {}
    data_path = pipeline_cfg.get("data_path")
    if not data_path or not (root / str(data_path)).exists():
        data_path = str(root / "data_sample")
    merged = dict(cfg)
    merged["pipeline"] = {**pipeline_cfg, "data_path": data_path}
    return DataIngestionConfig.from_dict(merged)
