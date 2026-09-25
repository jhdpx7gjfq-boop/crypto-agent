"""Tests for data sources layer."""

from unittest.mock import Mock, patch

import pytest
import requests

from src.data.contracts import DataSourceType
from src.data.sources import CoinGeckoSource


class TestCoinGeckoSource:
    """Tests for CoinGecko data source."""

    def test_init_sets_defaults(self):
        """Test initialization with default parameters."""
        source = CoinGeckoSource()
        assert source.timeout == 10
        assert source.retry_max == 3
        assert "coingecko" in source.base_url

    def test_init_custom_timeout(self):
        """Test initialization with custom timeout."""
        source = CoinGeckoSource(timeout_seconds=20)
        assert source.timeout == 20

    @patch("src.data.sources.requests.get")
    def test_fetch_sync_returns_datapoint(self, mock_get, mock_coingecko_response):
        """Test fetch_sync returns valid DataPoint."""
        mock_get.return_value = mock_coingecko_response

        source = CoinGeckoSource()
        datapoints = source.fetch_sync()

        assert len(datapoints) == 1
        point = datapoints[0]
        assert point.value == 65000.0
        assert point.asset == "BTC"
        assert point.currency == "USD"
        assert point.source == DataSourceType.COINGECKO
        assert point.metric == "price"
        assert point.timestamp is not None

    @patch("src.data.sources.requests.get")
    def test_fetch_sync_http_error(self, mock_get):
        """Test fetch_sync raises on HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("Server error")
        mock_get.return_value = mock_response

        source = CoinGeckoSource()
        with pytest.raises(requests.HTTPError):
            source.fetch_sync()

    @patch("src.data.sources.requests.get")
    def test_fetch_sync_malformed_response(self, mock_get):
        """Test fetch_sync handles malformed JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = KeyError("bitcoin")
        mock_get.return_value = mock_response

        source = CoinGeckoSource()
        with pytest.raises(KeyError):
            source.fetch_sync()

    @patch("src.data.sources.requests.get")
    def test_fetch_sync_timeout(self, mock_get):
        """Test fetch_sync respects timeout."""
        mock_get.side_effect = requests.Timeout("Connection timeout")

        source = CoinGeckoSource(timeout_seconds=5)
        with pytest.raises(requests.Timeout):
            source.fetch_sync()

        # Verify timeout was passed to requests.get
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["timeout"] == 5
