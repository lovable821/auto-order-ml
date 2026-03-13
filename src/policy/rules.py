"""Policy: min/max qty, rounding, service vs waste mode."""

from dataclasses import dataclass
from enum import Enum


class PolicyMode(str, Enum):
    """service_first, waste_first, balanced."""

    SERVICE_FIRST = "service_first"  # Minimize out-of-stock
    WASTE_FIRST = "waste_first"  # Minimize write-offs / excess
    BALANCED = "balanced"  # Compromise between OOS and waste


@dataclass
class OrderPolicy:
    """min/max qty, pallet rounding, policy_mode."""

    min_order_quantity: int = 1
    max_order_quantity: int = 1000
    round_to_pallet: bool = False
    pallet_size: int = 48
    policy_mode: PolicyMode = PolicyMode.BALANCED


def apply_policy(quantity: float, policy: OrderPolicy) -> int:
    """Clamp to min/max, optional pallet round."""
    q = max(policy.min_order_quantity, min(policy.max_order_quantity, int(quantity)))
    if policy.round_to_pallet and policy.pallet_size > 0:
        q = ((q + policy.pallet_size - 1) // policy.pallet_size) * policy.pallet_size
    return max(policy.min_order_quantity, q)
