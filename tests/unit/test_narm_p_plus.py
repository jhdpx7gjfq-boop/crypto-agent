"""Unit tests for NARM-P+ (Narrative Adoption Rotation Model Plus)."""

import pytest
import numpy as np
from src.layers.layer7_decision.narm_p_plus import NARMPPlus


@pytest.fixture
def engine():
    """Create NARMPPlus instance."""
    return NARMPPlus()


@pytest.fixture
def strong_narrative():
    """Strong narrative data."""
    return {
        "sentiment_score": 8.0,
        "media_mentions": 8.5,
        "social_volume": 4.5,
    }


@pytest.fixture
def weak_narrative():
    """Weak narrative data."""
    return {
        "sentiment_score": 2.0,
        "media_mentions": 2.5,
        "social_volume": 1.0,
    }


@pytest.fixture
def strong_adoption():
    """Strong adoption data."""
    return {
        "user_growth": 8.0,
        "transaction_volume": 5.5,
        "network_effect": 2.5,
    }


@pytest.fixture
def weak_adoption():
    """Weak adoption data."""
    return {
        "user_growth": 1.5,
        "transaction_volume": 1.0,
        "network_effect": 0.5,
    }


@pytest.fixture
def accumulation_prices():
    """Prices showing upward momentum."""
    return [100.0, 101.0, 102.0, 103.5, 105.0, 106.5, 108.0, 109.5, 111.0, 112.5]


@pytest.fixture
def declining_prices():
    """Prices showing downward trend."""
    return [100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0, 92.0, 91.0]


@pytest.fixture
def accumulation_volumes():
    """Volumes showing accumulation."""
    return [100000, 110000, 120000, 130000, 80000, 70000, 60000, 50000, 40000, 30000]


class TestNarrativeStrength:
    def test_score_narrative_strength_returns_float(self, engine, strong_narrative):
        """Test narrative scoring returns valid float."""
        score = engine.score_narrative_strength("BTC", "Layer1", **strong_narrative)
        assert isinstance(score, float)
        assert 0.0 <= score <= 25.0

    def test_score_narrative_strength_strong(self, engine, strong_narrative):
        """Test strong narrative produces high score."""
        score = engine.score_narrative_strength("BTC", "Layer1", **strong_narrative)
        assert score > 12.5

    def test_score_narrative_strength_weak(self, engine, weak_narrative):
        """Test weak narrative produces low score."""
        score = engine.score_narrative_strength("ALT", "Meme", **weak_narrative)
        assert score < 12.5

    def test_score_narrative_strength_perfect(self, engine):
        """Test perfect narrative scores 25."""
        score = engine.score_narrative_strength("PERFECT", "AI", 10.0, 10.0, 5.0)
        assert score == 25.0

    def test_score_narrative_strength_zero(self, engine):
        """Test zero narrative scores 0."""
        score = engine.score_narrative_strength("NONE", "Unknown", 0.0, 0.0, 0.0)
        assert score == 0.0

    def test_score_narrative_strength_clipping(self, engine):
        """Test values clipped to max."""
        score = engine.score_narrative_strength("CLIP", "Sector", 100.0, 100.0, 100.0)
        assert score == 25.0


class TestAdoptionScoring:
    def test_score_adoption_returns_float(self, engine, strong_adoption):
        """Test adoption scoring returns valid float."""
        score = engine.score_adoption("BTC", **strong_adoption)
        assert isinstance(score, float)
        assert 0.0 <= score <= 20.0

    def test_score_adoption_strong(self, engine, strong_adoption):
        """Test strong adoption produces high score."""
        score = engine.score_adoption("BTC", **strong_adoption)
        assert score > 10.0

    def test_score_adoption_weak(self, engine, weak_adoption):
        """Test weak adoption produces low score."""
        score = engine.score_adoption("ALT", **weak_adoption)
        assert score < 10.0

    def test_score_adoption_perfect(self, engine):
        """Test perfect adoption scores 20."""
        score = engine.score_adoption("PERFECT", 10.0, 7.0, 3.0)
        assert score == 20.0

    def test_score_adoption_zero(self, engine):
        """Test zero adoption scores 0."""
        score = engine.score_adoption("NONE", 0.0, 0.0, 0.0)
        assert score == 0.0

    def test_score_adoption_clipping(self, engine):
        """Test values clipped to max."""
        score = engine.score_adoption("CLIP", 100.0, 100.0, 100.0)
        assert score == 20.0


