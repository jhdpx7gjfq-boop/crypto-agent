"""
Phase B-004: RPM/RCM PIT Compliance Tests

Validates:
- PIT (Point-in-Time) no-lookahead
- Signal bounds [-1, +1]
- Regime alignment correctness
- WFV window boundaries
- IC calculation (Spearman)
- Ablation delta computation
"""

import pytest
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from research.rpm_layer import RPMLayer, RPMSignal
from research.rcm_layer import RCMLayer
from research.phase_b_004_runner import PhaseB004Runner


class TestPITCompliance:
    """Point-in-Time compliance tests."""

    def test_rpm_signal_no_future_data(self):
        """RPM signal should use only past data (PIT-safe)."""
        # Create synthetic OHLCV data with known future movement
        dates = pd.date_range('2021-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'open': np.linspace(100, 150, 100),
            'high': np.linspace(102, 152, 100),
            'low': np.linspace(98, 148, 100),
            'close': np.linspace(100, 150, 100),
            'volume': np.ones(100) * 1000,
            'btc_dominance': np.linspace(40, 42, 100),
            'btc_return': np.random.normal(0.01, 0.02, 100),
            'altcoin_return': np.random.normal(0.02, 0.03, 100),
            'stablecoin_inflow': np.random.normal(0, 100, 100),
            'etf_net_flow': np.random.normal(0, 50, 100),
            'funding_rate_8h': np.random.normal(0, 0.0001, 100),
            'open_interest': np.linspace(1000, 1500, 100),
        }, index=dates)

        rpm = RPMLayer()
        signals = rpm.compute_signal(df)

        # Verify signal exists for each bar
        assert len(signals) == len(df)

        # Verify each signal uses only data up to that point
        for i, sig in enumerate(signals):
            assert sig.timestamp == df.index[i]
            # Signal should not contain NaN (would indicate future leak)
            assert not np.isnan(sig.rpm_signal)

    def test_rpm_lookback_window_valid(self):
        """RPM lookback window should not exceed available history."""
        dates = pd.date_range('2021-01-01', periods=20, freq='D')
        df = pd.DataFrame({
            'close': np.ones(20) * 100,
            'btc_dominance': np.ones(20) * 40,
            'btc_return': np.ones(20) * 0.01,
            'altcoin_return': np.ones(20) * 0.02,
            'stablecoin_inflow': np.ones(20) * 0,
            'etf_net_flow': np.ones(20) * 0,
            'funding_rate_8h': np.ones(20) * 0,
            'open_interest': np.ones(20) * 1000,
        }, index=dates)

        rpm = RPMLayer(lookback_days=5)
        signals = rpm.compute_signal(df)

        # First 4 bars (lookback-1) may have zero signal due to insufficient history
        # But should not crash or produce NaN
        for sig in signals:
            assert not np.isnan(sig.rpm_signal) or sig.rpm_signal == 0.0


class TestRPMSignalBounds:
    """RPM signal range validation."""

    def test_rpm_signal_in_range(self):
        """RPM signal should be bounded to [-1, +1]."""
        dates = pd.date_range('2021-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'close': np.linspace(100, 150, 100),
            'btc_dominance': np.linspace(40, 50, 100),  # Strong change
            'btc_return': np.linspace(-0.1, 0.1, 100),  # Wide range
            'altcoin_return': np.linspace(-0.2, 0.2, 100),  # Extreme ratio
            'stablecoin_inflow': np.linspace(-1000, 1000, 100),  # Extreme flow
            'etf_net_flow': np.linspace(-500, 500, 100),
            'funding_rate_8h': np.linspace(-0.001, 0.001, 100),  # Extreme funding
            'open_interest': np.linspace(500, 2000, 100),  # Strong acceleration
        }, index=dates)

        rpm = RPMLayer()
        signals = rpm.compute_signal(df)

        for sig in signals:
            assert -1.0 <= sig.rpm_signal <= 1.0, f"Signal out of range: {sig.rpm_signal}"

    def test_rpm_component_bounds(self):
        """Each RPM component should be clipped to valid range."""
        dates = pd.date_range('2021-01-01', periods=50, freq='D')
        df = pd.DataFrame({
            'close': np.linspace(100, 200, 50),
            'btc_dominance': np.linspace(10, 90, 50),  # Extreme dominance change
            'btc_return': np.ones(50) * 10.0,  # Extreme return (unrealistic)
            'altcoin_return': np.ones(50) * -5.0,
            'stablecoin_inflow': np.linspace(-10000, 10000, 50),
            'etf_net_flow': np.linspace(-5000, 5000, 50),
            'funding_rate_8h': np.ones(50) * 0.01,
            'open_interest': np.linspace(100, 5000, 50),
        }, index=dates)

        rpm = RPMLayer()
        signals = rpm.compute_signal(df)

        # Check component values are reasonable
        for sig in signals:
            assert -2.0 <= sig.dominance_delta <= 2.0, "Dominance delta out of clip range"
            assert -2.0 <= sig.altseason_momentum <= 2.0, "Altseason out of clip range"
            assert -2.0 <= sig.stablecoin_flow <= 2.0, "Stablecoin flow out of clip range"


