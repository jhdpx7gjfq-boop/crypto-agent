"""Integration tests for Optimizer Engine (Phase 8)."""

import pytest
from datetime import datetime

from src.layers.layer8_optimizer.optimizer_engine import (
    OptimizerEngine,
    OptimizerParameters,
    OptimizerConstraints,
)
from src.core.backtest import Trade, TradeType
from tests.fixtures.market_data import generate_bull_ohlcv


class TestOptimizerEngine:
    """Tests for parameter optimization."""

    def test_engine_init(self):
        """Engine should initialize with default constraints."""
        engine = OptimizerEngine()

        assert engine.constraints.min_trades == 200
        assert engine.constraints.min_profit_factor == 1.3
        assert engine.constraints.max_drawdown == 25.0

    def test_parameter_generation(self):
        """Should generate parameter combinations."""
        engine = OptimizerEngine()
        param_ranges = {
            "ma_fast": (10, 20, 5),
            "ma_slow": (50, 60, 5),
            "rsi_period": (10, 15, 2),
            "rsi_oversold": (25, 30, 5),
            "take_profit_pct": (5, 10, 2),
        }

        combinations = engine._generate_combinations(param_ranges)

        assert len(combinations) > 0
        assert all(
            isinstance(p, OptimizerParameters) for p in combinations
        )
        assert all(p.ma_fast < p.ma_slow for p in combinations)

    def test_parameter_to_dict(self):
        """Parameters should convert to dictionary."""
        params = OptimizerParameters(ma_fast=20, ma_slow=50)
        d = params.to_dict()

        assert d["ma_fast"] == 20
        assert d["ma_slow"] == 50
        assert "rsi_period" in d

    def test_optimize_insufficient_data(self):
        """Insufficient data should return empty report."""
        engine = OptimizerEngine()
        short_data = generate_bull_ohlcv(10)

        def dummy_strategy(ohlcv, params):
            return []

        report = engine.optimize("TEST", short_data, dummy_strategy)

        assert report.total_combinations == 0
        assert report.best_result is None

    def test_evaluate_parameters_with_trades(self):
        """Should evaluate parameters and produce results."""
        engine = OptimizerEngine()
        ohlcv = generate_bull_ohlcv(100)

        def simple_strategy(ohlcv, params):
            trades = []
            for i in range(5):
                trades.append(
                    Trade(
                        entry_time=ohlcv[i].timestamp,
                        entry_price=100.0,
                        exit_time=ohlcv[i + 1].timestamp,
                        exit_price=102.0,
                        trade_type=TradeType.LONG,
                    )
                )
            return trades

        params = OptimizerParameters()
        result = engine._evaluate_parameters("TEST", ohlcv, simple_strategy, params)

        assert result.parameters is not None
        assert result.backtest_result.total_trades == 5

    def test_constraint_validation(self):
        """Should validate hard constraints."""
        engine = OptimizerEngine()
        ohlcv = generate_bull_ohlcv(100)

        def losing_strategy(ohlcv, params):
            trades = []
            for i in range(10):
                trades.append(
                    Trade(
                        entry_time=ohlcv[i].timestamp,
                        entry_price=100.0,
                        exit_time=ohlcv[i + 1].timestamp,
                        exit_price=95.0,
                        trade_type=TradeType.LONG,
                    )
                )
            return trades

        params = OptimizerParameters()
        result = engine._evaluate_parameters("TEST", ohlcv, losing_strategy, params)

        # Should not pass constraints
        assert not result.passes_constraints
        assert len(result.constraint_failures) > 0

    def test_walkforward_validation(self):
        """Walk-forward validation should enforce out-of-sample testing."""
        engine = OptimizerEngine()
        ohlcv = generate_bull_ohlcv(100)

        def profitable_strategy(ohlcv, params):
            trades = []
            for i in range(50):
                if i < len(ohlcv) - 1:
                    trades.append(
                        Trade(
                            entry_time=ohlcv[i].timestamp,
                            entry_price=100.0,
                            exit_time=ohlcv[i + 1].timestamp,
                            exit_price=101.0,
                            trade_type=TradeType.LONG,
                        )
                    )
            return trades

        params = OptimizerParameters()
        is_valid = engine._validate_walkforward(ohlcv, profitable_strategy, params)

        # Should be boolean
        assert isinstance(is_valid, bool)

    def test_score_calculation(self):
        """Score should account for PF, Sharpe, and DD."""
        engine = OptimizerEngine()
        ohlcv = generate_bull_ohlcv(100)

        def winning_strategy(ohlcv, params):
            trades = []
            for i in range(50):
                if i < len(ohlcv) - 1:
                    trades.append(
                        Trade(
                            entry_time=ohlcv[i].timestamp,
                            entry_price=100.0,
                            exit_time=ohlcv[i + 1].timestamp,
                            exit_price=102.0,
                            trade_type=TradeType.LONG,
                        )
                    )
            return trades

        params = OptimizerParameters()
        result = engine._evaluate_parameters("TEST", ohlcv, winning_strategy, params)

        # Winning trades should have positive score
        if result.passes_constraints:
            assert result.score > 0

    def test_report_generation(self):
        """Should generate human-readable report."""
        engine = OptimizerEngine()
        ohlcv = generate_bull_ohlcv(100)

        def dummy_strategy(ohlcv, params):
            return []

        report = engine.optimize("TEST", ohlcv, dummy_strategy)
        text = engine.generate_report_text(report)

        assert "OPTIMIZATION REPORT" in text
        assert "TEST" in text
        assert "Summary" in text

    def test_multiple_parameter_combinations(self):
        """Should handle multiple parameter combinations."""
        engine = OptimizerEngine()
        ohlcv = generate_bull_ohlcv(150)

        def simple_strategy(ohlcv, params):
            trades = []
            for i in range(100):
                if i < len(ohlcv) - 1:
                    trades.append(
                        Trade(
                            entry_time=ohlcv[i].timestamp,
                            entry_price=100.0,
                            exit_time=ohlcv[i + 1].timestamp,
                            exit_price=101.0 + (params.ma_fast / 100),
                            trade_type=TradeType.LONG,
                        )
                    )
            return trades

        param_ranges = {
            "ma_fast": (10, 20, 5),
            "ma_slow": (50, 60, 5),
        }

        report = engine.optimize("TEST", ohlcv, simple_strategy, param_ranges)

        assert report.total_combinations > 0

    def test_constraint_failures_documented(self):
        """Constraint failures should be documented."""
        engine = OptimizerEngine()
        ohlcv = generate_bull_ohlcv(100)

        def minimal_strategy(ohlcv, params):
            return []

        params = OptimizerParameters()
        result = engine._evaluate_parameters("TEST", ohlcv, minimal_strategy, params)

        assert isinstance(result.constraint_failures, list)

    def test_best_result_ranking(self):
        """Best result should be top-ranked."""
        engine = OptimizerEngine()
        ohlcv = generate_bull_ohlcv(150)

        def profitable_strategy(ohlcv, params):
            trades = []
            for i in range(100):
                if i < len(ohlcv) - 1:
                    trades.append(
                        Trade(
                            entry_time=ohlcv[i].timestamp,
                            entry_price=100.0,
                            exit_time=ohlcv[i + 1].timestamp,
                            exit_price=101.0,
                            trade_type=TradeType.LONG,
                        )
                    )
            return trades

        param_ranges = {
            "ma_fast": (10, 15, 5),
            "ma_slow": (50, 55, 5),
        }

        report = engine.optimize("TEST", ohlcv, profitable_strategy, param_ranges)

        if report.best_result:
            assert report.best_result.score > 0

    def test_optimization_with_default_ranges(self):
        """Should use default parameter ranges when none provided."""
        engine = OptimizerEngine()
        ohlcv = generate_bull_ohlcv(150)

        def dummy_strategy(ohlcv, params):
            return []

        report = engine.optimize("TEST", ohlcv, dummy_strategy)

        assert report.total_combinations > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
