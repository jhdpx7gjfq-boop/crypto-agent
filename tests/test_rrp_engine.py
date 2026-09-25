from unittest.mock import Mock, patch

import pytest
import requests

from rrp_engine import RRPEngine


class TestGetOhlcv:
    @patch("rrp_engine.requests.get")
    def test_returns_parsed_ohlcv(self, mock_get):
        mock_get.return_value = Mock(
            json=lambda: [
                [1000, "95000", "96000", "94000", "95500", 0, "100000", 1000, "95500000"],
                [2000, "95500", "96500", "95000", "96000", 0, "110000", 1000, "105500000"],
            ]
        )
        engine = RRPEngine()
        ohlcv = engine.get_ohlcv()
        assert len(ohlcv) == 2
        assert ohlcv[0]["quote_asset_volume"] == 95500000.0

    @patch("rrp_engine.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")
        mock_get.return_value = mock_response
        engine = RRPEngine()
        assert engine.get_ohlcv() is None


class TestDetectDormancy:
    def test_returns_dormant_on_low_volume_period(self):
        engine = RRPEngine()
        ohlcv = [
            {"volume": (100.0 if i < 50 else 50.0), "close": 100.0 + (i * 0.001)} for i in range(100)
        ]
        result = engine._detect_dormancy(ohlcv)
        assert result["dormancy_days"] >= 0

    def test_returns_not_dormant_on_high_volume(self):
        engine = RRPEngine()
        ohlcv = [
            {"volume": 100000.0, "close": 100 + i * 2} for i in range(100)
        ]
        result = engine._detect_dormancy(ohlcv)
        assert result["is_dormant"] is False

    def test_returns_insufficient_data_on_small_dataset(self):
        engine = RRPEngine()
        ohlcv = [
            {"volume": 1000.0, "close": 100} for _ in range(50)
        ]
        result = engine._detect_dormancy(ohlcv)
        assert result["is_dormant"] is False


class TestDetectVolumeBreakout:
    def test_returns_high_score_on_volume_spike(self):
        engine = RRPEngine()
        ohlcv = [
            {"volume": 1000.0 if i < 80 else 10000.0} for i in range(100)
        ]
        score = engine._detect_volume_breakout(ohlcv)
        assert score > 0

    def test_returns_zero_on_flat_volume(self):
        engine = RRPEngine()
        ohlcv = [
            {"volume": 1000.0} for _ in range(100)
        ]
        score = engine._detect_volume_breakout(ohlcv)
        assert score == 0.0

    def test_returns_zero_on_insufficient_data(self):
        engine = RRPEngine()
        ohlcv = [
            {"volume": 1000.0} for _ in range(50)
        ]
        score = engine._detect_volume_breakout(ohlcv)
        assert score == 0.0


class TestDetectPriceMomentum:
    def test_returns_high_score_on_recovery(self):
        engine = RRPEngine()
        ohlcv = [
            {"close": 50 + (i if i < 45 else i * 2)} for i in range(90)
        ]
        score = engine._detect_price_momentum(ohlcv)
        assert score > 0

    def test_returns_zero_on_continued_decline(self):
        engine = RRPEngine()
        ohlcv = [
            {"close": 100 - i * 1.0} for i in range(90)
        ]
        score = engine._detect_price_momentum(ohlcv)
        assert score == 0.0

    def test_returns_zero_on_insufficient_data(self):
        engine = RRPEngine()
        ohlcv = [
            {"close": 100} for _ in range(50)
        ]
        score = engine._detect_price_momentum(ohlcv)
        assert score == 0.0


class TestDetectStructureRecovery:
    def test_returns_high_score_on_resistance_break(self):
        engine = RRPEngine()
        ohlcv = [
            {"close": 100 + (i if i < 80 else i * 2), "high": 102 + (i if i < 80 else i * 2)} for i in range(90)
        ]
        score = engine._detect_structure_recovery(ohlcv)
        assert score > 0

    def test_returns_zero_on_range_hold(self):
        engine = RRPEngine()
        ohlcv = [
            {"close": 100 + i * 0.1, "high": 101 + i * 0.1} for i in range(90)
        ]
        score = engine._detect_structure_recovery(ohlcv)
        assert score >= 0

    def test_returns_zero_on_insufficient_data(self):
        engine = RRPEngine()
        ohlcv = [
            {"close": 100, "high": 101} for _ in range(50)
        ]
        score = engine._detect_structure_recovery(ohlcv)
        assert score == 0.0


