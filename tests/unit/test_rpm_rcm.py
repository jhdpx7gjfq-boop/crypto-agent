"""Unit tests for RPM/RCM (Rotation Confirmation Model)."""

import pytest
import numpy as np
from src.layers.layer7_decision.rpm_rcm import RPMEngine


@pytest.fixture
def engine():
    """Create RPMEngine instance."""
    return RPMEngine()


@pytest.fixture
def bullish_prices():
    """Bullish price movement."""
    return [100.0 + i for i in range(20)]


@pytest.fixture
def bearish_prices():
    """Bearish price movement."""
    return [100.0 - i for i in range(20)]


@pytest.fixture
def high_volumes():
    """Increasing volumes."""
    return [100000 + i*5000 for i in range(20)]


class TestCapitalFlowCalculation:
    def test_calculate_capital_flow_returns_float(self, engine, bullish_prices, high_volumes):
        """Test capital flow returns valid float."""
        flow = engine.calculate_capital_flow("BTC", bullish_prices, high_volumes)
        assert isinstance(flow, float)
        assert 0.0 <= flow <= 25.0

    def test_calculate_capital_flow_bullish(self, engine, bullish_prices, high_volumes):
        """Test bullish prices produce high flow."""
        flow = engine.calculate_capital_flow("BTC", bullish_prices, high_volumes)
        assert flow > 5.0

    def test_calculate_capital_flow_bearish(self, engine, bearish_prices):
        """Test bearish prices produce low flow."""
        volumes = [100000] * 20
        flow = engine.calculate_capital_flow("BTC", bearish_prices, volumes)
        assert flow >= 0.0

    def test_calculate_capital_flow_insufficient_data(self, engine):
        """Test insufficient data."""
        flow = engine.calculate_capital_flow("BTC", [100.0], [100000], timeframe_days=20)
        assert flow == 0.0


class TestRelativeStrengthCalculation:
    def test_calculate_relative_strength_returns_float(self, engine):
        """Test relative strength returns valid float."""
        rs = engine.calculate_relative_strength("BTC", 10.0, 5.0, 3.0)
        assert isinstance(rs, float)
        assert 0.0 <= rs <= 25.0

    def test_calculate_relative_strength_outperformance(self, engine):
        """Test outperformance vs sector and market."""
        rs = engine.calculate_relative_strength("BTC", 20.0, 5.0, 3.0)
        assert rs > 0.0

    def test_calculate_relative_strength_underperformance(self, engine):
        """Test underperformance."""
        rs = engine.calculate_relative_strength("ALT", 2.0, 5.0, 3.0)
        assert rs >= 0.0

    def test_calculate_relative_strength_zero_returns(self, engine):
        """Test with zero returns."""
        rs = engine.calculate_relative_strength("NONE", 0.0, 0.0, 0.0)
        assert rs == 0.0


class TestNarrativeAcceleration:
    def test_detect_narrative_acceleration_returns_float(self, engine):
        """Test narrative acceleration returns valid float."""
        narrative = engine.detect_narrative_acceleration("BTC", 8.0, 6.0, 2.5)
        assert isinstance(narrative, float)
        assert 0.0 <= narrative <= 20.0

    def test_detect_narrative_acceleration_strong(self, engine):
        """Test strong narrative acceleration."""
        narrative = engine.detect_narrative_acceleration("BTC", 8.0, 6.0, 2.5)
        assert narrative > 5.0

    def test_detect_narrative_acceleration_weak(self, engine):
        """Test weak narrative."""
        narrative = engine.detect_narrative_acceleration("ALT", 2.0, 1.0, 0.5)
        assert narrative < 5.0

    def test_detect_narrative_acceleration_perfect(self, engine):
        """Test perfect narrative score 20."""
        narrative = engine.detect_narrative_acceleration("PERFECT", 10.0, 7.0, 3.0)
        assert narrative == 20.0


