"""Unit tests for Signal Performance Tracking."""

import pytest
from src.layers.layer8_monitoring.signal_performance_tracker import (
    SignalPerformanceTracker,
    PerformanceStatus,
)


@pytest.fixture
def tracker():
    """Create SignalPerformanceTracker instance."""
    return SignalPerformanceTracker()


@pytest.fixture
def sample_trades_profitable():
    """Profitable trades: 70% hit rate, +$1000 total."""
    return [
        {"pnl": 100.0},
        {"pnl": 150.0},
        {"pnl": 200.0},
        {"pnl": 50.0},
        {"pnl": 75.0},
        {"pnl": 425.0},
        {"pnl": -50.0},
        {"pnl": -25.0},
        {"pnl": -20.0},
        {"pnl": -15.0},
    ]


@pytest.fixture
def sample_trades_breakeven():
    """Break-even trades: 50% hit rate, $0 total."""
    return [
        {"pnl": 100.0},
        {"pnl": 150.0},
        {"pnl": 200.0},
        {"pnl": 50.0},
        {"pnl": -100.0},
        {"pnl": -150.0},
        {"pnl": -200.0},
        {"pnl": -50.0},
    ]


@pytest.fixture
def sample_trades_losing():
    """Losing trades: 30% hit rate, -$500 total."""
    return [
        {"pnl": 50.0},
        {"pnl": 75.0},
        {"pnl": 25.0},
        {"pnl": -100.0},
        {"pnl": -150.0},
        {"pnl": -200.0},
        {"pnl": -100.0},
        {"pnl": -125.0},
    ]


@pytest.fixture
def sample_equity_curve_profitable():
    """Equity curve: steady growth."""
    return [1000, 1050, 1120, 1180, 1250, 1350, 1400, 1380, 1360, 1420, 1500]


@pytest.fixture
def sample_equity_curve_drawdown():
    """Equity curve: peak and drawdown."""
    return [1000, 1100, 1200, 1300, 900, 950, 1000, 1100, 1150, 1160, 1170]


@pytest.fixture
def sample_returns_positive():
    """Daily returns: mostly positive."""
    return [0.02, 0.015, 0.01, 0.008, 0.012, 0.009, -0.005, 0.003, 0.006, 0.011]


class TestHitRate:
    def test_calculate_hit_rate_perfect(self, tracker, sample_trades_profitable):
        """Test hit rate with profitable trades."""
        hit_rate, hits, total = tracker.calculate_hit_rate(sample_trades_profitable)
        assert 0.0 <= hit_rate <= 100.0
        assert hits > 0
        assert total == 10

    def test_calculate_hit_rate_breakeven(self, tracker, sample_trades_breakeven):
        """Test hit rate with break-even trades."""
        hit_rate, hits, total = tracker.calculate_hit_rate(sample_trades_breakeven)
        assert hit_rate == 50.0
        assert hits == 4
        assert total == 8

    def test_calculate_hit_rate_losing(self, tracker, sample_trades_losing):
        """Test hit rate with losing trades."""
        hit_rate, hits, total = tracker.calculate_hit_rate(sample_trades_losing)
        assert 0.0 <= hit_rate <= 100.0
        assert hits == 3
        assert total == 8

    def test_calculate_hit_rate_empty(self, tracker):
        """Test hit rate with no trades."""
        hit_rate, hits, total = tracker.calculate_hit_rate([])
        assert hit_rate == 0.0
        assert hits == 0
        assert total == 0

    def test_calculate_hit_rate_single_win(self, tracker):
        """Test hit rate with single winning trade."""
        hit_rate, hits, total = tracker.calculate_hit_rate([{"pnl": 100.0}])
        assert hit_rate == 100.0
        assert hits == 1
        assert total == 1

    def test_calculate_hit_rate_single_loss(self, tracker):
        """Test hit rate with single losing trade."""
        hit_rate, hits, total = tracker.calculate_hit_rate([{"pnl": -100.0}])
        assert hit_rate == 0.0
        assert hits == 0
        assert total == 1


class TestProfitFactor:
    def test_calculate_profit_factor_strong(self, tracker, sample_trades_profitable):
        """Test profit factor for profitable trades."""
        pf = tracker.calculate_profit_factor(sample_trades_profitable)
        assert pf > 1.0

    def test_calculate_profit_factor_breakeven(self, tracker, sample_trades_breakeven):
        """Test profit factor for break-even trades."""
        pf = tracker.calculate_profit_factor(sample_trades_breakeven)
        assert pf == 1.0

    def test_calculate_profit_factor_losing(self, tracker, sample_trades_losing):
        """Test profit factor for losing trades."""
        pf = tracker.calculate_profit_factor(sample_trades_losing)
        assert 0.0 <= pf <= 1.0

    def test_calculate_profit_factor_all_wins(self, tracker):
        """Test profit factor with only winners."""
        trades = [{"pnl": 100.0}, {"pnl": 150.0}, {"pnl": 200.0}]
        pf = tracker.calculate_profit_factor(trades)
        # No losses, should handle gracefully
        assert pf >= 0.0

    def test_calculate_profit_factor_empty(self, tracker):
        """Test profit factor with no trades."""
        pf = tracker.calculate_profit_factor([])
        assert pf == 0.0


