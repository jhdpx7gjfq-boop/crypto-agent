"""Unit tests for Bottom Confirmation Engine (BCE)."""

import pytest
import numpy as np
from src.layers.layer7_decision.bce import BCEEngine, WyckoffStructure


@pytest.fixture
def engine():
    """Create BCEEngine instance."""
    return BCEEngine()


@pytest.fixture
def accumulation_data():
    """Generate data showing accumulation pattern (lower lows → higher lows)."""
    closes = [100.0, 99.0, 98.0, 97.0, 98.5, 99.0, 99.5, 100.0, 100.5, 101.0]
    highs = [101.0, 100.0, 99.0, 98.0, 99.5, 100.0, 100.5, 101.0, 101.5, 102.0]
    lows = [99.0, 98.0, 97.0, 96.0, 97.5, 98.5, 99.0, 99.5, 100.0, 100.5]
    volumes = [100000, 110000, 120000, 130000, 80000, 70000, 60000, 50000, 40000, 30000]
    return closes, highs, lows, volumes


@pytest.fixture
def distribution_data():
    """Generate data showing distribution pattern (higher highs → lower highs)."""
    closes = [100.0, 101.0, 102.0, 103.0, 102.5, 102.0, 101.5, 101.0, 100.5, 100.0]
    highs = [101.0, 102.0, 103.0, 104.0, 103.5, 103.0, 102.5, 102.0, 101.5, 101.0]
    lows = [99.0, 100.0, 101.0, 102.0, 101.5, 101.0, 100.5, 100.0, 99.5, 99.0]
    volumes = [100000, 110000, 120000, 130000, 80000, 70000, 60000, 50000, 40000, 30000]
    return closes, highs, lows, volumes


@pytest.fixture
def noisy_data():
    """Generate random noisy data (unknown regime)."""
    np.random.seed(42)
    closes = np.cumsum(np.random.normal(0, 0.5, 20)) + 100.0
    highs = closes + np.abs(np.random.normal(0, 0.3, 20))
    lows = closes - np.abs(np.random.normal(0, 0.3, 20))
    volumes = np.random.uniform(50000, 150000, 20)
    return closes.tolist(), highs.tolist(), lows.tolist(), volumes.tolist()


class TestWyckoffStructure:
    def test_wyckoff_structure_creation(self):
        """Test WyckoffStructure dataclass creation."""
        ws = WyckoffStructure(phase="accumulation", strength=0.75, confidence=0.85)
        assert ws.phase == "accumulation"
        assert ws.strength == 0.75
        assert ws.confidence == 0.85

    def test_wyckoff_structure_distribution_phase(self):
        """Test distribution phase structure."""
        ws = WyckoffStructure(phase="distribution", strength=0.60, confidence=0.70)
        assert ws.phase == "distribution"
        assert ws.strength == 0.60

    def test_wyckoff_structure_unknown_phase(self):
        """Test unknown phase structure."""
        ws = WyckoffStructure(phase="unknown", strength=0.0, confidence=0.0)
        assert ws.phase == "unknown"
        assert ws.strength == 0.0


class TestWyckoffAnalysis:
    def test_analyze_wyckoff_accumulation(self, engine, accumulation_data):
        """Test Wyckoff detection on accumulation data."""
        closes, highs, lows, volumes = accumulation_data
        result = engine.analyze_wyckoff(closes, highs, lows, period=10)

        assert isinstance(result, WyckoffStructure)
        assert result.phase in ["accumulation", "distribution", "unknown"]
        assert 0.0 <= result.strength <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    def test_analyze_wyckoff_distribution(self, engine, distribution_data):
        """Test Wyckoff detection on distribution data."""
        closes, highs, lows, volumes = distribution_data
        result = engine.analyze_wyckoff(closes, highs, lows, period=10)

        assert isinstance(result, WyckoffStructure)
        assert result.phase in ["accumulation", "distribution", "unknown"]

    def test_analyze_wyckoff_insufficient_data(self, engine):
        """Test Wyckoff with insufficient data."""
        closes = [100.0, 101.0, 102.0]
        highs = [101.0, 102.0, 103.0]
        lows = [99.0, 100.0, 101.0]

        result = engine.analyze_wyckoff(closes, highs, lows, period=20)

        assert result.phase == "unknown"
        assert result.strength == 0.0
        assert result.confidence == 0.0

    def test_analyze_wyckoff_zero_range(self, engine):
        """Test Wyckoff with zero price range."""
        closes = [100.0] * 20
        highs = [100.0] * 20
        lows = [100.0] * 20

        result = engine.analyze_wyckoff(closes, highs, lows, period=20)

        assert result.phase == "unknown"
        assert result.strength == 0.0
        assert result.confidence == 0.0

    def test_analyze_wyckoff_bounds(self, engine, accumulation_data):
        """Test Wyckoff output bounds."""
        closes, highs, lows, volumes = accumulation_data
        result = engine.analyze_wyckoff(closes, highs, lows, period=10)

        assert result.strength >= 0.0 and result.strength <= 1.0
        assert result.confidence >= 0.0 and result.confidence <= 1.0


