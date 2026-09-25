"""Unit tests for backtesting framework."""

import pytest
from datetime import datetime, timedelta

from src.core.backtest import Trade, TradeType, BacktestEngine, WalkForwardValidator
from tests.fixtures.market_data import generate_mock_ohlcv


class TestTrade:
    """Tests for Trade dataclass."""

    def test_trade_creation_long(self):
        """Long trade should be created correctly."""
        now = datetime.utcnow()
        trade = Trade(
            entry_time=now,
            entry_price=100.0,
            exit_time=now + timedelta(days=1),
            exit_price=105.0,
            trade_type=TradeType.LONG,
        )
        assert trade.trade_type == TradeType.LONG
        assert trade.quantity == 1.0

    def test_trade_pnl_long(self):
        """Long trade P&L should be positive on up move."""
        now = datetime.utcnow()
        trade = Trade(
            entry_time=now,
            entry_price=100.0,
            exit_time=now + timedelta(days=1),
            exit_price=110.0,
            trade_type=TradeType.LONG,
            quantity=1.0,
        )
        assert trade.pnl == 10.0  # 110 - 100
        assert trade.pnl_pct == 10.0  # (110-100)/100 * 100
        assert trade.is_winning is True

    def test_trade_pnl_long_losing(self):
        """Long trade should be losing on down move."""
        now = datetime.utcnow()
        trade = Trade(
            entry_time=now,
            entry_price=100.0,
            exit_time=now + timedelta(days=1),
            exit_price=95.0,
            trade_type=TradeType.LONG,
        )
        assert trade.pnl == -5.0
        assert trade.pnl_pct == -5.0
        assert trade.is_winning is False

    def test_trade_pnl_short(self):
        """Short trade P&L should be positive on down move."""
        now = datetime.utcnow()
        trade = Trade(
            entry_time=now,
            entry_price=100.0,
            exit_time=now + timedelta(days=1),
            exit_price=90.0,
            trade_type=TradeType.SHORT,
        )
        assert trade.pnl == 10.0  # 100 - 90
        assert trade.pnl_pct == 10.0
        assert trade.is_winning is True


