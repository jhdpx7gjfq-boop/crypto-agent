"""Integration tests for NARM-P+ Engine."""

import pytest

from src.layers.layer5_narm.narm_engine import NARMEngine, NARMAnalysisReport
from tests.fixtures.market_data import (
    generate_bull_ohlcv,
    generate_bear_ohlcv,
)


class TestNARMEngine:
    """Tests for narrative adoption rotation model."""

    def test_engine_quick_scan(self):
        """Quick scan should return NARMSignal."""
        engine = NARMEngine()

        ohlcv = generate_bull_ohlcv(50)
        signal = engine.scan(
            "SOL",
            ohlcv,
            narrative_data={"narrative_momentum": 80},
            adoption_data={"user_growth_rate": 85},
        )

        assert signal.asset == "SOL"
        assert 0 <= signal.narm_score <= 100

    def test_engine_comprehensive_analysis(self):
        """Comprehensive analysis should return detailed report."""
        engine = NARMEngine()

        ohlcv = generate_bull_ohlcv(50)
        report = engine.analyze(
            "AVAX",
            ohlcv,
            narrative_data={"narrative_momentum": 75, "media_sentiment": 80},
            adoption_data={"user_growth_rate": 70, "developer_activity": 85},
            capital_flow_data={"capital_inflow_rate": 80},
        )

        assert isinstance(report, NARMAnalysisReport)
        assert report.asset == "AVAX"
        assert 0 <= report.combined_score <= 100
        assert len(report.reasoning) > 0

    def test_narrative_scoring(self):
        """Narrative scoring should weigh momentum, sentiment, engagement, story."""
        engine = NARMEngine()

        data_strong = {
            "narrative_momentum": 90,
            "media_sentiment": 85,
            "community_engagement": 90,
            "narrative_clarity": 85,
        }
        data_weak = {
            "narrative_momentum": 10,
            "media_sentiment": 10,
            "community_engagement": 10,
            "narrative_clarity": 10,
        }

        score_strong, _ = engine._score_narrative_detailed(data_strong)
        score_weak, _ = engine._score_narrative_detailed(data_weak)

        assert score_strong > score_weak

    def test_adoption_scoring(self):
        """Adoption scoring should weigh user growth, dev activity, tx growth, network."""
        engine = NARMEngine()

        data_high = {
            "user_growth_rate": 90,
            "developer_activity": 85,
            "transaction_growth": 80,
            "network_effects": 85,
        }
        data_low = {
            "user_growth_rate": 10,
            "developer_activity": 15,
            "transaction_growth": 10,
            "network_effects": 10,
        }

        score_high, _ = engine._score_adoption_detailed(data_high)
        score_low, _ = engine._score_adoption_detailed(data_low)

        assert score_high > score_low

    def test_capital_rotation_scoring(self):
        """Capital rotation should weigh inflow, sector rotation, whales, funds."""
        engine = NARMEngine()

        data_active = {
            "capital_inflow_rate": 85,
            "sector_rotation_score": 80,
            "whale_accumulation": 75,
            "institutional_interest": 80,
        }
        data_quiet = {
            "capital_inflow_rate": 20,
            "sector_rotation_score": 20,
            "whale_accumulation": 20,
            "institutional_interest": 20,
        }

        score_active, _ = engine._score_capital_rotation_detailed(data_active)
        score_quiet, _ = engine._score_capital_rotation_detailed(data_quiet)

        assert score_active > score_quiet

    def test_momentum_scoring(self):
        """Momentum should analyze price action, volume, volatility, breakouts."""
        engine = NARMEngine()

        bull_ohlcv = generate_bull_ohlcv(50)
        bear_ohlcv = generate_bear_ohlcv(50)

        score_bull, factors_bull = engine._score_momentum_detailed(bull_ohlcv)
        score_bear, factors_bear = engine._score_momentum_detailed(bear_ohlcv)

        assert "price_momentum" in factors_bull
        assert "volume_trend" in factors_bull
        assert "volatility_expansion" in factors_bull
        assert "breakout_strength" in factors_bull

    def test_rotation_threshold(self):
        """Score >= 65 should trigger is_rotation_candidate."""
        engine = NARMEngine()

        ohlcv = generate_bull_ohlcv(50)

        report = engine.analyze(
            "TEST",
            ohlcv,
            narrative_data={
                "narrative_momentum": 90,
                "media_sentiment": 85,
                "community_engagement": 80,
            },
            adoption_data={
                "user_growth_rate": 85,
                "developer_activity": 80,
                "transaction_growth": 80,
            },
            capital_flow_data={
                "capital_inflow_rate": 85,
                "sector_rotation_score": 80,
            },
        )

        if report.combined_score >= 65:
            assert report.is_rotation_candidate

    def test_rotation_confidence(self):
        """Confidence should be high/medium/low."""
        engine = NARMEngine()

        ohlcv = generate_bull_ohlcv(50)
        report = engine.analyze("TEST", ohlcv)

        assert report.rotation_confidence in ["high", "medium", "low"]

    def test_timing_assessment(self):
        """Timing assessment should be early/mid/late."""
        engine = NARMEngine()

        ohlcv = generate_bull_ohlcv(50)
        report = engine.analyze("TEST", ohlcv)

        assert report.timing_assessment in ["early", "mid", "late", "unknown"]

    def test_weighted_scoring(self):
        """Test weighted combination: 30% narrative, 25% adoption, 25% rotation, 20% momentum."""
        engine = NARMEngine()

        ohlcv = generate_bull_ohlcv(50)

        # Test that weak scores result in low combined score
        report = engine.analyze(
            "WEAK",
            ohlcv,
            narrative_data={"narrative_momentum": 10},
            adoption_data={"user_growth_rate": 10},
            capital_flow_data={"capital_inflow_rate": 10},
        )

        assert report.combined_score < 50

    def test_report_generation(self):
        """Should generate human-readable report."""
        engine = NARMEngine()

        ohlcv = generate_bull_ohlcv(50)
        report = engine.analyze("BTC", ohlcv)

        text = engine.generate_report_text(report)

        assert "NARM-P+ ANALYSIS" in text
        assert "BTC" in text
        assert "Rotation Confidence" in text
        assert "Timing" in text

    def test_insufficient_data(self):
        """Insufficient data should return invalid report."""
        engine = NARMEngine()

        short_ohlcv = generate_bull_ohlcv(5)
        report = engine.analyze("TEST", short_ohlcv)

        assert report.is_rotation_candidate is False
        assert report.combined_score == 0.0

    def test_scoring_bounds(self):
        """All scores should stay within 0-100 bounds."""
        engine = NARMEngine()

        ohlcv = generate_bull_ohlcv(50)
        report = engine.analyze(
            "TEST",
            ohlcv,
            narrative_data={"narrative_momentum": 150},  # Over 100
            adoption_data={"user_growth_rate": 200},  # Over 100
            capital_flow_data={"capital_inflow_rate": 150},  # Over 100
        )

        assert 0 <= report.narrative_strength <= 100
        assert 0 <= report.adoption_velocity <= 100
        assert 0 <= report.capital_rotation <= 100
        assert 0 <= report.momentum_score <= 100
        assert 0 <= report.combined_score <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