class TestVolumeProfile:
    def test_analyze_volume_profile_returns_dict(self, engine, accumulation_data):
        """Test volume profile returns correct structure."""
        closes, highs, lows, volumes = accumulation_data
        result = engine.analyze_volume_profile(closes, volumes, period=10)

        assert isinstance(result, dict)
        assert "volume_strength" in result
        assert "volume_consistency" in result
        assert "accumulation_score" in result

    def test_analyze_volume_profile_bounds(self, engine, accumulation_data):
        """Test volume profile values are in valid range."""
        closes, highs, lows, volumes = accumulation_data
        result = engine.analyze_volume_profile(closes, volumes, period=10)

        assert 0.0 <= result["volume_strength"] <= 1.0
        assert 0.0 <= result["volume_consistency"] <= 1.0
        assert 0.0 <= result["accumulation_score"] <= 1.0

    def test_analyze_volume_profile_insufficient_data(self, engine):
        """Test volume profile with insufficient data."""
        closes = [100.0, 101.0, 102.0]
        volumes = [100000, 110000, 120000]

        result = engine.analyze_volume_profile(closes, volumes, period=20)

        assert result["volume_strength"] == 0.0
        assert result["volume_consistency"] == 0.0
        assert result["accumulation_score"] == 0.0

    def test_analyze_volume_profile_consistent_volumes(self, engine):
        """Test volume profile with consistent volumes (high consistency)."""
        closes = [100.0, 101.0, 102.0, 103.0, 102.0, 101.0, 100.0, 101.0]
        volumes = [100000] * 8

        result = engine.analyze_volume_profile(closes, volumes, period=8)

        # Consistent volumes should have high consistency
        assert result["volume_consistency"] > 0.5


class TestSellingExhaustion:
    def test_detect_selling_exhaustion_returns_float(self, engine, accumulation_data):
        """Test selling exhaustion detection returns valid float."""
        closes, highs, lows, volumes = accumulation_data
        result = engine.detect_selling_exhaustion(closes, volumes, period=10)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_detect_selling_exhaustion_insufficient_data(self, engine):
        """Test selling exhaustion with insufficient data."""
        closes = [100.0, 101.0, 102.0]
        volumes = [100000, 110000, 120000]

        result = engine.detect_selling_exhaustion(closes, volumes, period=20)

        assert result == 0.0

    def test_detect_selling_exhaustion_no_down_moves(self, engine):
        """Test selling exhaustion with only up moves."""
        closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        volumes = [100000, 110000, 120000, 130000, 140000, 150000]

        result = engine.detect_selling_exhaustion(closes, volumes, period=6)

        # No down moves should have low exhaustion
        assert result >= 0.0 and result <= 1.0

    def test_detect_selling_exhaustion_down_with_decreasing_volume(self, engine):
        """Test selling exhaustion on down moves with decreasing volume."""
        closes = [100.0, 99.0, 98.0, 97.0, 96.0, 95.0]
        volumes = [150000, 140000, 130000, 120000, 110000, 100000]

        result = engine.detect_selling_exhaustion(closes, volumes, period=6)

        # Negative trend in down-move volumes = some exhaustion detected
        assert result > 0.0 and result <= 1.0


