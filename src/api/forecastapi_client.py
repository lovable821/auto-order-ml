"""ForecastAPI client (forecastapi.com)."""

import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


def get_forecast_token() -> str:
    """Token from FORECAST_API_TOKEN or AUTHORIZATION (Bearer ...)."""
    token = os.getenv("FORECAST_API_TOKEN", "").strip()
    if token:
        return token

    auth = os.getenv("AUTHORIZATION", "").strip()
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()

    raise ValueError(
        "No ForecastAPI token found. Set FORECAST_API_TOKEN or AUTHORIZATION (Bearer ...) in .env"
    )


class ForecastAPIError(Exception):
    """API error."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ForecastAPIClient:
    """Forecast from time series. POST /forecast."""

    BASE_URL = "https://forecastapi.com/v2"

    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Token from env if None."""
        self._token = token or get_forecast_token()
        self._base_url = (base_url or self.BASE_URL).rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def get_forecast(
        self,
        identifier: str,
        data: list[dict[str, Any]],
        periods: int = 6,
        frequency: str = "M",
        data_type: str = "sales",
        model: str = "standard",
    ) -> dict[str, Any]:
        """Forecast from data. identifier, data [{date, value}], periods, frequency."""
        url = f"{self._base_url}/forecast"
        payload = {
            "identifier": identifier,
            "data": data,
            "periods": periods,
            "frequency": frequency,
            "data_type": data_type,
            "model": model,
        }
        try:
            response = self._session.post(url, json=payload, timeout=self._timeout)
            response.raise_for_status()
            result = response.json()
            logger.info(
                "Forecast for %s: %d periods, method=%s",
                identifier,
                len(result.get("forecast", [])),
                result.get("method", "unknown"),
            )
            return result
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            body = e.response.text if e.response else None
            logger.error("ForecastAPI error: %s - %s", status_code, body)
            raise ForecastAPIError(
                message=str(e),
                status_code=status_code,
                response=body,
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error("ForecastAPI request failed: %s", e)
            raise ForecastAPIError(message=str(e)) from e

    def forecast_to_dataframe(self, result: dict[str, Any]) -> pd.DataFrame:
        """Forecast response -> DataFrame."""
        forecast = result.get("forecast", [])
        if not forecast:
            return pd.DataFrame(columns=["date", "value", "lower", "upper"])
        return pd.DataFrame(forecast)
