"""Unit tests for X20 Engine."""

import pytest
from src.layers.layer7_decision.x20_engine import X20Engine, X20Score


@pytest.fixture
def engine():
    """Create X20Engine instance."""
    return X20Engine()


@pytest.fixture
def strong_fundamentals():
    """Strong fundamental data."""
    return {
        "team_quality": 4.5,
        "investor_quality": 4.0,
        "tokenomics_health": 3.5,
        "unlock_risk": 3.0,
        "revenue_adoption": 4.0,
        "competitive_advantage": 3.5,
    }


@pytest.fixture
def weak_fundamentals():
    """Weak fundamental data."""
    return {
        "team_quality": 1.5,
        "investor_quality": 1.0,
        "tokenomics_health": 1.5,
        "unlock_risk": 1.0,
        "revenue_adoption": 1.0,
        "competitive_advantage": 1.5,
    }


@pytest.fixture
def strong_narrative():
    """Strong narrative data."""
    return {
        "sector_strength": 8.0,
        "capital_rotation": 7.5,
        "attention_growth": 4.5,
        "adoption_narrative": 4.0,
    }


@pytest.fixture
def weak_narrative():
    """Weak narrative data."""
    return {
        "sector_strength": 2.0,
        "capital_rotation": 2.5,
        "attention_growth": 1.5,
        "adoption_narrative": 1.0,
    }


@pytest.fixture
def strong_quantitative():
    """Strong quantitative data."""
    return {
        "momentum": 12.0,
        "relative_strength": 11.0,
        "volatility_regime": 4.0,
        "liquidity": 4.5,
    }


@pytest.fixture
def weak_quantitative():
    """Weak quantitative data."""
    return {
        "momentum": 3.0,
        "relative_strength": 2.5,
        "volatility_regime": 1.0,
        "liquidity": 1.5,
    }


class TestX20Score:
    def test_x20_score_creation(self):
        """Test X20Score dataclass creation."""
        score = X20Score(fundamental=20.0, narrative=20.0, quantitative=30.0, total=70.0)
        assert score.fundamental == 20.0
        assert score.narrative == 20.0
        assert score.quantitative == 30.0
        assert score.total == 70.0

    def test_x20_score_fields(self):
        """Test X20Score field ranges."""
        score = X20Score(fundamental=30.0, narrative=30.0, quantitative=40.0, total=100.0)
        assert score.fundamental <= 30.0
        assert score.narrative <= 30.0
        assert score.quantitative <= 40.0
        assert score.total <= 100.0


