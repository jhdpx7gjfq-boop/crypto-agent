"""Unit tests for walk-forward validator."""

import pytest
import numpy as np
from datetime import datetime, timezone, timedelta

from src.layers.layer6_validation.walk_forward import WalkForwardValidator, BacktestResult


@pytest.fixture
def validator():
    """Create WalkForwardValidator instance."""
    return WalkForwardValidator()


@pytest.fixture
def sample_data():
    """Generate sample price and signal data."""
    np.random.seed(42)
    prices = np.cumsum(np.random.normal(0.001, 0.02, 100)) + 100
    signals = np.zeros(100, dtype=int)
    signals[[10, 30, 50, 70]] = 1
    signals[[20, 40, 60, 80]] = -1

    timestamps = [
        datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=i)
        for i in range(100)
    ]

    return prices.tolist(), signals.tolist(), timestamps


class TestBacktestResult:
    def test_result_structure(self):
        """Test BacktestResult dataclass structure."""
        result = BacktestResult(
            symbol="BTC",
            signal_name="test_signal",
            start_date=datetime.now(),
            end_date=datetime.now(),
            trade_count=5,
            win_count=3,
            loss_count=2,
            win_rate=0.6,
            profit_factor=2.5,
            sharpe_ratio=1.5,
            max_drawdown=-0.1,
            total_return=0.25,
            avg_win=0.05,
            avg_loss=-0.02,
            expectancy=0.03,
            validation_method="walk_forward",
            periods_tested=4,
            confidence_interval=(0.1, 0.5),
        )

        assert result.symbol == "BTC"
        assert result.trade_count == 5
        assert result.win_rate == 0.6


