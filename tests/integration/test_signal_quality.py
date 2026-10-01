"""
Integration tests for Signal Quality Filter (Phase 3 Component 3).

Tests:
- Confidence scoring from component alignment
- Signal clustering detection
- Win probability estimation
- Regime filtering
- Signal quality validation
"""

import pytest
from datetime import datetime, timedelta
from src.layers.layer3_wyckoff.signal_quality import (
    SignalQualityFilter,
    RegimeFilter,
    SignalQuality,
)


class TestSignalQualityFilter:
    """Tests for SignalQualityFilter class."""

    @pytest.fixture
    def filter_instance(self):
        """Create filter without regime dependency for basic tests."""
        return SignalQualityFilter(regime_filter=None)

    def test_high_quality_signal(self, filter_instance):
        """Test evaluation of high-confidence signal."""
        signal = filter_instance.evaluate_signal(
            asset='BTCUSDT',
            timestamp=datetime.now(),
            bce_score=0.85,  # >= 5/6
            components={
                'wyckoff_structure': 0.85,
                'volume_analysis': 0.82,
                'selling_exhaustion': 0.80,
                'smart_money_accumulation': 0.78,
                'market_structure': 0.83,
                'momentum_confirmation': 0.81,
            },
            timeframe_alignment=0.90,
        )

        assert signal.bce_score == 0.85
        assert signal.confidence >= 75.0  # High confidence
        assert signal.win_probability >= 0.6

    def test_confidence_scoring_variance(self, filter_instance):
        """Test rejection of low-confidence signal."""
        signal = filter_instance.evaluate_signal(
            asset='BTCUSDT',
            timestamp=datetime.now(),
            bce_score=0.55,  # Low BCE
            components={
                'wyckoff_structure': 0.45,
                'volume_analysis': 0.50,
                'selling_exhaustion': 0.40,
                'smart_money_accumulation': 0.50,
                'market_structure': 0.45,
                'momentum_confirmation': 0.48,
            },
            timeframe_alignment=0.60,
        )

        assert signal.confidence < 70.0
        assert signal.is_rejected
        assert any('confidence' in r.lower() for r in signal.rejection_reasons)

    def test_component_consistency_calculation(self, filter_instance):
        """Test component consistency scoring."""
        # High consistency: components aligned
        signal_aligned = filter_instance.evaluate_signal(
            asset='BTCUSDT',
            timestamp=datetime.now(),
            bce_score=0.80,
            components={
                'wyckoff_structure': 0.80,
                'volume_analysis': 0.81,
                'selling_exhaustion': 0.79,
                'smart_money_accumulation': 0.80,
                'market_structure': 0.81,
                'momentum_confirmation': 0.80,
            },
            timeframe_alignment=0.85,
        )

        # Low consistency: components scattered
        signal_scattered = filter_instance.evaluate_signal(
            asset='ETHUSDT',
            timestamp=datetime.now(),
            bce_score=0.70,
            components={
                'wyckoff_structure': 0.95,
                'volume_analysis': 0.45,
                'selling_exhaustion': 0.90,
                'smart_money_accumulation': 0.30,
                'market_structure': 0.85,
                'momentum_confirmation': 0.50,
            },
            timeframe_alignment=0.85,
        )

        assert signal_aligned.component_consistency > signal_scattered.component_consistency

    def test_pattern_strength_calculation(self, filter_instance):
        """Test pattern strength scoring."""
        # Strong pattern
        strong = filter_instance.evaluate_signal(
            asset='BTCUSDT',
            timestamp=datetime.now(),
            bce_score=0.88,
            components={
                'wyckoff_structure': 0.90,
                'volume_analysis': 0.88,
                'selling_exhaustion': 0.85,
                'smart_money_accumulation': 0.87,
                'market_structure': 0.89,
                'momentum_confirmation': 0.86,
            },
            timeframe_alignment=0.90,
        )

        # Weak pattern
        weak = filter_instance.evaluate_signal(
            asset='ETHUSDT',
            timestamp=datetime.now(),
            bce_score=0.62,
            components={
                'wyckoff_structure': 0.55,
                'volume_analysis': 0.58,
                'selling_exhaustion': 0.50,
                'smart_money_accumulation': 0.65,
                'market_structure': 0.60,
                'momentum_confirmation': 0.70,
            },
            timeframe_alignment=0.65,
        )

        assert strong.pattern_strength > weak.pattern_strength

    def test_signal_clustering_detection(self, filter_instance):
        """Test clustering detection with multiple signals."""
        now = datetime.now()
        signal1_time = now
        signal2_time = now + timedelta(minutes=15)  # Within window
        signal3_time = now + timedelta(hours=2)  # Outside window

        # First signal: no prior signals
        signal1 = filter_instance.evaluate_signal(
            asset='BTCUSDT',
            timestamp=signal1_time,
            bce_score=0.85,
            components={
                'wyckoff_structure': 0.85,
                'volume_analysis': 0.82,
                'selling_exhaustion': 0.80,
                'smart_money_accumulation': 0.78,
                'market_structure': 0.83,
                'momentum_confirmation': 0.81,
            },
            timeframe_alignment=0.90,
            recent_signals=[],
        )

        assert not signal1.is_clustered
        assert signal1.time_since_last_signal is None

        # Second signal: within cluster window
        signal2 = filter_instance.evaluate_signal(
            asset='BTCUSDT',
            timestamp=signal2_time,
            bce_score=0.84,
            components={
                'wyckoff_structure': 0.84,
                'volume_analysis': 0.81,
                'selling_exhaustion': 0.79,
                'smart_money_accumulation': 0.77,
                'market_structure': 0.82,
                'momentum_confirmation': 0.80,
            },
            timeframe_alignment=0.89,
            recent_signals=[signal1_time],
        )

        assert signal2.is_clustered
        assert signal2.time_since_last_signal == pytest.approx(15.0, abs=1)

        # Third signal: outside cluster window
        signal3 = filter_instance.evaluate_signal(
            asset='BTCUSDT',
            timestamp=signal3_time,
            bce_score=0.86,
            components={
                'wyckoff_structure': 0.86,
                'volume_analysis': 0.83,
                'selling_exhaustion': 0.81,
                'smart_money_accumulation': 0.79,
                'market_structure': 0.84,
                'momentum_confirmation': 0.82,
            },
            timeframe_alignment=0.91,
            recent_signals=[signal1_time, signal2_time],
        )

        assert not signal3.is_clustered  # Beyond window
        assert signal3.time_since_last_signal == pytest.approx(120.0, abs=1)

    def test_win_probability_estimation(self, filter_instance):
        """Test win probability increases with signal quality."""
        strong_signal = filter_instance.evaluate_signal(
            asset='BTCUSDT',
            timestamp=datetime.now(),
            bce_score=0.88,
            components={
                'wyckoff_structure': 0.90,
                'volume_analysis': 0.88,
                'selling_exhaustion': 0.85,
                'smart_money_accumulation': 0.87,
                'market_structure': 0.89,
                'momentum_confirmation': 0.86,
            },
            timeframe_alignment=0.90,
        )

        weak_signal = filter_instance.evaluate_signal(
            asset='ETHUSDT',
            timestamp=datetime.now(),
            bce_score=0.65,
            components={
                'wyckoff_structure': 0.60,
                'volume_analysis': 0.65,
                'selling_exhaustion': 0.62,
                'smart_money_accumulation': 0.68,
                'market_structure': 0.63,
                'momentum_confirmation': 0.67,
            },
            timeframe_alignment=0.68,
        )

        assert strong_signal.win_probability > weak_signal.win_probability

    def test_filter_signals_by_confidence(self, filter_instance):
        """Test filtering signals by confidence threshold."""
        signals = [
            filter_instance.evaluate_signal(
                asset='BTCUSDT',
                timestamp=datetime.now(),
                bce_score=0.88,
                components={
                    'wyckoff_structure': 0.88,
                    'volume_analysis': 0.87,
                    'selling_exhaustion': 0.86,
                    'smart_money_accumulation': 0.87,
                    'market_structure': 0.88,
                    'momentum_confirmation': 0.87,
                },
                timeframe_alignment=0.90,
            ),
            filter_instance.evaluate_signal(
                asset='ETHUSDT',
                timestamp=datetime.now() + timedelta(minutes=5),
                bce_score=0.70,
                components={
                    'wyckoff_structure': 0.65,
                    'volume_analysis': 0.70,
                    'selling_exhaustion': 0.68,
                    'smart_money_accumulation': 0.72,
                    'market_structure': 0.67,
                    'momentum_confirmation': 0.71,
                },
                timeframe_alignment=0.72,
            ),
        ]

        # Filter with high threshold
        filtered = filter_instance.filter_signals(signals, min_confidence=75.0, require_regime_alignment=False)

        assert len(filtered) == 1
        assert filtered[0].asset == 'BTCUSDT'

    def test_get_best_signal_per_asset(self, filter_instance):
        """Test selecting best signal per asset from cluster."""
        signals = [
            filter_instance.evaluate_signal(
                asset='BTCUSDT',
                timestamp=datetime.now(),
                bce_score=0.83,
                components={
                    'wyckoff_structure': 0.83,
                    'volume_analysis': 0.82,
                    'selling_exhaustion': 0.80,
                    'smart_money_accumulation': 0.81,
                    'market_structure': 0.83,
                    'momentum_confirmation': 0.82,
                },
                timeframe_alignment=0.85,
            ),
            filter_instance.evaluate_signal(
                asset='BTCUSDT',
                timestamp=datetime.now() + timedelta(minutes=5),
                bce_score=0.86,
                components={
                    'wyckoff_structure': 0.87,
                    'volume_analysis': 0.85,
                    'selling_exhaustion': 0.84,
                    'smart_money_accumulation': 0.86,
                    'market_structure': 0.86,
                    'momentum_confirmation': 0.85,
                },
                timeframe_alignment=0.88,
            ),
            filter_instance.evaluate_signal(
                asset='ETHUSDT',
                timestamp=datetime.now(),
                bce_score=0.80,
                components={
                    'wyckoff_structure': 0.80,
                    'volume_analysis': 0.79,
                    'selling_exhaustion': 0.78,
                    'smart_money_accumulation': 0.81,
                    'market_structure': 0.80,
                    'momentum_confirmation': 0.79,
                },
                timeframe_alignment=0.82,
            ),
        ]

        best = filter_instance.get_best_signal_per_asset(signals)

        assert 'BTCUSDT' in best
        assert 'ETHUSDT' in best
        assert best['BTCUSDT'].confidence >= best['ETHUSDT'].confidence


