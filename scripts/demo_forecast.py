#!/usr/bin/env python3
"""
Demo: Get real forecasts from ForecastAPI using token from .env.

Uses sample sales data, sends to ForecastAPI, prints forecast results.
Run: python scripts/demo_forecast.py
"""

import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.forecastapi_client import ForecastAPIClient, get_forecast_token


def sample_sales_data() -> list[dict]:
    """Sample time series for demo (monthly sales). Use YYYY-MM-DD format."""
    return [
        {"date": "2024-01-01", "value": 120},
        {"date": "2024-02-01", "value": 135},
        {"date": "2024-03-01", "value": 155},
        {"date": "2024-04-01", "value": 142},
        {"date": "2024-05-01", "value": 168},
        {"date": "2024-06-01", "value": 175},
        {"date": "2024-07-01", "value": 181},
        {"date": "2024-08-01", "value": 192},
        {"date": "2024-09-01", "value": 178},
        {"date": "2024-10-01", "value": 195},
        {"date": "2024-11-01", "value": 210},
        {"date": "2024-12-01", "value": 225},
    ]


def main() -> int:
    print("ForecastAPI Demo - Real forecast from forecastapi.com\n")

    try:
        token = get_forecast_token()
        print(f"Token loaded from .env ({len(token)} chars)\n")
    except ValueError as e:
        print(f"Error: {e}")
        print("Add FORECAST_API_TOKEN or Authorization=Bearer <token> to .env")
        return 1

    client = ForecastAPIClient(token=token)
    data = sample_sales_data()

    print("Sending sample sales data to ForecastAPI...")
    print(f"  Identifier: SKU-DEMO-001")
    print(f"  Data points: {len(data)}")
    print(f"  Requesting: 6 forecast periods (monthly)\n")

    try:
        result = client.get_forecast(
            identifier="SKU-DEMO-001",
            data=data,
            periods=6,
            frequency="M",
            data_type="sales",
        )
    except Exception as e:
        print(f"API Error: {e}")
        if hasattr(e, "response") and e.response:
            r = str(e.response)
            print(f"Response: {r[:500]}..." if len(r) > 500 else f"Response: {r}")
        return 1

    print("=" * 50)
    print("Forecast Results (from ForecastAPI)")
    print("=" * 50)

    # Support API response formats: result.forecasts or result.forecast_values
    res = result.get("result") or {}
    forecast = result.get("forecast", [])
    if isinstance(res, dict) and not forecast:
        # Format: result.forecasts = [{period, forecast, date, lower, upper}]
        items = res.get("forecasts", [])
        if items:
            forecast = [
                {
                    "date": r.get("date"),
                    "value": r.get("forecast", r.get("value")),
                    "lower": r.get("lower"),
                    "upper": r.get("upper"),
                }
                for r in items
            ]
        # Fallback: forecast_dates + forecast_values
        if not forecast:
            dates = res.get("forecast_dates", [])
            values = res.get("forecast_values", [])
            forecast = [{"date": d, "value": v} for d, v in zip(dates, values)]

    print("Forecast:")
    for row in forecast:
        val = row.get("value", row.get("forecast", 0))
        lo = row.get("lower", "N/A")
        hi = row.get("upper", "N/A")
        dt = row.get("date", "N/A")
        print(f"  {dt}: {val:.1f} (range: {lo}-{hi})")

    analysis = result.get("analysis", {})
    if analysis:
        print(f"\nAnalysis: trend={analysis.get('trend', 'N/A')}, seasonality={analysis.get('seasonality', 'N/A')}")

    print("\nDone. Real data from ForecastAPI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
