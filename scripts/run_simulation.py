#!/usr/bin/env python3
"""Run inventory sim demo."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.inventory.simulation import InventorySimulator, SimulationReport
from src.policy.rules import OrderPolicy, PolicyMode


def main() -> None:
    # 14 days of demand (realistic retail pattern)
    demand_ts = [
        ("2024-01-01", 20),
        ("2024-01-02", 25),
        ("2024-01-03", 18),
        ("2024-01-04", 30),
        ("2024-01-05", 22),
        ("2024-01-06", 28),
        ("2024-01-07", 15),
        ("2024-01-08", 35),
        ("2024-01-09", 40),
        ("2024-01-10", 25),
        ("2024-01-11", 30),
        ("2024-01-12", 22),
        ("2024-01-13", 28),
        ("2024-01-14", 20),
    ]

    # Forecast: constant 25/day (simplified ML forecast)
    forecast = 25.0

    # Initial conditions
    initial_stock = 50
    expiration_days = 7

    print("Inventory Simulation (Balanced Policy)")
    print("=" * 50)
    print(f"Demand: 14 days, total={sum(d for _, d in demand_ts)}")
    print(f"Forecast: {forecast}/day")
    print(f"Initial stock: {initial_stock}")
    print(f"Expiration: {expiration_days} days")
    print()

    parser = argparse.ArgumentParser()
    parser.add_argument("--plot", "-p", action="store_true", help="Save visualization plots")
    parser.add_argument("--output", "-o", default="outputs/figures", help="Output directory for plots")
    args = parser.parse_args()

    policy = OrderPolicy(policy_mode=PolicyMode.BALANCED)
    sim = InventorySimulator(
        demand_ts=demand_ts,
        forecast_demand=forecast,
        initial_stock=initial_stock,
        expiration_days=expiration_days,
        policy=policy,
        lead_time_days=0,
    )

    report = sim.simulate()

    if args.plot:
        from src.evaluation.visualization import plot_inventory_levels, plot_stockouts_vs_waste
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=True)
        plot_inventory_levels(report.time_series, save_path=out / "inventory_levels.png")
        plot_stockouts_vs_waste(report.time_series, save_path=out / "stockouts_vs_waste.png")
        print(f"Plots saved to {out}")

    print("Metrics:")
    for k, v in report.metrics.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}")
        else:
            print(f"  {k}: {v}")

    print("\nTime series (first 5 days):")
    print(report.time_series.head().to_string(index=False))

    print("\nTime series (last 5 days):")
    print(report.time_series.tail().to_string(index=False))


if __name__ == "__main__":
    main()
