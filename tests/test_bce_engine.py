from unittest.mock import Mock, patch

import pytest
import requests

from bce_engine import BottomConfirmationEngine


class TestGetOhlcv:
    @patch("bce_engine.requests.get")
    def test_returns_parsed_ohlcv(self, mock_get):
        mock_get.return_value = Mock(
            json=lambda: [
                [1000, "95000", "96000", "94000", "95500", 0, "100000", 1000],
                [2000, "95500", "96500", "95000", "96000", 0, "110000", 1000],
            ]
        )
        engine = BottomConfirmationEngine()
        ohlcv = engine.get_ohlcv()
        assert len(ohlcv) == 2
        assert ohlcv[0]["close"] == 95500.0
        assert ohlcv[0]["volume"] == 1000.0
        assert ohlcv[1]["timestamp"] == 2000

    @patch("bce_engine.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")
        mock_get.return_value = mock_response
        engine = BottomConfirmationEngine()
        assert engine.get_ohlcv() is None

    @patch("bce_engine.requests.get")
    def test_returns_none_on_malformed_data(self, mock_get):
        mock_get.return_value = Mock(json=lambda: [["invalid"]])
        engine = BottomConfirmationEngine()
        assert engine.get_ohlcv() is None

    @patch("bce_engine.requests.get")
    def test_uses_custom_symbol(self, mock_get):
        mock_get.return_value = Mock(json=lambda: [])
        engine = BottomConfirmationEngine(symbol="ETHUSDT")
        engine.get_ohlcv()
        call_args = mock_get.call_args
        assert call_args[1]["params"]["symbol"] == "ETHUSDT"


class TestCalculateSupportResistance:
    def test_returns_min_low_as_support(self):
        engine = BottomConfirmationEngine()
        ohlcv = [
            {"low": 1000, "high": 1100},
            {"low": 950, "high": 1050},
            {"low": 1020, "high": 1120},
        ]
        sr = engine._calculate_support_resistance(ohlcv)
        assert sr["support"] == 950

    def test_returns_max_high_as_resistance(self):
        engine = BottomConfirmationEngine()
        ohlcv = [
            {"low": 1000, "high": 1100},
            {"low": 950, "high": 1150},
            {"low": 1020, "high": 1120},
        ]
        sr = engine._calculate_support_resistance(ohlcv)
        assert sr["resistance"] == 1150

    def test_handles_insufficient_data(self):
        engine = BottomConfirmationEngine()
        sr = engine._calculate_support_resistance([])
        assert sr["support"] is None
        assert sr["resistance"] is None


class TestCalculateRelativeVolume:
    def test_returns_one_when_no_history(self):
        engine = BottomConfirmationEngine()
        rel_vol = engine._calculate_relative_volume([{"volume": 1000}])
        assert rel_vol == 1.0

    def test_calculates_current_vs_average(self):
        engine = BottomConfirmationEngine()
        ohlcv = [{"volume": 1000} for _ in range(21)]
        ohlcv[-1]["volume"] = 2000
        rel_vol = engine._calculate_relative_volume(ohlcv)
        assert rel_vol > 1.9

    def test_handles_zero_average_volume(self):
        engine = BottomConfirmationEngine()
        ohlcv = [{"volume": 0} for _ in range(21)]
        rel_vol = engine._calculate_relative_volume(ohlcv)
        assert rel_vol == 1.0


class TestDetectExhaustion:
    def test_returns_high_exhaustion_on_low_volume_bounce(self):
        engine = BottomConfirmationEngine()
        ohlcv = [
            {"close": 100, "volume": 1000},
            {"close": 101, "volume": 1000},
            {"close": 99, "volume": 1000},
            {"close": 100, "volume": 1000},
            {"close": 101, "volume": 500},
            {"close": 102, "volume": 600},
            {"close": 101, "volume": 700},
            {"close": 102, "volume": 800},
            {"close": 103, "volume": 900},
            {"close": 104, "volume": 500},
            {"close": 105, "volume": 600},
            {"close": 106, "volume": 550},
            {"close": 107, "volume": 600},
            {"close": 108, "volume": 500},
            {"close": 109, "volume": 400},
        ]
        score = engine._detect_exhaustion(ohlcv)
        assert score == 2

    def test_returns_moderate_on_high_volume_decline_no_bounce(self):
        engine = BottomConfirmationEngine()
        ohlcv = [
            {"close": 100, "volume": 500},
            {"close": 99, "volume": 500},
            {"close": 98, "volume": 500},
            {"close": 97, "volume": 500},
            {"close": 96, "volume": 500},
            {"close": 95, "volume": 2000},
            {"close": 94, "volume": 2500},
            {"close": 93, "volume": 2200},
            {"close": 92, "volume": 2300},
            {"close": 91, "volume": 2100},
            {"close": 90, "volume": 2400},
            {"close": 89, "volume": 2200},
            {"close": 88, "volume": 2300},
            {"close": 87, "volume": 2000},
            {"close": 86, "volume": 2100},
        ]
        score = engine._detect_exhaustion(ohlcv)
        assert score == 1


