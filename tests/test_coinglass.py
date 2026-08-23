from unittest.mock import Mock, patch

import pytest
import requests

from coinglass import BASE_URL, COINGLASS_DATA_STATUS, CoinGlassAPIError, CoinGlassClient


def test_data_status_is_unverified_until_real_api_evidence_is_recorded():
    # Passing unit tests only prove the client behaves correctly against
    # mocked responses -- see ENDPOINT_VALIDATION.md for what actually
    # promotes this to API_VERIFIED and beyond.
    assert COINGLASS_DATA_STATUS == "UNVERIFIED"


def make_response(data=None, code="0", msg="success"):
    return Mock(
        raise_for_status=lambda: None,
        json=lambda: {"code": code, "msg": msg, "data": data if data is not None else []},
    )


class TestClientInit:
    def test_uses_explicit_api_key(self):
        client = CoinGlassClient(api_key="explicit-key")
        assert client.api_key == "explicit-key"

    @patch.dict("os.environ", {"COINGLASS_API_KEY": "env-key"})
    def test_falls_back_to_env_var(self):
        client = CoinGlassClient()
        assert client.api_key == "env-key"

    @patch.dict("os.environ", {}, clear=True)
    def test_raises_when_no_key_available(self):
        with pytest.raises(KeyError):
            CoinGlassClient()


class TestGet:
    @patch("coinglass.requests.get")
    def test_sends_api_key_header_and_drops_none_params(self, mock_get):
        mock_get.return_value = make_response(data=[{"a": 1}])
        client = CoinGlassClient(api_key="k")

        result = client.open_interest_history("binance", "BTCUSDT", "1h", limit=None)

        assert result == [{"a": 1}]
        args, kwargs = mock_get.call_args
        assert args[0] == f"{BASE_URL}/api/futures/open-interest/history"
        assert kwargs["headers"]["CG-API-KEY"] == "k"
        assert kwargs["params"] == {"exchange": "binance", "symbol": "BTCUSDT", "interval": "1h"}

    @patch("coinglass.requests.get")
    def test_raises_coinglass_error_on_non_zero_code(self, mock_get):
        mock_get.return_value = make_response(code="1", msg="invalid api key")
        client = CoinGlassClient(api_key="k")

        with pytest.raises(CoinGlassAPIError, match="invalid api key"):
            client.open_interest_history("binance", "BTCUSDT", "1h")

    @patch("coinglass.requests.get")
    def test_propagates_http_errors(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("boom")
        mock_get.return_value = mock_response
        client = CoinGlassClient(api_key="k")

        with pytest.raises(requests.HTTPError):
            client.open_interest_history("binance", "BTCUSDT", "1h")


class TestEndpointPaths:
    @patch("coinglass.requests.get")
    def test_open_interest_aggregated_history(self, mock_get):
        mock_get.return_value = make_response()
        CoinGlassClient(api_key="k").open_interest_aggregated_history("BTC", "1h")
        assert mock_get.call_args[0][0] == f"{BASE_URL}/api/futures/open-interest/aggregated-history"

    @patch("coinglass.requests.get")
    def test_funding_rate_history(self, mock_get):
        mock_get.return_value = make_response()
        CoinGlassClient(api_key="k").funding_rate_history("binance", "BTCUSDT", "8h")
        assert mock_get.call_args[0][0] == f"{BASE_URL}/api/futures/funding-rate/history"

    @patch("coinglass.requests.get")
    def test_funding_rate_oi_weighted_history(self, mock_get):
        mock_get.return_value = make_response()
        CoinGlassClient(api_key="k").funding_rate_oi_weighted_history("BTC", "8h")
        assert mock_get.call_args[0][0] == f"{BASE_URL}/api/futures/funding-rate/oi-weight-history"

    @patch("coinglass.requests.get")
    def test_funding_rate_vol_weighted_history(self, mock_get):
        mock_get.return_value = make_response()
        CoinGlassClient(api_key="k").funding_rate_vol_weighted_history("BTC", "8h")
        assert mock_get.call_args[0][0] == f"{BASE_URL}/api/futures/funding-rate/vol-weight-history"

    @patch("coinglass.requests.get")
    def test_liquidation_history(self, mock_get):
        mock_get.return_value = make_response()
        CoinGlassClient(api_key="k").liquidation_history("binance", "BTCUSDT", "1h")
        assert mock_get.call_args[0][0] == f"{BASE_URL}/api/futures/liquidation/history"

    @patch("coinglass.requests.get")
    def test_liquidation_aggregated_history(self, mock_get):
        mock_get.return_value = make_response()
        CoinGlassClient(api_key="k").liquidation_aggregated_history("BTC", "1h")
        assert mock_get.call_args[0][0] == f"{BASE_URL}/api/futures/liquidation/aggregated-history"

    @patch("coinglass.requests.get")
    def test_spot_cvd_history(self, mock_get):
        mock_get.return_value = make_response()
        CoinGlassClient(api_key="k").spot_cvd_history("binance", "BTCUSDT", "1h")
        assert mock_get.call_args[0][0] == f"{BASE_URL}/api/spot/cvd/history"

    @patch("coinglass.requests.get")
    def test_futures_cvd_history(self, mock_get):
        mock_get.return_value = make_response()
        CoinGlassClient(api_key="k").futures_cvd_history("binance", "BTCUSDT", "1h")
        assert mock_get.call_args[0][0] == f"{BASE_URL}/api/futures/cvd/history"

    @patch("coinglass.requests.get")
    def test_spot_coin_netflow(self, mock_get):
        mock_get.return_value = make_response()
        CoinGlassClient(api_key="k").spot_coin_netflow("BTC", "1h")
        assert mock_get.call_args[0][0] == f"{BASE_URL}/api/spot/coin/netflow"
