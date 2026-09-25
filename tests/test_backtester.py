"""Tests for Backtester."""

from datetime import UTC, datetime

import pandas as pd
import pytest

from src.backtester.base import BacktestSignal, PortfolioState
from src.backtester.mock import MockBacktester


class TestMockBacktester:
    """Tests for Mock Backtester."""

    def test_setup_initializes_config(self) -> None:
        """Test setup initializes configuration."""
        bt = MockBacktester()
        config = {
            "buy_threshold": 60000,
            "sell_threshold": 70000,
            "position_size": 0.5,
        }

        bt.setup(config)

        assert bt.config == config

    def test_setup_empty_config_raises(self) -> None:
        """Test setup raises on empty config."""
        bt = MockBacktester()

        with pytest.raises(ValueError):
            bt.setup({})

    def test_get_portfolio_state_returns_state(self) -> None:
        """Test get_portfolio_state returns PortfolioState."""
        bt = MockBacktester()
        state = bt.get_portfolio_state()

        assert isinstance(state, PortfolioState)
        assert state.cash == 10000.0
        assert state.equity == 10000.0

    def test_generate_signals_on_empty_features(self) -> None:
        """Test generate_signals handles empty features."""
        bt = MockBacktester()
        bt.setup({"buy_threshold": 60000, "sell_threshold": 70000})

        ts = datetime.now(UTC)
        signals = bt.generate_signals({}, ts)

        assert signals == []

    def test_generate_signals_buy_signal(self) -> None:
        """Test generate_signals produces LONG signal on buy threshold."""
        bt = MockBacktester()
        bt.setup(
            {
                "buy_threshold": 70000,
                "sell_threshold": 80000,
                "position_size": 0.5,
            }
        )

        ts = datetime.now(UTC)
        features = {
            "BTC": pd.DataFrame({
                "raw_price": [65000.0],
                "timestamp": [ts],
            })
        }

        signals = bt.generate_signals(features, ts)

        assert len(signals) == 1
        assert signals[0].action == "LONG"
        assert signals[0].asset == "BTC"
        assert signals[0].entry_price == 65000.0

    def test_generate_signals_sell_signal(self) -> None:
        """Test generate_signals produces EXIT signal on sell threshold."""
        bt = MockBacktester()
        bt.setup(
            {
                "buy_threshold": 60000,
                "sell_threshold": 70000,
                "position_size": 0.5,
            }
        )

        ts = datetime.now(UTC)

        # First, create an active trade
        bt.active_trades["BTC"] = {
            "entry_price": 65000.0,
            "quantity": 0.1,
            "entry_time": ts,
        }

        features = {
            "BTC": pd.DataFrame({
                "raw_price": [75000.0],
                "timestamp": [ts],
            })
        }

        signals = bt.generate_signals(features, ts)

        assert len(signals) == 1
        assert signals[0].action == "EXIT"
        assert signals[0].asset == "BTC"

    def test_on_signal_long_updates_portfolio(self) -> None:
        """Test on_signal LONG updates portfolio."""
        bt = MockBacktester()
        bt.setup(
            {
                "buy_threshold": 60000,
                "sell_threshold": 70000,
                "position_size": 0.5,
            }
        )

        ts = datetime.now(UTC)
        signal = BacktestSignal(
            timestamp=ts,
            asset="BTC",
            action="LONG",
            confidence=0.8,
            entry_price=65000.0,
        )

        bt.on_signal(signal)

        state = bt.get_portfolio_state()
        assert "BTC" in state.positions
        assert state.cash < 10000.0
        assert "BTC" in bt.active_trades

    def test_on_signal_exit_closes_trade(self) -> None:
        """Test on_signal EXIT closes open trade."""
        bt = MockBacktester()
        bt.setup({"position_size": 0.5})

        ts = datetime.now(UTC)

        # Open trade
        entry_signal = BacktestSignal(
            timestamp=ts,
            asset="BTC",
            action="LONG",
            confidence=0.8,
            entry_price=65000.0,
        )
        bt.on_signal(entry_signal)

        # Close trade
        exit_signal = BacktestSignal(
            timestamp=ts,
            asset="BTC",
            action="EXIT",
            confidence=0.8,
            exit_price=70000.0,
        )
        bt.on_signal(exit_signal)

        state = bt.get_portfolio_state()
        assert "BTC" not in state.positions
        assert "BTC" not in bt.active_trades
        assert len(bt.trade_log) == 1
        assert bt.trade_log[0]["pnl"] > 0

    def test_backtest_invalid_dates_raises(self) -> None:
        """Test backtest raises on invalid dates."""
        bt = MockBacktester()
        bt.setup({"position_size": 0.5})

        start = datetime.now(UTC)
        end = start

        with pytest.raises(ValueError):
            bt.backtest(start, end, 10000.0)

    def test_backtest_invalid_capital_raises(self) -> None:
        """Test backtest raises on invalid capital."""
        bt = MockBacktester()
        bt.setup({"position_size": 0.5})

        start = datetime.now(UTC)
        end = start

        with pytest.raises(ValueError):
            bt.backtest(start, end, -1000.0)

    def test_get_metrics_returns_backtest_metrics(self) -> None:
        """Test get_metrics returns BacktestMetrics."""
        bt = MockBacktester()
        bt.setup({"position_size": 0.5})

        ts = datetime.now(UTC)
        entry_signal = BacktestSignal(
            timestamp=ts,
            asset="BTC",
            action="LONG",
            confidence=0.8,
            entry_price=65000.0,
        )
        bt.on_signal(entry_signal)

        exit_signal = BacktestSignal(
            timestamp=ts,
            asset="BTC",
            action="EXIT",
            confidence=0.8,
            exit_price=70000.0,
        )
        bt.on_signal(exit_signal)

        metrics = bt.get_metrics()

        assert metrics.total_return > 0
        assert metrics.trade_count == 1
        assert metrics.win_rate == 1.0

    def test_close_does_not_raise(self) -> None:
        """Test close() completes without error."""
        bt = MockBacktester()
        bt.close()

    def test_portfolio_timestamp_updated_on_signal(self) -> None:
        """Test portfolio.timestamp updates to signal.timestamp."""
        bt = MockBacktester()
        bt.setup({"position_size": 0.5})

        ts1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        ts2 = datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC)

        signal1 = BacktestSignal(
            timestamp=ts1,
            asset="BTC",
            action="LONG",
            confidence=0.8,
            entry_price=65000.0,
        )
        bt.on_signal(signal1)
        assert bt.portfolio.timestamp == ts1

        signal2 = BacktestSignal(
            timestamp=ts2,
            asset="BTC",
            action="EXIT",
            confidence=0.8,
            exit_price=70000.0,
        )
        bt.on_signal(signal2)
        assert bt.portfolio.timestamp == ts2

    def test_equity_curve_updates_on_long(self) -> None:
        """Test equity_curve updates when LONG signal processed."""
        bt = MockBacktester()
        bt.setup({"position_size": 0.5})

        initial_length = len(bt.equity_curve)

        ts = datetime.now(UTC)
        signal = BacktestSignal(
            timestamp=ts,
            asset="BTC",
            action="LONG",
            confidence=0.8,
            entry_price=65000.0,
        )
        bt.on_signal(signal)

        assert len(bt.equity_curve) == initial_length + 1
        assert bt.equity_curve[-1] < 10000.0

    def test_equity_curve_updates_on_exit(self) -> None:
        """Test equity_curve updates when EXIT signal processed."""
        bt = MockBacktester()
        bt.setup({"position_size": 0.5})

        ts = datetime.now(UTC)

        entry_signal = BacktestSignal(
            timestamp=ts,
            asset="BTC",
            action="LONG",
            confidence=0.8,
            entry_price=65000.0,
        )
        bt.on_signal(entry_signal)
        length_after_entry = len(bt.equity_curve)

        exit_signal = BacktestSignal(
            timestamp=ts,
            asset="BTC",
            action="EXIT",
            confidence=0.8,
            exit_price=70000.0,
        )
        bt.on_signal(exit_signal)

        assert len(bt.equity_curve) == length_after_entry + 1
        assert bt.equity_curve[-1] > bt.equity_curve[-2]

    def test_trade_log_has_provenance(self) -> None:
        """Test trade_log entries include provenance."""
        bt = MockBacktester()
        bt.setup({"position_size": 0.5})

        ts = datetime.now(UTC)

        entry_signal = BacktestSignal(
            timestamp=ts,
            asset="BTC",
            action="LONG",
            confidence=0.8,
            entry_price=65000.0,
            metadata={"price_timestamp": ts.isoformat()},
        )
        bt.on_signal(entry_signal)

        exit_signal = BacktestSignal(
            timestamp=ts,
            asset="BTC",
            action="EXIT",
            confidence=0.8,
            exit_price=70000.0,
            metadata={"price_timestamp": ts.isoformat()},
        )
        bt.on_signal(exit_signal)

        assert len(bt.trade_log) == 1
        trade = bt.trade_log[0]
        assert "provenance" in trade
        assert "signal_timestamp" in trade["provenance"]
        assert "price_timestamp" in trade["provenance"]
        assert "confidence" in trade["provenance"]

    def test_metrics_not_hardcoded(self) -> None:
        """Test get_metrics returns real values, not hardcoded ones."""
        bt = MockBacktester()
        bt.setup({"position_size": 0.5})

        ts = datetime.now(UTC)

        entry_signal = BacktestSignal(
            timestamp=ts,
            asset="BTC",
            action="LONG",
            confidence=0.8,
            entry_price=65000.0,
        )
        bt.on_signal(entry_signal)

        exit_signal = BacktestSignal(
            timestamp=ts,
            asset="BTC",
            action="EXIT",
            confidence=0.8,
            exit_price=70000.0,
        )
        bt.on_signal(exit_signal)

        metrics = bt.get_metrics()

        assert metrics.sharpe_ratio != 1.5
        assert metrics.max_drawdown != -5.0
        assert metrics.total_return > 0

    def test_execution_convention_t_price_t(self) -> None:
        """Test execution convention: signal at T uses price at T (no T+1)."""
        bt = MockBacktester()
        bt.setup({"buy_threshold": 70000, "sell_threshold": 80000})

        ts = datetime.now(UTC)

        features = {
            "BTC": pd.DataFrame({
                "raw_price": [75000.0, 65000.0],
                "timestamp": [ts, ts],
            })
        }

        signals = bt.generate_signals(features, ts)

        assert len(signals) == 1
        assert signals[0].action == "LONG"
        assert signals[0].entry_price == 65000.0
        assert signals[0].metadata["price_timestamp"] == ts.isoformat()
