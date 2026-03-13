"""API layer - REST endpoints and request/response handling."""

from src.api.forecasto_client import ForecastoAPIError, ForecastoClient

__all__ = ["ForecastoClient", "ForecastoAPIError"]
