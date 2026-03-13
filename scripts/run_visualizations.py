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
from src.pipeline.part_a_runner import run_part_a
from src.pipeline.data_ingestion_pipeline import DataIngestionConfig
from src.inventory.simulation import InventorySimulator
from src.policy.rules import OrderPolicy, PolicyMode


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate visualization charts")
    parser.add_argument("--output", "-o", default="outputs/figures", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Saving figures to {output_dir}")

    # Part A: demand forecast
    cfg = DataIngestionConfig(data_source="csv", data_path=PROJECT_ROOT / "data_sample")
    part_a_result = run_part_a(config=cfg)

    # Simulation
    demand_ts = [
        ("2024-01-01", 20), ("2024-01-02", 25), ("2024-01-03", 18), ("2024-01-04", 30),
        ("2024-01-05", 22), ("2024-01-06", 28), ("2024-01-07", 15), ("2024-01-08", 35),
        ("2024-01-09", 40), ("2024-01-10", 25), ("2024-01-11", 30), ("2024-01-12", 22),
        ("2024-01-13", 28), ("2024-01-14", 20),
    ]
    sim = InventorySimulator(
        demand_ts=demand_ts,
        forecast_demand=25.0,
        initial_stock=50,
        expiration_days=7,
        policy=OrderPolicy(policy_mode=PolicyMode.BALANCED),
    )
    simulation_report = sim.simulate()

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
