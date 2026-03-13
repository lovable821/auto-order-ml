#!/usr/bin/env python3
"""CLI: full pipeline, --api, --train, --part-a, --part-b, --simulate, --visualize."""

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
        help="Run model training pipeline only (through forecast)",
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
        "--policy",
        type=str,
        choices=["service_first", "waste_first", "balanced"],
        default="balanced",
        help="Part C policy mode: service_first (min OOS), waste_first (min waste), balanced",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run inventory simulation demo",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate all visualization charts (Part A + simulation)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Path to configuration file",
    )
    return parser.parse_args()


def _setup_logging(config_path: str) -> None:
    """Configure structured logging from config."""
    from src.config.logging_config import setup_logging

    try:
        import yaml
        path = Path(config_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        with open(path) as f:
            cfg = yaml.safe_load(f) or {}
        log_cfg = cfg.get("logging", {})
        setup_logging(
            level=log_cfg.get("level", "INFO"),
            log_file=log_cfg.get("log_file"),
        )
    except Exception:
        setup_logging(level="INFO")


def run_full_pipeline(config_path: str) -> int:
    """Run full pipeline: ingestion through simulation."""
    from src.pipeline.orchestrator import run_pipeline

    config_full_path = str(PROJECT_ROOT / config_path)
    ctx = run_pipeline(config_path=config_full_path)

    # Print summary
    if ctx.model is not None:
        print("\n[Pipeline] Model trained successfully")
        if ctx.metrics:
            print(f"  WAPE: {ctx.metrics.get('wape', 0):.4f}")
            print(f"  Bias: {ctx.metrics.get('bias', 0):.4f}")

    if ctx.forecasts is not None and not ctx.forecasts.empty:
        print("\n[Pipeline] Tomorrow's predicted demand:")
        print(ctx.forecasts.to_string(index=False))

    if ctx.orders is not None and not ctx.orders.empty:
        print("\n[Pipeline] Recommended order quantities:")
        print(ctx.orders.to_string(index=False))

    if ctx.simulation_report is not None:
        print("\n[Pipeline] Simulation metrics:")
        for k, v in ctx.simulation_report.metrics.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.2f}")
            else:
                print(f"  {k}: {v}")

    print("\n[Pipeline] Done.")
    return 0


def run_api(config_path: str) -> int:
    """Start the REST API server."""
    print(f"[API] Starting server with config: {config_path}")
    print("[API] Use: uvicorn src.api.app:app --reload")
    return 0


def run_train(config_path: str) -> int:
    """Run model training only (pipeline through forecast generation)."""
    from src.pipeline.orchestrator import run_pipeline

    config_full_path = str(PROJECT_ROOT / config_path)
    ctx = run_pipeline(config_path=config_full_path)

    if ctx.model is None:
        print("[Train] No model trained (insufficient data)")
        return 1

    print(f"[Train] WAPE: {ctx.metrics.get('wape', 0):.4f}")
    print(f"[Train] Bias: {ctx.metrics.get('bias', 0):.4f}")
    print("[Train] Done.")
    return 0


def run_part_a_cli(config_path: str) -> int:
    """Run Part A: demand forecast for tomorrow."""
    from src.pipeline.orchestrator import run_pipeline

    config_full_path = str(PROJECT_ROOT / config_path)
    ctx = run_pipeline(config_path=config_full_path)

    if ctx.model is None:
        print("[Part A] No model trained (insufficient data)")
        return 1

    print(f"[Part A] WAPE: {ctx.metrics.get('wape', 0):.4f}")
    print(f"[Part A] Bias: {ctx.metrics.get('bias', 0):.4f}")
    print("\n[Part A] Tomorrow's predicted demand:")
    print(ctx.forecasts.to_string(index=False))
    return 0


def run_part_b_cli(config_path: str, policy_mode: str = "balanced") -> int:
    """Run Part B: order quantity for tomorrow."""
    from src.pipeline.orchestrator import run_pipeline

    config_full_path = str(PROJECT_ROOT / config_path)
    ctx = run_pipeline(
        config_path=config_full_path,
        config_overrides={"policy": {"policy_mode": policy_mode}},
    )

    if ctx.orders is None or ctx.orders.empty:
        print("[Part B] No orders (no forecasts)")
        return 1

    print("\n[Part B] Recommended order quantities:")
    print(ctx.orders.to_string(index=False))
    return 0


def run_simulation_cli() -> int:
    """Run inventory simulation demo."""
    import sys

    orig_argv = sys.argv.copy()
    sys.argv = [orig_argv[0]]  # run_simulation has its own --plot, --output
    try:
        from scripts.run_simulation import main as sim_main
        sim_main()
    finally:
        sys.argv = orig_argv
    return 0


def run_visualize_cli() -> int:
    """Generate all visualization charts."""
    import subprocess

    script = PROJECT_ROOT / "scripts" / "run_visualizations.py"
    subprocess.run([sys.executable, str(script)], check=True)
    return 0


def main() -> int:
    """Main entrypoint."""
    args = parse_args()
    config_path = args.config
    if not Path(config_path).is_absolute():
        config_path = str(PROJECT_ROOT / config_path)

    _setup_logging(config_path)

    if args.api:
        return run_api(config_path)
    if args.train:
        return run_train(config_path)
    if args.part_a:
        return run_part_a_cli(config_path)
    if args.part_b:
        return run_part_b_cli(config_path, policy_mode=args.policy)
    if args.simulate:
        return run_simulation_cli()
    if args.visualize:
        return run_visualize_cli()

    return run_full_pipeline(config_path)


if __name__ == "__main__":
    sys.exit(main())
