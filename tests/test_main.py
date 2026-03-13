"""Tests for main entrypoint."""

import pytest
from unittest.mock import patch


def test_import_main():
    """Verify main module can be imported."""
    import main  # noqa: F401


def test_project_structure(project_root):
    """Verify required directories exist."""
    required_dirs = ["src", "configs", "tests", "notebooks"]
    for dir_name in required_dirs:
        assert (project_root / dir_name).is_dir(), f"Missing directory: {dir_name}"