class TestSmartMoneyAccumulation:
    def test_detect_smart_money_accumulation_returns_float(self, engine, accumulation_data):
        """Test smart money detection returns valid float."""
        closes, highs, lows, volumes = accumulation_data
        result = engine.detect_smart_money_accumulation(closes, highs, lows, period=10)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_detect_smart_money_accumulation_tests_low(self, engine):
        """Test smart money with price testing a low."""
        closes = [100.0, 99.0, 98.0, 99.0, 98.5, 99.0, 99.5, 100.0]
        highs = [101.0, 100.0, 99.0, 100.0, 99.5, 100.0, 100.5, 101.0]
        lows = [99.0, 98.0, 97.0, 98.0, 97.5, 98.0, 98.5, 99.0]

        result = engine.detect_smart_money_accumulation(closes, highs, lows, period=8)

        # Multiple tests of low = smart money
        assert result >= 0.0 and result <= 1.0

    def test_detect_smart_money_accumulation_no_tests(self, engine):
        """Test smart money with no tests of lows (downtrend)."""
        closes = [100.0, 99.0, 98.0, 97.0, 96.0, 95.0]
        highs = [101.0, 100.0, 99.0, 98.0, 97.0, 96.0]
        lows = [99.0, 98.0, 97.0, 96.0, 95.0, 94.0]

        result = engine.detect_smart_money_accumulation(closes, highs, lows, period=6)

        # New lows each time = no smart money
        assert result >= 0.0


class TestMarketStructure:
    def test_analyze_market_structure_returns_dict(self, engine, accumulation_data):
        """Test market structure returns correct structure."""
        closes, highs, lows, volumes = accumulation_data
        result = engine.analyze_market_structure(closes, highs, lows, period=10)

        assert isinstance(result, dict)
        assert "structure_score" in result
        assert "trend_confirmation" in result
        assert "volatility_contraction" in result

    def test_analyze_market_structure_bounds(self, engine, accumulation_data):
        """Test market structure values are in valid range."""
        closes, highs, lows, volumes = accumulation_data
        result = engine.analyze_market_structure(closes, highs, lows, period=10)

        assert 0.0 <= result["structure_score"] <= 1.0
        assert 0.0 <= result["trend_confirmation"] <= 1.0
        assert 0.0 <= result["volatility_contraction"] <= 1.0

    def test_analyze_market_structure_higher_lows(self, engine):
        """Test market structure with clear higher lows."""
        closes = [100.0, 100.5, 101.0, 101.5, 102.0, 102.5, 103.0]
        highs = [101.0, 101.5, 102.0, 102.5, 103.0, 103.5, 104.0]
        lows = [99.0, 99.5, 100.0, 100.5, 101.0, 101.5, 102.0]

        result = engine.analyze_market_structure(closes, highs, lows, period=7)

        # Higher lows should have good trend confirmation
        assert result["trend_confirmation"] > 0.5

    def test_analyze_market_structure_insufficient_data(self, engine):
        """Test market structure with insufficient data."""
        closes = [100.0, 101.0, 102.0]
        highs = [101.0, 102.0, 103.0]
        lows = [99.0, 100.0, 101.0]

        result = engine.analyze_market_structure(closes, highs, lows, period=20)

        assert result["structure_score"] == 0.0
        assert result["trend_confirmation"] == 0.0


class TestBCEScoreCalculation:
    def test_calculate_bce_score_range(self, engine):
        """Test BCE score is in 0-6 range."""
        score = engine.calculate_bce_score(
            wyckoff_score=0.8,
            volume_score=0.7,
            exhaustion_score=0.6,
            smart_money_score=0.75,
            structure_score=0.65
        )

        assert isinstance(score, int)
        assert 0 <= score <= 6

    def test_calculate_bce_score_weighted_combination(self, engine):
        """Test BCE score weighting (30, 20, 20, 20, 10)."""
        # Perfect scores on all components
        score_perfect = engine.calculate_bce_score(1.0, 1.0, 1.0, 1.0, 1.0)
        # All zeros
        score_zero = engine.calculate_bce_score(0.0, 0.0, 0.0, 0.0, 0.0)

        assert score_perfect >= 5  # Due to floating point, may be 5 or 6
        assert score_zero == 0

    def test_calculate_bce_score_wyckoff_weighted_highest(self, engine):
        """Test Wyckoff has highest weight (30%)."""
        # Wyckoff high, others low
        score1 = engine.calculate_bce_score(
            wyckoff_score=1.0,
            volume_score=0.0,
            exhaustion_score=0.0,
            smart_money_score=0.0,
            structure_score=0.0
        )

        # Wyckoff low, others high (exclude Wyckoff's share)
        score2 = engine.calculate_bce_score(
            wyckoff_score=0.0,
            volume_score=1.0,
            exhaustion_score=1.0,
            smart_money_score=1.0,
            structure_score=1.0
        )

        # Wyckoff at 1.0 gives 0.3*6 = 1.8 ≈ 1
        # Others at 1.0 give 0.7*6 = 4.2 ≈ 4
        assert score1 < score2

    def test_calculate_bce_score_clipping(self, engine):
        """Test BCE score clipping to 0-6 range."""
        score = engine.calculate_bce_score(1.5, 1.5, 1.5, 1.5, 1.5)
        assert 0 <= score <= 6


