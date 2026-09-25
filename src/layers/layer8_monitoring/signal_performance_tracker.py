"""Signal Performance Tracking. Measures hit rate, drawdown, Sharpe, expectancy."""

from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np


class PerformanceStatus(Enum):
    """Signal performance status."""
    PERFORMING = "performing"
    WARNING = "warning"
    DEGRADED = "degraded"


@dataclass
class PerformanceMetrics:
    """Signal performance metrics."""
    symbol: str
    signal_id: str
    trades: int
    hits: int
    hit_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    expectancy: float
    avg_win: float
    avg_loss: float
    win_loss_ratio: float
    total_pnl: float
    status: PerformanceStatus
    lookback_days: int


class SignalPerformanceTracker:
    """Tracks signal performance metrics over time."""

    def calculate_hit_rate(self, trades: List[Dict]) -> Tuple[float, int, int]:
        """
        Calculate hit rate from trades.

        Args:
            trades: List of trade dicts with 'pnl' key

        Returns:
            (hit_rate 0-100, hit_count, total_trades)
        """
        if not trades or len(trades) == 0:
            return 0.0, 0, 0

        hits = sum(1 for t in trades if t.get("pnl", 0) > 0)
        total = len(trades)
        hit_rate = (hits / total * 100) if total > 0 else 0.0

        return float(hit_rate), hits, total

    def calculate_profit_factor(self, trades: List[Dict]) -> float:
        """
        Calculate profit factor (gross profit / gross loss).

        Args:
            trades: List of trade dicts with 'pnl' key

        Returns:
            Profit factor (>=1.0 is profitable, >1.3 is strong)
        """
        if not trades or len(trades) == 0:
            return 0.0

        gross_profit = sum(max(0, t.get("pnl", 0)) for t in trades)
        gross_loss = abs(sum(min(0, t.get("pnl", 0)) for t in trades))

        if gross_loss == 0:
            return 0.0 if gross_profit == 0 else float("inf")

        factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        return min(float(factor), 100.0)  # Cap at 100 for numerical stability

    def calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """
        Calculate maximum drawdown from equity curve.

        Args:
            equity_curve: List of cumulative equity values

        Returns:
            Max drawdown as percentage (0-100, negative means loss)
        """
        if not equity_curve or len(equity_curve) < 2:
            return 0.0

        equity_arr = np.array(equity_curve)
        cumulative_max = np.maximum.accumulate(equity_arr)
        drawdown = (equity_arr - cumulative_max) / cumulative_max * 100
        max_dd = np.min(drawdown)

        return float(max_dd)

    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sharpe ratio from returns.

        Args:
            returns: List of period returns (decimal, e.g., 0.05 = 5%)
            risk_free_rate: Annual risk-free rate (default 2%)

        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0

        returns_arr = np.array(returns)
        mean_return = np.mean(returns_arr)
        std_return = np.std(returns_arr)

        if std_return == 0:
            return 0.0

        # Annualize: assuming returns are daily, multiply by sqrt(252)
        sharpe = (mean_return - (risk_free_rate / 252)) / std_return * np.sqrt(252)

        return float(sharpe)

    def calculate_expectancy(self, trades: List[Dict]) -> float:
        """
        Calculate expectancy (average PnL per trade).

        Args:
            trades: List of trade dicts with 'pnl' key

        Returns:
            Average expectancy per trade
        """
        if not trades or len(trades) == 0:
            return 0.0

        pnls = [t.get("pnl", 0) for t in trades]
        expectancy = np.mean(pnls)

        return float(expectancy)

    def calculate_win_loss_ratio(self, trades: List[Dict]) -> Tuple[float, float, float]:
        """
        Calculate average win, average loss, and win/loss ratio.

        Args:
            trades: List of trade dicts with 'pnl' key

        Returns:
            (avg_win, avg_loss, ratio)
        """
        if not trades or len(trades) == 0:
            return 0.0, 0.0, 0.0

        wins = [t.get("pnl", 0) for t in trades if t.get("pnl", 0) > 0]
        losses = [t.get("pnl", 0) for t in trades if t.get("pnl", 0) < 0]

        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = abs(np.mean(losses)) if losses else 0.0
        ratio = avg_win / avg_loss if avg_loss > 0 else 0.0

        return float(avg_win), float(avg_loss), float(ratio)

    def get_performance_status(
        self,
        hit_rate: float,
        profit_factor: float,
        max_drawdown: float,
        sharpe_ratio: float,
    ) -> PerformanceStatus:
        """
        Determine performance status from metrics.

        Args:
            hit_rate: Hit rate 0-100
            profit_factor: Profit factor >=0
            max_drawdown: Max drawdown (negative)
            sharpe_ratio: Sharpe ratio

        Returns:
            Status: PERFORMING (>40% hit, >1.3 PF, DD>-25%, Sharpe>0.5)
                   WARNING (30-40% hit, 1.0-1.3 PF, DD -25% to -40%, 0.3<Sharpe<0.5)
                   DEGRADED (<30% hit, <1.0 PF, DD<-40%, Sharpe<0.3)
        """
        score = 0

        # Hit rate: 40%+ = 1 point
        if hit_rate >= 40.0:
            score += 1
        elif hit_rate >= 30.0:
            score += 0  # Neutral

        # Profit factor: >1.3 = 1 point
        if profit_factor > 1.3:
            score += 1
        elif profit_factor > 1.0:
            score += 0

        # Drawdown: >-25% = 1 point
        if max_drawdown > -25.0:
            score += 1
        elif max_drawdown > -40.0:
            score += 0

        # Sharpe: >0.5 = 1 point
        if sharpe_ratio > 0.5:
            score += 1
        elif sharpe_ratio > 0.3:
            score += 0

        if score >= 3:
            return PerformanceStatus.PERFORMING
        elif score >= 1:
            return PerformanceStatus.WARNING
        else:
            return PerformanceStatus.DEGRADED

    def track_signal_performance(
        self,
        symbol: str,
        signal_id: str,
        trades: List[Dict],
        equity_curve: List[float],
        returns: List[float],
        lookback_days: int = 90,
    ) -> PerformanceMetrics:
        """
        Complete signal performance tracking pipeline.

        Args:
            symbol: Asset symbol
            signal_id: Signal identifier
            trades: List of trade dicts with 'pnl' key
            equity_curve: Cumulative equity over time
            returns: Period returns (decimal)
            lookback_days: Lookback window in days

        Returns:
            PerformanceMetrics with all calculations
        """
        hit_rate, hits, total_trades = self.calculate_hit_rate(trades)
        profit_factor = self.calculate_profit_factor(trades)
        max_drawdown = self.calculate_max_drawdown(equity_curve)
        sharpe_ratio = self.calculate_sharpe_ratio(returns)
        expectancy = self.calculate_expectancy(trades)
        avg_win, avg_loss, wl_ratio = self.calculate_win_loss_ratio(trades)

        total_pnl = sum(t.get("pnl", 0) for t in trades)
        status = self.get_performance_status(hit_rate, profit_factor, max_drawdown, sharpe_ratio)

        return PerformanceMetrics(
            symbol=symbol,
            signal_id=signal_id,
            trades=total_trades,
            hits=hits,
            hit_rate=hit_rate,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            expectancy=expectancy,
            avg_win=avg_win,
            avg_loss=avg_loss,
            win_loss_ratio=wl_ratio,
            total_pnl=total_pnl,
            status=status,
            lookback_days=lookback_days,
        )

    def rank_signals_by_performance(self, metrics: List[PerformanceMetrics]) -> List[PerformanceMetrics]:
        """
        Rank signals by composite performance score.

        Args:
            metrics: List of PerformanceMetrics

        Returns:
            Sorted list by Sharpe (descending)
        """
        return sorted(metrics, key=lambda m: m.sharpe_ratio, reverse=True)

    def filter_by_status(
        self, metrics: List[PerformanceMetrics], min_status: str = "WARNING"
    ) -> List[PerformanceMetrics]:
        """
        Filter signals by performance status.

        Args:
            metrics: List of PerformanceMetrics
            min_status: Minimum status ("PERFORMING", "WARNING", "DEGRADED")

        Returns:
            Filtered list meeting minimum status
        """
        status_order = {"PERFORMING": 2, "WARNING": 1, "DEGRADED": 0}
        min_level = status_order.get(min_status, 0)

        return [m for m in metrics if status_order.get(m.status.value, -1) >= min_level]

    def generate_performance_summary(self, metrics: PerformanceMetrics) -> Dict[str, str]:
        """
        Generate human-readable performance summary.

        Args:
            metrics: PerformanceMetrics

        Returns:
            Summary dict with text descriptions
        """
        return {
            "symbol": metrics.symbol,
            "signal_id": metrics.signal_id,
            "status": metrics.status.value.upper(),
            "trades": str(metrics.trades),
            "hit_rate": f"{metrics.hit_rate:.1f}%",
            "profit_factor": f"{metrics.profit_factor:.2f}",
            "max_drawdown": f"{metrics.max_drawdown:.1f}%",
            "sharpe_ratio": f"{metrics.sharpe_ratio:.2f}",
            "expectancy": f"{metrics.expectancy:.2f}",
            "total_pnl": f"{metrics.total_pnl:.2f}",
            "recommendation": "KEEP" if metrics.status == PerformanceStatus.PERFORMING else "MONITOR" if metrics.status == PerformanceStatus.WARNING else "INVESTIGATE",
        }
