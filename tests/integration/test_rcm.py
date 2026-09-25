"""Integration tests for RCM Engine."""

import pytest

from src.layers.layer6_rcm.rcm_engine import RCMEngine, RCMAnalysisReport
from tests.fixtures.market_data import generate_bull_ohlcv, generate_bear_ohlcv


class TestRCMEngine:
    """Tests for rotation confirmation model."""

    def test_engine_quick_scan(self):
        """Quick scan should return RCMSignal."""
        engine = RCMEngine()
        ohlcv = generate_bull_ohlcv(50)
        signal = engine.scan("BTC", ohlcv)

        assert signal.asset == "BTC"
        assert 0 <= signal.combined_score <= 100

    def test_engine_comprehensive_analysis(self):
        """Comprehensive analysis should return detailed report."""
        engine = RCMEngine()
        ohlcv = generate_bull_ohlcv(50)
        report = engine.analyze(
            "ETH",
            ohlcv,
            capital_flow_data={"inflow_velocity": 80},
            sector_data={"vs_btc_strength": 75},
            narrative_data={"narrative_velocity": 70},
            fundamental_data={"product_progress": 75},
            derivatives_data={"funding_rate_health": 70},
        )

        assert isinstance(report, RCMAnalysisReport)
        assert report.asset == "ETH"
        assert 0 <= report.combined_score <= 100
        assert len(report.reasoning) > 0

    def test_capital_flow_scoring(self):
        """Capital flow scoring should work."""
        engine = RCMEngine()
        data = {
            "inflow_velocity": 85,
            "exchange_volume": 80,
            "otc_activity": 75,
            "net_flow": 70,
        }
        score, factors = engine._score_capital_flow_detailed(data)
        assert score > 0
        assert score <= 100

    def test_relative_strength_scoring(self):
        """Relative strength should incorporate price action."""
        engine = RCMEngine()
        ohlcv = generate_bull_ohlcv(50)
        data = {"vs_btc_strength": 80, "vs_sector_strength": 75}
        score, factors = engine._score_relative_strength_detailed(data, ohlcv)
        assert score > 0
        assert score <= 100

    def test_narrative_acceleration_scoring(self):
        """Narrative acceleration scoring should work."""
        engine = RCMEngine()
        data = {
            "narrative_velocity": 85,
            "media_acceleration": 80,
            "social_momentum": 75,
            "theme_rotation_strength": 70,
        }
        score, factors = engine._score_narrative_acceleration_detailed(data)
        assert score > 0
        assert score <= 100

    def test_fundamental_confirmation_scoring(self):
        """Fundamental confirmation scoring should work."""
        engine = RCMEngine()
        data = {
            "product_progress": 80,
            "partnership_score": 75,
            "user_growth": 80,
            "revenue_metrics": 70,
        }
        score, factors = engine._score_fundamental_confirmation_detailed(data)
        assert score > 0
        assert score <= 100

    def test_derivatives_structure_scoring(self):
        """Derivatives structure scoring should work."""
        engine = RCMEngine()
        data = {
            "funding_rate_health": 80,
            "open_interest_trend": 75,
            "options_positioning": 70,
            "liquidation_risk": 30,
        }
        score, factors = engine._score_derivatives_structure_detailed(data)
        assert score > 0
        assert score <= 100

    def test_confirmation_threshold(self):
        """Score >= 70 should trigger is_confirmed_rotation."""
        engine = RCMEngine()
        ohlcv = generate_bull_ohlcv(50)
        report = engine.analyze(
            "TEST",
            ohlcv,
            capital_flow_data={"inflow_velocity": 90},
            sector_data={"vs_btc_strength": 85},
            narrative_data={"narrative_velocity": 80},
            fundamental_data={"product_progress": 85},
            derivatives_data={"funding_rate_health": 80},
        )

        if report.combined_score >= 70:
            assert report.is_confirmed_rotation

    def test_walk_forward_validation(self):
        """Walk-forward validation should check out-of-sample performance."""
        engine = RCMEngine()
        ohlcv = generate_bull_ohlcv(100)  # Need 60+ for walk-forward

        is_valid = engine._validate_rotation_walkforward(ohlcv, 75.0)
        assert isinstance(is_valid, bool)

    def test_rotation_quality_assessment(self):
        """Rotation quality should be strong/moderate/weak."""
        engine = RCMEngine()
        ohlcv = generate_bull_ohlcv(50)
        report = engine.analyze("TEST", ohlcv)

        assert report.rotation_quality in ["strong", "moderate", "weak"]

    def test_entry_confidence_assessment(self):
        """Entry confidence should be high/medium/low."""
        engine = RCMEngine()
        ohlcv = generate_bull_ohlcv(50)
        report = engine.analyze("TEST", ohlcv)

        assert report.entry_confidence in ["high", "medium", "low"]

    def test_report_generation(self):
        """Should generate human-readable report."""
        engine = RCMEngine()
        ohlcv = generate_bull_ohlcv(50)
        report = engine.analyze("ABC", ohlcv)

        text = engine.generate_report_text(report)

        assert "RCM ANALYSIS" in text
        assert "ABC" in text
        assert "Capital Flow" in text

    def test_insufficient_data(self):
        """Insufficient data should return invalid report."""
        engine = RCMEngine()
        short_ohlcv = generate_bull_ohlcv(5)
        report = engine.analyze("TEST", short_ohlcv)

        assert report.is_confirmed_rotation is False
        assert report.combined_score == 0.0

    def test_weighted_combination(self):
        """Test weighted combination of scores."""
        engine = RCMEngine()
        ohlcv = generate_bull_ohlcv(50)

        # Low scores should result in low combined
        report = engine.analyze(
            "WEAK",
            ohlcv,
            capital_flow_data={"inflow_velocity": 20},
            sector_data={"vs_btc_strength": 20},
            narrative_data={"narrative_velocity": 20},
            fundamental_data={"product_progress": 20},
            derivatives_data={"funding_rate_health": 20},
        )

        assert report.combined_score < 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
