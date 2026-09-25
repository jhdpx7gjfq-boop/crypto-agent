from unittest.mock import Mock, patch

import pytest
import requests

from x20_engine import X20Engine


class TestGetOhlcv:
    @patch("x20_engine.requests.get")
    def test_returns_parsed_ohlcv(self, mock_get):
        mock_get.return_value = Mock(
            json=lambda: [
                [1000, "95000", "96000", "94000", "95500", 0, "100000", 1000],
                [2000, "95500", "96500", "95000", "96000", 0, "110000", 1000],
            ]
        )
        engine = X20Engine()
        ohlcv = engine.get_ohlcv()
        assert len(ohlcv) == 2
        assert ohlcv[0]["close"] == 95500.0

    @patch("x20_engine.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")
        mock_get.return_value = mock_response
        engine = X20Engine()
        assert engine.get_ohlcv() is None


class TestCalculateMomentum:
    def test_returns_positive_momentum_on_uptrend(self):
        engine = X20Engine()
        ohlcv = [
            {"close": 100 + i * 0.5} for i in range(20)
        ]
        momentum = engine._calculate_momentum(ohlcv)
        assert momentum > 0

    def test_returns_zero_momentum_on_flat(self):
        engine = X20Engine()
        ohlcv = [{"close": 100.0} for _ in range(20)]
        momentum = engine._calculate_momentum(ohlcv)
        assert 0 <= momentum < 2

    def test_returns_zero_on_insufficient_data(self):
        engine = X20Engine()
        momentum = engine._calculate_momentum([{"close": 100}])
        assert momentum == 0.0


class TestCalculateVolatility:
    def test_returns_higher_volatility_on_wide_swings(self):
        engine = X20Engine()
        ohlcv = [
            {"high": 100 + i, "low": 95 - i, "close": 97.5} for i in range(14)
        ]
        volatility = engine._calculate_volatility(ohlcv)
        assert volatility > 10

    def test_returns_lower_volatility_on_tight_range(self):
        engine = X20Engine()
        ohlcv = [
            {"high": 100.1, "low": 99.9, "close": 100.0} for _ in range(14)
        ]
        volatility = engine._calculate_volatility(ohlcv)
        assert volatility < 5

    def test_returns_zero_on_insufficient_data(self):
        engine = X20Engine()
        volatility = engine._calculate_volatility([{"high": 100, "low": 99}])
        assert volatility == 0.0


class TestCalculateRelativeStrength:
    def test_returns_positive_rs_on_uptrend(self):
        engine = X20Engine()
        ohlcv = [
            {"close": 100 + i * 1.5} for i in range(14)
        ]
        rs = engine._calculate_relative_strength(ohlcv)
        assert rs > 5

    def test_returns_zero_rs_on_downtrend(self):
        engine = X20Engine()
        ohlcv = [
            {"close": 100 - i * 0.5} for i in range(14)
        ]
        rs = engine._calculate_relative_strength(ohlcv)
        assert rs == 0.0

    def test_returns_zero_on_insufficient_data(self):
        engine = X20Engine()
        rs = engine._calculate_relative_strength([{"close": 100}])
        assert rs == 0.0


class TestCalculateLiquidity:
    def test_returns_zero_on_very_low_volume(self):
        engine = X20Engine()
        ohlcv = [{"volume": 1000} for _ in range(20)]
        liquidity = engine._calculate_liquidity(ohlcv)
        assert liquidity == 0.0

    def test_returns_5_on_low_volume(self):
        engine = X20Engine()
        ohlcv = [{"volume": 500000} for _ in range(20)]
        liquidity = engine._calculate_liquidity(ohlcv)
        assert liquidity == 5.0

    def test_returns_10_on_medium_volume(self):
        engine = X20Engine()
        ohlcv = [{"volume": 5000000} for _ in range(20)]
        liquidity = engine._calculate_liquidity(ohlcv)
        assert liquidity == 10.0

    def test_returns_15_on_high_volume(self):
        engine = X20Engine()
        ohlcv = [{"volume": 30000000} for _ in range(20)]
        liquidity = engine._calculate_liquidity(ohlcv)
        assert liquidity == 15.0

    def test_returns_20_on_very_high_volume(self):
        engine = X20Engine()
        ohlcv = [{"volume": 100000000} for _ in range(20)]
        liquidity = engine._calculate_liquidity(ohlcv)
        assert liquidity == 20.0


