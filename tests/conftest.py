"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def sample_config_path() -> Path:
    """Path to sample config for testing."""
    return Path(__file__).parent.parent / "configs" / "default.yaml"


@pytest.fixture
def project_root() -> Path:
    """Project root directory."""
    return Path(__file__).parent.parent
