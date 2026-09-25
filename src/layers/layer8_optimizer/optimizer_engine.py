"""RPM X20 Optimizer Engine (Layer 8) — Parameter tuning with constraint enforcement."""

import logging
from typing import List, Optional, Dict, Any, Tuple, Callable
from datetime import datetime
from dataclasses import dataclass, field

from src.core.models import OHLCV, BacktestResult
from src.core.backtest import BacktestEngine, TradeType, Trade, WalkForwardValidator
from src.core.config import Config

logger = logging.getLogger(__name__)


@dataclass
class OptimizerConstraints:
    """Optimization constraints (must all pass)."""

    min_trades: int = 200
    min_profit_factor: float = 1.3
    max_drawdown: float = 25.0  # %
    min_sharpe: float = 0.5
    max_drawdown_pct: float = 25.0


@dataclass
class OptimizerParameters:
    """Tunable strategy parameters."""

    ma_fast: int = 20  # Fast moving average period
    ma_slow: int = 50  # Slow moving average period
    rsi_period: int = 14  # RSI calculation period
    rsi_oversold: float = 30.0  # RSI entry threshold
    rsi_overbought: float = 70.0  # RSI exit threshold
    volatility_threshold: float = 2.0  # Min volatility for entry
    position_size: float = 1.0  # Fraction of capital per trade
    stop_loss_pct: float = 2.0  # Stop loss percentage
    take_profit_pct: float = 5.0  # Take profit percentage

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ma_fast": self.ma_fast,
            "ma_slow": self.ma_slow,
            "rsi_period": self.rsi_period,
            "rsi_oversold": self.rsi_oversold,
            "rsi_overbought": self.rsi_overbought,
            "volatility_threshold": self.volatility_threshold,
            "position_size": self.position_size,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
        }


@dataclass
class OptimizationResult:
    """Single optimization run result."""

    parameters: OptimizerParameters
    backtest_result: BacktestResult
    walk_forward_valid: bool
    passes_constraints: bool
    constraint_failures: List[str] = field(default_factory=list)
    score: float = 0.0  # Composite score for ranking

    def __post_init__(self):
        """Validate after initialization."""
        if not self.constraint_failures:
            self.constraint_failures = []


