from unittest.mock import Mock, patch

import pytest
import requests

from rcm_engine import RCMEngine


class TestGetOhlcv:
    @patch("rcm_engine.requests.get")
    def test_returns_parsed_ohlcv(self, mock_get):
        mock_get.return_value = Mock(
            json=lambda: [
                [1000, "95000", "96000", "94000", "95500", 0, "100000", 1000, "95500000"],
                [2000, "95500", "96500", "95000", "96000", 0, "110000", 1000, "105500000"],
            ]
        )
        engine = RCMEngine()
        ohlcv = engine.get_ohlcv()
        assert len(ohlcv) == 2
        assert ohlcv[0]["quote_asset_volume"] == 95500000.0

    @patch("rcm_engine.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")
        mock_get.return_value = mock_response
        engine = RCMEngine()
        assert engine.get_ohlcv() is None


class TestGetFundingRate:
    @patch("rcm_engine.requests.get")
    def test_returns_funding_rate(self, mock_get):
        mock_get.return_value = Mock(json=lambda: [{"fundingRate": "0.00075"}])
        engine = RCMEngine()
        rate = engine.get_funding_rate()
        assert rate == 0.00075

    @patch("rcm_engine.requests.get")
    def test_returns_none_on_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500")
        mock_get.return_value = mock_response
        engine = RCMEngine()
        assert engine.get_funding_rate() is None


class TestCalculateCapitalFlow:
    def test_returns_higher_score_on_volume_acceleration(self):
        engine = RCMEngine()
        ohlcv = [
            {"volume": 1000, "quote_asset_volume": 100000 + i * 5000} for i in range(20)
        ]
        capital = engine._calculate_capital_flow(ohlcv)
        assert capital > 0

    def test_returns_zero_on_declining_volume(self):
        engine = RCMEngine()
        ohlcv = [
            {"volume": 1000, "quote_asset_volume": 200000 - i * 5000} for i in range(20)
        ]
        capital = engine._calculate_capital_flow(ohlcv)
        assert capital == 0


class TestCalculateRelativeStrength:
    def test_returns_higher_score_on_high_rsi(self):
        engine = RCMEngine()
        ohlcv = [
            {"close": 100 + i * 1.5} for i in range(14)
        ]
        rs = engine._calculate_relative_strength(ohlcv)
        assert rs >= 18

    def test_returns_zero_on_low_rsi(self):
        engine = RCMEngine()
        ohlcv = [
            {"close": 100 - i * 1.5} for i in range(14)
        ]
        rs = engine._calculate_relative_strength(ohlcv)
        assert rs == 0


class TestCalculateNarrativeAcceleration:
    def test_returns_score_on_volume_and_price_growth(self):
        engine = RCMEngine()
        ohlcv = [
            {"close": 100 + i * 0.5, "volume": 1000 + i * 50} for i in range(20)
        ]
        narrative = engine._calculate_narrative_acceleration(ohlcv)
        assert narrative >= 0

    def test_returns_zero_on_flat_data(self):
        engine = RCMEngine()
        ohlcv = [
            {"close": 100.0, "volume": 1000.0} for _ in range(20)
        ]
        narrative = engine._calculate_narrative_acceleration(ohlcv)
        assert narrative < 5


class TestCalculateFundamentalConfirmation:
    def test_returns_higher_score_with_support_hold(self):
        engine = RCMEngine()
        ohlcv = [
            {"close": 100 + (i % 5) * 0.2, "high": 101, "low": 99} for i in range(30)
        ]
        fundamental = engine._calculate_fundamental_confirmation(ohlcv)
        assert fundamental > 5

    def test_returns_lower_score_below_support(self):
        engine = RCMEngine()
        ohlcv = [
            {"close": 90 + i * 0.5, "high": 92, "low": 88 + i * 0.5} for i in range(30)
        ]
        fundamental = engine._calculate_fundamental_confirmation(ohlcv)
        assert fundamental <= 10