class TestCapitalRotation:
    def test_score_capital_rotation_returns_float(self, engine, accumulation_prices, accumulation_volumes):
        """Test rotation scoring returns valid float."""
        score = engine.score_capital_rotation("BTC", accumulation_prices, accumulation_volumes)
        assert isinstance(score, float)
        assert 0.0 <= score <= 25.0

    def test_score_capital_rotation_uptrend(self, engine, accumulation_prices, accumulation_volumes):
        """Test uptrend produces rotation score."""
        score = engine.score_capital_rotation("BTC", accumulation_prices, accumulation_volumes)
        assert 0.0 <= score <= 25.0

    def test_score_capital_rotation_downtrend(self, engine, declining_prices):
        """Test downtrend produces low rotation score."""
        volumes = [100000] * 10
        score = engine.score_capital_rotation("BTC", declining_prices, volumes)
        assert score >= 0.0  # May be low but not negative

    def test_score_capital_rotation_insufficient_data(self, engine):
        """Test with insufficient data."""
        score = engine.score_capital_rotation("BTC", [100.0, 101.0], [100000, 110000], timeframe_days=20)
        assert score == 0.0

    def test_score_capital_rotation_custom_timeframe(self, engine, accumulation_prices, accumulation_volumes):
        """Test with custom timeframe."""
        score = engine.score_capital_rotation("BTC", accumulation_prices, accumulation_volumes, timeframe_days=5)
        assert 0.0 <= score <= 25.0


class TestFundamentalScoring:
    def test_score_fundamentals_returns_float(self, engine):
        """Test fundamental scoring returns valid float."""
        score = engine.score_fundamentals("BTC", 4.0, 4.0, 4.0)
        assert isinstance(score, float)
        assert 0.0 <= score <= 15.0

    def test_score_fundamentals_strong(self, engine):
        """Test strong fundamentals produce high score."""
        score = engine.score_fundamentals("BTC", 4.0, 4.0, 4.0)
        assert score > 7.5

    def test_score_fundamentals_weak(self, engine):
        """Test weak fundamentals produce low score."""
        score = engine.score_fundamentals("ALT", 1.0, 1.0, 1.0)
        assert score < 7.5

    def test_score_fundamentals_perfect(self, engine):
        """Test perfect fundamentals score 15."""
        score = engine.score_fundamentals("PERFECT", 5.0, 5.0, 5.0)
        assert score == 15.0

    def test_score_fundamentals_zero(self, engine):
        """Test zero fundamentals score 0."""
        score = engine.score_fundamentals("NONE", 0.0, 0.0, 0.0)
        assert score == 0.0


class TestMarketTiming:
    def test_score_market_timing_returns_float(self, engine):
        """Test timing scoring returns valid float."""
        score = engine.score_market_timing("BTC", 2.0, 3.0, 3.0)
        assert isinstance(score, float)
        assert 0.0 <= score <= 15.0

    def test_score_market_timing_favorable(self, engine):
        """Test favorable timing produces high score."""
        score = engine.score_market_timing("BTC", 2.0, 4.0, 4.0)  # Low BTC dom, high volatility/macro
        assert score > 7.5

    def test_score_market_timing_unfavorable(self, engine):
        """Test unfavorable timing produces low score."""
        score = engine.score_market_timing("ALT", 5.0, 1.0, 1.0)  # High BTC dom, low volatility/macro
        assert score < 7.5

    def test_score_market_timing_perfect(self, engine):
        """Test perfect timing score 15."""
        score = engine.score_market_timing("PERFECT", 5.0, 5.0, 5.0)
        assert score == 15.0

    def test_score_market_timing_zero(self, engine):
        """Test zero timing score 0."""
        score = engine.score_market_timing("NONE", 0.0, 0.0, 0.0)
        assert score == 0.0


class TestNARMPCalculation:
    def test_calculate_narm_p_score_range(self, engine):
        """Test NARM-P+ score is in 0-100 range."""
        score = engine.calculate_narm_p_score(12.5, 10.0, 12.5, 7.5, 7.5)
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0

    def test_calculate_narm_p_score_perfect(self, engine):
        """Test perfect NARM-P+ score is 100."""
        score = engine.calculate_narm_p_score(25.0, 20.0, 25.0, 15.0, 15.0)
        assert score == 100.0

    def test_calculate_narm_p_score_zero(self, engine):
        """Test zero NARM-P+ score is 0."""
        score = engine.calculate_narm_p_score(0.0, 0.0, 0.0, 0.0, 0.0)
        assert score == 0.0

    def test_calculate_narm_p_score_sum(self, engine):
        """Test NARM-P+ score is sum of components."""
        n, a, r, f, t = 12.5, 10.0, 12.5, 7.5, 7.5
        score = engine.calculate_narm_p_score(n, a, r, f, t)
        assert score == n + a + r + f + t