@dataclass
class OptimizationReport:
    """Complete optimization sweep report."""

    asset: str
    total_combinations: int
    results_passing: int
    results_failing: int
    best_result: Optional[OptimizationResult]
    top_results: List[OptimizationResult] = field(default_factory=list)
    optimization_time_seconds: float = 0.0
    reasoning: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate after initialization."""
        if not self.reasoning:
            self.reasoning = []


class OptimizerEngine:
    """
    Parameter optimization with constraint enforcement.

    Features:
    - Sweep parameter ranges
    - Enforce hard constraints (200+ trades, PF > 1.3, DD < 25%)
    - Walk-forward validation on each candidate
    - Rank results by composite score
    - Human-readable reports
    """

    def __init__(self):
        self.config = Config
        self.constraints = OptimizerConstraints()
        self.wf_validator = WalkForwardValidator(total_periods=5, training_ratio=0.7)

    def optimize(
        self,
        asset: str,
        ohlcv_data: List[OHLCV],
        strategy_func: Callable,
        param_ranges: Optional[Dict[str, Tuple[int, int, int]]] = None,
    ) -> OptimizationReport:
        """
        Run parameter optimization sweep.

        Args:
            asset: Asset identifier
            ohlcv_data: OHLCV data for backtesting
            strategy_func: Function(ohlcv, params) -> List[Trade]
            param_ranges: Dict of param_name -> (min, max, step)

        Returns:
            OptimizationReport with ranked candidates
        """

        if not ohlcv_data or len(ohlcv_data) < 100:
            return OptimizationReport(
                asset=asset,
                total_combinations=0,
                results_passing=0,
                results_failing=0,
                best_result=None,
                reasoning=["Insufficient OHLCV data for optimization"],
            )

        # Default parameter ranges
        if param_ranges is None:
            param_ranges = {
                "ma_fast": (10, 30, 5),
                "ma_slow": (40, 100, 20),
                "rsi_period": (10, 20, 2),
                "rsi_oversold": (20, 40, 5),
                "take_profit_pct": (3, 10, 1),
            }

        # Generate parameter combinations
        combinations = self._generate_combinations(param_ranges)
        total = len(combinations)

        logger.info(f"Optimizing {asset}: {total} parameter combinations")

        passing_results: List[OptimizationResult] = []
        failing_results: List[OptimizationResult] = []

        for i, params in enumerate(combinations):
            result = self._evaluate_parameters(
                asset, ohlcv_data, strategy_func, params
            )

            if result.passes_constraints:
                passing_results.append(result)
            else:
                failing_results.append(result)

            if (i + 1) % max(1, total // 10) == 0:
                logger.info(
                    f"  Progress: {i+1}/{total} "
                    f"(passing: {len(passing_results)}, failing: {len(failing_results)})"
                )

        # Rank passing results
        ranked = sorted(passing_results, key=lambda r: r.score, reverse=True)

        best_result = ranked[0] if ranked else None

        reasoning = []
        reasoning.append(f"Total combinations evaluated: {total}")
        reasoning.append(f"Passing constraints: {len(passing_results)}")
        reasoning.append(f"Failing constraints: {len(failing_results)}")

        if best_result:
            reasoning.append(f"✓ Best score: {best_result.score:.2f}")
            reasoning.append(f"  PF: {best_result.backtest_result.profit_factor:.2f}")
            reasoning.append(f"  DD: {best_result.backtest_result.max_drawdown:.2f}%")
            reasoning.append(f"  Trades: {best_result.backtest_result.total_trades}")
        else:
            reasoning.append("✗ No parameter combinations passed constraints")

        return OptimizationReport(
            asset=asset,
            total_combinations=total,
            results_passing=len(passing_results),
            results_failing=len(failing_results),
            best_result=best_result,
            top_results=ranked[:5],
            reasoning=reasoning,
        )

    def _generate_combinations(
        self, param_ranges: Dict[str, Tuple[int, int, int]]
    ) -> List[OptimizerParameters]:
        """Generate all parameter combinations from ranges."""

        combinations = []

        # Extract ranges
        ma_fast_range = param_ranges.get("ma_fast", (10, 30, 5))
        ma_slow_range = param_ranges.get("ma_slow", (40, 100, 20))
        rsi_period_range = param_ranges.get("rsi_period", (10, 20, 2))
        rsi_oversold_range = param_ranges.get("rsi_oversold", (20, 40, 5))
        tp_range = param_ranges.get("take_profit_pct", (3, 10, 1))

        # Generate all combinations
        for ma_fast in range(ma_fast_range[0], ma_fast_range[1], ma_fast_range[2]):
            for ma_slow in range(ma_slow_range[0], ma_slow_range[1], ma_slow_range[2]):
                for rsi_period in range(
                    rsi_period_range[0], rsi_period_range[1], rsi_period_range[2]
                ):
                    for rsi_oversold in range(
                        int(rsi_oversold_range[0]),
                        int(rsi_oversold_range[1]),
                        int(rsi_oversold_range[2]),
                    ):
                        for tp in range(tp_range[0], tp_range[1], tp_range[2]):
                            # Ensure ma_fast < ma_slow
                            if ma_fast < ma_slow:
                                combinations.append(
                                    OptimizerParameters(
                                        ma_fast=ma_fast,
                                        ma_slow=ma_slow,
                                        rsi_period=rsi_period,
                                        rsi_oversold=float(rsi_oversold),
                                        take_profit_pct=float(tp),
                                    )
                                )

        return combinations

    def _evaluate_parameters(
        self,
        asset: str,
        ohlcv_data: List[OHLCV],
        strategy_func: Callable,
        params: OptimizerParameters,
    ) -> OptimizationResult:
        """Evaluate a single parameter set."""

        constraint_failures = []

        try:
            # Run backtest
            trades = strategy_func(ohlcv_data, params)

            engine = BacktestEngine()
            engine.add_trades_batch(trades)
            backtest_result = engine.compute_metrics()

            # Check constraints
            if backtest_result.total_trades < self.constraints.min_trades:
                constraint_failures.append(
                    f"trades={backtest_result.total_trades} < {self.constraints.min_trades}"
                )

            if backtest_result.profit_factor < self.constraints.min_profit_factor:
                constraint_failures.append(
                    f"PF={backtest_result.profit_factor:.2f} < {self.constraints.min_profit_factor}"
                )

            if backtest_result.max_drawdown > self.constraints.max_drawdown:
                constraint_failures.append(
                    f"DD={backtest_result.max_drawdown:.2f}% > {self.constraints.max_drawdown}%"
                )

            # Walk-forward validation
            wf_valid = self._validate_walkforward(ohlcv_data, strategy_func, params)

            if not wf_valid:
                constraint_failures.append("Walk-forward validation failed")

            passes = len(constraint_failures) == 0

            # Composite score: PF * Sharpe * (1 - DD/100)
            sharpe = backtest_result.sharpe_ratio or 0
            score = 0.0
            if passes:
                score = (
                    backtest_result.profit_factor
                    * max(1.0, sharpe)
                    * (1.0 - backtest_result.max_drawdown / 100.0)
                )

            return OptimizationResult(
                parameters=params,
                backtest_result=backtest_result,
                walk_forward_valid=wf_valid,
                passes_constraints=passes,
                constraint_failures=constraint_failures,
                score=score,
            )

        except Exception as e:
            logger.error(f"Error evaluating parameters: {e}")
            return OptimizationResult(
                parameters=params,
                backtest_result=BacktestResult(
                    strategy_name="error",
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    win_rate=0.0,
                    profit_factor=0.0,
                    max_drawdown=100.0,
                    avg_trade_return=0.0,
                ),
                walk_forward_valid=False,
                passes_constraints=False,
                constraint_failures=[f"Evaluation error: {str(e)}"],
                score=0.0,
            )

    def _validate_walkforward(
        self,
        ohlcv_data: List[OHLCV],
        strategy_func: Callable,
        params: OptimizerParameters,
    ) -> bool:
        """Run walk-forward validation for parameters."""

        if len(ohlcv_data) < 100:
            return False

        splits = self.wf_validator.get_train_test_splits(len(ohlcv_data))
        passed = 0

        for train_start, train_end, test_start, test_end in splits:
            train_data = ohlcv_data[train_start:train_end]
            test_data = ohlcv_data[test_start:test_end]

            if not train_data or not test_data:
                continue

            try:
                trades = strategy_func(test_data, params)

                if len(trades) >= self.constraints.min_trades:
                    engine = BacktestEngine()
                    engine.add_trades_batch(trades)
                    metrics = engine.compute_metrics()

                    if (
                        metrics.profit_factor >= self.constraints.min_profit_factor
                        and metrics.max_drawdown <= self.constraints.max_drawdown
                    ):
                        passed += 1

            except Exception:
                continue

        # All walks must pass
        return passed == len(splits)

    def generate_report_text(self, report: OptimizationReport) -> str:
        """Generate human-readable optimization report."""

        lines = [
            f"\n{'='*70}",
            f"OPTIMIZATION REPORT — {report.asset.upper()}",
            f"{'='*70}",
            f"",
            f"Summary:",
            f"  Total combinations: {report.total_combinations}",
            f"  Passing constraints: {report.results_passing}/{report.total_combinations}",
            f"  Optimization time: {report.optimization_time_seconds:.1f}s",
            f"",
        ]

        if report.best_result:
            best = report.best_result
            lines.extend([
                f"Best Parameters:",
                f"  Score: {best.score:.4f}",
                f"  MA Fast: {best.parameters.ma_fast}",
                f"  MA Slow: {best.parameters.ma_slow}",
                f"  RSI Period: {best.parameters.rsi_period}",
                f"  RSI Oversold: {best.parameters.rsi_oversold:.1f}",
                f"  Take Profit %: {best.parameters.take_profit_pct:.1f}",
                f"",
                f"Performance:",
                f"  Total Trades: {best.backtest_result.total_trades}",
                f"  Win Rate: {best.backtest_result.win_rate:.2f}%",
                f"  Profit Factor: {best.backtest_result.profit_factor:.2f}",
                f"  Max Drawdown: {best.backtest_result.max_drawdown:.2f}%",
                f"  Sharpe Ratio: {best.backtest_result.sharpe_ratio or 'N/A'}",
                f"  Walk-Forward Valid: {'✓ Yes' if best.walk_forward_valid else '✗ No'}",
                f"",
            ])

            if len(report.top_results) > 1:
                lines.extend([
                    f"Top 5 Results:",
                ])
                for i, result in enumerate(report.top_results[:5], 1):
                    lines.append(
                        f"  {i}. Score: {result.score:.4f} | "
                        f"PF: {result.backtest_result.profit_factor:.2f} | "
                        f"DD: {result.backtest_result.max_drawdown:.2f}%"
                    )
                lines.append("")

        else:
            lines.extend([
                f"✗ No parameter combinations passed all constraints",
                f"",
            ])

        lines.extend([
            f"Analysis:",
        ])

        for reason in report.reasoning:
            lines.append(f"  • {reason}")

        lines.extend([
            f"",
            f"{'='*70}",
            f"",
        ])

        return "\n".join(lines)