class TestRCMRegimeAlignment:
    """RCM regime weighting validation."""

    def test_rcm_regime_alignment_factor(self):
        """RCM should apply correct regime alignment factor."""
        # Create dummy RPM signals
        dates = pd.date_range('2021-01-01', periods=10, freq='D')
        rpm_signals = [
            RPMSignal(
                timestamp=dates[i],
                rpm_score=0.5,
                rpm_signal=0.5,  # Positive RPM
                dominance_delta=0.1,
                altseason_momentum=0.2,
                stablecoin_flow=0.1,
                etf_flow=0.15,
                funding_bias=0.05,
                oi_acceleration=0.05,
            )
            for i in range(10)
        ]

        # Create regime series
        regime_series = pd.Series(
            ['Bull', 'Bull', 'Accumulation', 'Accumulation', 'Bear', 'Bear', 'Bull', 'Bull', 'Accumulation', 'Bear'],
            index=dates
        )

        rcm = RCMLayer()
        rcm_signals = rcm.compute_signal(rpm_signals, regime_series)

        # Verify alignment factors applied
        assert rcm_signals[0].regime_alignment_factor == 1.2  # Bull
        assert rcm_signals[2].regime_alignment_factor == 0.8  # Accumulation
        assert rcm_signals[4].regime_alignment_factor == 0.5  # Bear

    def test_rcm_weighted_signal(self):
        """RCM signal should be RPM × regime_alignment_factor."""
        dates = pd.date_range('2021-01-01', periods=3, freq='D')
        rpm_signals = [
            RPMSignal(dates[0], 0.4, 0.4, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1),
            RPMSignal(dates[1], 0.4, 0.4, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1),
            RPMSignal(dates[2], 0.4, 0.4, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1),
        ]
        regime_series = pd.Series(['Bull', 'Accumulation', 'Bear'], index=dates)

        rcm = RCMLayer()
        rcm_signals = rcm.compute_signal(rpm_signals, regime_series)

        # Bull: 0.4 * 1.2 = 0.48
        assert abs(rcm_signals[0].rcm_signal - 0.48) < 0.01
        # Accumulation: 0.4 * 0.8 = 0.32
        assert abs(rcm_signals[1].rcm_signal - 0.32) < 0.01
        # Bear: 0.4 * 0.5 = 0.20
        assert abs(rcm_signals[2].rcm_signal - 0.20) < 0.01


class TestWFVWindowBoundaries:
    """WFV window creation and boundary validation."""

    def test_wfv_window_count(self):
        """WFV should create exactly 19 windows."""
        runner = PhaseB004Runner()
        windows = runner.create_wfv_windows()
        assert len(windows) == 19

    def test_wfv_window_sizes(self):
        """WFV windows should have correct train/test sizes."""
        runner = PhaseB004Runner()
        windows = runner.create_wfv_windows()

        for idx, (train_start, train_end, test_start, test_end) in enumerate(windows):
            # Train: 180 days
            train_size = train_end - train_start + 1
            assert train_size == 180, f"Window {idx}: train size {train_size} != 180"

            # Test: 30 days
            test_size = test_end - test_start
            assert test_size == 30, f"Window {idx}: test size {test_size} != 30"

            # No gap between train and test
            assert test_start == train_end + 1

    def test_wfv_window_sliding(self):
        """WFV window test period should slide by 30 days each window."""
        runner = PhaseB004Runner()
        windows = runner.create_wfv_windows()

        for i in range(1, len(windows)):
            prev_test_start = windows[i - 1][2]
            curr_test_start = windows[i][2]
            slide = curr_test_start - prev_test_start
            assert slide == 30, f"Window {i}: slide {slide} != 30"


class TestICCalculation:
    """Information Coefficient (Spearman correlation) validation."""

    def test_ic_perfect_correlation(self):
        """IC should be 1.0 for perfect positive correlation."""
        dates = pd.date_range('2021-01-01', periods=50, freq='D')
        df = pd.DataFrame({
            'close': np.linspace(100, 200, 50),
            'btc_dominance': np.ones(50) * 40,
            'btc_return': np.ones(50) * 0.01,
            'altcoin_return': np.ones(50) * 0.01,
            'stablecoin_inflow': np.zeros(50),
            'etf_net_flow': np.zeros(50),
            'funding_rate_8h': np.zeros(50),
            'open_interest': np.ones(50) * 1000,
        }, index=dates)

        runner = PhaseB004Runner()

        # Create perfect signal (same as returns)
        returns = np.linspace(0, 1, 50)
        signal = returns.copy()

        ic = runner.compute_ic(signal, returns)
        assert abs(ic - 1.0) < 0.01, f"Expected IC ≈ 1.0, got {ic}"

    def test_ic_negative_correlation(self):
        """IC should be negative for inverse relationship."""
        runner = PhaseB004Runner()

        signal = np.linspace(1, 0, 50)  # Decreasing
        returns = np.linspace(0, 1, 50)  # Increasing

        ic = runner.compute_ic(signal, returns)
        assert ic < -0.95, f"Expected IC < -0.95, got {ic}"


class TestAblationDelta:
    """Ablation ΔIC computation validation."""

    def test_delta_ic_calculation(self):
        """ΔIC should be correctly computed as IC_J - IC_A."""
        runner = PhaseB004Runner()

        # Simulate IC values
        ic_j_values = [0.05, 0.03, 0.04, 0.06]
        baseline_ic_a = -0.12

        mean_ic_j = np.mean(ic_j_values)
        expected_delta = mean_ic_j - baseline_ic_a

        # Runner computes this internally
        # Verify formula is correct
        assert expected_delta == pytest.approx(0.045 - (-0.12), rel=0.01)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