class TestRegimeFilter:
    """Tests for RegimeFilter class."""

    def test_risk_on_detection(self):
        """Test detection of risk-on regime."""
        regime = RegimeFilter()

        context, score = regime.assess_regime(
            timestamp=datetime.now(),
            btc_momentum=0.75,
            funding_rate=0.70,
            dxy_trend=-0.60,
            volatility_rank=0.45,
        )

        assert context == 'risk_on'
        assert score >= 0.6

    def test_risk_off_detection(self):
        """Test detection of risk-off regime."""
        regime = RegimeFilter()

        context, score = regime.assess_regime(
            timestamp=datetime.now(),
            btc_momentum=-0.70,
            funding_rate=-0.65,
            dxy_trend=0.70,
            volatility_rank=0.85,
        )

        assert context == 'risk_off'
        assert score <= 0.4

    def test_neutral_regime(self):
        """Test neutral regime detection."""
        regime = RegimeFilter()

        context, score = regime.assess_regime(
            timestamp=datetime.now(),
            btc_momentum=0.20,
            funding_rate=0.25,
            dxy_trend=-0.10,
            volatility_rank=0.55,
        )

        assert context == 'neutral'
        assert 0.35 < score < 0.65  # Relaxed bounds for neutral

    def test_regime_strength_tracking(self):
        """Test regime strength calculation over time."""
        regime = RegimeFilter()
        now = datetime.now()

        # Generate 10 assessments over 24 hours
        for i in range(10):
            regime.assess_regime(
                timestamp=now - timedelta(hours=24-i*2.5),
                btc_momentum=0.70,
                funding_rate=0.65,
                dxy_trend=-0.50,
                volatility_rank=0.45,
            )

        strength = regime.get_regime_strength(lookback_hours=24)
        assert 0.5 < strength <= 1.0  # Should show risk-on strength