class TestFundamentalScoring:
    def test_score_fundamentals_returns_float(self, engine, strong_fundamentals):
        """Test fundamental scoring returns valid float."""
        score = engine.score_fundamentals("BTC", **strong_fundamentals)
        assert isinstance(score, float)
        assert 0.0 <= score <= 30.0

    def test_score_fundamentals_strong(self, engine, strong_fundamentals):
        """Test strong fundamentals produce high score."""
        score = engine.score_fundamentals("BTC", **strong_fundamentals)
        assert score > 15.0

    def test_score_fundamentals_weak(self, engine, weak_fundamentals):
        """Test weak fundamentals produce low score."""
        score = engine.score_fundamentals("SCAM", **weak_fundamentals)
        assert score < 15.0

    def test_score_fundamentals_perfect(self, engine):
        """Test perfect fundamentals score 30."""
        score = engine.score_fundamentals("IDEAL", 5.0, 5.0, 5.0, 5.0, 5.0, 5.0)
        assert score == 30.0

    def test_score_fundamentals_zero(self, engine):
        """Test zero fundamentals score 0."""
        score = engine.score_fundamentals("ZERO", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert score == 0.0

    def test_score_fundamentals_clipping(self, engine):
        """Test values above 5 are clipped."""
        score = engine.score_fundamentals("CLIP", 10.0, 10.0, 10.0, 10.0, 10.0, 10.0)
        assert score == 30.0  # Clipped to 5 per component

    def test_score_fundamentals_negative_clipping(self, engine):
        """Test negative values are clipped to 0."""
        score = engine.score_fundamentals("NEG", -5.0, -5.0, -5.0, -5.0, -5.0, -5.0)
        assert score == 0.0


class TestNarrativeScoring:
    def test_score_narrative_returns_float(self, engine, strong_narrative):
        """Test narrative scoring returns valid float."""
        score = engine.score_narrative("BTC", **strong_narrative)
        assert isinstance(score, float)
        assert 0.0 <= score <= 30.0

    def test_score_narrative_strong(self, engine, strong_narrative):
        """Test strong narrative produces high score."""
        score = engine.score_narrative("BTC", **strong_narrative)
        assert score > 15.0

    def test_score_narrative_weak(self, engine, weak_narrative):
        """Test weak narrative produces low score."""
        score = engine.score_narrative("ALT", **weak_narrative)
        assert score < 15.0

    def test_score_narrative_perfect(self, engine):
        """Test perfect narrative scores 30."""
        score = engine.score_narrative("PERFECT", 10.0, 10.0, 5.0, 5.0)
        assert score == 30.0

    def test_score_narrative_zero(self, engine):
        """Test zero narrative scores 0."""
        score = engine.score_narrative("NONE", 0.0, 0.0, 0.0, 0.0)
        assert score == 0.0

    def test_score_narrative_sector_clipping(self, engine):
        """Test sector score clipped to 10."""
        score = engine.score_narrative("CLIP", 20.0, 0.0, 0.0, 0.0)
        assert score == 10.0

    def test_score_narrative_components_clipped(self, engine):
        """Test all components clipped individually."""
        score = engine.score_narrative("CLIP", 100.0, 100.0, 100.0, 100.0)
        assert score == 30.0


class TestQuantitativeScoring:
    def test_score_quantitative_returns_float(self, engine, strong_quantitative):
        """Test quantitative scoring returns valid float."""
        score = engine.score_quantitative(**strong_quantitative)
        assert isinstance(score, float)
        assert 0.0 <= score <= 40.0

    def test_score_quantitative_strong(self, engine, strong_quantitative):
        """Test strong quantitative produces high score."""
        score = engine.score_quantitative(**strong_quantitative)
        assert score > 20.0

    def test_score_quantitative_weak(self, engine, weak_quantitative):
        """Test weak quantitative produces low score."""
        score = engine.score_quantitative(**weak_quantitative)
        assert score < 20.0

    def test_score_quantitative_perfect(self, engine):
        """Test perfect quantitative scores 40."""
        score = engine.score_quantitative(15.0, 15.0, 5.0, 5.0)
        assert score == 40.0

    def test_score_quantitative_zero(self, engine):
        """Test zero quantitative scores 0."""
        score = engine.score_quantitative(0.0, 0.0, 0.0, 0.0)
        assert score == 0.0

    def test_score_quantitative_momentum_clipping(self, engine):
        """Test momentum clipped to 15."""
        score = engine.score_quantitative(30.0, 0.0, 0.0, 0.0)
        assert score == 15.0

    def test_score_quantitative_all_clipped(self, engine):
        """Test all components clipped."""
        score = engine.score_quantitative(100.0, 100.0, 100.0, 100.0)
        assert score == 40.0


class TestX20ScoreCalculation:
    def test_calculate_x20_score_range(self, engine):
        """Test X20 score is in 0-100 range."""
        score = engine.calculate_x20_score(15.0, 15.0, 20.0)
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0

    def test_calculate_x20_score_perfect(self, engine):
        """Test perfect X20 score is 100."""
        score = engine.calculate_x20_score(30.0, 30.0, 40.0)
        assert score == 100.0

    def test_calculate_x20_score_zero(self, engine):
        """Test zero X20 score is 0."""
        score = engine.calculate_x20_score(0.0, 0.0, 0.0)
        assert score == 0.0

    def test_calculate_x20_score_sum(self, engine):
        """Test X20 score is sum of components."""
        f, n, q = 20.0, 15.0, 25.0
        score = engine.calculate_x20_score(f, n, q)
        assert score == f + n + q

    def test_calculate_x20_score_clipping(self, engine):
        """Test X20 score clipped to 100."""
        score = engine.calculate_x20_score(50.0, 50.0, 50.0)
        assert score == 100.0  # Clipped to 100


class TestSignalValidation:
    def test_validate_x20_opportunity_threshold_50(self, engine):
        """Test X20 validation gate at 50."""
        assert engine.validate_x20_opportunity(50.0) is True
        assert engine.validate_x20_opportunity(51.0) is True
        assert engine.validate_x20_opportunity(49.9) is False
        assert engine.validate_x20_opportunity(0.0) is False

    def test_validate_x20_opportunity_boundary(self, engine):
        """Test validation at boundary."""
        assert engine.validate_x20_opportunity(49.99) is False
        assert engine.validate_x20_opportunity(50.0) is True

    def test_validate_x20_opportunity_perfect(self, engine):
        """Test validation with perfect score."""
        assert engine.validate_x20_opportunity(100.0) is True


class TestDetectX20Opportunities:
    def test_detect_x20_opportunities_returns_tuple(self, engine, strong_fundamentals, strong_narrative, strong_quantitative):
        """Test complete detection returns (score, metrics)."""
        score, metrics = engine.detect_x20_opportunities(
            "BTC",
            **strong_fundamentals,
            **strong_narrative,
            **strong_quantitative,
        )

        assert isinstance(score, float)
        assert isinstance(metrics, dict)
        assert 0.0 <= score <= 100.0

    def test_detect_x20_opportunities_metrics_completeness(self, engine, strong_fundamentals, strong_narrative, strong_quantitative):
        """Test all metrics are returned."""
        score, metrics = engine.detect_x20_opportunities(
            "BTC",
            **strong_fundamentals,
            **strong_narrative,
            **strong_quantitative,
        )

        required_keys = [
            "symbol",
            "fundamental",
            "fundamental_pct",
            "narrative",
            "narrative_pct",
            "quantitative",
            "quantitative_pct",
            "x20_score",
            "viable_opportunity",
        ]

        for key in required_keys:
            assert key in metrics, f"Missing metric: {key}"

    def test_detect_x20_opportunities_strong(self, engine, strong_fundamentals, strong_narrative, strong_quantitative):
        """Test strong opportunity detection."""
        score, metrics = engine.detect_x20_opportunities(
            "STRONG",
            **strong_fundamentals,
            **strong_narrative,
            **strong_quantitative,
        )

        assert score > 50.0
        assert metrics["viable_opportunity"] is True

    def test_detect_x20_opportunities_weak(self, engine, weak_fundamentals, weak_narrative, weak_quantitative):
        """Test weak opportunity detection."""
        score, metrics = engine.detect_x20_opportunities(
            "WEAK",
            **weak_fundamentals,
            **weak_narrative,
            **weak_quantitative,
        )

        assert score < 50.0
        assert metrics["viable_opportunity"] is False

    def test_detect_x20_opportunities_symbol_recorded(self, engine, strong_fundamentals, strong_narrative, strong_quantitative):
        """Test symbol is recorded in metrics."""
        score, metrics = engine.detect_x20_opportunities(
            "SYMBOL",
            **strong_fundamentals,
            **strong_narrative,
            **strong_quantitative,
        )

        assert metrics["symbol"] == "SYMBOL"

    def test_detect_x20_opportunities_percentages(self, engine, strong_fundamentals, strong_narrative, strong_quantitative):
        """Test percentage calculations."""
        score, metrics = engine.detect_x20_opportunities(
            "BTC",
            **strong_fundamentals,
            **strong_narrative,
            **strong_quantitative,
        )

        # Percentages should be 0-100
        assert 0.0 <= metrics["fundamental_pct"] <= 100.0
        assert 0.0 <= metrics["narrative_pct"] <= 100.0
        assert 0.0 <= metrics["quantitative_pct"] <= 100.0

    def test_detect_x20_opportunities_deterministic(self, engine, strong_fundamentals, strong_narrative, strong_quantitative):
        """Test detection is deterministic."""
        score1, metrics1 = engine.detect_x20_opportunities(
            "BTC",
            **strong_fundamentals,
            **strong_narrative,
            **strong_quantitative,
        )

        score2, metrics2 = engine.detect_x20_opportunities(
            "BTC",
            **strong_fundamentals,
            **strong_narrative,
            **strong_quantitative,
        )

        assert score1 == score2
        for key in metrics1:
            if isinstance(metrics1[key], (int, float)):
                assert abs(metrics1[key] - metrics2[key]) < 1e-10
            else:
                assert metrics1[key] == metrics2[key]


class TestRankingAndFiltering:
    def test_rank_opportunities_by_score(self, engine):
        """Test opportunities ranked by score descending."""
        opportunities = [
            ("BTC", 80.0, {}),
            ("ETH", 60.0, {}),
            ("ALT", 40.0, {}),
            ("MEME", 50.0, {}),
        ]

        ranked = engine.rank_opportunities(opportunities)

        assert ranked[0][1] == 80.0
        assert ranked[1][1] == 60.0
        assert ranked[2][1] == 50.0
        assert ranked[3][1] == 40.0

    def test_rank_opportunities_preserves_data(self, engine):
        """Test ranking preserves all data."""
        opportunities = [
            ("BTC", 80.0, {"data": "test"}),
            ("ETH", 60.0, {"data": "test2"}),
        ]

        ranked = engine.rank_opportunities(opportunities)

        assert ranked[0][0] == "BTC"
        assert ranked[0][2]["data"] == "test"

    def test_filter_by_threshold_default(self, engine):
        """Test filtering with default threshold (50)."""
        opportunities = [
            ("BTC", 80.0, {}),
            ("ETH", 60.0, {}),
            ("ALT", 40.0, {}),
            ("MEME", 50.0, {}),
        ]

        filtered = engine.filter_by_threshold(opportunities)

        assert len(filtered) == 3
        assert ("ALT", 40.0, {}) not in filtered

    def test_filter_by_threshold_custom(self, engine):
        """Test filtering with custom threshold."""
        opportunities = [
            ("BTC", 80.0, {}),
            ("ETH", 60.0, {}),
            ("ALT", 40.0, {}),
        ]

        filtered = engine.filter_by_threshold(opportunities, threshold=60.0)

        assert len(filtered) == 2
        assert filtered[0] == ("BTC", 80.0, {})
        assert filtered[1] == ("ETH", 60.0, {})

    def test_filter_by_threshold_empty_result(self, engine):
        """Test filtering returns empty when all below threshold."""
        opportunities = [
            ("A", 30.0, {}),
            ("B", 40.0, {}),
            ("C", 45.0, {}),
        ]

        filtered = engine.filter_by_threshold(opportunities, threshold=50.0)

        assert len(filtered) == 0

    def test_filter_by_threshold_all_pass(self, engine):
        """Test filtering returns all when all above threshold."""
        opportunities = [
            ("A", 60.0, {}),
            ("B", 70.0, {}),
            ("C", 80.0, {}),
        ]

        filtered = engine.filter_by_threshold(opportunities, threshold=50.0)

        assert len(filtered) == 3


class TestEdgeCases:
    def test_detect_x20_all_zeros(self, engine):
        """Test with all zero inputs."""
        score, metrics = engine.detect_x20_opportunities(
            "ZERO",
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,  # Fundamentals
            0.0, 0.0, 0.0, 0.0,  # Narrative
            0.0, 0.0, 0.0, 0.0,  # Quantitative
        )

        assert score == 0.0
        assert metrics["viable_opportunity"] is False

    def test_detect_x20_all_maximum(self, engine):
        """Test with all maximum inputs."""
        score, metrics = engine.detect_x20_opportunities(
            "MAX",
            5.0, 5.0, 5.0, 5.0, 5.0, 5.0,  # Fundamentals (30)
            10.0, 10.0, 5.0, 5.0,  # Narrative (30)
            15.0, 15.0, 5.0, 5.0,  # Quantitative (40)
        )

        assert score == 100.0
        assert metrics["viable_opportunity"] is True

    def test_detect_x20_partial_data(self, engine):
        """Test with partial strong data."""
        score, metrics = engine.detect_x20_opportunities(
            "PARTIAL",
            4.0, 4.0, 4.0, 0.0, 0.0, 0.0,  # Strong fundamentals but one area
            8.0, 0.0, 0.0, 0.0,  # Only sector strong
            12.0, 0.0, 0.0, 0.0,  # Only momentum strong
        )

        assert 0.0 <= score <= 100.0
        # Should still calculate but may not be viable

    def test_detect_x20_mixed_strengths(self, engine):
        """Test with mixed strong and weak areas."""
        score, metrics = engine.detect_x20_opportunities(
            "MIXED",
            5.0, 5.0, 5.0, 5.0, 5.0, 5.0,  # Perfect fundamentals
            0.0, 0.0, 0.0, 0.0,  # No narrative
            15.0, 15.0, 5.0, 5.0,  # Perfect quantitative
        )

        # Should score 30 (fundamental) + 0 (narrative) + 40 (quantitative) = 70
        assert score == 70.0
        assert metrics["viable_opportunity"] is True

    def test_detect_x20_extreme_values(self, engine):
        """Test with extreme out-of-range values."""
        score, metrics = engine.detect_x20_opportunities(
            "EXTREME",
            100.0, 100.0, 100.0, 100.0, 100.0, 100.0,  # Clipped to 5 each = 30
            100.0, 100.0, 100.0, 100.0,  # Clipped to 10/10/5/5 = 30
            100.0, 100.0, 100.0, 100.0,  # Clipped to 15/15/5/5 = 40
        )

        assert score == 100.0
        assert metrics["viable_opportunity"] is True

    def test_rank_empty_list(self, engine):
        """Test ranking empty opportunity list."""
        ranked = engine.rank_opportunities([])
        assert ranked == []

    def test_filter_empty_list(self, engine):
        """Test filtering empty opportunity list."""
        filtered = engine.filter_by_threshold([])
        assert filtered == []
