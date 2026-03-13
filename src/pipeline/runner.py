"""Pipeline runner - orchestrates data -> features -> forecast -> orders."""

from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: str) -> dict[str, Any]:
    """Load YAML configuration."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def run(config_path: str | Path) -> None:
    """Execute full pipeline."""
    config = load_config(str(config_path))
    # Wire: pipeline -> features -> models -> inventory -> policy
    _ = config  # Placeholder for pipeline logic