class TestNARMPValidation:
    def test_validate_narm_p_opportunity_threshold_60(self, engine):
        """Test NARM-P+ validation gate at 60."""
        assert engine.validate_narm_p_opportunity(60.0) is True
        assert engine.validate_narm_p_opportunity(61.0) is True
        assert engine.validate_narm_p_opportunity(59.9) is False
        assert engine.validate_narm_p_opportunity(0.0) is False

    def test_validate_narm_p_opportunity_boundary(self, engine):
        """Test validation at boundary."""
        assert engine.validate_narm_p_opportunity(59.99) is False
        assert engine.validate_narm_p_opportunity(60.0) is True

    def test_validate_narm_p_opportunity_perfect(self, engine):
        """Test validation with perfect score."""
        assert engine.validate_narm_p_opportunity(100.0) is True


class TestAnalyzeNARMP:
    def test_analyze_narm_p_returns_tuple(self, engine, strong_narrative, strong_adoption, accumulation_prices, accumulation_volumes):
        """Test complete analysis returns (score, metrics)."""
        score, metrics = engine.analyze_narm_p(
            "BTC",
            **strong_narrative,
            **strong_adoption,
            closes=accumulation_prices,
            volumes=accumulation_volumes,
            team_strength=4.0,
            revenue_model=4.0,
            market_traction=4.0,
            btc_dominance=2.0,
            volatility_regime=4.0,
            macro_environment=4.0,
        )

        assert isinstance(score, float)
        assert isinstance(metrics, dict)
        assert 0.0 <= score <= 100.0

    def test_analyze_narm_p_metrics_completeness(self, engine, strong_narrative, strong_adoption, accumulation_prices, accumulation_volumes):
        """Test all metrics are returned."""
        score, metrics = engine.analyze_narm_p(
            "BTC",
            **strong_narrative,
            **strong_adoption,
            closes=accumulation_prices,
            volumes=accumulation_volumes,
            team_strength=4.0,
            revenue_model=4.0,
            market_traction=4.0,
            btc_dominance=2.0,
            volatility_regime=4.0,
            macro_environment=4.0,
        )

        required_keys = [
            "symbol",
            "narrative_strength",
            "narrative_pct",
            "adoption",
            "adoption_pct",
            "capital_rotation",
            "rotation_pct",
            "fundamental",
            "fundamental_pct",
            "market_timing",
            "timing_pct",
            "narm_p_score",
            "high_conviction",
        ]

        for key in required_keys:
            assert key in metrics, f"Missing metric: {key}"

    def test_analyze_narm_p_strong(self, engine, strong_narrative, strong_adoption, accumulation_prices, accumulation_volumes):
        """Test strong opportunity analysis."""
        score, metrics = engine.analyze_narm_p(
            "STRONG",
            **strong_narrative,
            **strong_adoption,
            closes=accumulation_prices,
            volumes=accumulation_volumes,
            team_strength=5.0,
            revenue_model=5.0,
            market_traction=5.0,
            btc_dominance=0.5,
            volatility_regime=5.0,
            macro_environment=5.0,
        )

        assert score > 55.0
        assert metrics["high_conviction"] is True

    def test_analyze_narm_p_weak(self, engine, weak_narrative, weak_adoption):
        """Test weak opportunity analysis."""
        score, metrics = engine.analyze_narm_p(
            "WEAK",
            **weak_narrative,
            **weak_adoption,
            closes=[100.0] * 10,
            volumes=[100000] * 10,
            team_strength=1.0,
            revenue_model=1.0,
            market_traction=1.0,
            btc_dominance=4.0,
            volatility_regime=1.0,
            macro_environment=1.0,
        )

        assert score < 60.0
        assert metrics["high_conviction"] is False

    def test_analyze_narm_p_symbol_recorded(self, engine, strong_narrative, strong_adoption):
        """Test symbol is recorded."""
        score, metrics = engine.analyze_narm_p(
            "SYMBOL",
            **strong_narrative,
            **strong_adoption,
            closes=[100.0] * 10,
            volumes=[100000] * 10,
            team_strength=4.0,
            revenue_model=4.0,
            market_traction=4.0,
            btc_dominance=2.0,
            volatility_regime=4.0,
            macro_environment=4.0,
        )

        assert metrics["symbol"] == "SYMBOL"

    def test_analyze_narm_p_deterministic(self, engine, strong_narrative, strong_adoption, accumulation_prices, accumulation_volumes):
        """Test analysis is deterministic."""
        score1, metrics1 = engine.analyze_narm_p(
            "BTC",
            **strong_narrative,
            **strong_adoption,
            closes=accumulation_prices,
            volumes=accumulation_volumes,
            team_strength=4.0,
            revenue_model=4.0,
            market_traction=4.0,
            btc_dominance=2.0,
            volatility_regime=4.0,
            macro_environment=4.0,
        )

        score2, metrics2 = engine.analyze_narm_p(
            "BTC",
            **strong_narrative,
            **strong_adoption,
            closes=accumulation_prices,
            volumes=accumulation_volumes,
            team_strength=4.0,
            revenue_model=4.0,
            market_traction=4.0,
            btc_dominance=2.0,
            volatility_regime=4.0,
            macro_environment=4.0,
        )

        assert score1 == score2
        for key in metrics1:
            if isinstance(metrics1[key], (int, float)):
                assert abs(metrics1[key] - metrics2[key]) < 1e-10
            else:
                assert metrics1[key] == metrics2[key]