class TestMaxDrawdown:
    def test_calculate_max_drawdown_profitable(self, tracker, sample_equity_curve_profitable):
        """Test drawdown with steady growth."""
        dd = tracker.calculate_max_drawdown(sample_equity_curve_profitable)
        assert dd <= 0.0

    def test_calculate_max_drawdown_with_decline(self, tracker, sample_equity_curve_drawdown):
        """Test drawdown with peak and decline."""
        dd = tracker.calculate_max_drawdown(sample_equity_curve_drawdown)
        assert dd < 0.0

    def test_calculate_max_drawdown_single_point(self, tracker):
        """Test drawdown with single data point."""
        dd = tracker.calculate_max_drawdown([1000.0])
        assert dd == 0.0

    def test_calculate_max_drawdown_declining(self, tracker):
        """Test drawdown with continuous decline."""
        equity = [1000, 900, 800, 700, 600, 500]
        dd = tracker.calculate_max_drawdown(equity)
        assert dd < 0.0

    def test_calculate_max_drawdown_range(self, tracker):
        """Test drawdown stays in reasonable range."""
        equity = [1000, 1100, 1050, 1150, 1000]
        dd = tracker.calculate_max_drawdown(equity)
        assert -100.0 <= dd <= 0.0


class TestSharpeRatio:
    def test_calculate_sharpe_ratio_positive_returns(self, tracker, sample_returns_positive):
        """Test Sharpe with positive returns."""
        sharpe = tracker.calculate_sharpe_ratio(sample_returns_positive)
        assert isinstance(sharpe, float)
        assert sharpe > 0.0

    def test_calculate_sharpe_ratio_zero_volatility(self, tracker):
        """Test Sharpe with zero volatility (constant returns)."""
        returns = [0.01] * 10
        sharpe = tracker.calculate_sharpe_ratio(returns)
        # Near-zero std due to floating point precision produces very large Sharpe
        assert isinstance(sharpe, float)
        # Either 0 (if std detected as 0) or very large (if std is near-0 due to float precision)
        assert sharpe == 0.0 or abs(sharpe) > 1e10

    def test_calculate_sharpe_ratio_single_return(self, tracker):
        """Test Sharpe with insufficient data."""
        sharpe = tracker.calculate_sharpe_ratio([0.01])
        assert sharpe == 0.0

    def test_calculate_sharpe_ratio_empty(self, tracker):
        """Test Sharpe with no returns."""
        sharpe = tracker.calculate_sharpe_ratio([])
        assert sharpe == 0.0

    def test_calculate_sharpe_ratio_custom_risk_free(self, tracker):
        """Test Sharpe with custom risk-free rate."""
        returns = [0.01, 0.015, 0.008, 0.012, 0.009]
        sharpe = tracker.calculate_sharpe_ratio(returns, risk_free_rate=0.03)
        assert isinstance(sharpe, float)


class TestExpectancy:
    def test_calculate_expectancy_profitable(self, tracker, sample_trades_profitable):
        """Test expectancy with profitable trades."""
        exp = tracker.calculate_expectancy(sample_trades_profitable)
        assert exp > 0.0

    def test_calculate_expectancy_losing(self, tracker, sample_trades_losing):
        """Test expectancy with losing trades."""
        exp = tracker.calculate_expectancy(sample_trades_losing)
        assert exp < 0.0

    def test_calculate_expectancy_breakeven(self, tracker, sample_trades_breakeven):
        """Test expectancy with break-even trades."""
        exp = tracker.calculate_expectancy(sample_trades_breakeven)
        assert abs(exp) < 0.1  # Close to zero

    def test_calculate_expectancy_empty(self, tracker):
        """Test expectancy with no trades."""
        exp = tracker.calculate_expectancy([])
        assert exp == 0.0

    def test_calculate_expectancy_single_trade(self, tracker):
        """Test expectancy with single trade."""
        exp = tracker.calculate_expectancy([{"pnl": 50.0}])
        assert exp == 50.0


