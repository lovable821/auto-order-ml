"""
Forecasto API client for api.forecasto.ru.

All endpoints use POST with token in JSON body (per assignment spec).

Endpoints:
- Sales:     /sales         -> {token, START_DATE, FINISH_DATE}  (dd.MM.yyyy)
- Inventory: /inventory/stock -> {token, Date}
- Products:  /backend/delivery_info/api/v1/GetAll -> {token}
- Losses:    /loss/getall   -> {token, Date}
"""

import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Load .env for token
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(_env_path)
except ImportError:
    pass


class ForecastoAPIError(Exception):
    """Raised when Forecasto API returns an error."""

    def __init__(self, message: str, status_code: int | None = None, response: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ForecastoClient:
    """
    Client for Forecasto APIs.

    All methods return pandas DataFrames. Handles HTTP errors and provides
    configurable authentication via token.
    """

    BASE_URL = "https://api.forecasto.ru"

    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize the Forecasto API client.

        Args:
            token: API authentication token. Loads from AUTHORIZATION or FORECAST_API_TOKEN in .env if None.
            base_url: Base URL. Default: https://api.forecasto.ru
            timeout: Request timeout in seconds.
            max_retries: Number of retries for transient failures.
        """
        self._token = token or self._get_token_from_env()
        self._base_url = (base_url or self.BASE_URL).rstrip("/")
        self._timeout = timeout
        self._session = self._build_session(max_retries)

    def _build_session(self, max_retries: int) -> requests.Session:
        """Build a requests session. Token is sent in body per API spec."""
        session = requests.Session()
        session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _get_token_from_env(self) -> str:
        """Load token from .env. Request token from client per assignment."""
        for key in ("FORECASTO_TOKEN", "FORECAST_API_TOKEN"):
            token = os.getenv(key, "").strip()
            if token:
                return token
        auth = os.getenv("AUTHORIZATION", "").strip()
        if auth and auth.lower().startswith("bearer "):
            return auth[7:].strip()
        raise ValueError(
            "Token required. Set FORECASTO_TOKEN or FORECAST_API_TOKEN in .env (request from client)"
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute HTTP request and return JSON response.

        Raises:
            ForecastoAPIError: On HTTP errors or invalid responses.
        """
        url = f"{self._base_url}{endpoint}"
        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                timeout=self._timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            try:
                body = e.response.text if e.response is not None else None
            except Exception:
                body = None
            logger.error(
                "Forecasto API HTTP error: %s %s - %s. Response: %s",
                method,
                url,
                status_code,
                (body or "")[:500],
            )
            raise ForecastoAPIError(
                message=str(e),
                status_code=status_code,
                response=body,
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error("Forecasto API request failed: %s %s", method, url, exc_info=True)
            raise ForecastoAPIError(message=str(e)) from e

    def _to_dataframe(self, data: Any, default_columns: list[str] | None = None) -> pd.DataFrame:
        """Convert API response to pandas DataFrame."""
        if data is None:
            return pd.DataFrame(columns=default_columns or [])

        if isinstance(data, list):
            if not data:
                return pd.DataFrame(columns=default_columns or [])
            return pd.DataFrame(data)

        if isinstance(data, dict):
            # Handle {"data": [...], "items": [...], "result": [...]} etc.
            for key in ("data", "items", "results", "records", "result"):
                if key in data and isinstance(data[key], list):
                    return pd.DataFrame(data[key])
            # Single record as dict
            return pd.DataFrame([data])

        logger.warning("Unexpected response type %s, returning empty DataFrame", type(data))
        return pd.DataFrame(columns=default_columns or [])

    def get_sales(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get sales data. Dates in dd.MM.yyyy (e.g. 05.03.2026).

        API returns: Период, Номенклатура, Количество, Сумма, Код, Артикул, Группа.
        """
        logger.debug("Fetching sales from %s to %s", start_date, end_date)
        data = self._request(
            "POST",
            "/sales",
            json={
                "token": self._token,
                "START_DATE": start_date,
                "FINISH_DATE": end_date,
            },
        )
        df = self._to_dataframe(data, default_columns=["date", "product_id", "quantity", "amount"])
        logger.info("Retrieved %d sales records", len(df))
        return df

    def get_inventory(self, date: str) -> pd.DataFrame:
        """
        Get stock balance. Date in dd.MM.yyyy.
        Returns: Date, Code, Name, balance.
        """
        logger.debug("Fetching inventory for %s", date)
        data = self._request(
            "POST",
            "/inventory/stock",
            json={"token": self._token, "Date": date},
        )
        df = self._to_dataframe(data, default_columns=["product_id", "quantity", "warehouse_id"])
        logger.info("Retrieved %d inventory records", len(df))
        return df

    def get_products(self) -> pd.DataFrame:
        """
        Get product properties. Flattens item_information (ExpirationDays, MinStockLevel, etc.).
        """
        logger.debug("Fetching products")
        data = self._request(
            "POST",
            "/backend/delivery_info/api/v1/GetAll",
            json={"token": self._token},
        )
        items = data.get("items", []) if isinstance(data, dict) else []
        rows = []
        for item in items:
            row = {"item_code": item.get("item_code"), "item_name": item.get("item_name")}
            for info in item.get("item_information", []):
                if isinstance(info, dict):
                    row.update(info)
            rows.append(row)
        df = pd.DataFrame(rows) if rows else pd.DataFrame(
            columns=["item_code", "item_name", "ExpirationDays", "MinStockLevel"]
        )
        logger.info("Retrieved %d products", len(df))
        return df

    def get_losses(self, date: str) -> pd.DataFrame:
        """
        Get loss/waste data. Returns: Date, item_id, loss, totalloss, reason.
        """
        logger.debug("Fetching losses for %s", date)
        data = self._request(
            "POST",
            "/loss/getall",
            json={"token": self._token, "Date": date},
        )
        df = self._to_dataframe(data, default_columns=["product_id", "quantity", "reason", "date"])
        logger.info("Retrieved %d loss records", len(df))
        return df
