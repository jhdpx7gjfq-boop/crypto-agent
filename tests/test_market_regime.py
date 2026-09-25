from unittest.mock import Mock, patch

import pytest
import requests

from market_regime import MarketRegimeEngine


class TestGetBtcPrice:
    @patch("market_regime.requests.get")
    def test_returns_price_from_response(self, mock_get):
        mock_get.return_value = Mock(json=lambda: {"price": "95000.50"})
        engine = MarketRegimeEngine()
        assert engine.get_btc_price() == 95000.50

    @patch("market_regime.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")
        mock_get.return_value = mock_response
        engine = MarketRegimeEngine()
        assert engine.get_btc_price() is None

    @patch("market_regime.requests.get")
    def test_returns_none_on_malformed_response(self, mock_get):
        mock_get.return_value = Mock(json=lambda: {})
        engine = MarketRegimeEngine()
        assert engine.get_btc_price() is None

    @patch("market_regime.requests.get")
    def test_returns_none_on_timeout(self, mock_get):
        mock_get.side_effect = requests.Timeout("timeout")
        engine = MarketRegimeEngine()
        assert engine.get_btc_price() is None


class TestGetBtcFundingRate:
    @patch("market_regime.requests.get")
    def test_returns_funding_rate_from_response(self, mock_get):
        mock_get.return_value = Mock(json=lambda: [{"fundingRate": "0.00075"}])
        engine = MarketRegimeEngine()
        assert engine.get_btc_funding_rate() == 0.00075

    @patch("market_regime.requests.get")
    def test_returns_none_on_empty_response(self, mock_get):
        mock_get.return_value = Mock(json=lambda: [])
        engine = MarketRegimeEngine()
        assert engine.get_btc_funding_rate() is None

    @patch("market_regime.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500")
        mock_get.return_value = mock_response
        engine = MarketRegimeEngine()
        assert engine.get_btc_funding_rate() is None

    @patch("market_regime.requests.get")
    def test_returns_none_on_malformed_response(self, mock_get):
        mock_get.return_value = Mock(json=lambda: [{"wrongKey": "value"}])
        engine = MarketRegimeEngine()
        assert engine.get_btc_funding_rate() is None


class TestGetBtcOpenInterest:
    @patch("market_regime.requests.get")
    def test_returns_open_interest_from_response(self, mock_get):
        mock_get.return_value = Mock(json=lambda: {"openInterest": "42500000000.50"})
        engine = MarketRegimeEngine()
        assert engine.get_btc_open_interest() == 42500000000.50

    @patch("market_regime.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403")
        mock_get.return_value = mock_response
        engine = MarketRegimeEngine()
        assert engine.get_btc_open_interest() is None

    @patch("market_regime.requests.get")
    def test_returns_none_on_malformed_response(self, mock_get):
        mock_get.return_value = Mock(json=lambda: {})
        engine = MarketRegimeEngine()
        assert engine.get_btc_open_interest() is None


class TestDetectRegime:
    def test_bullish_greed_when_funding_high(self):
        engine = MarketRegimeEngine()
        regime = engine.detect_regime(btc_price=95000.0, funding_rate=0.001)
        assert regime["regime"] == "bullish_greed"
        assert regime["score"] > 50
        assert regime["btc_price"] == 95000.0
        assert regime["funding_rate"] == 0.001

    def test_bearish_when_funding_negative(self):
        engine = MarketRegimeEngine()
        regime = engine.detect_regime(btc_price=85000.0, funding_rate=-0.001)
        assert regime["regime"] == "bearish"
        assert regime["score"] < 50
        assert regime["btc_price"] == 85000.0

    def test_neutral_when_funding_neutral(self):
        engine = MarketRegimeEngine()
        regime = engine.detect_regime(btc_price=90000.0, funding_rate=0.00001)
        assert regime["regime"] == "neutral"
        assert regime["score"] == 50

    def test_returns_neutral_when_price_missing(self):
        engine = MarketRegimeEngine()
        regime = engine.detect_regime(btc_price=None, funding_rate=0.001)
        assert regime["regime"] == "neutral"
        assert regime["score"] == 50
        assert regime["btc_price"] is None

    def test_returns_neutral_when_funding_missing(self):
        engine = MarketRegimeEngine()
        regime = engine.detect_regime(btc_price=95000.0, funding_rate=None)
        assert regime["regime"] == "neutral"
        assert regime["score"] == 50
        assert regime["funding_rate"] is None

    def test_fetches_data_when_not_provided(self):
        engine = MarketRegimeEngine()
        with patch.object(engine, "get_btc_price", return_value=95000.0):
            with patch.object(engine, "get_btc_funding_rate", return_value=0.001):
                regime = engine.detect_regime()
                assert regime["btc_price"] == 95000.0
                assert regime["funding_rate"] == 0.001
                assert regime["regime"] == "bullish_greed"

    def test_regime_data_has_timestamp(self):
        engine = MarketRegimeEngine()
        regime = engine.detect_regime(btc_price=95000.0, funding_rate=0.001)
        assert "timestamp" in regime
        assert regime["timestamp"] is not None


class TestReport:
    def test_returns_readable_string_when_data_available(self):
        engine = MarketRegimeEngine()
        with patch.object(engine, "get_btc_price", return_value=95000.0):
            with patch.object(engine, "get_btc_funding_rate", return_value=0.00075):
                report = engine.report()
                assert "BULLISH_GREED" in report
                assert "95,000" in report
                assert "0.075%" in report

    def test_returns_unavailable_message_when_no_price(self):
        engine = MarketRegimeEngine()
        with patch.object(engine, "get_btc_price", return_value=None):
            with patch.object(engine, "get_btc_funding_rate", return_value=0.001):
                report = engine.report()
                assert "unavailable" in report.lower()

    def test_handles_none_funding_rate_in_report(self):
        engine = MarketRegimeEngine()
        with patch.object(engine, "get_btc_price", return_value=95000.0):
            with patch.object(engine, "get_btc_funding_rate", return_value=None):
                report = engine.report()
                assert "NEUTRAL" in report
                assert "N/A" in report
