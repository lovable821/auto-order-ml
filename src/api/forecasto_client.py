"""
Forecasto API client - production-ready client for Forecasto APIs.

Usage:
    client = ForecastoClient(token="your-token")
    sales = client.get_sales("01.01.2025", "01.03.2026")
    inventory = client.get_inventory("01.03.2026")
"""

import logging
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        token: str,
        base_url: str = "https://api.forecasto.com",
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize the Forecasto API client.

        Args:
            token: API authentication token.
            base_url: Base URL for the Forecasto API.
            timeout: Request timeout in seconds.
            max_retries: Number of retries for transient failures.
        """
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = self._build_session(max_retries)

    def _build_session(self, max_retries: int) -> requests.Session:
        """Build a requests session with retry logic."""
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _request(self, method: str, endpoint: str, params: dict[str, Any] | None = None) -> Any:
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
                "Forecasto API HTTP error: %s %s - %s",
                method,
                url,
                status_code,
                exc_info=True,
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
            # Handle {"data": [...], "items": [...]} etc.
            for key in ("data", "items", "results", "records"):
                if key in data and isinstance(data[key], list):
                    return pd.DataFrame(data[key])
            # Single record as dict
            return pd.DataFrame([data])

        logger.warning("Unexpected response type %s, returning empty DataFrame", type(data))
        return pd.DataFrame(columns=default_columns or [])

    def get_sales(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get sales data for the given date range.

        Args:
            start_date: Start date (e.g. "01.01.2025").
            end_date: End date (e.g. "01.03.2026").

        Returns:
            DataFrame with sales records.
        """
        logger.debug("Fetching sales from %s to %s", start_date, end_date)
        data = self._request(
            "GET",
            "/sales",
            params={"start_date": start_date, "end_date": end_date},
        )
        df = self._to_dataframe(data, default_columns=["date", "product_id", "quantity", "amount"])
        logger.info("Retrieved %d sales records", len(df))
        return df

    def get_inventory(self, date: str) -> pd.DataFrame:
        """
        Get inventory snapshot for the given date.

        Args:
            date: Date (e.g. "01.03.2026").

        Returns:
            DataFrame with inventory records.
        """
        logger.debug("Fetching inventory for %s", date)
        data = self._request("GET", "/inventory", params={"date": date})
        df = self._to_dataframe(data, default_columns=["product_id", "quantity", "warehouse_id"])
        logger.info("Retrieved %d inventory records", len(df))
        return df

    def get_products(self) -> pd.DataFrame:
        """
        Get product catalog.

        Returns:
            DataFrame with product records.
        """
        logger.debug("Fetching products")
        data = self._request("GET", "/products")
        df = self._to_dataframe(data, default_columns=["product_id", "name", "category", "sku"])
        logger.info("Retrieved %d products", len(df))
        return df

    def get_losses(self, date: str) -> pd.DataFrame:
        """
        Get loss/waste data for the given date.

        Args:
            date: Date (e.g. "01.03.2026").

        Returns:
            DataFrame with loss records.
        """
        logger.debug("Fetching losses for %s", date)
        data = self._request("GET", "/losses", params={"date": date})
        df = self._to_dataframe(data, default_columns=["product_id", "quantity", "reason", "date"])
        logger.info("Retrieved %d loss records", len(df))
        return df
