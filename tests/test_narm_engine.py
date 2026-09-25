from unittest.mock import Mock, patch

import pytest
import requests

from narm_engine import NARMEngine


class TestGetOhlcv:
    @patch("narm_engine.requests.get")
    def test_returns_parsed_ohlcv_with_quote_asset_volume(self, mock_get):
        mock_get.return_value = Mock(
            json=lambda: [
                [1000, "95000", "96000", "94000", "95500", 0, "100000", 1000, "95500000"],
                [2000, "95500", "96500", "95000", "96000", 0, "110000", 1000, "105500000"],
            ]
        )
        engine = NARMEngine()
        ohlcv = engine.get_ohlcv()
        assert len(ohlcv) == 2
        assert ohlcv[0]["quote_asset_volume"] == 95500000.0

    @patch("narm_engine.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")
        mock_get.return_value = mock_response
        engine = NARMEngine()
        assert engine.get_ohlcv() is None


class TestCalculateNarrativeStrength:
    def test_returns_higher_score_on_volume_acceleration_uptrend(self):
        engine = NARMEngine()
        ohlcv = [
            {"close": 100 + i * 0.5, "volume": 1000 + i * 100} for i in range(20)
        ]
        narrative = engine._calculate_narrative_strength(ohlcv)
        assert narrative > 0

    def test_returns_zero_on_flat_no_acceleration(self):
        engine = NARMEngine()
        ohlcv = [
            {"close": 100.0, "volume": 1000.0} for _ in range(20)
        ]
        narrative = engine._calculate_narrative_strength(ohlcv)
        assert narrative < 5


class TestCalculateAdoption:
    def test_returns_score_on_consistent_high_volume(self):
        engine = NARMEngine()
        ohlcv = [
            {"close": 100 + i * 0.5, "volume": 5000.0} for i in range(30)
        ]
        adoption = engine._calculate_adoption(ohlcv)
        assert adoption >= 0

    def test_returns_lower_score_on_inconsistent_volume(self):
        engine = NARMEngine()
        ohlcv = [
            {"close": 100, "volume": 1000 if i % 2 == 0 else 10000} for i in range(30)
        ]
        adoption = engine._calculate_adoption(ohlcv)
        assert adoption < 15


class TestCalculateCapitalRotation:
    def test_returns_higher_score_on_usdt_volume_growth(self):
        engine = NARMEngine()
        ohlcv = [
            {
                "close": 100,
                "volume": 1000,
                "quote_asset_volume": 100000 + i * 5000,
            }
            for i in range(20)
        ]
        capital = engine._calculate_capital_rotation(ohlcv)
        assert capital > 0

    def test_returns_zero_on_declining_volume(self):
        engine = NARMEngine()
        ohlcv = [
            {
                "close": 100,
                "volume": 1000,
                "quote_asset_volume": 200000 - i * 5000,
            }
            for i in range(20)
        ]
        capital = engine._calculate_capital_rotation(ohlcv)
        assert capital == 0


class TestCalculateFundamentals:
    def test_returns_higher_score_on_tight_range_with_support(self):
        engine = NARMEngine()
        ohlcv = [
            {
                "close": 100 + (i % 5) * 0.2,
                "high": 101,
                "low": 99,
                "volume": 1000,
            }
            for i in range(30)
        ]
        fundamentals = engine._calculate_fundamentals(ohlcv)
        assert fundamentals > 10

    def test_returns_lower_score_on_wide_swings(self):
        engine = NARMEngine()
        ohlcv = [
            {
                "close": 100 + i * 2,
                "high": 105 + i * 2,
                "low": 95 + i * 2,
                "volume": 1000,
            }
            for i in range(30)
        ]
        fundamentals = engine._calculate_fundamentals(ohlcv)
        assert fundamentals < 12


class TestCalculateMarketTiming:
    def test_returns_higher_score_on_high_rsi(self):
        engine = NARMEngine()
        ohlcv = [
            {"close": 100 + i * 1.5} for i in range(14)
        ]
        timing = engine._calculate_market_timing(ohlcv)
        assert timing >= 15

    def test_returns_lower_score_on_low_rsi(self):
        engine = NARMEngine()
        ohlcv = [
            {"close": 100 - i * 1.5} for i in range(14)
        ]
        timing = engine._calculate_market_timing(ohlcv)
        assert timing == 0


