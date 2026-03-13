#!/usr/bin/env python3
"""
Generate all visualization charts for demand forecasting and inventory simulation.

Usage:
    python scripts/run_visualizations.py
    python scripts/run_visualizations.py --output outputs/figures
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.visualization import plot_all_summary
from src.pipeline.orchestrator import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate visualization charts")
    parser.add_argument("--output", "-o", default="outputs/figures", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Saving figures to {output_dir}")

    # Run pipeline for forecast + simulation
    config_path = str(PROJECT_ROOT / "configs" / "default.yaml")
    ctx = run_pipeline(config_path=config_path)
    part_a_result = {
        "test_actual": ctx.test_actual,
        "test_predictions": ctx.test_predictions,
    } if ctx.test_actual is not None else None

    simulation_report = ctx.simulation_report

    # Generate all plots
    saved = plot_all_summary(
        part_a_result=part_a_result,
        simulation_report=simulation_report,
        output_dir=output_dir,
    )

    print(f"Saved {len(saved)} figures:")
    for p in saved:
        print(f"  {p}")


if __name__ == "__main__":
    main()
