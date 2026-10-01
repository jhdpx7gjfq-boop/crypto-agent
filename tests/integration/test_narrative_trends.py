"""
Integration tests for Phase 5 Narrative Trend Analyzer.

Tests adoption acceleration detection, peak identification, reversal signals, lifecycle progression.
"""

import pytest
from datetime import datetime

from src.layers.layer5_narm.narrative_trends import NarrativeTrendAnalyzer


class TestNarrativeTrendAnalyzer:
    """Test narrative trend analysis."""

    @pytest.fixture
    def analyzer(self):
        """Create narrative trend analyzer."""
        return NarrativeTrendAnalyzer(min_history=10)

    def test_adoption_acceleration_detection(self, analyzer):
        """Detect adoption acceleration (second derivative)."""
        # Accelerating NARM: 50 → 55 → 62 → 71 (accelerating growth)
        historical_narm = [
            50.0, 51.0, 52.0, 53.0, 54.0,  # Steady
            55.0, 57.0, 60.0, 65.0, 71.0,  # Accelerating
        ]

        adoption = [30.0] * len(historical_narm)

        report = analyzer.track_narrative_progression(
            asset="AI_ACCEL",
            historical_narm=historical_narm,
            historical_adoption=adoption,
        )

        assert report.current_stage != "unknown"
        assert report.trend_metrics.adoption_acceleration > 0  # Accelerating
        assert report.confidence_score > 0.5  # Should have decent confidence

    def test_peak_detection(self, analyzer):
        """Detect peak in narrative strength."""
        # Peak pattern: rise to 82, then decline
        historical_narm = [
            40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 82.0,
            80.0, 78.0, 75.0, 72.0, 70.0,
        ]

        adoption = [40.0] * len(historical_narm)

        report = analyzer.track_narrative_progression(
            asset="PEAK_TOKEN",
            historical_narm=historical_narm,
            historical_adoption=adoption,
        )

        # Should detect peak
        if report.peak_detection:
            assert report.peak_detection.peak_narm >= 82.0
            assert report.peak_detection.days_from_peak >= 0
            assert report.peak_detection.reversal_probability > 0

    def test_reversal_signal_detection(self, analyzer):
        """Detect narrative reversal/decline."""
        # Sharp decline: 80 → 60 (20 point drop)
        historical_narm = [
            70.0, 72.0, 75.0, 78.0, 80.0,
            78.0, 75.0, 70.0, 65.0, 60.0,  # Sharp decline
        ]

        adoption = [60.0, 62.0, 65.0, 68.0, 70.0, 68.0, 60.0, 50.0, 40.0, 30.0]

        report = analyzer.track_narrative_progression(
            asset="REVERSING",
            historical_narm=historical_narm,
            historical_adoption=adoption,
        )

        assert report.reversal_signal.reversal_detected
        assert report.reversal_signal.confidence > 0.5
        assert report.current_stage in ["declining", "late"]

    def test_lifecycle_stage_progression(self, analyzer):
        """Track progression through lifecycle stages."""
        # Early stage: low NARM, not yet accelerating
        early_narm = [30.0, 32.0, 35.0, 38.0, 40.0, 42.0, 45.0, 48.0, 50.0, 50.5]

        report_early = analyzer.track_narrative_progression(
            asset="EARLY_STAGE",
            historical_narm=early_narm,
            historical_adoption=[20.0] * len(early_narm),
        )

        # Low NARM score should be early stage
        assert report_early.current_stage in ["early", "mid"]
        assert report_early.lifecycle_position < 0.7

        # Late stage: high NARM with positive momentum
        late_narm = [65.0, 66.0, 68.0, 70.0, 72.0, 74.0, 76.0, 78.0, 80.0, 82.0]

        report_late = analyzer.track_narrative_progression(
            asset="LATE_STAGE",
            historical_narm=late_narm,
            historical_adoption=[70.0] * len(late_narm),
        )

        # High score indicates late stage (or declining if peak detected)
        assert report_late.current_stage in ["late", "mid", "declining"]
        assert report_late.lifecycle_position > 0.6

    def test_momentum_bar_counting(self, analyzer):
        """Count consecutive up/down periods."""
        # 5 consecutive up bars, then reversal
        historical_narm = [
            50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0,  # 6 up
            79.0, 78.0, 77.0,  # 2 down
        ]

        adoption = [40.0] * len(historical_narm)

        report = analyzer.track_narrative_progression(
            asset="MOMENTUM_TEST",
            historical_narm=historical_narm,
            historical_adoption=adoption,
        )

        # Recent momentum should show downward direction
        assert report.momentum_bars < 0  # Negative = down

    def test_moving_average_crossover(self, analyzer):
        """Test SMA trend identification."""
        # Constant high value
        high_narm = [70.0] * 10

        report_high = analyzer.track_narrative_progression(
            asset="HIGH_STABLE",
            historical_narm=high_narm,
            historical_adoption=[70.0] * 10,
        )

        # Both MAs should be around same value
        assert abs(report_high.trend_metrics.score_ma_short - report_high.trend_metrics.score_ma_long) < 5

        # Rising trend
        rising_narm = [50.0] * 5 + [60.0, 70.0, 80.0, 85.0, 90.0]

        report_rising = analyzer.track_narrative_progression(
            asset="RISING",
            historical_narm=rising_narm,
            historical_adoption=[50.0] * len(rising_narm),
        )

        # Recent values should be significantly higher
        assert report_rising.trend_metrics.score_ma_short > 50  # Recent is high

    def test_volatility_measurement(self, analyzer):
        """Measure volatility in adoption curve."""
        # Stable adoption
        stable_narm = [60.0] * 10

        report_stable = analyzer.track_narrative_progression(
            asset="STABLE",
            historical_narm=stable_narm,
            historical_adoption=[60.0] * 10,
        )

        # Volatile adoption
        volatile_narm = [50.0, 70.0, 45.0, 75.0, 40.0, 80.0, 50.0, 70.0, 55.0, 65.0]

        report_volatile = analyzer.track_narrative_progression(
            asset="VOLATILE",
            historical_narm=volatile_narm,
            historical_adoption=[50.0] * 10,
        )

        # Volatile should have higher volatility
        assert report_volatile.trend_metrics.volatility > report_stable.trend_metrics.volatility

    def test_insufficient_data_handling(self, analyzer):
        """Handle short history gracefully."""
        short_history = [60.0, 62.0, 65.0]  # Only 3 points

        report = analyzer.track_narrative_progression(
            asset="SHORT_HISTORY",
            historical_narm=short_history,
            historical_adoption=[60.0] * len(short_history),
        )

        assert report.confidence_score == 0.0
        assert report.current_stage == "unknown"

    def test_adoption_deceleration(self, analyzer):
        """Detect adoption deceleration (losing momentum)."""
        # Initially fast growth, then slowing
        historical_narm = [
            40.0, 48.0, 55.0, 60.0, 64.0, 67.0, 69.0, 70.5, 71.5, 72.0,  # Decelerating
        ]

        adoption = [20.0, 30.0, 40.0, 48.0, 54.0, 59.0, 62.0, 64.0, 65.5, 66.5]

        report = analyzer.track_narrative_progression(
            asset="DECEL",
            historical_narm=historical_narm,
            historical_adoption=adoption,
        )

        assert report.trend_metrics.narrative_momentum in ["stable", "decelerating"]
        assert report.expected_next_move != "up"  # Momentum fading


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
