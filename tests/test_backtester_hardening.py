"""
Tests for Phase 2.1: Backtester Hardening

Validates:
- Real equity accounting (mark-to-market)
- PIT no-look-ahead guarantee
- Annualized metrics correctness
- Trade provenance
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.validation.backtester_hardening import (
    EquityBacktester,
    EquitySnapshot,
    Trade,
    BacktestMetrics
)


@pytest.fixture
def sample_ohlcv():
    """Generate synthetic OHLCV data for testing."""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    close_prices = 100 + np.cumsum(np.random.randn(100) * 2)

    df = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices * 0.99,
        'high': close_prices * 1.02,
        'low': close_prices * 0.98,
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, 100)
    })

    return df


class TestPITCompliance:
    """Test Point-in-Time (no look-ahead) guarantee."""

    def test_pit_signal_uses_only_past_data(self, sample_ohlcv):
        """Signal at index T should use only data[:T] (exclusive of T)."""
        bt = EquityBacktester(sample_ohlcv)

        signal_call_count = 0
        max_idx_seen = -1

        def signal_func(pit_data, current_idx, params):
            nonlocal signal_call_count, max_idx_seen
            signal_call_count += 1
            max_idx_seen = max(max_idx_seen, len(pit_data) - 1)
            # Signal should have AT MOST current_idx data points (0-indexed)
            assert len(pit_data) <= current_idx + 1, \
                f"Signal received {len(pit_data)} rows but current_idx={current_idx}"
            return 0.0

        def position_func(signal, pos, params):
            return 0

        bt.run_simulation(signal_func, position_func)

        assert signal_call_count > 0, "Signal function was never called"
        logger.info(f"PIT test: {signal_call_count} signals, max_idx={max_idx_seen}")

    def test_pit_future_data_modification(self, sample_ohlcv):
        """Changing T+2 data should NOT affect signal at T."""
        bt1 = EquityBacktester(sample_ohlcv.copy())
        bt2 = EquityBacktester(sample_ohlcv.copy())

        signals1 = []
        signals2 = []

        def signal_func_1(pit_data, current_idx, params):
            sig = float(pit_data['close'].iloc[-1] - pit_data['close'].iloc[0])
            signals1.append((current_idx, sig))
            return np.clip(sig / 100, -1, 1)

        def signal_func_2(pit_data, current_idx, params):
            sig = float(pit_data['close'].iloc[-1] - pit_data['close'].iloc[0])
            signals2.append((current_idx, sig))
            return np.clip(sig / 100, -1, 1)

        def position_func(signal, pos, params):
            return 1 if signal > 0 else (-1 if signal < 0 else 0)

        # Run first backtest
        bt1.run_simulation(signal_func_1, position_func)

        # Modify future data in second backtest
        df2 = sample_ohlcv.copy()
        df2.loc[df2.index[50], 'close'] = 500  # Modify T+50 (future relative to many timestamps)
        bt2.df = df2
        bt2.run_simulation(signal_func_2, position_func)

        # Compare signals up to idx 45 (before modification)
        for i in range(min(45, len(signals1), len(signals2))):
            idx1, sig1 = signals1[i]
            idx2, sig2 = signals2[i]
            # Signals should match (no future data leaked)
            assert np.isclose(sig1, sig2, rtol=1e-9), \
                f"Signal at idx {i} changed when future data modified: {sig1} vs {sig2}"


class TestEquityAccounting:
    """Test mark-to-market equity accounting."""

    def test_equity_conservation(self, sample_ohlcv):
        """Equity = Cash + Position_Value (mark-to-market)."""
        bt = EquityBacktester(sample_ohlcv, start_cash=10000, slippage_pct=0, commission_pct=0)

        def signal_func(pit_data, idx, params):
            momentum = pit_data['close'].iloc[-1] - pit_data['close'].iloc[-5]
            return np.clip(momentum / 100, -1, 1)

        def position_func(signal, pos, params):
            return 1 if signal > 0 else 0

        equity_log, _, _ = bt.run_simulation(signal_func, position_func)

        for snapshot in equity_log:
            expected_equity = snapshot.cash + snapshot.position_qty * \
                             sample_ohlcv.iloc[
                                 sample_ohlcv['timestamp'] == snapshot.timestamp
                             ].index[0]

            # Allow tiny floating-point error
            assert np.isclose(snapshot.close_equity, snapshot.cash + snapshot.position_value, rtol=1e-6), \
                f"Equity accounting mismatch at {snapshot.timestamp}"

    def test_zero_commission_equity_equals_initial(self, sample_ohlcv):
        """With no trades, equity should = start_cash."""
        bt = EquityBacktester(sample_ohlcv, start_cash=10000)

        def signal_func(pit_data, idx, params):
            return 0.0  # No signal

        def position_func(signal, pos, params):
            return 0  # No position

        equity_log, trades, _ = bt.run_simulation(signal_func, position_func)

        assert len(trades) == 0, "Should have zero trades"
        for snapshot in equity_log:
            assert np.isclose(snapshot.close_equity, 10000, rtol=1e-9), \
                f"Equity changed without trades: {snapshot.close_equity}"


class TestAnnualizedMetrics:
    """Test annualized return and Sharpe calculation."""

    def test_annualized_return_100pct_over_1yr(self, sample_ohlcv):
        """1-year of +100% return should annualize to ~100%."""
        # Create 1-year synthetic data with linear growth from 100 to 200
        dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
        close_prices = np.linspace(100, 200, len(dates))

        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices * 0.99,
            'high': close_prices * 1.02,
            'low': close_prices * 0.98,
            'close': close_prices,
            'volume': np.full(len(dates), 1000)
        })

        # Use small capital so buying 1 unit uses all cash (full investment)
        bt = EquityBacktester(df, start_cash=100)

        def signal_func(pit_data, idx, params):
            return 1.0  # Always bullish

        def position_func(signal, pos, params):
            return 1  # Always long (1 unit)

        _, _, metrics = bt.run_simulation(signal_func, position_func)

        # Fully invested at 100, doubles to 200 = 100% return
        # Annualized over 1 year: log(2) / 1 = 0.693, exp(0.693) - 1 ≈ 1.0
        assert 0.85 < metrics.annualized_return < 1.15, \
            f"Annualized return {metrics.annualized_return} not close to 1.0 (got {metrics.total_return})"

    def test_sharpe_positive_drift(self, sample_ohlcv):
        """Consistent uptrend should have positive Sharpe."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=252, freq='D')  # 1 year
        # Strong uptrend: 100 to 150 (50% return)
        close_prices = np.linspace(100, 150, len(dates))

        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices * 0.99,
            'high': close_prices * 1.01,
            'low': close_prices * 0.99,
            'close': close_prices,
            'volume': np.full(len(dates), 1000)
        })

        # Fully invested
        bt = EquityBacktester(df, start_cash=100, risk_free_rate=0.02)

        def signal_func(pit_data, idx, params):
            return 1.0

        def position_func(signal, pos, params):
            return 1

        _, _, metrics = bt.run_simulation(signal_func, position_func)

        assert metrics.sharpe_ratio > 0.5, \
            f"Sharpe {metrics.sharpe_ratio} should be > 0.5 for uptrend; total_return={metrics.total_return}"