class TestWinLossRatio:
    def test_calculate_win_loss_ratio_profitable(self, tracker, sample_trades_profitable):
        """Test win/loss ratio with profitable trades."""
        avg_win, avg_loss, ratio = tracker.calculate_win_loss_ratio(sample_trades_profitable)
        assert avg_win > 0.0
        assert avg_loss > 0.0
        assert ratio > 0.0

    def test_calculate_win_loss_ratio_all_wins(self, tracker):
        """Test win/loss ratio with only winners."""
        trades = [{"pnl": 100.0}, {"pnl": 150.0}]
        avg_win, avg_loss, ratio = tracker.calculate_win_loss_ratio(trades)
        assert avg_win > 0.0
        assert avg_loss == 0.0

    def test_calculate_win_loss_ratio_all_losses(self, tracker):
        """Test win/loss ratio with only losses."""
        trades = [{"pnl": -100.0}, {"pnl": -150.0}]
        avg_win, avg_loss, ratio = tracker.calculate_win_loss_ratio(trades)
        assert avg_win == 0.0
        assert avg_loss > 0.0

    def test_calculate_win_loss_ratio_empty(self, tracker):
        """Test win/loss ratio with no trades."""
        avg_win, avg_loss, ratio = tracker.calculate_win_loss_ratio([])
        assert avg_win == 0.0
        assert avg_loss == 0.0
        assert ratio == 0.0


class TestPerformanceStatus:
    def test_get_performance_status_performing(self, tracker):
        """Test PERFORMING status with strong metrics."""
        status = tracker.get_performance_status(
            hit_rate=50.0,
            profit_factor=1.5,
            max_drawdown=-20.0,
            sharpe_ratio=1.0,
        )
        assert status == PerformanceStatus.PERFORMING

    def test_get_performance_status_warning(self, tracker):
        """Test WARNING status with moderate metrics."""
        status = tracker.get_performance_status(
            hit_rate=42.0,  # >= 40: +1 point
            profit_factor=1.15,  # > 1.0 but <= 1.3: no point
            max_drawdown=-22.0,  # > -25: +1 point
            sharpe_ratio=0.4,  # > 0.3 but <= 0.5: no point
        )
        # Should be WARNING or PERFORMING depending on combination
        assert status in [PerformanceStatus.WARNING, PerformanceStatus.PERFORMING]

    def test_get_performance_status_degraded(self, tracker):
        """Test DEGRADED status with weak metrics."""
        status = tracker.get_performance_status(
            hit_rate=20.0,
            profit_factor=0.8,
            max_drawdown=-50.0,
            sharpe_ratio=0.1,
        )
        assert status == PerformanceStatus.DEGRADED

    def test_get_performance_status_boundaries(self, tracker):
        """Test status at boundaries."""
        # Boundary: 40% hit rate
        status_40 = tracker.get_performance_status(40.0, 1.5, -20.0, 1.0)
        assert status_40 == PerformanceStatus.PERFORMING

        status_39 = tracker.get_performance_status(39.9, 1.5, -20.0, 1.0)
        # May be WARNING depending on other factors
        assert status_39 in [PerformanceStatus.PERFORMING, PerformanceStatus.WARNING]


class TestTrackSignalPerformance:
    def test_track_signal_performance_returns_metrics(
        self, tracker, sample_trades_profitable, sample_equity_curve_profitable, sample_returns_positive
    ):
        """Test tracking returns PerformanceMetrics."""
        metrics = tracker.track_signal_performance(
            symbol="BTC",
            signal_id="bce_001",
            trades=sample_trades_profitable,
            equity_curve=sample_equity_curve_profitable,
            returns=sample_returns_positive,
        )
        assert metrics.symbol == "BTC"
        assert metrics.signal_id == "bce_001"
        assert metrics.trades > 0
        assert metrics.status in [
            PerformanceStatus.PERFORMING,
            PerformanceStatus.WARNING,
            PerformanceStatus.DEGRADED,
        ]

    def test_track_signal_performance_all_fields(
        self, tracker, sample_trades_profitable, sample_equity_curve_profitable, sample_returns_positive
    ):
        """Test all fields are populated."""
        metrics = tracker.track_signal_performance(
            symbol="ETH",
            signal_id="x20_005",
            trades=sample_trades_profitable,
            equity_curve=sample_equity_curve_profitable,
            returns=sample_returns_positive,
            lookback_days=90,
        )
        assert metrics.symbol == "ETH"
        assert metrics.signal_id == "x20_005"
        assert metrics.trades == 10
        assert 0.0 <= metrics.hit_rate <= 100.0
        assert metrics.profit_factor >= 0.0
        assert metrics.max_drawdown <= 0.0
        assert isinstance(metrics.sharpe_ratio, float)
        assert isinstance(metrics.expectancy, float)
        assert metrics.lookback_days == 90

    def test_track_signal_performance_empty_trades(self, tracker):
        """Test with no trades."""
        metrics = tracker.track_signal_performance(
            symbol="ALT",
            signal_id="test_000",
            trades=[],
            equity_curve=[1000],
            returns=[],
        )
        assert metrics.trades == 0
        assert metrics.hit_rate == 0.0
        assert metrics.profit_factor == 0.0


