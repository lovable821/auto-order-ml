"""Ordering policy rules - min/max quantities, rounding."""

from dataclasses import dataclass


@dataclass
class OrderPolicy:
    """Ordering policy configuration."""

    min_order_quantity: int = 1
    max_order_quantity: int = 1000
    round_to_pallet: bool = False
    pallet_size: int = 48


def apply_policy(quantity: float, policy: OrderPolicy) -> int:
    """Apply ordering policy to raw quantity."""
    q = max(policy.min_order_quantity, min(policy.max_order_quantity, int(quantity)))
    if policy.round_to_pallet and policy.pallet_size > 0:
        q = ((q + policy.pallet_size - 1) // policy.pallet_size) * policy.pallet_size
    return max(policy.min_order_quantity, q)