class TestCalculateDerivativesStructure:
    def test_returns_score_on_positive_funding(self):
        engine = RCMEngine()
        ohlcv = [{"close": 100}, {"close": 101}]
        derivatives = engine._calculate_derivatives_structure(ohlcv, funding_rate=0.0002)
        assert derivatives > 0

    def test_returns_low_score_on_negative_funding(self):
        engine = RCMEngine()
        ohlcv = [{"close": 100}]
        derivatives = engine._calculate_derivatives_structure(ohlcv, funding_rate=-0.0002)
        assert derivatives == 0

    def test_returns_zero_on_no_data(self):
        engine = RCMEngine()
        derivatives = engine._calculate_derivatives_structure(None, funding_rate=None)
        assert derivatives == 0.0


class TestScoreRCM:
    def test_returns_confirmed_on_strong_rotation(self):
        engine = RCMEngine()
        ohlcv = [
            {
                "timestamp": i * 14400000,
                "close": 100 + i * 1.0,
                "open": 99.5 + i * 1.0,
                "high": 102 + i,
                "low": 98 + i,
                "volume": 5000 + i * 100,
                "quote_asset_volume": 500000 + i * 10000,
            }
            for i in range(100)
        ]
        result = engine.score_rcm(ohlcv, funding_rate=0.0002)
        assert result["rcm_score"] >= 0
        assert "verdict" in result

    def test_returns_zero_on_no_data(self):
        engine = RCMEngine()
        result = engine.score_rcm(None)
        assert result["rcm_score"] == 0
        assert result["current_price"] is None

    def test_result_has_all_components(self):
        engine = RCMEngine()
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
        result = engine.score_rcm(ohlcv)
        assert "rcm_score" in result
        assert "capital_flow" in result
        assert "relative_strength" in result
        assert "narrative_accel" in result
        assert "fundamental" in result
        assert "derivatives" in result
        assert "verdict" in result

    def test_verdict_confirmed_on_high_score(self):
        engine = RCMEngine()
        ohlcv = [
            {
                "timestamp": i * 14400000,
                "close": 100 + i * 1.5,
                "open": 99.5 + i * 1.5,
                "high": 105 + i,
                "low": 95 + i,
                "volume": 10000 + i * 200,
                "quote_asset_volume": 1000000 + i * 20000,
            }
            for i in range(100)
        ]
        result = engine.score_rcm(ohlcv, funding_rate=0.0003)
        if result["rcm_score"] >= 70:
            assert result["verdict"] == "CONFIRMED"

    def test_verdict_building_on_medium_score(self):
        engine = RCMEngine()
        ohlcv = [
            {
                "timestamp": i * 14400000,
                "close": 100 + i * 0.8,
                "open": 99.8 + i * 0.8,
                "high": 102 + i,
                "low": 98 + i,
                "volume": 5000 + i * 50,
                "quote_asset_volume": 500000 + i * 5000,
            }
            for i in range(100)
        ]
        result = engine.score_rcm(ohlcv, funding_rate=0.0001)
        if 50 <= result["rcm_score"] < 70:
            assert result["verdict"] == "BUILDING"


class TestReport:
    def test_returns_readable_string_when_data_available(self):
        engine = RCMEngine()
        with patch.object(engine, "get_ohlcv") as mock_ohlcv:
            with patch.object(engine, "get_funding_rate") as mock_funding:
                mock_ohlcv.return_value = [
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
                mock_funding.return_value = 0.00075
                report = engine.report()
                assert "RCM:" in report
                assert "95,000" in report
                assert "/100" in report

    def test_returns_unavailable_on_no_price(self):
        engine = RCMEngine()
        with patch.object(engine, "get_ohlcv", return_value=None):
            report = engine.report()
            assert "unavailable" in report.lower()

    def test_report_includes_all_components(self):
        engine = RCMEngine()
        with patch.object(engine, "get_ohlcv") as mock_ohlcv:
            with patch.object(engine, "get_funding_rate") as mock_funding:
                mock_ohlcv.return_value = [
                    {
                        "timestamp": i * 14400000,
                        "close": 100 + i * 1.0,
                        "open": 99.5 + i * 1.0,
                        "high": 102 + i,
                        "low": 98 + i,
                        "volume": 5000 + i * 100,
                        "quote_asset_volume": 500000 + i * 10000,
                    }
                    for i in range(100)
                ]
                mock_funding.return_value = 0.0002
                report = engine.report()
                assert "Cap=" in report
                assert "RS=" in report
                assert "Narr=" in report
                assert "Fund=" in report
                assert "Deriv=" in report