class TestSignalQualityWithRegime:
    """Tests for Signal Quality Filter with regime context."""

    @pytest.fixture
    def filter_with_regime(self):
        """Create filter with regime detection."""
        regime = RegimeFilter()
        return SignalQualityFilter(regime_filter=regime)

    def test_signal_valid_for_entry_risk_on(self, filter_with_regime):
        """Test entry readiness in risk-on regime."""
        # Set risk-on regime
        filter_with_regime.regime_filter.assess_regime(
            timestamp=datetime.now(),
            btc_momentum=0.75,
            funding_rate=0.70,
            dxy_trend=-0.60,
            volatility_rank=0.45,
        )

        signal = filter_with_regime.evaluate_signal(
            asset='BTCUSDT',
            timestamp=datetime.now(),
            bce_score=0.88,
            components={
                'wyckoff_structure': 0.88,
                'volume_analysis': 0.87,
                'selling_exhaustion': 0.86,
                'smart_money_accumulation': 0.87,
                'market_structure': 0.88,
                'momentum_confirmation': 0.87,
            },
            timeframe_alignment=0.90,
            recent_signals=[],
        )

        assert signal.is_valid_for_entry(min_confidence=70.0)

    def test_signal_rejected_risk_off(self, filter_with_regime):
        """Test signal rejection in risk-off regime."""
        # Set risk-off regime
        filter_with_regime.regime_filter.assess_regime(
            timestamp=datetime.now(),
            btc_momentum=-0.70,
            funding_rate=-0.65,
            dxy_trend=0.70,
            volatility_rank=0.85,
        )

        signal = filter_with_regime.evaluate_signal(
            asset='BTCUSDT',
            timestamp=datetime.now(),
            bce_score=0.88,
            components={
                'wyckoff_structure': 0.88,
                'volume_analysis': 0.87,
                'selling_exhaustion': 0.86,
                'smart_money_accumulation': 0.87,
                'market_structure': 0.88,
                'momentum_confirmation': 0.87,
            },
            timeframe_alignment=0.90,
            recent_signals=[],
        )

        assert not signal.is_valid_for_entry()
        assert any('risk-off' in r.lower() for r in signal.rejection_reasons)


