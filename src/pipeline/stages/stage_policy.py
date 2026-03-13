"""Stage 8: load policy from config."""

import logging
from typing import Optional

from src.pipeline.context import PipelineContext
from src.policy.rules import OrderPolicy, PolicyMode

logger = logging.getLogger(__name__)


def run_policy_stage(ctx: PipelineContext) -> PipelineContext:
    """Load OrderPolicy from config (mode, min/max qty, etc). Used by order optimization."""
    policy_cfg = ctx.config.get("policy", {})
    mode_str = policy_cfg.get("policy_mode", "balanced")
    try:
        mode = PolicyMode(mode_str.lower())
    except ValueError:
        mode = PolicyMode.BALANCED
        logger.warning("Unknown policy_mode '%s'; using balanced", mode_str)

    ctx.policy = OrderPolicy(
        min_order_quantity=policy_cfg.get("min_order_quantity", 1),
        max_order_quantity=policy_cfg.get("max_order_quantity", 1000),
        round_to_pallet=policy_cfg.get("round_to_pallet", False),
        pallet_size=policy_cfg.get("pallet_size", 48),
        policy_mode=mode,
    )
    logger.info("Policy loaded: mode=%s", mode.value)
    return ctx