class TestBacktestEngine:
    """Tests for BacktestEngine."""

    def test_engine_creation(self):
        """BacktestEngine should initialize with capital."""
        engine = BacktestEngine(initial_capital=50000.0)
        assert engine.initial_capital == 50000.0
        assert len(engine.trades) == 0

    def test_add_single_trade(self):
        """Should add a single trade."""
        engine = BacktestEngine()
        now = datetime.utcnow()

        trade = Trade(
            entry_time=now,
            entry_price=100.0,
            exit_time=now + timedelta(days=1),
            exit_price=105.0,
            trade_type=TradeType.LONG,
        )
        engine.add_trade(trade)

        assert len(engine.trades) == 1
        assert engine.trades[0].pnl == 5.0

    def test_add_batch_trades(self):
        """Should add multiple trades."""
        engine = BacktestEngine()
        now = datetime.utcnow()

        trades = [
            Trade(
                entry_time=now + timedelta(days=i),
                entry_price=100.0,
                exit_time=now + timedelta(days=i+1),
                exit_price=105.0,
                trade_type=TradeType.LONG,
            )
            for i in range(5)
        ]
        engine.add_trades_batch(trades)

        assert len(engine.trades) == 5

    def test_compute_metrics_empty(self):
        """Empty backtest should return zeros."""
        engine = BacktestEngine()
        metrics = engine.compute_metrics()

        assert metrics.total_trades == 0
        assert metrics.win_rate == 0.0
        assert metrics.profit_factor == 0.0

    def test_compute_metrics_single_win(self):
        """Single winning trade metrics."""
        engine = BacktestEngine(initial_capital=100000.0)
        now = datetime.utcnow()

        trade = Trade(
            entry_time=now,
            entry_price=100.0,
            exit_time=now + timedelta(days=1),
            exit_price=110.0,
            trade_type=TradeType.LONG,
        )
        engine.add_trade(trade)

        metrics = engine.compute_metrics()

        assert metrics.total_trades == 1
        assert metrics.winning_trades == 1
        assert metrics.losing_trades == 0
        assert metrics.win_rate == 100.0

    def test_compute_metrics_mixed_trades(self):
        """Mixed winning/losing trades."""
        engine = BacktestEngine(initial_capital=100000.0)
        now = datetime.utcnow()

        # 3 winning trades, 2 losing
        trades = [
            Trade(now, 100.0, now + timedelta(days=1), 110.0, TradeType.LONG),
            Trade(now, 100.0, now + timedelta(days=1), 90.0, TradeType.LONG),
            Trade(now, 100.0, now + timedelta(days=1), 105.0, TradeType.LONG),
            Trade(now, 100.0, now + timedelta(days=1), 95.0, TradeType.LONG),
            Trade(now, 100.0, now + timedelta(days=1), 120.0, TradeType.LONG),
        ]
        engine.add_trades_batch(trades)

        metrics = engine.compute_metrics()

        assert metrics.total_trades == 5
        assert metrics.winning_trades == 3
        assert metrics.losing_trades == 2
        assert metrics.win_rate == 60.0

    def test_profit_factor_computation(self):
        """Profit factor should be gross_profit / gross_loss."""
        engine = BacktestEngine()
        now = datetime.utcnow()

        # Gross profit: 10 + 5 = 15
        # Gross loss: 5
        # PF: 15/5 = 3.0
        trades = [
            Trade(now, 100.0, now + timedelta(days=1), 110.0, TradeType.LONG),  # +10
            Trade(now, 100.0, now + timedelta(days=1), 105.0, TradeType.LONG),  # +5
            Trade(now, 100.0, now + timedelta(days=1), 95.0, TradeType.LONG),   # -5
        ]
        engine.add_trades_batch(trades)

        metrics = engine.compute_metrics()

        assert metrics.profit_factor == pytest.approx(3.0, abs=0.01)

    def test_max_drawdown_computation(self):
        """Max drawdown should track equity peak-to-trough."""
        engine = BacktestEngine(initial_capital=100000.0)
        now = datetime.utcnow()

        trades = [
            Trade(now, 100.0, now + timedelta(days=1), 110.0, TradeType.LONG),   # +10
            Trade(now, 100.0, now + timedelta(days=1), 90.0, TradeType.LONG),    # -10
            Trade(now, 100.0, now + timedelta(days=1), 70.0, TradeType.LONG),    # -30
        ]
        engine.add_trades_batch(trades)

        metrics = engine.compute_metrics()

        # Max drawdown from peak (110k) to trough (70k) = 40k / 110k ≈ 36.4%
        assert metrics.max_drawdown > 0


class TestWalkForwardValidator:
    """Tests for walk-forward validation."""

    def test_get_train_test_splits(self):
        """Should generate correct train/test splits."""
        validator = WalkForwardValidator(total_periods=5)

        splits = validator.get_train_test_splits(data_length=1000)

        assert len(splits) <= 5
        assert all(len(split) == 4 for split in splits)

        # Each split should have valid ranges
        for train_start, train_end, test_start, test_end in splits:
            assert train_start >= 0
            assert train_end > train_start
            assert test_start >= train_end
            assert test_end <= 1000

    def test_walk_forward_no_lookahead(self):
        """Walk-forward should never train on future data."""
        validator = WalkForwardValidator(total_periods=3)

        splits = validator.get_train_test_splits(data_length=300)

        for i, (train_start, train_end, test_start, test_end) in enumerate(splits):
            # Training data must end before test data starts
            assert train_end <= test_start, f"Split {i} has lookahead bias"

    def test_walk_forward_progressive(self):
        """Test windows should move forward in time."""
        validator = WalkForwardValidator(total_periods=5)

        splits = validator.get_train_test_splits(data_length=1000)

        test_starts = [s[2] for s in splits]

        # Test starts should be increasing
        for i in range(len(test_starts) - 1):
            assert test_starts[i] < test_starts[i + 1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