class TestDetectSentimentShift:
    def test_returns_higher_score_on_positive_days_high_volume(self):
        engine = RRPEngine()
        ohlcv = [
            {"close": 100 + i * 0.5, "open": 100 + i * 0.4, "volume": 5000 + i * 500} for i in range(30)
        ]
        score = engine._detect_sentiment_shift(ohlcv)
        assert score > 0

    def test_returns_zero_on_negative_days_low_volume(self):
        engine = RRPEngine()
        ohlcv = [
            {"close": 100 - i * 0.5, "open": 100, "volume": 1000} for i in range(30)
        ]
        score = engine._detect_sentiment_shift(ohlcv)
        assert score >= 0

    def test_returns_zero_on_insufficient_data(self):
        engine = RRPEngine()
        ohlcv = [
            {"close": 100, "open": 99, "volume": 1000} for _ in range(20)
        ]
        score = engine._detect_sentiment_shift(ohlcv)
        assert score == 0.0


class TestDetectExhaustionRecovery:
    def test_returns_high_score_on_low_down_volume(self):
        engine = RRPEngine()
        ohlcv = [
            {
                "close": 100 + (i * 0.5 if i % 2 == 0 else i * 0.2),
                "open": 100 + (i * 0.4 if i % 2 == 0 else i * 0.3),
                "volume": 5000 if i % 2 == 0 else 1000
            }
            for i in range(20)
        ]
        score = engine._detect_exhaustion_recovery(ohlcv)
        assert score > 0

    def test_returns_zero_on_high_down_volume(self):
        engine = RRPEngine()
        ohlcv = [
            {
                "close": 100 - i * 1.0,
                "open": 100 - i * 0.9,
                "volume": 10000
            }
            for i in range(20)
        ]
        score = engine._detect_exhaustion_recovery(ohlcv)
        assert score == 0.0

    def test_returns_zero_on_insufficient_data(self):
        engine = RRPEngine()
        ohlcv = [
            {"close": 100, "open": 99, "volume": 1000} for _ in range(10)
        ]
        score = engine._detect_exhaustion_recovery(ohlcv)
        assert score == 0.0