class TestSignalQualityIntegration:
    """Integration tests for complete signal quality workflow."""

    def test_end_to_end_signal_evaluation(self):
        """Test complete signal evaluation workflow."""
        regime = RegimeFilter()
        filter_inst = SignalQualityFilter(regime_filter=regime)

        # Set risk-on regime
        regime.assess_regime(
            timestamp=datetime.now(),
            btc_momentum=0.75,
            funding_rate=0.70,
            dxy_trend=-0.60,
            volatility_rank=0.45,
        )

        # Simulate receiving multiple signals
        signals = []
        for i in range(3):
            timestamp = datetime.now() + timedelta(hours=i*2)
            signal = filter_inst.evaluate_signal(
                asset='BTCUSDT',
                timestamp=timestamp,
                bce_score=0.85 - i*0.02,
                components={
                    'wyckoff_structure': 0.85 - i*0.02,
                    'volume_analysis': 0.83 - i*0.02,
                    'selling_exhaustion': 0.82 - i*0.02,
                    'smart_money_accumulation': 0.84 - i*0.02,
                    'market_structure': 0.83 - i*0.02,
                    'momentum_confirmation': 0.82 - i*0.02,
                },
                timeframe_alignment=0.88 - i*0.02,
                recent_signals=[s.timestamp for s in signals],
            )
            signals.append(signal)

        # Validate workflow
        assert len(signals) == 3
        assert signals[0].confidence > signals[2].confidence

        # Filter for entry-ready signals
        entry_ready = [s for s in signals if s.is_valid_for_entry()]
        assert len(entry_ready) > 0
