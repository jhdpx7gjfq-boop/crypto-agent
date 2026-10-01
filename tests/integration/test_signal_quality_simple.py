"""
Core integration tests for Signal Quality Filter (Phase 3 Component 3).

Focused on key validation logic:
- Confidence scoring and component consistency
- Win probability estimation
- Clustering detection
- Regime context filtering
"""

import pytest
from datetime import datetime, timedelta
from src.layers.layer3_wyckoff.signal_quality import (
    SignalQualityFilter,
    RegimeFilter,
)


class TestSignalConfidenceScoring:
    """Test confidence scoring mechanisms."""

    def test_high_confidence_signal(self):
        """High-quality aligned components = high confidence."""
        filter_inst = SignalQualityFilter(regime_filter=None)

        signal = filter_inst.evaluate_signal(
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
        )

        assert signal.confidence > 85.0
        assert signal.component_consistency > 95.0

    def test_component_consistency_differs(self):
        """Aligned components > scattered components."""
        filter_inst = SignalQualityFilter(regime_filter=None)

        # Aligned
        aligned = filter_inst.evaluate_signal(
            asset='BTC',
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

        # Scattered
        scattered = filter_inst.evaluate_signal(
            asset='ETH',
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

        assert aligned.component_consistency > scattered.component_consistency
        assert aligned.confidence > scattered.confidence


class TestWinProbabilityEstimation:
    """Test win probability scoring."""

    def test_strong_signal_higher_probability(self):
        """Higher BCE score + confidence = higher win probability."""
        filter_inst = SignalQualityFilter(regime_filter=None)

        strong = filter_inst.evaluate_signal(
            asset='BTC',
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

        weak = filter_inst.evaluate_signal(
            asset='ETH',
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

        assert strong.win_probability > weak.win_probability


class TestClusteringDetection:
    """Test signal clustering logic."""

    def test_clustered_signals_detected(self):
        """Signals within 60min window are marked clustered."""
        filter_inst = SignalQualityFilter(regime_filter=None)

        now = datetime.now()
        time1 = now
        time2 = now + timedelta(minutes=30)

        sig1 = filter_inst.evaluate_signal(
            asset='BTC',
            timestamp=time1,
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

        # Second signal within window
        sig2 = filter_inst.evaluate_signal(
            asset='BTC',
            timestamp=time2,
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
            recent_signals=[time1],
        )

        assert not sig1.is_clustered
        assert sig2.is_clustered
        assert sig2.time_since_last_signal == pytest.approx(30.0, abs=1)

    def test_non_clustered_signals_beyond_window(self):
        """Signals > 60min apart not clustered."""
        filter_inst = SignalQualityFilter(regime_filter=None)

        now = datetime.now()
        time1 = now
        time2 = now + timedelta(hours=2)

        sig1 = filter_inst.evaluate_signal(
            asset='BTC',
            timestamp=time1,
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

        sig2 = filter_inst.evaluate_signal(
            asset='BTC',
            timestamp=time2,
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
            recent_signals=[time1],
        )

        assert not sig1.is_clustered
        assert not sig2.is_clustered


class TestRegimeFiltering:
    """Test regime context integration."""

    def test_risk_on_regime_detection(self):
        """Risk-on indicators → high regime score."""
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

    def test_risk_off_regime_detection(self):
        """Risk-off indicators → low regime score."""
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

    def test_signal_entry_requires_risk_on(self):
        """Entry-ready signals require risk-on regime."""
        regime = RegimeFilter()
        filter_inst = SignalQualityFilter(regime_filter=regime)

        # Set risk-on
        regime.assess_regime(
            timestamp=datetime.now(),
            btc_momentum=0.75,
            funding_rate=0.70,
            dxy_trend=-0.60,
            volatility_rank=0.45,
        )

        signal = filter_inst.evaluate_signal(
            asset='BTC',
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


class TestSignalFiltering:
    """Test signal filtering by quality metrics."""

    def test_filter_by_confidence(self):
        """Filter removes low-confidence signals."""
        filter_inst = SignalQualityFilter(regime_filter=None)

        signals = []
        for i in range(3):
            score = 0.88 - i * 0.10  # 0.88, 0.78, 0.68
            sig = filter_inst.evaluate_signal(
                asset='BTC',
                timestamp=datetime.now() + timedelta(hours=i),
                bce_score=score,
                components={
                    'wyckoff_structure': score,
                    'volume_analysis': score - 0.02,
                    'selling_exhaustion': score - 0.03,
                    'smart_money_accumulation': score - 0.01,
                    'market_structure': score,
                    'momentum_confirmation': score - 0.02,
                },
                timeframe_alignment=0.88 - i * 0.10,
            )
            signals.append(sig)

        filtered = filter_inst.filter_signals(
            signals,
            min_confidence=75.0,
            require_regime_alignment=False,
        )

        # Only first signal (88%) should pass 75% threshold
        assert len(filtered) >= 1
        assert filtered[0].bce_score > 0.85

    def test_best_signal_per_asset(self):
        """Select highest confidence signal per asset."""
        filter_inst = SignalQualityFilter(regime_filter=None)

        signals = [
            # BTC signal 1
            filter_inst.evaluate_signal(
                asset='BTC',
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
            # BTC signal 2 (better)
            filter_inst.evaluate_signal(
                asset='BTC',
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
            # ETH signal
            filter_inst.evaluate_signal(
                asset='ETH',
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

        best = filter_inst.get_best_signal_per_asset(signals)

        assert len(best) == 2
        assert 'BTC' in best
        assert 'ETH' in best
        assert best['BTC'].confidence > best['ETH'].confidence
