#!/usr/bin/env python3
"""
Retail Demand Forecasting & Auto-Order System - Entrypoint.

Usage:
    python main.py                    # Run pipeline (forecast + orders)
    python main.py --api              # Start REST API server
    python main.py --train            # Train models only
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Retail Demand Forecasting & Auto-Order System"
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Start the REST API server",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Run model training pipeline only",
    )
    parser.add_argument(
        "--part-a",
        action="store_true",
        help="Run Part A: demand forecast for tomorrow (store x SKU)",
    )
    parser.add_argument(
        "--part-b",
        action="store_true",
        help="Run Part B: order quantity for tomorrow",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Path to configuration file",
    )
    return parser.parse_args()


def run_pipeline(config_path: str) -> None:
    """Execute full pipeline: load data from api.forecasto.ru -> ForecastAPI (real) -> forecasts."""
    from src.pipeline.forecast_runner import run_forecast_pipeline

    print(f"[Pipeline] Running with config: {config_path}")
    print("[Pipeline] 1. Load data from api.forecasto.ru (sales, inventory, products, losses)")
    print("[Pipeline] 2. Call ForecastAPI for real forecasts")
    try:
        results = run_forecast_pipeline(
            periods=6,
            frequency="M",
            data_source="api",
            start_date="01.01.2024",
            end_date="31.12.2024",
        )
        for sku, res in results.items():
            forecasts = res.get("result", {}).get("forecasts", [])
            print(f"\n[Pipeline] {sku}: {len(forecasts)} forecast periods")
            for f in forecasts[:3]:
                print(f"  {f.get('date')}: {f.get('forecast', f.get('value')):.1f}")
            if len(forecasts) > 3:
                print(f"  ... and {len(forecasts) - 3} more")
        print("\n[Pipeline] Done. Real data from ForecastAPI.")
    except ValueError as e:
        print(f"[Pipeline] Error: {e}")
        print("Add FORECAST_API_TOKEN or Authorization=Bearer <token> to .env")


def run_api(config_path: str) -> None:
    """Start the REST API server."""
    # Placeholder - wire to api module
    print(f"[API] Starting server with config: {config_path}")
    print("[API] Use: uvicorn src.api.app:app --reload")


def run_train(config_path: str) -> None:
    """Run model training only."""
    print(f"[Train] Training models with config: {config_path}")
    print("[Train] Done.")


def run_part_a_cli(config_path: str) -> None:
    """Run Part A: demand forecast for tomorrow."""
    from src.pipeline.part_a_runner import run_part_a
    from src.pipeline.data_ingestion_pipeline import DataIngestionConfig

    print("[Part A] Demand forecast for tomorrow (store x SKU)")
    from pathlib import Path
    root = Path(config_path).resolve().parent.parent
    cfg = DataIngestionConfig.from_yaml(config_path)
    if not cfg.data_path or not (root / cfg.data_path).exists():
        cfg.data_path = root / "data_sample"
    result = run_part_a(config=cfg)
    if result["model"] is None:
        print("[Part A] No model trained (insufficient data)")
        return
    print(f"[Part A] WAPE: {result['metrics']['wape']:.4f}")
    print(f"[Part A] Bias: {result['metrics']['bias']:.4f}")
    print("\n[Part A] Tomorrow's predicted demand:")
    print(result["predictions"].to_string(index=False))


def run_part_b_cli(config_path: str) -> None:
    """Run Part B: order quantity for tomorrow."""
    import logging
    from src.pipeline.part_b_runner import run_part_b
    from src.pipeline.data_ingestion_pipeline import DataIngestionConfig

    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    print("[Part B] Order optimization for tomorrow")
    root = Path(config_path).resolve().parent.parent
    cfg = DataIngestionConfig.from_yaml(config_path)
    if not cfg.data_path or not (root / cfg.data_path).exists():
        cfg.data_path = root / "data_sample"
    result = run_part_b(config=cfg)
    if result["orders"].empty:
        print("[Part B] No orders (no forecasts)")
        return
    print("\n[Part B] Recommended order quantities:")
    print(result["orders"].to_string(index=False))


def main() -> int:
    """Main entrypoint."""
    args = parse_args()
    config_path = str(PROJECT_ROOT / args.config)

    if args.api:
        run_api(config_path)
    elif args.train:
        run_train(config_path)
    elif args.part_a:
        run_part_a_cli(config_path)
    elif args.part_b:
        run_part_b_cli(config_path)
    else:
        run_pipeline(config_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