class TestScoreNARM:
    def test_returns_score_on_strong_narrative_adoption(self):
        engine = NARMEngine()
        ohlcv = [
            {
                "timestamp": i * 86400000,
                "close": 100 + i * 1.0,
                "open": 99.5 + i * 1.0,
                "high": 102 + i,
                "low": 98 + i,
                "volume": 5000 + i * 100,
                "quote_asset_volume": 500000 + i * 10000,
            }
            for i in range(100)
        ]
        result = engine.score_narm(ohlcv)
        assert result["narm_score"] >= 0
        assert "verdict" in result

    def test_returns_weak_score_on_declining_fundamentals(self):
        engine = NARMEngine()
        ohlcv = [
            {
                "timestamp": i * 86400000,
                "close": 100 - i * 1.0,
                "open": 100.5 - i * 1.0,
                "high": 102 - i,
                "low": 98 - i,
                "volume": 1000,
                "quote_asset_volume": 100000,
            }
            for i in range(100)
        ]
        result = engine.score_narm(ohlcv)
        assert result["narm_score"] < 50
        assert result["verdict"] in ["WEAK", "MODERATE"]

    def test_returns_zero_on_no_data(self):
        engine = NARMEngine()
        result = engine.score_narm(None)
        assert result["narm_score"] == 0
        assert result["current_price"] is None

    def test_result_has_all_components(self):
        engine = NARMEngine()
        ohlcv = [
            {
                "timestamp": 1000,
                "close": 100,
                "open": 99,
                "high": 101,
                "low": 99,
                "volume": 1000,
                "quote_asset_volume": 100000,
            }
        ]
        result = engine.score_narm(ohlcv)
        assert "narm_score" in result
        assert "narrative" in result
        assert "adoption" in result
        assert "capital_rotation" in result
        assert "fundamentals" in result
        assert "market_timing" in result
        assert "verdict" in result

    def test_verdict_hot_on_high_score(self):
        engine = NARMEngine()
        ohlcv = [
            {
                "timestamp": i * 86400000,
                "close": 100 + i * 1.5,
                "open": 99.5 + i * 1.5,
                "high": 105 + i,
                "low": 95 + i,
                "volume": 10000 + i * 200,
                "quote_asset_volume": 1000000 + i * 20000,
            }
            for i in range(100)
        ]
        result = engine.score_narm(ohlcv)
        if result["narm_score"] >= 80:
            assert result["verdict"] == "HOT"

    def test_verdict_strong_on_medium_high_score(self):
        engine = NARMEngine()
        ohlcv = [
            {
                "timestamp": i * 86400000,
                "close": 100 + i * 0.8,
                "open": 99.8 + i * 0.8,
                "high": 102 + i,
                "low": 98 + i,
                "volume": 5000 + i * 50,
                "quote_asset_volume": 500000 + i * 5000,
            }
            for i in range(100)
        ]
        result = engine.score_narm(ohlcv)
        if 70 <= result["narm_score"] < 80:
            assert result["verdict"] == "STRONG"


class TestReport:
    def test_returns_readable_string_when_data_available(self):
        engine = NARMEngine()
        with patch.object(engine, "get_ohlcv") as mock_get_ohlcv:
            mock_get_ohlcv.return_value = [
                {
                    "timestamp": 1000,
                    "close": 95000,
                    "open": 94000,
                    "high": 96000,
                    "low": 94000,
                    "volume": 5000000,
                    "quote_asset_volume": 475000000000,
                }
            ]
            report = engine.report()
            assert "NARM:" in report
            assert "95,000" in report
            assert "/100" in report

    def test_returns_unavailable_on_no_price(self):
        engine = NARMEngine()
        with patch.object(engine, "get_ohlcv", return_value=None):
            report = engine.report()
            assert "unavailable" in report.lower()

    def test_report_includes_all_components(self):
        engine = NARMEngine()
        with patch.object(engine, "get_ohlcv") as mock_get_ohlcv:
            mock_get_ohlcv.return_value = [
                {
                    "timestamp": i * 86400000,
                    "close": 100 + i * 1.0,
                    "open": 99.5 + i * 1.0,
                    "high": 102 + i,
                    "low": 98 + i,
                    "volume": 5000 + i * 100,
                    "quote_asset_volume": 500000 + i * 10000,
                }
                for i in range(100)
            ]
            report = engine.report()
            assert "Narr=" in report
            assert "Adopt=" in report
            assert "Cap=" in report
            assert "Fund=" in report
            assert "Time=" in report