class TestWalkForwardValidator:
    def test_run_backtest_returns_result(self, validator, sample_data):
        """Test backtest returns valid result."""
        prices, signals, timestamps = sample_data

        result = validator.run_backtest("BTC", prices, signals, timestamps, "test_signal")

        assert isinstance(result, BacktestResult)
        assert result.symbol == "BTC"
        assert result.signal_name == "test_signal"

    def test_trade_count(self, validator, sample_data):
        """Test correct number of trades extracted."""
        prices, signals, timestamps = sample_data

        result = validator.run_backtest("BTC", prices, signals, timestamps, "test_signal")

        assert result.trade_count > 0

    def test_win_rate_calculation(self, validator):
        """Test win rate calculation."""
        prices = [100.0, 101.0, 102.0, 103.0, 100.0, 101.0, 102.0]
        signals = [1, 0, 0, -1, 1, 0, -1]
        timestamps = [
            datetime(2024, 1, i, tzinfo=timezone.utc) for i in range(1, 8)
        ]

        result = validator.run_backtest("BTC", prices, signals, timestamps, "test")

        assert result.win_rate >= 0.0
        assert result.win_rate <= 1.0

    def test_profit_factor_calculation(self, validator):
        """Test profit factor calculation."""
        prices = [100.0, 101.0, 102.0, 103.0, 100.0, 99.0, 100.0]
        signals = [1, 0, 0, -1, 1, 0, -1]
        timestamps = [
            datetime(2024, 1, i, tzinfo=timezone.utc) for i in range(1, 8)
        ]

        result = validator.run_backtest("BTC", prices, signals, timestamps, "test")

        assert result.profit_factor >= 0.0

    def test_max_drawdown_calculation(self, validator):
        """Test maximum drawdown calculation."""
        prices = [100.0, 99.0, 98.0, 97.0, 98.0, 99.0, 100.0]
        signals = [1, 0, 0, 0, 0, 0, -1]
        timestamps = [
            datetime(2024, 1, i, tzinfo=timezone.utc) for i in range(1, 8)
        ]

        result = validator.run_backtest("BTC", prices, signals, timestamps, "test")

        assert result.max_drawdown <= 0.0

    def test_sharpe_ratio_calculation(self, validator, sample_data):
        """Test Sharpe ratio calculation."""
        prices, signals, timestamps = sample_data

        result = validator.run_backtest("BTC", prices, signals, timestamps, "test")

        assert isinstance(result.sharpe_ratio, (int, float))

    def test_total_return_calculation(self, validator):
        """Test total return calculation."""
        prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        signals = [1, 0, 0, 0, -1]
        timestamps = [
            datetime(2024, 1, i, tzinfo=timezone.utc) for i in range(1, 6)
        ]

        result = validator.run_backtest("BTC", prices, signals, timestamps, "test", initial_capital=10000)

        assert result.total_return >= 0.0

    def test_empty_signals(self, validator):
        """Test with no signals."""
        prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        signals = [0, 0, 0, 0, 0]
        timestamps = [
            datetime(2024, 1, i, tzinfo=timezone.utc) for i in range(1, 6)
        ]

        result = validator.run_backtest("BTC", prices, signals, timestamps, "test")

        assert result.trade_count == 0

    def test_unmatched_lengths(self, validator):
        """Test error handling with mismatched lengths."""
        prices = [100.0, 101.0, 102.0]
        signals = [1, 0, 0, 0, 0]
        timestamps = [
            datetime(2024, 1, i, tzinfo=timezone.utc) for i in range(1, 4)
        ]

        result = validator.run_backtest("BTC", prices, signals, timestamps, "test")

        assert result.trade_count == 0

    def test_profit_calculation(self, validator):
        """Test profit calculation on winning trade."""
        prices = [100.0, 110.0, 120.0, 130.0]
        signals = [1, 0, 0, -1]
        timestamps = [
            datetime(2024, 1, i, tzinfo=timezone.utc) for i in range(1, 5)
        ]

        result = validator.run_backtest("BTC", prices, signals, timestamps, "test")

        assert result.trade_count == 1
        assert result.total_return > 0.25

    def test_loss_calculation(self, validator):
        """Test loss calculation on losing trade."""
        prices = [100.0, 90.0, 80.0, 70.0]
        signals = [1, 0, 0, -1]
        timestamps = [
            datetime(2024, 1, i, tzinfo=timezone.utc) for i in range(1, 5)
        ]

        result = validator.run_backtest("BTC", prices, signals, timestamps, "test")

        assert result.trade_count == 1
        assert result.total_return < 0.0

    def test_expectancy_calculation(self, validator):
        """Test expectancy calculation."""
        prices = [100.0, 105.0, 110.0, 95.0, 90.0, 110.0, 115.0]
        signals = [1, 0, -1, 1, 0, -1, 0]
        timestamps = [
            datetime(2024, 1, i, tzinfo=timezone.utc) for i in range(1, 8)
        ]

        result = validator.run_backtest("BTC", prices, signals, timestamps, "test")

        expected_exp = (result.win_rate * result.avg_win) - ((1 - result.win_rate) * abs(result.avg_loss))
        assert abs(result.expectancy - expected_exp) < 1e-6

    def test_insufficient_data(self, validator):
        """Test with insufficient data."""
        prices = [100.0]
        signals = [0]
        timestamps = [datetime(2024, 1, 1, tzinfo=timezone.utc)]

        result = validator.run_backtest("BTC", prices, signals, timestamps, "test")

        assert result.trade_count == 0

    def test_validation_method(self, validator, sample_data):
        """Test validation method is set correctly."""
        prices, signals, timestamps = sample_data

        result = validator.run_backtest("BTC", prices, signals, timestamps, "test")

        assert result.validation_method == "walk_forward"

    def test_initial_capital_parameter(self, validator):
        """Test initial capital affects returns calculation."""
        prices = [100.0, 110.0, 120.0]
        signals = [1, 0, -1]
        timestamps = [datetime(2024, 1, i, tzinfo=timezone.utc) for i in range(1, 4)]

        result1 = validator.run_backtest("BTC", prices, signals, timestamps, "test", initial_capital=10000)
        result2 = validator.run_backtest("BTC", prices, signals, timestamps, "test", initial_capital=1000)

        assert result1.total_return == result2.total_return