class TestDetectAccumulation:
    def test_returns_high_accumulation_on_tight_range_balanced(self):
        engine = BottomConfirmationEngine()
        ohlcv = [
            {"close": 100, "open": 99, "high": 101, "low": 99, "volume": 1000},
            {"close": 101, "open": 100, "high": 102, "low": 100, "volume": 1100},
            {"close": 100.5, "open": 101, "high": 101.5, "low": 100, "volume": 1050},
            {"close": 101.2, "open": 100.5, "high": 101.5, "low": 100.5, "volume": 1150},
            {"close": 100.8, "open": 101.2, "high": 101.5, "low": 100.5, "volume": 1080},
            {"close": 101.5, "open": 100.8, "high": 102, "low": 100.8, "volume": 1120},
            {"close": 101, "open": 101.5, "high": 101.5, "low": 100.8, "volume": 1090},
            {"close": 100.9, "open": 101, "high": 101.5, "low": 100.8, "volume": 1100},
            {"close": 101.3, "open": 100.9, "high": 101.5, "low": 100.9, "volume": 1110},
            {"close": 101.1, "open": 101.3, "high": 101.5, "low": 100.9, "volume": 1095},
        ]
        score = engine._detect_accumulation(ohlcv)
        assert score == 2

    def test_returns_zero_on_wide_range_downtrend(self):
        engine = BottomConfirmationEngine()
        ohlcv = [
            {"close": 100, "open": 105, "high": 105, "low": 100, "volume": 500},
            {"close": 95, "open": 100, "high": 100, "low": 95, "volume": 500},
            {"close": 90, "open": 95, "high": 95, "low": 90, "volume": 500},
            {"close": 85, "open": 90, "high": 90, "low": 85, "volume": 500},
            {"close": 80, "open": 85, "high": 85, "low": 80, "volume": 500},
            {"close": 75, "open": 80, "high": 80, "low": 75, "volume": 500},
            {"close": 70, "open": 75, "high": 75, "low": 70, "volume": 500},
            {"close": 65, "open": 70, "high": 70, "low": 65, "volume": 500},
            {"close": 60, "open": 65, "high": 65, "low": 60, "volume": 500},
            {"close": 55, "open": 60, "high": 60, "low": 55, "volume": 500},
        ]
        score = engine._detect_accumulation(ohlcv)
        assert score == 0


class TestAnalyzePriceStructure:
    def test_returns_downtrend_on_lower_lows_highs(self):
        engine = BottomConfirmationEngine()
        ohlcv = [
            {"low": 100, "high": 110},
            {"low": 98, "high": 108},
            {"low": 96, "high": 106},
            {"low": 94, "high": 104},
            {"low": 92, "high": 102},
            {"low": 90, "high": 100},
            {"low": 88, "high": 98},
            {"low": 86, "high": 96},
            {"low": 84, "high": 94},
            {"low": 82, "high": 92},
        ]
        score = engine._analyze_price_structure(ohlcv)
        assert score == 0

    def test_returns_accumulation_on_stable_structure(self):
        engine = BottomConfirmationEngine()
        ohlcv = [
            {"low": 90, "high": 110},
            {"low": 91, "high": 109},
            {"low": 92, "high": 108},
            {"low": 91, "high": 109},
            {"low": 92, "high": 110},
            {"low": 91, "high": 109},
            {"low": 92, "high": 111},
            {"low": 91, "high": 110},
            {"low": 92, "high": 111},
            {"low": 91, "high": 110},
        ]
        score = engine._analyze_price_structure(ohlcv)
        assert score >= 1


class TestScoreBce:
    def test_returns_valid_bce_score_on_accumulation(self):
        engine = BottomConfirmationEngine()
        ohlcv = [
            {"timestamp": i * 1000, "close": 100 + i * 0.1, "open": 100 + i * 0.05, "high": 101 + i * 0.1, "low": 99 + i * 0.1, "volume": 1000}
            for i in range(20)
        ]
        result = engine.score_bce(ohlcv)
        assert "bce_score" in result
        assert 0 <= result["bce_score"] <= 6
        assert result["current_price"] == ohlcv[-1]["close"]

    def test_returns_zero_on_downtrend(self):
        engine = BottomConfirmationEngine()
        ohlcv = [
            {"timestamp": i * 1000, "close": 100 - i, "open": 101 - i, "high": 102 - i, "low": 99 - i, "volume": 1000}
            for i in range(20)
        ]
        result = engine.score_bce(ohlcv)
        assert result["bce_score"] == 0

    def test_returns_neutral_on_insufficient_data(self):
        engine = BottomConfirmationEngine()
        result = engine.score_bce(None)
        assert result["bce_score"] == 0
        assert result["current_price"] is None

    def test_result_has_required_fields(self):
        engine = BottomConfirmationEngine()
        ohlcv = [
            {"timestamp": 1000, "close": 100, "open": 99, "high": 101, "low": 99, "volume": 1000}
        ]
        result = engine.score_bce(ohlcv)
        assert "timestamp" in result
        assert "bce_score" in result
        assert "exhaustion" in result
        assert "accumulation" in result
        assert "structure" in result
        assert "relative_volume" in result
        assert "support" in result
        assert "resistance" in result
        assert "current_price" in result


class TestReport:
    def test_returns_readable_string_when_data_available(self):
        engine = BottomConfirmationEngine()
        with patch.object(engine, "get_ohlcv") as mock_get_ohlcv:
            mock_get_ohlcv.return_value = [
                {"timestamp": 1000, "close": 95000, "open": 94000, "high": 96000, "low": 94000, "volume": 2000}
            ]
            report = engine.report()
            assert "BCE:" in report
            assert "95,000" in report
            assert "/6" in report

    def test_returns_unavailable_on_no_price(self):
        engine = BottomConfirmationEngine()
        with patch.object(engine, "get_ohlcv", return_value=None):
            report = engine.report()
            assert "unavailable" in report.lower()

    def test_report_includes_verdict(self):
        engine = BottomConfirmationEngine()
        with patch.object(engine, "get_ohlcv") as mock_get_ohlcv:
            mock_get_ohlcv.return_value = [
                {"timestamp": i * 1000, "close": 100 + i * 0.1, "open": 100 + i * 0.05, "high": 101 + i * 0.1, "low": 99 + i * 0.1, "volume": 1000}
                for i in range(20)
            ]
            report = engine.report()
            assert "VALID" in report or "INVALID" in report