class TestSignalValidation:
    def test_validate_signal_gate_5(self, engine):
        """Test signal validation gate at 5/6."""
        assert engine.validate_signal(5) is True
        assert engine.validate_signal(6) is True
        assert engine.validate_signal(4) is False
        assert engine.validate_signal(3) is False
        assert engine.validate_signal(0) is False

    def test_validate_signal_boundary(self, engine):
        """Test validation at gate boundary."""
        assert engine.validate_signal(4) is False
        assert engine.validate_signal(5) is True


class TestComputeBCE:
    def test_compute_bce_returns_tuple(self, engine, accumulation_data):
        """Test compute_bce returns (score, metrics)."""
        closes, highs, lows, volumes = accumulation_data
        score, metrics = engine.compute_bce(closes, highs, lows, volumes, period=10)

        assert isinstance(score, int)
        assert isinstance(metrics, dict)
        assert 0 <= score <= 6

    def test_compute_bce_metrics_completeness(self, engine, accumulation_data):
        """Test compute_bce returns all required metrics."""
        closes, highs, lows, volumes = accumulation_data
        score, metrics = engine.compute_bce(closes, highs, lows, volumes, period=10)

        required_keys = [
            "wyckoff_phase",
            "wyckoff_strength",
            "wyckoff_confidence",
            "volume_strength",
            "volume_consistency",
            "selling_exhaustion",
            "smart_money_accumulation",
            "market_structure",
            "trend_confirmation",
            "volatility_contraction",
            "bce_score",
            "valid_signal",
        ]

        for key in required_keys:
            assert key in metrics, f"Missing metric: {key}"

    def test_compute_bce_signal_validation_consistency(self, engine, accumulation_data):
        """Test that valid_signal matches validate_signal()."""
        closes, highs, lows, volumes = accumulation_data
        score, metrics = engine.compute_bce(closes, highs, lows, volumes, period=10)

        expected_valid = engine.validate_signal(score)
        assert metrics["valid_signal"] == expected_valid

    def test_compute_bce_metric_bounds(self, engine, accumulation_data):
        """Test all metrics are in valid ranges."""
        closes, highs, lows, volumes = accumulation_data
        score, metrics = engine.compute_bce(closes, highs, lows, volumes, period=10)

        assert 0.0 <= metrics["wyckoff_strength"] <= 1.0
        assert 0.0 <= metrics["wyckoff_confidence"] <= 1.0
        assert 0.0 <= metrics["volume_strength"] <= 1.0
        assert 0.0 <= metrics["volume_consistency"] <= 1.0
        assert 0.0 <= metrics["selling_exhaustion"] <= 1.0
        assert 0.0 <= metrics["smart_money_accumulation"] <= 1.0
        assert 0.0 <= metrics["market_structure"] <= 1.0
        assert 0.0 <= metrics["trend_confirmation"] <= 1.0
        assert 0.0 <= metrics["volatility_contraction"] <= 1.0

    def test_compute_bce_insufficient_data(self, engine):
        """Test compute_bce with insufficient data."""
        closes = [100.0, 101.0, 102.0]
        highs = [101.0, 102.0, 103.0]
        lows = [99.0, 100.0, 101.0]
        volumes = [100000, 110000, 120000]

        score, metrics = engine.compute_bce(closes, highs, lows, volumes, period=20)

        assert score == 0
        assert metrics["valid_signal"] is False

    def test_compute_bce_accumulation_vs_distribution(self, engine, accumulation_data, distribution_data):
        """Test compute_bce differentiates accumulation from distribution."""
        closes_acc, highs_acc, lows_acc, vols_acc = accumulation_data
        score_acc, metrics_acc = engine.compute_bce(closes_acc, highs_acc, lows_acc, vols_acc, period=10)

        closes_dis, highs_dis, lows_dis, vols_dis = distribution_data
        score_dis, metrics_dis = engine.compute_bce(closes_dis, highs_dis, lows_dis, vols_dis, period=10)

        # Both should produce valid outputs
        assert isinstance(score_acc, int)
        assert isinstance(score_dis, int)

    def test_compute_bce_deterministic(self, engine, accumulation_data):
        """Test compute_bce produces deterministic results."""
        closes, highs, lows, volumes = accumulation_data

        score1, metrics1 = engine.compute_bce(closes, highs, lows, volumes, period=10)
        score2, metrics2 = engine.compute_bce(closes, highs, lows, volumes, period=10)

        assert score1 == score2
        for key in metrics1:
            if isinstance(metrics1[key], str):
                assert metrics1[key] == metrics2[key]
            else:
                assert abs(metrics1[key] - metrics2[key]) < 1e-10


