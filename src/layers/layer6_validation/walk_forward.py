"""Walk-forward validator with metrics calculation for strategy backtesting."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import numpy as np


@dataclass
class BacktestResult:
    """Results from walk-forward backtest."""

    symbol: str
    signal_name: str
    start_date: datetime
    end_date: datetime
    trade_count: int
    win_count: int
    loss_count: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    total_return: float
    avg_win: float
    avg_loss: float
    expectancy: float
    validation_method: str
    periods_tested: int
    confidence_interval: Tuple[float, float]
    notes: Optional[str] = None


class WalkForwardValidator:
    """Execute walk-forward validation with robust metrics calculation."""

    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate

    def run_backtest(
        self,
        symbol: str,
        prices: List[float],
        signals: List[int],
        timestamps: List[datetime],
        signal_name: str,
        initial_capital: float = 10000,
    ) -> BacktestResult:
        """
        Execute single walk-forward test.

        Args:
            symbol: Crypto symbol
            prices: Price series
            signals: Buy signals (1=buy, 0=no signal, -1=sell)
            timestamps: Timestamps for each candle
            signal_name: Name of signal being tested
            initial_capital: Starting capital for position sizing

        Returns:
            BacktestResult with metrics
        """
        if len(prices) < 2 or len(signals) != len(prices):
            return self._empty_result(symbol, signal_name, start_date=timestamps[0] if timestamps else datetime.now())

        trades = self._extract_trades(prices, signals, timestamps)
        if not trades:
            return self._empty_result(symbol, signal_name, start_date=timestamps[0] if timestamps else datetime.now())

        returns = self._calculate_returns(trades)
        if not returns:
            return self._empty_result(symbol, signal_name, start_date=timestamps[0] if timestamps else datetime.now())

        equity_curve = self._calculate_equity_curve(returns, initial_capital)

        metrics = {
            "trade_count": len(trades),
            "win_count": len([r for r in returns if r > 0]),
            "loss_count": len([r for r in returns if r < 0]),
            "win_rate": len([r for r in returns if r > 0]) / len(returns) if returns else 0,
            "profit_factor": self._calculate_profit_factor(returns),
            "sharpe_ratio": self._calculate_sharpe_ratio(returns),
            "max_drawdown": self._calculate_max_drawdown(equity_curve),
            "total_return": (equity_curve[-1] - initial_capital) / initial_capital if equity_curve else 0,
            "avg_win": np.mean([r for r in returns if r > 0]) if any(r > 0 for r in returns) else 0,
            "avg_loss": np.mean([r for r in returns if r < 0]) if any(r < 0 for r in returns) else 0,
        }

        metrics["expectancy"] = (
            (metrics["win_rate"] * metrics["avg_win"]) -
            ((1 - metrics["win_rate"]) * abs(metrics["avg_loss"]))
        )

        return BacktestResult(
            symbol=symbol,
            signal_name=signal_name,
            start_date=timestamps[0] if timestamps else datetime.now(),
            end_date=timestamps[-1] if timestamps else datetime.now(),
            trade_count=metrics["trade_count"],
            win_count=metrics["win_count"],
            loss_count=metrics["loss_count"],
            win_rate=metrics["win_rate"],
            profit_factor=metrics["profit_factor"],
            sharpe_ratio=metrics["sharpe_ratio"],
            max_drawdown=metrics["max_drawdown"],
            total_return=metrics["total_return"],
            avg_win=metrics["avg_win"],
            avg_loss=metrics["avg_loss"],
            expectancy=metrics["expectancy"],
            validation_method="walk_forward",
            periods_tested=1,
            confidence_interval=(0.0, 0.0),
        )

    def _extract_trades(
        self, prices: List[float], signals: List[int], timestamps: List[datetime]
    ) -> List[dict]:
        """Extract buy/sell trades from signals."""
        trades = []
        position = None

        for i, signal in enumerate(signals):
            if signal == 1 and position is None:
                position = {"entry_price": prices[i], "entry_idx": i, "entry_time": timestamps[i]}
            elif signal == -1 and position is not None:
                position["exit_price"] = prices[i]
                position["exit_idx"] = i
                position["exit_time"] = timestamps[i]
                trades.append(position)
                position = None

        if position and len(prices) > position["entry_idx"]:
            position["exit_price"] = prices[-1]
            position["exit_idx"] = len(prices) - 1
            position["exit_time"] = timestamps[-1]
            trades.append(position)

        return trades

    def _calculate_returns(self, trades: List[dict]) -> List[float]:
        """Calculate trade returns as percentage."""
        returns = []
        for trade in trades:
            if "exit_price" in trade and "entry_price" in trade:
                ret = (trade["exit_price"] - trade["entry_price"]) / trade["entry_price"]
                returns.append(ret)
        return returns

    def _calculate_equity_curve(self, returns: List[float], initial_capital: float) -> List[float]:
        """Calculate cumulative equity curve."""
        equity = [initial_capital]
        for ret in returns:
            equity.append(equity[-1] * (1 + ret))
        return equity

    def _calculate_profit_factor(self, returns: List[float]) -> float:
        """Calculate profit factor: sum(wins) / abs(sum(losses))."""
        wins = sum([r for r in returns if r > 0])
        losses = abs(sum([r for r in returns if r < 0]))

        if losses == 0:
            return 0.0 if wins == 0 else float('inf')

        return wins / losses

    def _calculate_sharpe_ratio(self, returns: List[float], periods_per_year: int = 365) -> float:
        """Calculate annualized Sharpe ratio."""
        if not returns or len(returns) < 2:
            return 0.0

        returns_arr = np.array(returns)
        excess_returns = returns_arr - (self.risk_free_rate / periods_per_year)

        if np.std(excess_returns) == 0:
            return 0.0

        return float(np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(periods_per_year))

    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """Calculate maximum drawdown from peak."""
        if not equity_curve or len(equity_curve) < 2:
            return 0.0

        equity_arr = np.array(equity_curve)
        peak = np.maximum.accumulate(equity_arr)
        drawdown = (equity_arr - peak) / peak
        return float(np.min(drawdown))

    def _empty_result(self, symbol: str, signal_name: str, start_date: datetime) -> BacktestResult:
        """Return empty backtest result."""
        return BacktestResult(
            symbol=symbol,
            signal_name=signal_name,
            start_date=start_date,
            end_date=start_date,
            trade_count=0,
            win_count=0,
            loss_count=0,
            win_rate=0.0,
            profit_factor=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            total_return=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            expectancy=0.0,
            validation_method="walk_forward",
            periods_tested=1,
            confidence_interval=(0.0, 0.0),
            notes="No trades or insufficient data",
        )
