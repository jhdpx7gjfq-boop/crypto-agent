"""Unit tests for RRP (Revival Radar Pipeline)."""

import pytest
import numpy as np
from src.layers.layer7_decision.rrp import RRPEngine


@pytest.fixture
def engine():
    """Create RRPEngine instance."""
    return RRPEngine()


@pytest.fixture
def recovering_prices():
    """Price recovering from lows."""
    low_period = [50.0] * 10
    recovery_period = [50.0 + i * 2 for i in range(20)]
    return low_period + recovery_period


@pytest.fixture
def dead_prices():
    """Stagnant/dead price."""
    return [50.0] * 30


@pytest.fixture
def high_volumes():
    """Increasing volumes."""
    return [100000 + i * 5000 for i in range(30)]


@pytest.fixture
def low_volumes():
    """Stagnant volumes."""
    return [50000] * 30


class TestMomentumFromLows:
    def test_detect_momentum_from_lows_returns_float(self, engine, recovering_prices, high_volumes):
        """Test momentum returns valid float."""
        momentum = engine.detect_momentum_from_lows("BTC", recovering_prices)
        assert isinstance(momentum, float)
        assert 0.0 <= momentum <= 30.0

    def test_detect_momentum_from_lows_recovery(self, engine, recovering_prices):
        """Test strong recovery from lows."""
        momentum = engine.detect_momentum_from_lows("BTC", recovering_prices)
        assert 0.0 <= momentum <= 30.0

    def test_detect_momentum_from_lows_stagnant(self, engine, dead_prices):
        """Test stagnant prices produce low momentum."""
        momentum = engine.detect_momentum_from_lows("BTC", dead_prices)
        assert 0.0 <= momentum < 5.0

    def test_detect_momentum_from_lows_insufficient_data(self, engine):
        """Test insufficient data."""
        momentum = engine.detect_momentum_from_lows("BTC", [50.0], lookback_days=90)
        assert momentum == 0.0


class TestVolumeConfirmation:
    def test_detect_volume_confirmation_returns_float(self, engine, high_volumes):
        """Test volume confirmation returns valid float."""
        volume = engine.detect_volume_confirmation("BTC", high_volumes)
        assert isinstance(volume, float)
        assert 0.0 <= volume <= 25.0

    def test_detect_volume_confirmation_high_volumes(self, engine, high_volumes):
        """Test high volume confirmation."""
        volume = engine.detect_volume_confirmation("BTC", high_volumes)
        assert 0.0 <= volume <= 25.0

    def test_detect_volume_confirmation_low_volumes(self, engine, low_volumes):
        """Test low volume produces low score."""
        volume = engine.detect_volume_confirmation("BTC", low_volumes)
        assert 0.0 <= volume < 10.0

    def test_detect_volume_confirmation_insufficient_data(self, engine):
        """Test insufficient data."""
        volume = engine.detect_volume_confirmation("BTC", [100000], lookback_days=90)
        assert volume == 0.0


class TestAdoptionAcceleration:
    def test_detect_adoption_acceleration_returns_float(self, engine):
        """Test adoption acceleration returns valid float."""
        adoption = engine.detect_adoption_acceleration("BTC", 5.0, 3.0, 1.0)
        assert isinstance(adoption, float)
        assert 0.0 <= adoption <= 20.0

    def test_detect_adoption_acceleration_strong(self, engine):
        """Test strong adoption growth."""
        adoption = engine.detect_adoption_acceleration("BTC", 8.0, 5.0, 2.0)
        assert adoption > 10.0

    def test_detect_adoption_acceleration_weak(self, engine):
        """Test weak adoption."""
        adoption = engine.detect_adoption_acceleration("ALT", 1.0, 0.5, 0.3)
        assert adoption < 5.0

    def test_detect_adoption_acceleration_perfect(self, engine):
        """Test perfect adoption score 20."""
        adoption = engine.detect_adoption_acceleration("PERFECT", 10.0, 7.0, 3.0)
        assert adoption == 20.0


class TestNarrativeRevival:
    def test_detect_narrative_revival_returns_float(self, engine):
        """Test narrative revival returns valid float."""
        narrative = engine.detect_narrative_revival("BTC", 5.0, 3.0, 2.0)
        assert isinstance(narrative, float)
        assert 0.0 <= narrative <= 15.0

    def test_detect_narrative_revival_strong(self, engine):
        """Test strong narrative revival."""
        narrative = engine.detect_narrative_revival("BTC", 6.0, 4.0, 2.5)
        assert narrative > 8.0

    def test_detect_narrative_revival_weak(self, engine):
        """Test weak narrative."""
        narrative = engine.detect_narrative_revival("ALT", 1.0, 1.0, 0.5)
        assert narrative < 5.0

    def test_detect_narrative_revival_perfect(self, engine):
        """Test perfect narrative score 15."""
        narrative = engine.detect_narrative_revival("PERFECT", 7.0, 5.0, 3.0)
        assert narrative == 15.0


