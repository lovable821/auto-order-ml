"""Inventory - stock management, order logic, and simulation."""

from src.inventory.order_optimizer import (
    compute_order_qty,
    compute_order_recommendations,
)
from src.inventory.simulation import InventorySimulator, SimulationReport

__all__ = [
    "compute_order_qty",
    "compute_order_recommendations",
    "InventorySimulator",
    "SimulationReport",
]
