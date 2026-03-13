"""Logging setup - level, format, optional file output."""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str | Path] = None,
    format_string: Optional[str] = None,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional path to log file. If provided, logs are also written to file.
        format_string: Optional custom format. Default uses structured format with
            timestamp, level, logger name, and message.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    default_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    fmt = format_string or default_format
    date_fmt = "%Y-%m-%d %H:%M:%S"

    # Root logger
    root = logging.getLogger()
    root.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    console.setFormatter(logging.Formatter(fmt, datefmt=date_fmt))
    root.addHandler(console)

    # File handler (optional)
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(fmt, datefmt=date_fmt))
        root.addHandler(file_handler)

    # Reduce noise from third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("lightgbm").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given module name.

    Args:
        name: Module name (typically __name__).

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
