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
    def test_fetch_returns_datapoint(self, mock_get, mock_coingecko_response):
        """Test fetch returns valid DataPoint."""
        mock_get.return_value = mock_coingecko_response

        source = CoinGeckoSource()
        datapoints = source.fetch()

        assert len(datapoints) == 1
        point = datapoints[0]
        assert point.value == 65000.0
        assert point.asset == "BTC"
        assert point.currency == "USD"
        assert point.source == DataSourceType.COINGECKO
        assert point.metric == "price"
        assert point.timestamp is not None
        assert point.timestamp.tzinfo is not None

    @patch("src.data.sources.requests.get")
    def test_fetch_http_error(self, mock_get):
        """Test fetch raises on HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("Server error")
        mock_get.return_value = mock_response

        source = CoinGeckoSource()
        with pytest.raises(requests.HTTPError):
            source.fetch()

    @patch("src.data.sources.requests.get")
    def test_fetch_malformed_response(self, mock_get):
        """Test fetch handles malformed JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = KeyError("bitcoin")
        mock_get.return_value = mock_response

        source = CoinGeckoSource()
        with pytest.raises(KeyError):
            source.fetch()

    @patch("src.data.sources.requests.get")
    def test_fetch_timeout(self, mock_get):
        """Test fetch respects timeout."""
        mock_get.side_effect = requests.Timeout("Connection timeout")

        source = CoinGeckoSource(timeout_seconds=5)
        with pytest.raises(requests.Timeout):
            source.fetch()

        # Verify timeout was passed to requests.get
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["timeout"] == 5