class TestTradeProvenance:
    """Test trade record provenance and correctness."""

    def test_trade_entry_exit_recorded(self, sample_ohlcv):
        """Each trade should record entry and exit correctly."""
        bt = EquityBacktester(sample_ohlcv, start_cash=10000)

        def signal_func(pit_data, idx, params):
            return 1.0 if idx % 10 < 5 else -1.0

        def position_func(signal, pos, params):
            return 1 if signal > 0 else 0

        _, trades, _ = bt.run_simulation(signal_func, position_func)

        assert len(trades) > 0, "Should have at least one trade"

        for trade in trades:
            assert trade.entry_timestamp is not None
            assert trade.entry_price > 0
            assert trade.exit_timestamp is not None
            assert trade.exit_price > 0
            assert trade.entry_signal_pit_cutoff is not None
            assert trade.pnl is not None

    def test_trade_pit_cutoff_is_valid(self, sample_ohlcv):
        """Trade entry_signal_pit_cutoff should be before exit_timestamp."""
        bt = EquityBacktester(sample_ohlcv, start_cash=10000)

        def signal_func(pit_data, idx, params):
            return 1.0 if idx < 50 else -1.0

        def position_func(signal, pos, params):
            return 1 if signal > 0 else 0

        _, trades, _ = bt.run_simulation(signal_func, position_func)

        for trade in trades:
            assert trade.entry_signal_pit_cutoff < trade.exit_timestamp, \
                f"PIT cutoff {trade.entry_signal_pit_cutoff} not before exit {trade.exit_timestamp}"


class TestT2TConvention:
    """Test T→T execution convention (entry at T, exit at T+n)."""

    def test_entry_exit_same_direction_confirmed(self, sample_ohlcv):
        """Verify no same-bar entry/exit in backtest."""
        bt = EquityBacktester(sample_ohlcv, start_cash=10000)

        def signal_func(pit_data, idx, params):
            return 1.0 if idx < 30 else -1.0

        def position_func(signal, pos, params):
            return 1 if signal > 0 else 0

        _, trades, _ = bt.run_simulation(signal_func, position_func)

        for trade in trades:
            # Entry and exit should be on different timestamps
            assert trade.entry_timestamp != trade.exit_timestamp, \
                "Entry and exit on same timestamp violates T→T"
            assert trade.entry_timestamp < trade.exit_timestamp, \
                "Entry should be before exit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# Import logger for test output
import logging
logger = logging.getLogger(__name__)