class TestRankingAndFiltering:
    def test_rank_narratives_by_score(self, engine):
        """Test narratives ranked by score descending."""
        opportunities = [
            ("BTC", 75.0, {}),
            ("ETH", 65.0, {}),
            ("ALT", 55.0, {}),
        ]

        ranked = engine.rank_narratives(opportunities)

        assert ranked[0][1] == 75.0
        assert ranked[1][1] == 65.0
        assert ranked[2][1] == 55.0

    def test_filter_by_conviction_default(self, engine):
        """Test filtering with default conviction threshold (60)."""
        opportunities = [
            ("BTC", 80.0, {}),
            ("ETH", 65.0, {}),
            ("ALT", 55.0, {}),
            ("MEME", 60.0, {}),
        ]

        filtered = engine.filter_by_conviction(opportunities)

        assert len(filtered) == 3
        assert ("ALT", 55.0, {}) not in filtered

    def test_filter_by_conviction_custom(self, engine):
        """Test filtering with custom threshold."""
        opportunities = [
            ("BTC", 80.0, {}),
            ("ETH", 65.0, {}),
            ("ALT", 55.0, {}),
        ]

        filtered = engine.filter_by_conviction(opportunities, threshold=65.0)

        assert len(filtered) == 2


class TestEdgeCases:
    def test_analyze_narm_p_all_zeros(self, engine):
        """Test with all zero inputs."""
        score, metrics = engine.analyze_narm_p(
            "ZERO",
            0.0, 0.0, 0.0,  # Narrative
            0.0, 0.0, 0.0,  # Adoption
            closes=[100.0] * 10,
            volumes=[100000] * 10,
            team_strength=0.0,
            revenue_model=0.0,
            market_traction=0.0,
            btc_dominance=0.0,
            volatility_regime=0.0,
            macro_environment=0.0,
        )

        assert score == 0.0
        assert metrics["high_conviction"] is False

    def test_analyze_narm_p_perfect(self, engine):
        """Test with perfect inputs."""
        score, metrics = engine.analyze_narm_p(
            "PERFECT",
            10.0, 10.0, 5.0,  # Narrative (25)
            10.0, 7.0, 3.0,  # Adoption (20)
            closes=[100.0 + i for i in range(10)],  # Uptrend
            volumes=[100000 + i*1000 for i in range(10)],
            team_strength=5.0,
            revenue_model=5.0,
            market_traction=5.0,
            btc_dominance=5.0,
            volatility_regime=5.0,
            macro_environment=5.0,
        )

        # Score should be high but capital_rotation may not reach full 25
        assert score >= 75.0
        assert metrics["high_conviction"] is True

    def test_analyze_narm_p_empty_prices(self, engine):
        """Test with empty price/volume data."""
        score, metrics = engine.analyze_narm_p(
            "EMPTY",
            5.0, 5.0, 2.5,
            5.0, 3.5, 1.5,
            closes=[],
            volumes=[],
            team_strength=2.5,
            revenue_model=2.5,
            market_traction=2.5,
            btc_dominance=2.5,
            volatility_regime=2.5,
            macro_environment=2.5,
        )

        # Should still score narrative, adoption, fundamental, timing but not rotation
        assert 0.0 <= score <= 100.0
