from unittest.mock import Mock, patch

import pytest
import requests

from binance_public import (
    BINANCE_DATA_STATUS,
    FUTURES_BASE_URL,
    SPOT_BASE_URL,
    BinanceAPIError,
    BinancePublicClient,
    cvd_from_klines,
)
from coinglass import STATUS_LEVELS
from http_retry import RateLimitError


def test_data_status_is_a_recognized_verification_level():
    # Guards against a typo silently making this an unrecognized value --
    # see research/candidates/DATA-SRC-004_BINANCE_PUBLIC_FREE/OVERVIEW.md
    # for what actually justifies each level.
    assert BINANCE_DATA_STATUS in STATUS_LEVELS


def make_response(status_code=200, payload=None, headers=None):
    response = Mock()
    response.status_code = status_code
    response.headers = headers or {}
    response.json = lambda: payload if payload is not None else []
    response.raise_for_status = lambda: None
    return response


# Binance kline: [open_time, open, high, low, close, volume, close_time,
# quote_volume, num_trades, taker_buy_base_volume, taker_buy_quote_volume, ignore]
def make_kline(open_time, close_time, volume, taker_buy_base):
    return [open_time, "0", "0", "0", "0", str(volume), close_time, "0", 1, str(taker_buy_base), "0", "0"]


class TestOpenInterest:
    @patch("binance_public.requests.get")
    def test_open_interest_path_and_params(self, mock_get):
        mock_get.return_value = make_response(payload={"symbol": "BTCUSDT", "openInterest": "123"})
        client = BinancePublicClient()

        result = client.open_interest("BTCUSDT")

        assert result == {"symbol": "BTCUSDT", "openInterest": "123"}
        args, kwargs = mock_get.call_args
        assert args[0] == f"{FUTURES_BASE_URL}/fapi/v1/openInterest"
        assert kwargs["params"] == {"symbol": "BTCUSDT"}

    @patch("binance_public.requests.get")
    def test_open_interest_history_drops_none_params(self, mock_get):
        mock_get.return_value = make_response(payload=[])
        client = BinancePublicClient()

        client.open_interest_history("BTCUSDT", "1h", limit=None)

        assert mock_get.call_args[0][0] == f"{FUTURES_BASE_URL}/futures/data/openInterestHist"
        assert mock_get.call_args[1]["params"] == {"symbol": "BTCUSDT", "period": "1h"}


class TestFundingRate:
    @patch("binance_public.requests.get")
    def test_funding_rate_history_path(self, mock_get):
        mock_get.return_value = make_response(payload=[])
        client = BinancePublicClient()

        client.funding_rate_history("BTCUSDT", limit=10)

        assert mock_get.call_args[0][0] == f"{FUTURES_BASE_URL}/fapi/v1/fundingRate"
        assert mock_get.call_args[1]["params"] == {"symbol": "BTCUSDT", "limit": 10}


class TestCvdComputation:
    def test_cvd_accumulates_delta_across_klines(self):
        klines = [
            make_kline(1, 2, volume=100, taker_buy_base=70),  # delta = 70 - 30 = 40
            make_kline(2, 3, volume=50, taker_buy_base=10),  # delta = 10 - 40 = -30
        ]

        records = cvd_from_klines(klines)

        assert records[0] == {
            "open_time": 1,
            "close_time": 2,
            "taker_buy_volume": 70.0,
            "taker_sell_volume": 30.0,
            "delta": 40.0,
            "cvd": 40.0,
        }
        assert records[1]["delta"] == -30.0
        assert records[1]["cvd"] == 10.0  # 40 + (-30)

    def test_empty_klines_returns_empty_list(self):
        assert cvd_from_klines([]) == []

    @patch("binance_public.requests.get")
    def test_futures_cvd_history_uses_futures_klines(self, mock_get):
        mock_get.return_value = make_response(payload=[make_kline(1, 2, 100, 60)])
        client = BinancePublicClient()

        result = client.futures_cvd_history("BTCUSDT", "1h", limit=5)

        assert mock_get.call_args[0][0] == f"{FUTURES_BASE_URL}/fapi/v1/klines"
        assert result[0]["cvd"] == 20.0  # 60 - 40

    @patch("binance_public.requests.get")
    def test_spot_cvd_history_uses_spot_klines(self, mock_get):
        mock_get.return_value = make_response(payload=[make_kline(1, 2, 100, 60)])
        client = BinancePublicClient()

        client.spot_cvd_history("BTCUSDT", "1h", limit=5)

        assert mock_get.call_args[0][0] == f"{SPOT_BASE_URL}/api/v3/klines"


class TestErrorHandling:
    @patch("binance_public.requests.get")
    def test_raises_binance_api_error_on_error_payload(self, mock_get):
        mock_get.return_value = make_response(payload={"code": -1121, "msg": "Invalid symbol."})
        client = BinancePublicClient()

        with pytest.raises(BinanceAPIError, match="Invalid symbol"):
            client.open_interest("NOTASYMBOL")

    @patch("binance_public.requests.get")
    def test_propagates_http_errors(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("boom")
        mock_get.return_value = mock_response
        client = BinancePublicClient()

        with pytest.raises(requests.HTTPError):
            client.open_interest("BTCUSDT")


class TestRateLimit:
    @patch("binance_public.time.sleep")
    @patch("binance_public.requests.get")
    def test_retries_on_429_then_succeeds(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            make_response(status_code=429, headers={}),
            make_response(payload={"symbol": "BTCUSDT", "openInterest": "1"}),
        ]
        client = BinancePublicClient(max_retries=3, backoff_base=1.0)

        result = client.open_interest("BTCUSDT")

        assert result == {"symbol": "BTCUSDT", "openInterest": "1"}
        mock_sleep.assert_called_once_with(1.0)

    @patch("binance_public.time.sleep")
    @patch("binance_public.requests.get")
    def test_retries_on_418_ip_ban(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            make_response(status_code=418, headers={"Retry-After": "10"}),
            make_response(payload={"symbol": "BTCUSDT", "openInterest": "1"}),
        ]
        client = BinancePublicClient(max_retries=3, backoff_base=1.0)

        client.open_interest("BTCUSDT")

        mock_sleep.assert_called_once_with(10.0)

    @patch("binance_public.time.sleep")
    @patch("binance_public.requests.get")
    def test_raises_rate_limit_error_after_exhausting_retries(self, mock_get, mock_sleep):
        mock_get.return_value = make_response(status_code=429, headers={})
        client = BinancePublicClient(max_retries=2, backoff_base=1.0)

        with pytest.raises(RateLimitError):
            client.open_interest("BTCUSDT")

        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2