class TestFundamentalConfirmation:
    def test_confirm_fundamentals_returns_float(self, engine):
        """Test fundamental confirmation returns valid float."""
        fundamental = engine.confirm_fundamentals("BTC", 5.0, 5.0, 4.0)
        assert isinstance(fundamental, float)
        assert 0.0 <= fundamental <= 20.0

    def test_confirm_fundamentals_strong(self, engine):
        """Test strong fundamentals."""
        fundamental = engine.confirm_fundamentals("BTC", 5.0, 5.0, 4.0)
        assert fundamental > 10.0

    def test_confirm_fundamentals_weak(self, engine):
        """Test weak fundamentals."""
        fundamental = engine.confirm_fundamentals("ALT", 1.0, 1.0, 1.0)
        assert fundamental < 10.0

    def test_confirm_fundamentals_perfect(self, engine):
        """Test perfect fundamentals score 20."""
        fundamental = engine.confirm_fundamentals("PERFECT", 7.0, 7.0, 6.0)
        assert fundamental == 20.0


class TestDerivativesStructure:
    def test_analyze_derivatives_structure_returns_float(self, engine):
        """Test derivatives structure returns valid float."""
        derivatives = engine.analyze_derivatives_structure("BTC", 3.0, 2.0, 2.0)
        assert isinstance(derivatives, float)
        assert 0.0 <= derivatives <= 10.0

    def test_analyze_derivatives_structure_positive(self, engine):
        """Test positive derivatives structure."""
        derivatives = engine.analyze_derivatives_structure("BTC", 3.0, 2.0, 2.0)
        assert derivatives > 0.0

    def test_analyze_derivatives_structure_perfect(self, engine):
        """Test perfect derivatives score 10."""
        derivatives = engine.analyze_derivatives_structure("PERFECT", 4.0, 3.0, 3.0)
        assert derivatives == 10.0

    def test_analyze_derivatives_structure_clipping(self, engine):
        """Test clipping to max."""
        derivatives = engine.analyze_derivatives_structure("CLIP", 100.0, 100.0, 100.0)
        assert derivatives == 10.0


class TestRPMScoreCalculation:
    def test_calculate_rpm_score_range(self, engine):
        """Test RPM score range."""
        score = engine.calculate_rpm_score(12.5, 12.5, 10.0, 10.0, 5.0)
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0

    def test_calculate_rpm_score_perfect(self, engine):
        """Test perfect RPM score 100."""
        score = engine.calculate_rpm_score(25.0, 25.0, 20.0, 20.0, 10.0)
        assert score == 100.0

    def test_calculate_rpm_score_zero(self, engine):
        """Test zero RPM score."""
        score = engine.calculate_rpm_score(0.0, 0.0, 0.0, 0.0, 0.0)
        assert score == 0.0

    def test_calculate_rpm_score_weighting(self, engine):
        """Test score weighting (25, 25, 20, 20, 10)."""
        # Capital flow dominant
        score1 = engine.calculate_rpm_score(25.0, 0.0, 0.0, 0.0, 0.0)
        # Derivatives dominant
        score2 = engine.calculate_rpm_score(0.0, 0.0, 0.0, 0.0, 10.0)

        assert score1 > score2


class TestRPMValidation:
    def test_validate_rpm_opportunity_threshold_55(self, engine):
        """Test RPM validation gate at 55."""
        assert engine.validate_rpm_opportunity(55.0) is True
        assert engine.validate_rpm_opportunity(54.9) is False
        assert engine.validate_rpm_opportunity(100.0) is True
        assert engine.validate_rpm_opportunity(0.0) is False

    def test_validate_rpm_opportunity_boundary(self, engine):
        """Test validation at boundary."""
        assert engine.validate_rpm_opportunity(54.99) is False
        assert engine.validate_rpm_opportunity(55.0) is True


