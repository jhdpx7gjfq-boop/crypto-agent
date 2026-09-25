"""Backtesting framework with walk-forward validation."""

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Callable, Dict, Any
from enum import Enum

from src.core.models import OHLCV, BacktestResult


logger = logging.getLogger(__name__)


class TradeType(str, Enum):
    """Trade direction."""
    LONG = "long"
    SHORT = "short"


@dataclass
class Trade:
    """Single trade record."""

    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    trade_type: TradeType
    quantity: float = 1.0
    commission: float = 0.0  # % of trade value
    tags: Dict[str, Any] = field(default_factory=dict)

    @property
    def pnl(self) -> float:
        """P&L in absolute terms."""
        if self.trade_type == TradeType.LONG:
            return (self.exit_price - self.entry_price) * self.quantity
        else:  # SHORT
            return (self.entry_price - self.exit_price) * self.quantity

    @property
    def pnl_pct(self) -> float:
        """P&L as percentage."""
        if self.entry_price == 0:
            return 0.0

        if self.trade_type == TradeType.LONG:
            return ((self.exit_price - self.entry_price) / self.entry_price) * 100
        else:
            return ((self.entry_price - self.exit_price) / self.entry_price) * 100

    @property
    def is_winning(self) -> bool:
        """Trade is profitable."""
        return self.pnl > 0


class BacktestEngine:
    """
    Backtesting framework.

    Features:
    - Trade tracking
    - Performance metrics
    - Drawdown analysis
    - Walk-forward support
    """

    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.config = None

    def add_trade(self, trade: Trade) -> None:
        """Record a trade."""
        self.trades.append(trade)

    def add_trades_batch(self, trades: List[Trade]) -> None:
        """Record multiple trades."""
        self.trades.extend(trades)

    def compute_metrics(self) -> BacktestResult:
        """Compute backtest metrics."""

        if not self.trades:
            logger.warning("No trades to analyze")
            return BacktestResult(
                strategy_name="empty",
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                profit_factor=0.0,
                max_drawdown=0.0,
                avg_trade_return=0.0,
                notes="No trades executed",
            )

        # Basic counts
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.is_winning)
        losing_trades = total_trades - winning_trades

        # Win rate
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        # P&L
        total_pnl = sum(t.pnl for t in self.trades)
        gross_profit = sum(t.pnl for t in self.trades if t.is_winning)
        gross_loss = abs(sum(t.pnl for t in self.trades if not t.is_winning))

        # Profit factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0 if gross_profit == 0 else float("inf")

        # Average return
        avg_trade_return = (total_pnl / self.initial_capital) * 100 if self.initial_capital > 0 else 0.0

        # Drawdown (simple calculation)
        max_drawdown = self._compute_max_drawdown()

        # Sharpe ratio (simple approximation)
        sharpe = self._compute_sharpe_ratio()
        sortino = self._compute_sortino_ratio()

        return BacktestResult(
            strategy_name="backtest",
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate * 100,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            avg_trade_return=avg_trade_return,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            walk_forward_passed=False,  # Must be set by validator
            lookahead_bias_detected=False,
        )

    def _compute_max_drawdown(self) -> float:
        """Compute maximum drawdown %."""

        if not self.trades:
            return 0.0

        cumulative_pnl = 0.0
        peak = self.initial_capital
        max_dd = 0.0

        for trade in self.trades:
            cumulative_pnl += trade.pnl
            current_equity = self.initial_capital + cumulative_pnl

            if current_equity > peak:
                peak = current_equity

            drawdown_pct = ((peak - current_equity) / peak) * 100 if peak > 0 else 0

            if drawdown_pct > max_dd:
                max_dd = drawdown_pct

        return max_dd

    def _compute_sharpe_ratio(self) -> Optional[float]:
        """Sharpe ratio (approximate)."""

        if len(self.trades) < 2:
            return None

        returns_pct = [t.pnl_pct for t in self.trades]

        mean_return = sum(returns_pct) / len(returns_pct)

        if len(returns_pct) < 2:
            return None

        variance = sum((r - mean_return) ** 2 for r in returns_pct) / len(returns_pct)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return 0.0

        # Simple Sharpe (annualized assuming ~250 trading days)
        rf_rate = 0.02  # Risk-free rate 2%
        sharpe = ((mean_return - rf_rate) / std_dev) * (250 ** 0.5)

        return sharpe

    def _compute_sortino_ratio(self) -> Optional[float]:
        """Sortino ratio (downside deviation)."""

        if len(self.trades) < 2:
            return None

        returns_pct = [t.pnl_pct for t in self.trades]
        mean_return = sum(returns_pct) / len(returns_pct)

        # Downside deviation (only negative returns)
        downside_returns = [r - mean_return for r in returns_pct if r < mean_return]

        if not downside_returns:
            return None

        downside_variance = sum(r ** 2 for r in downside_returns) / len(returns_pct)
        downside_std = downside_variance ** 0.5

        if downside_std == 0:
            return 0.0

        rf_rate = 0.02
        sortino = ((mean_return - rf_rate) / downside_std) * (250 ** 0.5)

        return sortino