class TestBCEConfluence:
    def test_detect_bce_confluence_returns_float(self, engine):
        """Test BCE confluence returns valid float."""
        bce = engine.detect_bce_confluence("BTC", 3.0)
        assert isinstance(bce, float)
        assert 0.0 <= bce <= 10.0

    def test_detect_bce_confluence_medium(self, engine):
        """Test medium BCE confluence."""
        bce = engine.detect_bce_confluence("BTC", 3.0)
        assert 3.0 < bce < 6.0

    def test_detect_bce_confluence_perfect(self, engine):
        """Test perfect BCE score 6 → 10."""
        bce = engine.detect_bce_confluence("PERFECT", 6.0)
        assert bce == 10.0

    def test_detect_bce_confluence_zero(self, engine):
        """Test zero BCE."""
        bce = engine.detect_bce_confluence("NONE", 0.0)
        assert bce == 0.0


class TestRRPScoreCalculation:
    def test_calculate_rrp_score_range(self, engine):
        """Test RRP score range."""
        score = engine.calculate_rrp_score(15.0, 12.5, 10.0, 7.5, 5.0)
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0

    def test_calculate_rrp_score_perfect(self, engine):
        """Test perfect RRP score 100."""
        score = engine.calculate_rrp_score(30.0, 25.0, 20.0, 15.0, 10.0)
        assert score == 100.0

    def test_calculate_rrp_score_zero(self, engine):
        """Test zero RRP score."""
        score = engine.calculate_rrp_score(0.0, 0.0, 0.0, 0.0, 0.0)
        assert score == 0.0

    def test_calculate_rrp_score_weighting(self, engine):
        """Test score weighting (30, 25, 20, 15, 10)."""
        # Momentum dominant
        score1 = engine.calculate_rrp_score(30.0, 0.0, 0.0, 0.0, 0.0)
        # BCE dominant
        score2 = engine.calculate_rrp_score(0.0, 0.0, 0.0, 0.0, 10.0)

        assert score1 > score2


class TestRRPValidation:
    def test_validate_rrp_revival_threshold_50(self, engine):
        """Test RRP validation gate at 50."""
        assert engine.validate_rrp_revival(50.0) is True
        assert engine.validate_rrp_revival(49.9) is False
        assert engine.validate_rrp_revival(100.0) is True
        assert engine.validate_rrp_revival(0.0) is False

    def test_validate_rrp_revival_boundary(self, engine):
        """Test validation at boundary."""
        assert engine.validate_rrp_revival(49.99) is False
        assert engine.validate_rrp_revival(50.0) is True


