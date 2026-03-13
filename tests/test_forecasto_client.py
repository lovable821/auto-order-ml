"""Forecasto client tests."""

import pytest
import pandas as pd
from unittest.mock import ANY, Mock, patch

from src.api.forecasto_client import ForecastoClient, ForecastoAPIError


@pytest.fixture
def client() -> ForecastoClient:
    """Create client with mock token."""
    return ForecastoClient(token="test-token", base_url="https://api.test.com")


def test_client_initialization():
    """Verify client initializes with token (sent in body per API spec)."""
    c = ForecastoClient(token="my-token")
    assert c._token == "my-token"
    assert "Content-Type" in c._session.headers


def test_client_configurable_base_url():
    """Verify base_url is configurable."""
    c = ForecastoClient(token="x", base_url="https://custom.api/v1")
    assert c._base_url == "https://custom.api/v1"


@patch("src.api.forecasto_client.ForecastoClient._request")
def test_get_sales_returns_dataframe(mock_request: Mock, client: ForecastoClient):
    """get_sales returns pandas DataFrame."""
    mock_request.return_value = [
        {"date": "01.01.2025", "product_id": "P1", "quantity": 10, "amount": 100}
    ]
    df = client.get_sales("01.01.2025", "01.03.2026")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert "product_id" in df.columns
    mock_request.assert_called_once()
    call_args = mock_request.call_args
    assert call_args[0][:2] == ("POST", "/sales")
    assert call_args[1]["json"]["START_DATE"] == "01.01.2025"
    assert call_args[1]["json"]["FINISH_DATE"] == "01.03.2026"


@patch("src.api.forecasto_client.ForecastoClient._request")
def test_get_inventory_returns_dataframe(mock_request: Mock, client: ForecastoClient):
    """get_inventory returns pandas DataFrame."""
    mock_request.return_value = [{"product_id": "P1", "quantity": 50}]
    df = client.get_inventory("01.03.2026")
    assert isinstance(df, pd.DataFrame)
    mock_request.assert_called_once_with(
        "POST", "/inventory/stock", json={"token": ANY, "Date": "01.03.2026"}
    )


@patch("src.api.forecasto_client.ForecastoClient._request")
def test_get_products_returns_dataframe(mock_request: Mock, client: ForecastoClient):
    """get_products returns pandas DataFrame."""
    mock_request.return_value = [{"product_id": "P1", "name": "Product 1"}]
    df = client.get_products()
    assert isinstance(df, pd.DataFrame)
    mock_request.assert_called_once_with(
        "POST", "/backend/delivery_info/api/v1/GetAll", json={"token": ANY}
    )


@patch("src.api.forecasto_client.ForecastoClient._request")
def test_get_losses_returns_dataframe(mock_request: Mock, client: ForecastoClient):
    """get_losses returns pandas DataFrame."""
    mock_request.return_value = [{"product_id": "P1", "quantity": 2, "reason": "expired"}]
    df = client.get_losses("01.03.2026")
    assert isinstance(df, pd.DataFrame)
    mock_request.assert_called_once_with(
        "POST", "/loss/getall", json={"token": ANY, "Date": "01.03.2026"}
    )


@patch("src.api.forecasto_client.ForecastoClient._request")
def test_empty_response_returns_empty_dataframe(mock_request: Mock, client: ForecastoClient):
    """Empty API response returns empty DataFrame with columns."""
    mock_request.return_value = []
    df = client.get_sales("01.01.2025", "01.01.2025")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_http_error_raises_forecasto_api_error(client: ForecastoClient):
    """HTTP errors raise ForecastoAPIError."""
    import requests

    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "404 Client Error", response=mock_response
    )

    with patch.object(client._session, "request", return_value=mock_response):
        with pytest.raises(ForecastoAPIError) as exc_info:
            client.get_sales("01.01.2025", "01.03.2026")
        assert exc_info.value.status_code == 404
