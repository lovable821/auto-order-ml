"""Ordering policy rules - min/max quantities, rounding, OOS vs waste modes."""

from dataclasses import dataclass
from enum import Enum


class PolicyMode(str, Enum):
    """Part C: Dynamic policy mode – OOS vs waste balance."""

    SERVICE_FIRST = "service_first"  # Minimize out-of-stock
    WASTE_FIRST = "waste_first"  # Minimize write-offs / excess
    BALANCED = "balanced"  # Compromise between OOS and waste


@dataclass
class OrderPolicy:
    """Ordering policy configuration."""

    min_order_quantity: int = 1
    max_order_quantity: int = 1000
    round_to_pallet: bool = False
    pallet_size: int = 48
    policy_mode: PolicyMode = PolicyMode.BALANCED


def apply_policy(quantity: float, policy: OrderPolicy) -> int:
    """Apply ordering policy to raw quantity."""
    q = max(policy.min_order_quantity, min(policy.max_order_quantity, int(quantity)))
    if policy.round_to_pallet and policy.pallet_size > 0:
        q = ((q + policy.pallet_size - 1) // policy.pallet_size) * policy.pallet_size
    return max(policy.min_order_quantity, q)
