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
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Path to configuration file",
    )
    return parser.parse_args()


def run_pipeline(config_path: str) -> None:
    """Execute full pipeline: data -> features -> forecast -> orders."""
    # Placeholder - wire to pipeline module
    print(f"[Pipeline] Running with config: {config_path}")
    print("[Pipeline] 1. Load data")
    print("[Pipeline] 2. Feature engineering")
    print("[Pipeline] 3. Demand forecasting")
    print("[Pipeline] 4. Generate auto-orders")
    print("[Pipeline] Done.")


def run_api(config_path: str) -> None:
    """Start the REST API server."""
    # Placeholder - wire to api module
    print(f"[API] Starting server with config: {config_path}")
    print("[API] Use: uvicorn src.api.app:app --reload")


def run_train(config_path: str) -> None:
    """Run model training only."""
    print(f"[Train] Training models with config: {config_path}")
    print("[Train] Done.")


def main() -> int:
    """Main entrypoint."""
    args = parse_args()
    config_path = str(PROJECT_ROOT / args.config)

    if args.api:
        run_api(config_path)
    elif args.train:
        run_train(config_path)
    else:
        run_pipeline(config_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
