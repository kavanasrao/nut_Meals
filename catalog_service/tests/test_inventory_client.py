"""Unit tests for InventoryClient, mocking the downstream HTTP call."""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.inventory_client import InventoryClient

pytestmark = pytest.mark.asyncio


async def test_get_stock_for_skus_empty_input_short_circuits():
    client = InventoryClient()
    result = await client.get_stock_for_skus([])
    assert result == {}


async def test_get_stock_for_skus_returns_mapped_results():
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {
        "results": [
            {"sku": "SKU-1", "is_in_stock": True, "quantity_available": 10},
            {"sku": "SKU-2", "is_in_stock": False, "quantity_available": 0},
        ]
    }

    mock_async_client = AsyncMock()
    mock_async_client.__aenter__.return_value = mock_async_client
    mock_async_client.post = AsyncMock(return_value=fake_response)

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        client = InventoryClient()
        result = await client.get_stock_for_skus(["SKU-1", "SKU-2"])

    assert result["SKU-1"]["is_in_stock"] is True
    assert result["SKU-2"]["quantity_available"] == 0


async def test_get_stock_for_skus_returns_empty_on_http_error():
    mock_async_client = AsyncMock()
    mock_async_client.__aenter__.return_value = mock_async_client
    mock_async_client.post = AsyncMock(side_effect=httpx.ConnectTimeout("timeout"))

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        client = InventoryClient()
        result = await client.get_stock_for_skus(["SKU-1"])

    assert result == {}
