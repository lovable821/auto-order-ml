"""Inventory simulation - FIFO stock, expiration, order policy."""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union

import pandas as pd

from src.inventory.order_optimizer import compute_order_qty
from src.policy.rules import OrderPolicy, PolicyMode


@dataclass
class SimulationReport:
    """Output of an inventory simulation run."""

    metrics: dict[str, float] = field(default_factory=dict)
    time_series: pd.DataFrame = field(default_factory=pd.DataFrame)

    def __repr__(self) -> str:
        lines = ["Simulation Report", "=" * 40]
        for k, v in self.metrics.items():
            lines.append(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
        return "\n".join(lines)


def _to_dataframe(
    demand_ts: Union[pd.DataFrame, list[tuple[Any, float]], dict[Any, float]]
) -> pd.DataFrame:
    """Normalize demand time series to DataFrame with columns [date, demand]."""
    if isinstance(demand_ts, pd.DataFrame):
        df = demand_ts.copy()
        demand_col = next(
            (c for c in df.columns if str(c).lower() in ("demand", "quantity", "qty")),
            df.columns[1] if len(df.columns) > 1 else None,
        )
        date_col = next(
            (c for c in df.columns if str(c).lower() in ("date", "day", "period")),
            df.columns[0] if len(df.columns) > 0 else None,
        )
        if demand_col and date_col:
            return df[[date_col, demand_col]].rename(
                columns={date_col: "date", demand_col: "demand"}
            )
        return df
    if isinstance(demand_ts, dict):
        return pd.DataFrame(list(demand_ts.items()), columns=["date", "demand"])
    if isinstance(demand_ts, list):
        return pd.DataFrame(demand_ts, columns=["date", "demand"])
    raise TypeError("demand_ts must be DataFrame, dict, or list of (date, demand)")


def _get_forecast(
    forecast: Union[float, pd.Series, dict, Callable[[Any], float]],
    date: Any,
) -> float:
    """Resolve forecast for a given date."""
    if callable(forecast):
        return float(forecast(date))
    if isinstance(forecast, (int, float)):
        return float(forecast)
    if isinstance(forecast, (pd.Series, dict)):
        return float(forecast.get(date, forecast.get(str(date), 0.0)))
    return 0.0


class InventorySimulator:
    """
    Simulates inventory behavior over time for a single SKU.

    Uses FIFO consumption and batch-based expiration tracking.
    Orders are computed daily using the ML-driven ordering policy.
    """

    def __init__(
        self,
        demand_ts: Union[pd.DataFrame, list[tuple[Any, float]], dict[Any, float]],
        forecast_demand: Union[float, pd.Series, dict, Callable[[Any], float]],
        initial_stock: float,
        expiration_days: float,
        policy: Optional[OrderPolicy] = None,
        *,
        lead_time_days: int = 0,
    ):
        """
        Initialize the simulator.

        Args:
            demand_ts: Actual demand time series. DataFrame with [date, demand],
                or list of (date, demand), or dict date -> demand.
            forecast_demand: Predicted demand. Constant float, or per-day Series/dict,
                or callable(date) -> float.
            initial_stock: Starting inventory level.
            expiration_days: Shelf life in days. Stock older than this becomes waste.
            policy: Ordering policy (min/max, policy_mode). Default: balanced.
            lead_time_days: Days between order placement and arrival. Default 0.
        """
        self.demand_df = _to_dataframe(demand_ts)
        self.demand_df["date"] = pd.to_datetime(self.demand_df["date"])
        self.demand_df = self.demand_df.sort_values("date").reset_index(drop=True)

        self.forecast_demand = forecast_demand
        self.expiration_days = max(0, float(expiration_days))
        self.policy = policy or OrderPolicy(policy_mode=PolicyMode.BALANCED)
        self.lead_time_days = max(0, lead_time_days)

        # Batches: list of (quantity, days_remaining). FIFO: consume from lowest days_remaining.
        self._batches: list[tuple[float, float]] = []
        if initial_stock > 0:
            self._batches.append((float(initial_stock), self.expiration_days))

        # Pending orders: (arrival_date, quantity)
        self._pending_orders: list[tuple[Any, int]] = []

    def _total_stock(self) -> float:
        """Total stock across all batches."""
        return sum(qty for qty, _ in self._batches)

    def _consume(self, amount: float) -> float:
        """
        Consume amount from stock (FIFO: oldest batches first).
        Returns actual quantity consumed.
        """
        remaining = amount
        new_batches = []
        for qty, days in self._batches:
            if remaining <= 0:
                new_batches.append((qty, days))
                continue
            take = min(qty, remaining)
            remaining -= take
            if qty - take > 0:
                new_batches.append((qty - take, days))
        self._batches = new_batches
        return amount - remaining

    def _age_batches(self) -> float:
        """
        Age all batches by 1 day. Remove expired stock.
        Returns quantity wasted this period.
        """
        waste = 0.0
        new_batches = []
        for qty, days in self._batches:
            days_left = days - 1
            if days_left <= 0:
                waste += qty
            else:
                new_batches.append((qty, days_left))
        self._batches = new_batches
        return waste

    def _run_day(
        self,
        date: Any,
        demand: float,
        forecast: float,
    ) -> dict[str, Any]:
        """
        Execute one day of the simulation.

        Returns dict with: demand, actual_sales, lost_sales, waste, stock_before,
        stock_after, order_placed, order_arrived.
        """
        # 1. Age batches and collect waste
        waste = self._age_batches()

        # 2. Process pending order arrivals
        order_arrived = 0
        still_pending = []
        for arr_date, qty in self._pending_orders:
            if pd.Timestamp(arr_date) <= pd.Timestamp(date):
                order_arrived += qty
            else:
                still_pending.append((arr_date, qty))
        self._pending_orders = still_pending

        if order_arrived > 0:
            self._batches.append((float(order_arrived), self.expiration_days))
            self._batches.sort(key=lambda x: x[1])  # FIFO: oldest first

        stock_before = self._total_stock()

        # 3. Satisfy demand (FIFO)
        actual_sales = self._consume(min(demand, stock_before))
        lost_sales = max(0, demand - actual_sales)

        stock_after = self._total_stock()

        # 4. Compute recommended order (for next period)
        order_placed = compute_order_qty(
            forecast_demand=forecast,
            current_stock=stock_after,
            expiration_days=self.expiration_days,
            min_order=self.policy.min_order_quantity,
            max_order=self.policy.max_order_quantity,
            policy=self.policy,
            policy_mode=self.policy.policy_mode,
        )

        if order_placed > 0 and self.lead_time_days >= 0:
            arr_date = pd.Timestamp(date) + pd.Timedelta(days=self.lead_time_days + 1)
            self._pending_orders.append((arr_date, order_placed))

        return {
            "date": date,
            "demand": demand,
            "actual_sales": actual_sales,
            "lost_sales": lost_sales,
            "waste": waste,
            "stock_before": stock_before,
            "stock_after": stock_after,
            "order_placed": order_placed,
            "order_arrived": order_arrived,
        }

    def simulate(self) -> SimulationReport:
        """
        Run the full simulation over the demand time series.

        Returns:
            SimulationReport with metrics and daily time series.
        """
        rows = []
        for _, row in self.demand_df.iterrows():
            date = row["date"]
            demand = float(row["demand"])
            forecast = _get_forecast(self.forecast_demand, date)
            day_result = self._run_day(date, demand, forecast)
            rows.append(day_result)

        ts = pd.DataFrame(rows)
        metrics = self.calculate_metrics(ts)
        return SimulationReport(metrics=metrics, time_series=ts)

    def calculate_metrics(self, time_series: pd.DataFrame) -> dict[str, float]:
        """
        Compute simulation metrics from the time series.

        Metrics:
            - total_sales: Sum of actual sales
            - lost_sales: Sum of unmet demand (stockouts)
            - waste_quantity: Sum of expired/wasted stock
            - service_level: Fraction of demand satisfied (1 - lost_sales / total_demand)
            - inventory_turnover: total_sales / avg_inventory

        Args:
            time_series: DataFrame from simulate() with columns demand, actual_sales,
                lost_sales, waste, stock_before, stock_after.

        Returns:
            Dict of metric name -> value.
        """

        total_demand = time_series["demand"].sum()
        total_sales = time_series["actual_sales"].sum()
        lost_sales = time_series["lost_sales"].sum()
        waste = time_series["waste"].sum()

        service_level = (
            1.0 - (lost_sales / total_demand) if total_demand > 0 else 1.0
        )

        avg_stock = (
            (time_series["stock_before"] + time_series["stock_after"]) / 2
        ).mean()
        inventory_turnover = (
            total_sales / avg_stock if avg_stock > 0 else 0.0
        )

        return {
            "total_sales": total_sales,
            "lost_sales": lost_sales,
            "waste_quantity": waste,
            "service_level": service_level,
            "inventory_turnover": inventory_turnover,
            "total_demand": total_demand,
        }