class TestCalculateRiskReward:
    def test_returns_higher_score_on_winning_candles(self):
        engine = X20Engine()
        ohlcv = [
            {"close": 100 + i * 0.5, "open": 100 + i * 0.4, "high": 101 + i, "low": 99 + i}
            for i in range(10)
        ]
        rr = engine._calculate_risk_reward(ohlcv)
        assert rr > 5

    def test_returns_lower_score_on_losing_candles(self):
        engine = X20Engine()
        ohlcv = [
            {"close": 100 - i * 0.5, "open": 100 - i * 0.4, "high": 101 - i, "low": 99 - i}
            for i in range(10)
        ]
        rr = engine._calculate_risk_reward(ohlcv)
        assert rr < 10

    def test_returns_zero_on_insufficient_data(self):
        engine = X20Engine()
        rr = engine._calculate_risk_reward([{"close": 100, "open": 99}])
        assert rr == 0.0


class TestScoreX20:
    def test_returns_strong_score_on_bullish_setup(self):
        engine = X20Engine()
        ohlcv = [
            {
                "timestamp": i * 1000,
                "close": 100 + i * 0.5,
                "open": 100 + i * 0.4,
                "high": 102 + i,
                "low": 98 + i,
                "volume": 50000000,
            }
            for i in range(100)
        ]
        result = engine.score_x20(ohlcv)
        assert result["x20_score"] >= 50
        assert result["verdict"] in ["STRONG", "MODERATE"]

    def test_returns_weak_score_on_bearish_setup(self):
        engine = X20Engine()
        ohlcv = [
            {
                "timestamp": i * 1000,
                "close": 100 - i * 0.5,
                "open": 100 - i * 0.4,
                "high": 102 - i,
                "low": 98 - i,
                "volume": 1000,
            }
            for i in range(100)
        ]
        result = engine.score_x20(ohlcv)
        assert result["x20_score"] < 50
        assert result["verdict"] == "WEAK"

    def test_returns_zero_on_no_data(self):
        engine = X20Engine()
        result = engine.score_x20(None)
        assert result["x20_score"] == 0
        assert result["current_price"] is None

    def test_result_has_all_fields(self):
        engine = X20Engine()
        ohlcv = [
            {
                "timestamp": 1000,
                "close": 100,
                "open": 99,
                "high": 101,
                "low": 99,
                "volume": 1000000,
            }
        ]
        result = engine.score_x20(ohlcv)
        assert "timestamp" in result
        assert "x20_score" in result
        assert "momentum" in result
        assert "volatility" in result
        assert "relative_strength" in result
        assert "liquidity" in result
        assert "risk_reward" in result
        assert "current_price" in result
        assert "verdict" in result

    def test_verdict_is_strong_on_high_score(self):
        engine = X20Engine()
        ohlcv = [
            {
                "timestamp": i * 1000,
                "close": 100 + i,
                "open": 99 + i,
                "high": 105 + i,
                "low": 95 + i,
                "volume": 100000000,
            }
            for i in range(100)
        ]
        result = engine.score_x20(ohlcv)
        if result["x20_score"] >= 70:
            assert result["verdict"] == "STRONG"

    def test_verdict_is_moderate_on_medium_score(self):
        engine = X20Engine()
        result = engine.score_x20(None)
        if 50 <= result["x20_score"] < 70:
            assert result["verdict"] == "MODERATE"


class TestReport:
    def test_returns_readable_string_when_data_available(self):
        engine = X20Engine()
        with patch.object(engine, "get_ohlcv") as mock_get_ohlcv:
            mock_get_ohlcv.return_value = [
                {
                    "timestamp": 1000,
                    "close": 95000,
                    "open": 94000,
                    "high": 96000,
                    "low": 94000,
                    "volume": 50000000,
                }
            ]
            report = engine.report()
            assert "X20:" in report
            assert "95,000" in report
            assert "/100" in report

    def test_returns_unavailable_on_no_price(self):
        engine = X20Engine()
        with patch.object(engine, "get_ohlcv", return_value=None):
            report = engine.report()
            assert "unavailable" in report.lower()

    def test_report_includes_all_scores(self):
        engine = X20Engine()
        with patch.object(engine, "get_ohlcv") as mock_get_ohlcv:
            mock_get_ohlcv.return_value = [
                {
                    "timestamp": i * 1000,
                    "close": 100 + i * 0.5,
                    "open": 99.5 + i * 0.5,
                    "high": 102 + i,
                    "low": 98 + i,
                    "volume": 50000000,
                }
                for i in range(100)
            ]
            report = engine.report()
            assert "Mom=" in report
            assert "Vol=" in report
            assert "RS=" in report
            assert "Liq=" in report
            assert "RR=" in report