class TestAnalyzeRRP:
    def test_analyze_rrp_returns_tuple(self, engine, recovering_prices, high_volumes):
        """Test complete RRP analysis returns tuple."""
        score, metrics = engine.analyze_rrp(
            "BTC",
            closes=recovering_prices,
            volumes=high_volumes,
            bce_score=4.5,
            user_growth=6.0,
            transaction_growth=4.0,
            address_growth=2.0,
            social_velocity=5.0,
            media_mentions=3.0,
            sentiment_shift=1.5,
        )

        assert isinstance(score, float)
        assert isinstance(metrics, dict)
        assert 0.0 <= score <= 100.0

    def test_analyze_rrp_metrics_completeness(self, engine, recovering_prices, high_volumes):
        """Test all metrics returned."""
        score, metrics = engine.analyze_rrp(
            "BTC",
            closes=recovering_prices,
            volumes=high_volumes,
            bce_score=4.5,
            user_growth=6.0,
            transaction_growth=4.0,
            address_growth=2.0,
            social_velocity=5.0,
            media_mentions=3.0,
            sentiment_shift=1.5,
        )

        required_keys = [
            "symbol",
            "momentum_from_lows",
            "momentum_pct",
            "volume_confirmation",
            "volume_pct",
            "adoption_acceleration",
            "adoption_pct",
            "narrative_revival",
            "narrative_pct",
            "bce_confluence",
            "bce_pct",
            "rrp_score",
            "revival_signal",
        ]

        for key in required_keys:
            assert key in metrics, f"Missing metric: {key}"

    def test_analyze_rrp_strong_revival(self, engine, recovering_prices, high_volumes):
        """Test strong revival signal."""
        score, metrics = engine.analyze_rrp(
            "STRONG",
            closes=recovering_prices,
            volumes=high_volumes,
            bce_score=5.5,
            user_growth=7.0,
            transaction_growth=5.0,
            address_growth=2.5,
            social_velocity=6.0,
            media_mentions=4.0,
            sentiment_shift=2.0,
        )

        assert score > 20.0
        assert isinstance(metrics["revival_signal"], bool)

    def test_analyze_rrp_weak_revival(self, engine, dead_prices, low_volumes):
        """Test weak revival signal."""
        score, metrics = engine.analyze_rrp(
            "WEAK",
            closes=dead_prices,
            volumes=low_volumes,
            bce_score=1.0,
            user_growth=0.5,
            transaction_growth=0.3,
            address_growth=0.2,
            social_velocity=0.5,
            media_mentions=0.3,
            sentiment_shift=0.1,
        )

        assert score < 50.0
        assert metrics["revival_signal"] is False

    def test_analyze_rrp_symbol_recorded(self, engine, recovering_prices, high_volumes):
        """Test symbol is recorded."""
        score, metrics = engine.analyze_rrp(
            "SYMBOL",
            closes=recovering_prices,
            volumes=high_volumes,
            bce_score=3.0,
            user_growth=3.0,
            transaction_growth=2.0,
            address_growth=1.0,
            social_velocity=2.0,
            media_mentions=1.0,
            sentiment_shift=0.5,
        )

        assert metrics["symbol"] == "SYMBOL"

    def test_analyze_rrp_deterministic(self, engine, recovering_prices, high_volumes):
        """Test deterministic behavior."""
        score1, metrics1 = engine.analyze_rrp(
            "BTC",
            closes=recovering_prices,
            volumes=high_volumes,
            bce_score=4.5,
            user_growth=6.0,
            transaction_growth=4.0,
            address_growth=2.0,
            social_velocity=5.0,
            media_mentions=3.0,
            sentiment_shift=1.5,
        )

        score2, metrics2 = engine.analyze_rrp(
            "BTC",
            closes=recovering_prices,
            volumes=high_volumes,
            bce_score=4.5,
            user_growth=6.0,
            transaction_growth=4.0,
            address_growth=2.0,
            social_velocity=5.0,
            media_mentions=3.0,
            sentiment_shift=1.5,
        )

        assert score1 == score2
        for key in metrics1:
            if isinstance(metrics1[key], (int, float)):
                assert abs(metrics1[key] - metrics2[key]) < 1e-10
            else:
                assert metrics1[key] == metrics2[key]


class TestRankingAndFiltering:
    def test_rank_revivals_by_score(self, engine):
        """Test ranking by score descending."""
        opportunities = [
            ("BTC", 65.0, {}),
            ("ETH", 55.0, {}),
            ("ALT", 45.0, {}),
        ]

        ranked = engine.rank_revivals(opportunities)

        assert ranked[0][1] == 65.0
        assert ranked[1][1] == 55.0
        assert ranked[2][1] == 45.0

    def test_filter_by_revival_signal_default(self, engine):
        """Test filtering with default threshold (50)."""
        opportunities = [
            ("BTC", 70.0, {}),
            ("ETH", 55.0, {}),
            ("ALT", 45.0, {}),
            ("MEME", 50.0, {}),
        ]

        filtered = engine.filter_by_revival_signal(opportunities)

        assert len(filtered) == 3
        assert ("ALT", 45.0, {}) not in filtered

    def test_filter_by_revival_signal_custom(self, engine):
        """Test filtering with custom threshold."""
        opportunities = [
            ("BTC", 75.0, {}),
            ("ETH", 60.0, {}),
            ("ALT", 45.0, {}),
        ]

        filtered = engine.filter_by_revival_signal(opportunities, threshold=60.0)

        assert len(filtered) == 2


class TestEdgeCases:
    def test_analyze_rrp_all_zeros(self, engine, dead_prices, low_volumes):
        """Test with all zero inputs."""
        score, metrics = engine.analyze_rrp(
            "ZERO",
            closes=dead_prices,
            volumes=low_volumes,
            bce_score=0.0,
            user_growth=0.0,
            transaction_growth=0.0,
            address_growth=0.0,
            social_velocity=0.0,
            media_mentions=0.0,
            sentiment_shift=0.0,
        )

        assert score == 0.0
        assert metrics["revival_signal"] is False

    def test_analyze_rrp_perfect(self, engine, recovering_prices, high_volumes):
        """Test with strong inputs."""
        score, metrics = engine.analyze_rrp(
            "PERFECT",
            closes=recovering_prices,
            volumes=high_volumes,
            bce_score=6.0,
            user_growth=10.0,
            transaction_growth=7.0,
            address_growth=3.0,
            social_velocity=7.0,
            media_mentions=5.0,
            sentiment_shift=3.0,
        )

        assert score >= 40.0
        assert isinstance(metrics["revival_signal"], bool)

    def test_rank_empty_list(self, engine):
        """Test ranking empty list."""
        ranked = engine.rank_revivals([])
        assert ranked == []

    def test_filter_empty_list(self, engine):
        """Test filtering empty list."""
        filtered = engine.filter_by_revival_signal([])
        assert filtered == []