class TestAnalyzeRPM:
    def test_analyze_rpm_returns_tuple(self, engine, bullish_prices, high_volumes):
        """Test complete RPM analysis returns tuple."""
        score, metrics = engine.analyze_rpm(
            "BTC",
            closes=bullish_prices,
            volumes=high_volumes,
            symbol_return=15.0,
            sector_return=8.0,
            market_return=5.0,
            social_volume=7.0,
            media_mentions=5.0,
            sentiment_change=2.0,
            team_execution=5.0,
            revenue_growth=4.0,
            adoption_metrics=3.0,
            liquidation_level=3.0,
            basis_level=2.0,
            funding_rate=2.0,
        )

        assert isinstance(score, float)
        assert isinstance(metrics, dict)
        assert 0.0 <= score <= 100.0

    def test_analyze_rpm_metrics_completeness(self, engine, bullish_prices, high_volumes):
        """Test all metrics returned."""
        score, metrics = engine.analyze_rpm(
            "BTC",
            closes=bullish_prices,
            volumes=high_volumes,
            symbol_return=15.0,
            sector_return=8.0,
            market_return=5.0,
            social_volume=7.0,
            media_mentions=5.0,
            sentiment_change=2.0,
            team_execution=5.0,
            revenue_growth=4.0,
            adoption_metrics=3.0,
            liquidation_level=3.0,
            basis_level=2.0,
            funding_rate=2.0,
        )

        required_keys = [
            "symbol",
            "capital_flow",
            "capital_flow_pct",
            "relative_strength",
            "relative_strength_pct",
            "narrative_acceleration",
            "narrative_pct",
            "fundamental_confirmation",
            "fundamental_pct",
            "derivatives_structure",
            "derivatives_pct",
            "rpm_score",
            "rotation_signal",
        ]

        for key in required_keys:
            assert key in metrics, f"Missing metric: {key}"

    def test_analyze_rpm_strong_rotation(self, engine, bullish_prices, high_volumes):
        """Test strong rotation signal."""
        score, metrics = engine.analyze_rpm(
            "STRONG",
            closes=bullish_prices,
            volumes=high_volumes,
            symbol_return=20.0,
            sector_return=5.0,
            market_return=3.0,
            social_volume=8.0,
            media_mentions=6.0,
            sentiment_change=2.5,
            team_execution=6.0,
            revenue_growth=5.0,
            adoption_metrics=4.0,
            liquidation_level=3.5,
            basis_level=2.5,
            funding_rate=2.5,
        )

        assert score > 55.0
        assert metrics["rotation_signal"] is True

    def test_analyze_rpm_weak_rotation(self, engine, bearish_prices):
        """Test weak rotation signal."""
        volumes = [100000] * 20
        score, metrics = engine.analyze_rpm(
            "WEAK",
            closes=bearish_prices,
            volumes=volumes,
            symbol_return=-10.0,
            sector_return=2.0,
            market_return=1.0,
            social_volume=1.0,
            media_mentions=0.5,
            sentiment_change=0.0,
            team_execution=1.0,
            revenue_growth=0.5,
            adoption_metrics=0.5,
            liquidation_level=0.5,
            basis_level=0.5,
            funding_rate=0.5,
        )

        assert score < 55.0
        assert metrics["rotation_signal"] is False

    def test_analyze_rpm_symbol_recorded(self, engine):
        """Test symbol is recorded."""
        score, metrics = engine.analyze_rpm(
            "SYMBOL",
            closes=[100.0] * 20,
            volumes=[100000] * 20,
            symbol_return=5.0,
            sector_return=2.0,
            market_return=1.0,
            social_volume=3.0,
            media_mentions=2.0,
            sentiment_change=1.0,
            team_execution=3.0,
            revenue_growth=2.0,
            adoption_metrics=2.0,
            liquidation_level=1.0,
            basis_level=1.0,
            funding_rate=1.0,
        )

        assert metrics["symbol"] == "SYMBOL"

    def test_analyze_rpm_deterministic(self, engine, bullish_prices, high_volumes):
        """Test deterministic behavior."""
        score1, metrics1 = engine.analyze_rpm(
            "BTC",
            closes=bullish_prices,
            volumes=high_volumes,
            symbol_return=15.0,
            sector_return=8.0,
            market_return=5.0,
            social_volume=7.0,
            media_mentions=5.0,
            sentiment_change=2.0,
            team_execution=5.0,
            revenue_growth=4.0,
            adoption_metrics=3.0,
            liquidation_level=3.0,
            basis_level=2.0,
            funding_rate=2.0,
        )

        score2, metrics2 = engine.analyze_rpm(
            "BTC",
            closes=bullish_prices,
            volumes=high_volumes,
            symbol_return=15.0,
            sector_return=8.0,
            market_return=5.0,
            social_volume=7.0,
            media_mentions=5.0,
            sentiment_change=2.0,
            team_execution=5.0,
            revenue_growth=4.0,
            adoption_metrics=3.0,
            liquidation_level=3.0,
            basis_level=2.0,
            funding_rate=2.0,
        )

        assert score1 == score2
        for key in metrics1:
            if isinstance(metrics1[key], (int, float)):
                assert abs(metrics1[key] - metrics2[key]) < 1e-10
            else:
                assert metrics1[key] == metrics2[key]