class WalkForwardValidator:
    """
    Walk-forward validation for strategies.

    Prevents lookahead bias by:
    1. Splitting data into train/test windows
    2. Training on past data only
    3. Testing on future data
    4. Rolling forward
    """

    def __init__(
        self,
        total_periods: int = 5,
        training_ratio: float = 0.7,
    ):
        self.total_periods = total_periods
        self.training_ratio = training_ratio
        self.results: List[BacktestResult] = []

    def get_train_test_splits(self, data_length: int) -> List[tuple]:
        """
        Generate train/test index ranges.

        Returns: List of (train_start, train_end, test_start, test_end) tuples
        """

        step_size = int(data_length / self.total_periods)
        splits = []

        for i in range(self.total_periods):
            test_start = i * step_size
            test_end = (i + 1) * step_size if i < self.total_periods - 1 else data_length

            # Training data: everything before test
            train_end = test_start
            train_start = max(0, int(train_end * (1 - self.training_ratio)))

            if train_end > train_start:  # Only if valid training window
                splits.append((train_start, train_end, test_start, test_end))

        logger.info(f"Generated {len(splits)} walk-forward splits")
        return splits

    def validate(
        self,
        strategy_func: Callable,
        ohlcv_data: List[OHLCV],
        min_profit_factor: float = 1.3,
        min_trades: int = 200,
    ) -> bool:
        """
        Run walk-forward validation.

        Args:
            strategy_func: Function that takes (train_ohlcv, test_ohlcv) → trades
            ohlcv_data: All OHLCV data
            min_profit_factor: Minimum profit factor threshold
            min_trades: Minimum trades required

        Returns:
            True if strategy passes all walks
        """

        splits = self.get_train_test_splits(len(ohlcv_data))
        passed = 0
        failed = 0

        for train_start, train_end, test_start, test_end in splits:
            train_data = ohlcv_data[train_start:train_end]
            test_data = ohlcv_data[test_start:test_end]

            if not train_data or not test_data:
                continue

            # Run strategy
            try:
                trades = strategy_func(train_data, test_data)

                if not trades or len(trades) < min_trades:
                    logger.warning(f"Walk {passed + failed}: Only {len(trades)} trades (need {min_trades})")
                    failed += 1
                    continue

                # Evaluate
                engine = BacktestEngine()
                engine.add_trades_batch(trades)
                metrics = engine.compute_metrics()

                if metrics.profit_factor >= min_profit_factor:
                    logger.info(f"Walk {passed + failed}: PF={metrics.profit_factor:.2f} ✓")
                    passed += 1
                else:
                    logger.warning(f"Walk {passed + failed}: PF={metrics.profit_factor:.2f} (need {min_profit_factor})")
                    failed += 1

                self.results.append(metrics)

            except Exception as e:
                logger.error(f"Walk {passed + failed} failed: {e}")
                failed += 1

        # All walks must pass
        all_passed = failed == 0 and passed == len(splits)

        logger.info(f"Walk-forward validation: {passed}/{len(splits)} passed")

        return all_passed
