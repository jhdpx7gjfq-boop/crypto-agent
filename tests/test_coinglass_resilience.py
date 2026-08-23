"""Rate-limit / quota resilience tests -- kept separate from the P0
functional suite (test_coinglass.py) so the two concerns aren't mixed.
"""

from unittest.mock import Mock, call, patch

import pytest

from coinglass import CoinGlassClient, RateLimitError


def make_response(status_code=200, data=None, code="0", msg="success", headers=None):
    response = Mock()
    response.status_code = status_code
    response.headers = headers or {}
    response.json = lambda: {"code": code, "msg": msg, "data": data if data is not None else []}
    if status_code == 429:
        response.raise_for_status.side_effect = AssertionError("raise_for_status should not be reached on 429")
    else:
        response.raise_for_status = lambda: None
    return response


class TestQuotaTracking:
    @patch("coinglass.requests.get")
    def test_rate_limit_headers_are_recorded(self, mock_get):
        mock_get.return_value = make_response(headers={"API-KEY-MAX-LIMIT": "30", "API-KEY-USE-LIMIT": "1"})
        client = CoinGlassClient(api_key="k")

        client.open_interest_history("binance", "BTCUSDT", "1h")

        assert client.rate_limit_max == "30"
        assert client.rate_limit_used == "1"

    @patch("coinglass.requests.get")
    def test_quota_tracking_reflects_latest_response(self, mock_get):
        client = CoinGlassClient(api_key="k")
        mock_get.return_value = make_response(headers={"API-KEY-MAX-LIMIT": "30", "API-KEY-USE-LIMIT": "1"})
        client.open_interest_history("binance", "BTCUSDT", "1h")
        mock_get.return_value = make_response(headers={"API-KEY-MAX-LIMIT": "30", "API-KEY-USE-LIMIT": "2"})
        client.open_interest_history("binance", "BTCUSDT", "1h")

        assert client.rate_limit_used == "2"

    @patch("coinglass.requests.get")
    def test_missing_quota_headers_do_not_crash(self, mock_get):
        mock_get.return_value = make_response(headers={})
        client = CoinGlassClient(api_key="k")

        client.open_interest_history("binance", "BTCUSDT", "1h")

        assert client.rate_limit_max is None
        assert client.rate_limit_used is None


class TestRateLimit429:
    @patch("coinglass.time.sleep")
    @patch("coinglass.requests.get")
    def test_retries_then_succeeds_after_429(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            make_response(status_code=429, headers={}),
            make_response(data=[{"a": 1}]),
        ]
        client = CoinGlassClient(api_key="k", max_retries=3, backoff_base=1.0)

        result = client.open_interest_history("binance", "BTCUSDT", "1h")

        assert result == [{"a": 1}]
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(1.0)

    @patch("coinglass.time.sleep")
    @patch("coinglass.requests.get")
    def test_raises_rate_limit_error_after_exhausting_retries(self, mock_get, mock_sleep):
        mock_get.return_value = make_response(status_code=429, headers={})
        client = CoinGlassClient(api_key="k", max_retries=2, backoff_base=1.0)

        with pytest.raises(RateLimitError):
            client.open_interest_history("binance", "BTCUSDT", "1h")

        assert mock_get.call_count == 3  # initial attempt + 2 retries
        assert mock_sleep.call_count == 2

    @patch("coinglass.time.sleep")
    @patch("coinglass.requests.get")
    def test_retry_after_header_extends_the_wait(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            make_response(status_code=429, headers={"Retry-After": "5"}),
            make_response(data=[{"a": 1}]),
        ]
        client = CoinGlassClient(api_key="k", max_retries=3, backoff_base=1.0)

        client.open_interest_history("binance", "BTCUSDT", "1h")

        mock_sleep.assert_called_once_with(5.0)

    @patch("coinglass.time.sleep")
    @patch("coinglass.requests.get")
    def test_exponential_backoff_grows_and_is_capped(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            make_response(status_code=429, headers={}),
            make_response(status_code=429, headers={}),
            make_response(status_code=429, headers={}),
            make_response(data=[{"a": 1}]),
        ]
        client = CoinGlassClient(api_key="k", max_retries=5, backoff_base=1.0, backoff_max=3.0)

        client.open_interest_history("binance", "BTCUSDT", "1h")

        assert mock_sleep.call_args_list == [call(1.0), call(2.0), call(3.0)]  # 1, 2, 4 capped at 3


class TestLocalThrottling:
    @patch("coinglass.time.sleep")
    @patch("coinglass.time.monotonic")
    @patch("coinglass.requests.get")
    def test_min_request_interval_spaces_out_calls(self, mock_get, mock_monotonic, mock_sleep):
        mock_get.return_value = make_response(data=[{"a": 1}])
        mock_monotonic.side_effect = [0.0, 0.1, 0.1]  # first call end, throttle check, second call end
        client = CoinGlassClient(api_key="k", min_request_interval=0.5)

        client.open_interest_history("binance", "BTCUSDT", "1h")
        client.open_interest_history("binance", "BTCUSDT", "1h")

        mock_sleep.assert_called_once_with(pytest.approx(0.4))

    @patch("coinglass.time.sleep")
    @patch("coinglass.requests.get")
    def test_no_throttling_by_default(self, mock_get, mock_sleep):
        mock_get.return_value = make_response(data=[{"a": 1}])
        client = CoinGlassClient(api_key="k")

        client.open_interest_history("binance", "BTCUSDT", "1h")
        client.open_interest_history("binance", "BTCUSDT", "1h")

        mock_sleep.assert_not_called()