class TestRankingAndFiltering:
    def test_rank_rotations_by_score(self, engine):
        """Test ranking by score descending."""
        opportunities = [
            ("BTC", 70.0, {}),
            ("ETH", 60.0, {}),
            ("ALT", 50.0, {}),
        ]

        ranked = engine.rank_rotations(opportunities)

        assert ranked[0][1] == 70.0
        assert ranked[1][1] == 60.0
        assert ranked[2][1] == 50.0

    def test_filter_by_rotation_signal_default(self, engine):
        """Test filtering with default threshold (55)."""
        opportunities = [
            ("BTC", 75.0, {}),
            ("ETH", 60.0, {}),
            ("ALT", 50.0, {}),
            ("MEME", 55.0, {}),
        ]

        filtered = engine.filter_by_rotation_signal(opportunities)

        assert len(filtered) == 3
        assert ("ALT", 50.0, {}) not in filtered

    def test_filter_by_rotation_signal_custom(self, engine):
        """Test filtering with custom threshold."""
        opportunities = [
            ("BTC", 80.0, {}),
            ("ETH", 65.0, {}),
            ("ALT", 50.0, {}),
        ]

        filtered = engine.filter_by_rotation_signal(opportunities, threshold=65.0)

        assert len(filtered) == 2


class TestEdgeCases:
    def test_analyze_rpm_all_zeros(self, engine):
        """Test with all zero inputs."""
        score, metrics = engine.analyze_rpm(
            "ZERO",
            closes=[100.0] * 20,
            volumes=[100000] * 20,
            symbol_return=0.0,
            sector_return=0.0,
            market_return=0.0,
            social_volume=0.0,
            media_mentions=0.0,
            sentiment_change=0.0,
            team_execution=0.0,
            revenue_growth=0.0,
            adoption_metrics=0.0,
            liquidation_level=0.0,
            basis_level=0.0,
            funding_rate=0.0,
        )

        assert score == 0.0
        assert metrics["rotation_signal"] is False

    def test_analyze_rpm_perfect(self, engine, bullish_prices, high_volumes):
        """Test with perfect inputs."""
        score, metrics = engine.analyze_rpm(
            "PERFECT",
            closes=bullish_prices,
            volumes=high_volumes,
            symbol_return=30.0,
            sector_return=10.0,
            market_return=5.0,
            social_volume=10.0,
            media_mentions=7.0,
            sentiment_change=3.0,
            team_execution=7.0,
            revenue_growth=7.0,
            adoption_metrics=6.0,
            liquidation_level=4.0,
            basis_level=3.0,
            funding_rate=3.0,
        )

        assert score >= 85.0
        assert metrics["rotation_signal"] is True

    def test_rank_empty_list(self, engine):
        """Test ranking empty list."""
        ranked = engine.rank_rotations([])
        assert ranked == []

    def test_filter_empty_list(self, engine):
        """Test filtering empty list."""
        filtered = engine.filter_by_rotation_signal([])
        assert filtered == []