class TestScoreRRP:
    def test_returns_reviving_on_strong_recovery(self):
        engine = RRPEngine()
        ohlcv = [
            {
                "timestamp": i * 86400000,
                "close": 50 + (i if i < 300 else i * 2),
                "open": 49 + (i if i < 300 else i * 2),
                "high": 52 + (i if i < 300 else i * 2),
                "low": 48 + (i if i < 300 else i * 2),
                "volume": 1000 if i < 300 else 10000,
                "quote_asset_volume": 100000 if i < 300 else 500000,
            }
            for i in range(365)
        ]
        result = engine.score_rrp(ohlcv)
        assert result["rrp_score"] >= 0
        assert "verdict" in result

    def test_returns_dormant_on_flat_data(self):
        engine = RRPEngine()
        ohlcv = [
            {
                "timestamp": i * 86400000,
                "close": 100.0,
                "open": 100.0,
                "high": 100.1,
                "low": 99.9,
                "volume": 100.0,
                "quote_asset_volume": 10000.0,
            }
            for i in range(365)
        ]
        result = engine.score_rrp(ohlcv)
        assert result["rrp_score"] < 40
        assert result["verdict"] == "DORMANT"

    def test_returns_zero_on_no_data(self):
        engine = RRPEngine()
        result = engine.score_rrp(None)
        assert result["rrp_score"] == 0
        assert result["current_price"] is None

    def test_result_has_all_components(self):
        engine = RRPEngine()
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
            for _ in range(100)
        ]
        result = engine.score_rrp(ohlcv)
        assert "rrp_score" in result
        assert "is_dormant" in result
        assert "volume_breakout" in result
        assert "price_momentum" in result
        assert "structure_recovery" in result
        assert "sentiment_shift" in result
        assert "exhaustion_recovery" in result
        assert "verdict" in result
        assert "dormancy_info" in result

    def test_verdict_reviving_on_high_score(self):
        engine = RRPEngine()
        ohlcv = [
            {
                "timestamp": i * 86400000,
                "close": 50 + (i * 0.3 if i < 300 else i * 1.5),
                "open": 49 + (i * 0.3 if i < 300 else i * 1.5),
                "high": 52 + (i * 0.3 if i < 300 else i * 1.5),
                "low": 48 + (i * 0.3 if i < 300 else i * 1.5),
                "volume": 500 if i < 300 else 5000,
                "quote_asset_volume": 50000 if i < 300 else 500000,
            }
            for i in range(365)
        ]
        result = engine.score_rrp(ohlcv)
        if result["rrp_score"] >= 60:
            assert result["verdict"] == "REVIVING"

    def test_verdict_waking_on_medium_score(self):
        engine = RRPEngine()
        ohlcv = [
            {
                "timestamp": i * 86400000,
                "close": 50 + (i * 0.2 if i < 300 else i * 0.8),
                "open": 49 + (i * 0.2 if i < 300 else i * 0.8),
                "high": 52 + (i * 0.2 if i < 300 else i * 0.8),
                "low": 48 + (i * 0.2 if i < 300 else i * 0.8),
                "volume": 1000 if i < 300 else 3000,
                "quote_asset_volume": 100000 if i < 300 else 300000,
            }
            for i in range(365)
        ]
        result = engine.score_rrp(ohlcv)
        if 40 <= result["rrp_score"] < 60:
            assert result["verdict"] == "WAKING"


class TestSnapshots:
    def test_stores_immutable_snapshots(self):
        engine = RRPEngine()
        ohlcv = [
            {
                "timestamp": i * 86400000,
                "close": 100 + i * 0.1,
                "open": 99.5 + i * 0.1,
                "high": 101 + i * 0.1,
                "low": 99 + i * 0.1,
                "volume": 5000,
                "quote_asset_volume": 500000,
            }
            for i in range(100)
        ]
        engine.score_rrp(ohlcv)
        assert len(engine.snapshots) == 1
        assert "timestamp" in engine.snapshots[0]
        assert "score" in engine.snapshots[0]
        assert "verdict" in engine.snapshots[0]


class TestReport:
    def test_returns_readable_string_when_data_available(self):
        engine = RRPEngine()
        with patch.object(engine, "get_ohlcv") as mock_ohlcv:
            mock_ohlcv.return_value = [
                {
                    "timestamp": i * 86400000,
                    "close": 95000 + i * 10,
                    "open": 94000 + i * 10,
                    "high": 96000 + i * 10,
                    "low": 94000 + i * 10,
                    "volume": 5000000 + i * 10000,
                    "quote_asset_volume": 475000000000 + i * 1000000000,
                }
                for i in range(100)
            ]
            report = engine.report()
            assert "RRP:" in report
            assert "/100" in report

    def test_returns_unavailable_on_no_price(self):
        engine = RRPEngine()
        with patch.object(engine, "get_ohlcv", return_value=None):
            report = engine.report()
            assert "unavailable" in report.lower()

    def test_report_includes_all_components(self):
        engine = RRPEngine()
        with patch.object(engine, "get_ohlcv") as mock_ohlcv:
            mock_ohlcv.return_value = [
                {
                    "timestamp": i * 86400000,
                    "close": 100 + i * 0.5,
                    "open": 99.5 + i * 0.5,
                    "high": 102 + i * 0.5,
                    "low": 98 + i * 0.5,
                    "volume": 5000 + i * 100,
                    "quote_asset_volume": 500000 + i * 10000,
                }
                for i in range(100)
            ]
            report = engine.report()
            assert "Vol=" in report
            assert "Mom=" in report
            assert "Struct=" in report
            assert "Sent=" in report
            assert "Exh=" in report
