"""Charts for forecast evaluation and inventory simulation."""

from pathlib import Path
from typing import Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# Style for technical reports
plt.rcParams.update({
    "figure.dpi": 150,
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.figsize": (8, 5),
})


def plot_actual_vs_predicted(
    actual: Union[np.ndarray, pd.Series, list],
    predicted: Union[np.ndarray, pd.Series, list],
    dates: Optional[Union[pd.DatetimeIndex, list, np.ndarray]] = None,
    title: str = "Actual vs Predicted Demand",
    ax: Optional[plt.Axes] = None,
    save_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Plot actual vs predicted demand time series.

    Args:
        actual: Actual demand values.
        predicted: Predicted demand values.
        dates: Optional x-axis labels (dates).
        title: Chart title.
        ax: Optional matplotlib axes. If None, creates new figure.
        save_path: Optional path to save the figure.

    Returns:
        matplotlib Figure.
    """
    actual = np.asarray(actual)
    predicted = np.asarray(predicted)
    n = len(actual)

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 5))
    else:
        fig = ax.figure

    x = np.arange(n) if dates is None else pd.to_datetime(dates)
    ax.plot(x, actual, "o-", label="Actual", color="#2e86ab", markersize=4, linewidth=1.5)
    ax.plot(x, predicted, "s--", label="Predicted", color="#e94f37", markersize=4, linewidth=1.5)

    ax.set_xlabel("Time" if dates is None else "Date")
    ax.set_ylabel("Demand")
    ax.set_title(title)
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    if dates is not None:
        fig.autofmt_xdate()

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    return fig


def plot_inventory_levels(
    time_series: pd.DataFrame,
    date_col: str = "date",
    stock_col: str = "stock_after",
    demand_col: Optional[str] = "demand",
    title: str = "Inventory Levels Over Time",
    ax: Optional[plt.Axes] = None,
    save_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Plot inventory levels over time, optionally with demand overlay.

    Args:
        time_series: DataFrame from simulation or similar (date, stock, demand).
        date_col: Column name for dates.
        stock_col: Column name for stock levels (e.g. stock_after, stock_before).
        demand_col: Optional column for demand overlay. None to omit.
        title: Chart title.
        ax: Optional matplotlib axes.
        save_path: Optional path to save the figure.

    Returns:
        matplotlib Figure.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 5))
    else:
        fig = ax.figure

    dates = pd.to_datetime(time_series[date_col])
    stock = time_series[stock_col].values

    ax.fill_between(dates, stock, alpha=0.3, color="#2e86ab")
    ax.plot(dates, stock, "o-", color="#2e86ab", markersize=4, linewidth=1.5, label="Inventory")

    if demand_col and demand_col in time_series.columns:
        demand = time_series[demand_col].values
        ax.plot(dates, demand, "s--", color="#e94f37", markersize=4, linewidth=1.5, label="Demand")

    ax.set_xlabel("Date")
    ax.set_ylabel("Quantity")
    ax.set_title(title)
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    fig.autofmt_xdate()
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    return fig


def plot_stockouts_vs_waste(
    time_series: pd.DataFrame,
    date_col: str = "date",
    lost_sales_col: str = "lost_sales",
    waste_col: str = "waste",
    title: str = "Stockouts vs Waste Over Time",
    ax: Optional[plt.Axes] = None,
    save_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Plot lost sales (stockouts) and waste quantities over time.

    Args:
        time_series: DataFrame with lost_sales and waste columns.
        date_col: Column name for dates.
        lost_sales_col: Column name for stockouts/lost sales.
        waste_col: Column name for waste.
        title: Chart title.
        ax: Optional matplotlib axes.
        save_path: Optional path to save the figure.

    Returns:
        matplotlib Figure.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 5))
    else:
        fig = ax.figure

    dates = pd.to_datetime(time_series[date_col])
    lost_sales = time_series[lost_sales_col].values
    waste = time_series[waste_col].values

    width = 0.35
    x = np.arange(len(dates))
    ax.bar(x - width / 2, lost_sales, width, label="Stockouts (lost sales)", color="#e94f37", alpha=0.8)
    ax.bar(x + width / 2, waste, width, label="Waste", color="#44af69", alpha=0.8)

    ax.set_xlabel("Date")
    ax.set_ylabel("Quantity")
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels([d.strftime("%Y-%m-%d") for d in dates], rotation=45, ha="right")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    return fig


def plot_forecast_error_distribution(
    actual: Union[np.ndarray, pd.Series, list],
    predicted: Union[np.ndarray, pd.Series, list],
    title: str = "Forecast Error Distribution",
    ax: Optional[plt.Axes] = None,
    save_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Plot distribution of forecast errors (actual - predicted).

    Args:
        actual: Actual demand values.
        predicted: Predicted demand values.
        title: Chart title.
        ax: Optional matplotlib axes.
        save_path: Optional path to save the figure.

    Returns:
        matplotlib Figure.
    """
    actual = np.asarray(actual)
    predicted = np.asarray(predicted)
    errors = actual - predicted

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 5))
    else:
        fig = ax.figure

    ax.hist(errors, bins=min(30, max(1, len(errors) // 2)), color="#2e86ab", alpha=0.7, edgecolor="white")
    ax.axvline(0, color="#e94f37", linestyle="--", linewidth=2, label="Zero error")
    ax.axvline(np.mean(errors), color="#44af69", linestyle="-", linewidth=2, label=f"Mean error = {np.mean(errors):.2f}")

    ax.set_xlabel("Forecast Error (Actual - Predicted)")
    ax.set_ylabel("Frequency")
    ax.set_title(title)
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    return fig


def plot_all_summary(
    part_a_result: Optional[dict] = None,
    simulation_report: Optional[object] = None,
    output_dir: Union[str, Path] = "outputs/figures",
) -> list[Path]:
    """
    Generate all standard plots from Part A and/or simulation results.

    Args:
        part_a_result: Dict from run_part_a with test_actual, test_predictions.
        simulation_report: SimulationReport from InventorySimulator.simulate().
        output_dir: Directory to save figures.

    Returns:
        List of saved file paths.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    saved_paths = []

    if part_a_result:
        actual = part_a_result.get("test_actual")
        preds = part_a_result.get("test_predictions")
        if actual is not None and preds is not None:
            p1 = out / "actual_vs_predicted.png"
            plot_actual_vs_predicted(actual, preds, title="Actual vs Predicted Demand (Part A)", save_path=p1)
            saved_paths.append(p1)

            p4 = out / "forecast_error_distribution.png"
            plot_forecast_error_distribution(actual, preds, title="Forecast Error Distribution", save_path=p4)
            saved_paths.append(p4)

    if simulation_report and hasattr(simulation_report, "time_series"):
        ts = simulation_report.time_series
        p2 = out / "inventory_levels.png"
        plot_inventory_levels(ts, title="Inventory Levels Over Time", save_path=p2)
        saved_paths.append(p2)

        p3 = out / "stockouts_vs_waste.png"
        plot_stockouts_vs_waste(ts, title="Stockouts vs Waste Over Time", save_path=p3)
        saved_paths.append(p3)

    return saved_paths