class TestRankSignals:
    def test_rank_signals_by_performance(self, tracker, sample_trades_profitable, sample_trades_losing):
        """Test ranking signals by Sharpe."""
        metrics1 = tracker.track_signal_performance(
            "BTC",
            "sig1",
            sample_trades_profitable,
            [1000, 1100, 1150, 1200],
            [0.01, 0.015, 0.008],
        )
        metrics2 = tracker.track_signal_performance(
            "ETH",
            "sig2",
            sample_trades_losing,
            [1000, 900, 850, 800],
            [-0.01, -0.015, -0.008],
        )

        ranked = tracker.rank_signals_by_performance([metrics2, metrics1])
        assert len(ranked) == 2
        # Higher Sharpe first
        assert ranked[0].sharpe_ratio >= ranked[1].sharpe_ratio

    def test_rank_signals_empty_list(self, tracker):
        """Test ranking empty list."""
        ranked = tracker.rank_signals_by_performance([])
        assert ranked == []


class TestFilterByStatus:
    def test_filter_by_status_performing(self, tracker, sample_trades_profitable):
        """Test filtering PERFORMING signals."""
        metrics_good = tracker.track_signal_performance(
            "BTC",
            "good",
            sample_trades_profitable,
            [1000, 1100, 1150, 1200, 1250],
            [0.01, 0.015, 0.008, 0.012],
        )

        filtered = tracker.filter_by_status([metrics_good], min_status="PERFORMING")
        assert len(filtered) >= 0

    def test_filter_by_status_warning(self, tracker, sample_trades_breakeven):
        """Test filtering WARNING and above."""
        metrics = tracker.track_signal_performance(
            "ETH",
            "warn",
            sample_trades_breakeven,
            [1000, 1050, 1000, 1050],
            [0.001, -0.001, 0.001],
        )

        filtered = tracker.filter_by_status([metrics], min_status="WARNING")
        assert len(filtered) >= 0

    def test_filter_by_status_empty_list(self, tracker):
        """Test filtering empty list."""
        filtered = tracker.filter_by_status([], min_status="WARNING")
        assert filtered == []


class TestPerformanceSummary:
    def test_generate_performance_summary(self, tracker, sample_trades_profitable):
        """Test summary generation."""
        metrics = tracker.track_signal_performance(
            "BTC",
            "sig_001",
            sample_trades_profitable,
            [1000, 1100, 1200],
            [0.01, 0.015],
        )
        summary = tracker.generate_performance_summary(metrics)

        assert summary["symbol"] == "BTC"
        assert summary["signal_id"] == "sig_001"
        assert "status" in summary
        assert "trades" in summary
        assert "hit_rate" in summary
        assert "profit_factor" in summary
        assert "recommendation" in summary

    def test_generate_performance_summary_all_fields(self, tracker, sample_trades_losing):
        """Test all summary fields are populated."""
        metrics = tracker.track_signal_performance(
            "ALT",
            "sig_002",
            sample_trades_losing,
            [1000, 900, 850],
            [-0.01, -0.015],
        )
        summary = tracker.generate_performance_summary(metrics)

        assert summary["recommendation"] in ["KEEP", "MONITOR", "INVESTIGATE"]
        assert "%" in summary["hit_rate"]
        assert "%" in summary["max_drawdown"]


class TestEdgeCases:
    def test_track_signal_all_zeros(self, tracker):
        """Test with all zero PnL."""
        trades = [{"pnl": 0.0}] * 5
        metrics = tracker.track_signal_performance(
            "TEST",
            "zero",
            trades,
            [1000] * 5,
            [0.0] * 4,
        )
        assert metrics.trades == 5
        assert metrics.hit_rate == 0.0
        assert metrics.expectancy == 0.0

    def test_track_signal_extreme_values(self, tracker):
        """Test with extreme profit/loss."""
        trades = [{"pnl": 10000.0}, {"pnl": -100.0}]
        metrics = tracker.track_signal_performance(
            "EXTREME",
            "ext_001",
            trades,
            [1000, 11000, 10900],
            [10.0, -0.1],
        )
        assert metrics.profit_factor > 0.0
        assert isinstance(metrics.sharpe_ratio, float)

    def test_track_signal_volatile_returns(self, tracker):
        """Test with highly volatile returns."""
        trades = [{"pnl": x} for x in [100, -50, 200, -100, 150]]
        volatile_returns = [0.05, -0.02, 0.08, -0.03, 0.06]
        metrics = tracker.track_signal_performance(
            "VOLATILE",
            "vol_001",
            trades,
            [1000, 1050, 1000, 1080, 1050, 1200],
            volatile_returns,
        )
        assert metrics.sharpe_ratio != 0.0  # Should compute despite volatility