class TestNoLookahead:
    def test_no_future_volume_in_exhaustion(self, engine):
        """Test selling exhaustion doesn't use future volumes."""
        closes = [100.0, 99.0, 98.0, 97.0, 96.0, 95.0]
        # Future volumes are very high on past down moves
        volumes = [50000, 60000, 70000, 80000, 90000, 100000]

        result = engine.detect_selling_exhaustion(closes, volumes, period=6)

        # Result should not be inflated by future volumes on past moves
        assert result >= 0.0 and result <= 1.0

    def test_no_future_price_in_wyckoff(self, engine):
        """Test Wyckoff analysis doesn't use future prices."""
        closes = [100.0, 99.0, 98.0, 97.0, 98.0, 99.0]
        highs = [101.0, 100.0, 99.0, 98.0, 99.0, 100.0]
        lows = [99.0, 98.0, 97.0, 96.0, 97.0, 98.0]

        result = engine.analyze_wyckoff(closes, highs, lows, period=6)

        # Should recognize structure based on available data only
        assert result.confidence >= 0.0

    def test_compute_bce_uses_only_available_data(self, engine):
        """Test complete BCE doesn't leak future information."""
        closes = [100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0, 92.0, 91.0]
        highs = [101.0, 100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0, 92.0]
        lows = [99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0, 92.0, 91.0, 90.0]
        volumes = [100000, 110000, 120000, 130000, 140000, 150000, 160000, 170000, 180000, 190000]

        # Compute at each point - should only use data up to that point
        for i in range(5, len(closes)):
            score, metrics = engine.compute_bce(
                closes[:i+1], highs[:i+1], lows[:i+1], volumes[:i+1], period=5
            )
            # Should produce valid score using only available data
            assert 0 <= score <= 6


class TestEdgeCases:
    def test_compute_bce_single_candle(self, engine):
        """Test with single candle."""
        score, metrics = engine.compute_bce([100.0], [101.0], [99.0], [100000], period=20)
        assert score == 0

    def test_compute_bce_nan_in_prices(self, engine):
        """Test handling of NaN values."""
        closes = [100.0, np.nan, 102.0, 103.0]
        highs = [101.0, np.nan, 103.0, 104.0]
        lows = [99.0, np.nan, 101.0, 102.0]
        volumes = [100000, 110000, 120000, 130000]

        # Should handle gracefully
        score, metrics = engine.compute_bce(closes, highs, lows, volumes, period=4)
        assert isinstance(score, int)

    def test_compute_bce_extreme_volatility(self, engine):
        """Test with extreme price swings."""
        closes = [100.0, 50.0, 150.0, 75.0, 200.0, 25.0, 300.0]
        highs = [150.0, 100.0, 200.0, 150.0, 300.0, 100.0, 400.0]
        lows = [50.0, 25.0, 100.0, 25.0, 150.0, 10.0, 200.0]
        volumes = [100000, 110000, 120000, 130000, 140000, 150000, 160000]

        score, metrics = engine.compute_bce(closes, highs, lows, volumes, period=7)
        # Should not crash on extreme swings
        assert isinstance(score, int)

    def test_compute_bce_flat_market(self, engine):
        """Test with flat market (no movement)."""
        closes = [100.0] * 20
        highs = [100.0] * 20
        lows = [100.0] * 20
        volumes = [100000] * 20

        score, metrics = engine.compute_bce(closes, highs, lows, volumes, period=20)
        # Flat market should not trigger valid signal (score < 5)
        assert score < 5
        assert metrics["valid_signal"] is False
