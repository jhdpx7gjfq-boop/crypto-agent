"""Mock Backtester implementation for testing."""

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from src.utils.logging import get_logger

from .base import Backtester, BacktestMetrics, BacktestSignal, PortfolioState

logger = get_logger(__name__)


class MockBacktester(Backtester):
    """Simple mock backtester: BUY-HOLD-SELL on threshold."""

    def __init__(self) -> None:
        """Initialize mock backtester."""
        self.config: dict[str, Any] = {}
        self.initial_cash = 10000.0
        self.portfolio = PortfolioState(
            timestamp=datetime.now(),
            positions={},
            cash=self.initial_cash,
            equity=self.initial_cash,
        )
        self.equity_curve: list[float] = [self.initial_cash]
        self.trade_log: list[dict[str, Any]] = []
        self.active_trades: dict[str, dict[str, Any]] = {}
        self.last_price: dict[str, float] = {}

    def _update_equity_curve_event(self) -> None:
        """Update equity curve at trade event.

        LIMITATION (Documented):
        Equity = cash + mark-to-market value of positions (at last observed price).
        This is EVENT-DRIVEN (updates only on LONG/EXIT), NOT observation-driven.

        This is NOT a complete daily/continuous mark-to-market equity curve.
        It only reflects portfolio state after trade execution events.
        Gaps between events mean equity is stale (positions priced at last trade price).

        Acceptable for mock/backtester foundation. Phase 3+ will require
        observation-based equity recalculation (full mark-to-market at each price update).
        """
        marked_value = sum(
            qty * self.last_price.get(asset, 0.0)
            for asset, qty in self.portfolio.positions.items()
        )
        total_equity = self.portfolio.cash + marked_value
        self.equity_curve.append(total_equity)

    def setup(self, config: dict[str, Any]) -> None:
        """Setup with config.

        Args:
            config: Config dict. Expected keys:
                - buy_threshold: price level to buy
                - sell_threshold: price level to sell
                - position_size: % of capital per trade
        """
        if not config:
            raise ValueError("Config cannot be empty")

        self.config = config
        logger.info("Mock backtester configured", extra={"extra_fields": config})

    def generate_signals(
        self,
        features: dict[str, pd.DataFrame],
        timestamp: datetime,
    ) -> list[BacktestSignal]:
        """Generate simple buy/sell signals on raw_price feature.

        Execution convention: Signal at timestamp T uses price at T (not T+1).
        - current_price = df["raw_price"].iloc[-1] is the last available price ≤ timestamp T
        - This ensures point-in-time safety — no forward-looking data access
        - Signals generated at T can use only data up to and including T

        Args:
            features: Dict mapping asset -> DataFrame.
            timestamp: Current timestamp (point-in-time).

        Returns:
            List of signals.
        """
        signals = []

        for asset, df in features.items():
            if df.empty or "raw_price" not in df.columns:
                continue

            current_price = df["raw_price"].iloc[-1]
            self.last_price[asset] = current_price

            buy_threshold = self.config.get("buy_threshold", 60000)
            sell_threshold = self.config.get("sell_threshold", 70000)

            if asset in self.active_trades:
                if current_price >= sell_threshold:
                    signals.append(
                        BacktestSignal(
                            timestamp=timestamp,
                            asset=asset,
                            action="EXIT",
                            confidence=0.8,
                            exit_price=current_price,
                            metadata={"price_timestamp": timestamp.isoformat()},
                        )
                    )
            elif current_price <= buy_threshold:
                signals.append(
                    BacktestSignal(
                        timestamp=timestamp,
                        asset=asset,
                        action="LONG",
                        confidence=0.7,
                        entry_price=current_price,
                        metadata={"price_timestamp": timestamp.isoformat()},
                    )
                )

        return signals

    def on_signal(self, signal: BacktestSignal) -> None:
        """Process signal and update portfolio.

        Args:
            signal: BacktestSignal.
        """
        position_size = self.config.get("position_size", 0.5)

        if signal.action == "LONG":
            if signal.entry_price is None:
                logger.warning("LONG signal missing entry_price")
                return

            allocation = self.portfolio.cash * position_size
            quantity = allocation / signal.entry_price

            self.active_trades[signal.asset] = {
                "entry_price": signal.entry_price,
                "quantity": quantity,
                "entry_time": signal.timestamp,
            }

            self.portfolio.positions[signal.asset] = quantity
            self.portfolio.cash -= allocation
            self.portfolio.timestamp = signal.timestamp

            self._update_equity_curve_event()

            logger.info(
                "LONG signal processed",
                extra={
                    "extra_fields": {
                        "asset": signal.asset,
                        "price": signal.entry_price,
                        "quantity": quantity,
                    }
                },
            )

        elif signal.action == "EXIT":
            if signal.asset not in self.active_trades:
                logger.warning("EXIT signal for non-existent position")
                return

            if signal.exit_price is None:
                logger.warning("EXIT signal missing exit_price")
                return

            trade = self.active_trades.pop(signal.asset)
            proceeds = trade["quantity"] * signal.exit_price
            pnl = proceeds - (trade["quantity"] * trade["entry_price"])

            self.portfolio.cash += proceeds
            self.portfolio.positions.pop(signal.asset, None)
            self.portfolio.timestamp = signal.timestamp

            self.trade_log.append(
                {
                    "asset": signal.asset,
                    "entry_price": trade["entry_price"],
                    "exit_price": signal.exit_price,
                    "quantity": trade["quantity"],
                    "pnl": pnl,
                    "entry_time": trade["entry_time"],
                    "exit_time": signal.timestamp,
                    "provenance": {
                        "signal_timestamp": signal.timestamp.isoformat(),
                        "price_timestamp": signal.metadata.get("price_timestamp"),
                        "confidence": signal.confidence,
                        "feature_source": signal.metadata.get("feature_source", "unknown"),
                        "feature_name": signal.metadata.get("feature_name", "raw_price"),
                        "snapshot_ref": {
                            "asset": signal.asset,
                            "timestamp": signal.metadata.get("price_timestamp"),
                            "feature": signal.metadata.get("feature_name", "raw_price"),
                        },
                    },
                }
            )

            self._update_equity_curve_event()

            logger.info(
                "EXIT signal processed",
                extra={
                    "extra_fields": {
                        "asset": signal.asset,
                        "pnl": pnl,
                        "return": pnl / (trade["quantity"] * trade["entry_price"]),
                    }
                },
            )

    def _calculate_metrics(self) -> BacktestMetrics:
        """Calculate real metrics from equity_curve and trade_log."""
        if not self.equity_curve or len(self.equity_curve) < 1:
            raise ValueError("No equity curve data")

        equity = np.array(self.equity_curve)

        total_return_pct = ((equity[-1] - equity[0]) / equity[0]) * 100

        if len(equity) > 1:
            returns = np.diff(equity) / equity[:-1]
            max_drawdown = self._calculate_max_drawdown(equity)
            sharpe = self._calculate_sharpe(returns)
        else:
            max_drawdown = 0.0
            sharpe = 0.0

        profit_factor = self._calculate_profit_factor()
        win_rate = (
            sum(1 for t in self.trade_log if t["pnl"] > 0) / len(self.trade_log)
            if self.trade_log
            else 0.0
        )

        return BacktestMetrics(
            total_return=total_return_pct,
            annual_return=total_return_pct,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            profit_factor=profit_factor,
            trade_count=len(self.trade_log),
            win_rate=win_rate,
            equity_curve=self.equity_curve,
            trade_log=self.trade_log,
        )

    def _calculate_max_drawdown(self, equity: np.ndarray[Any, np.dtype[np.floating[Any]]]) -> float:
        """Calculate max drawdown % from equity curve."""
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max
        return float(np.min(drawdown) * 100) if len(drawdown) > 0 else 0.0

    def _calculate_sharpe(self, returns: np.ndarray[Any, np.dtype[np.floating[Any]]], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio (event-period, not annualized).

        LIMITATION: Returns are calculated between equity_curve events (LONG/EXIT only),
        not daily observations. Without knowing the true inter-event frequency,
        annualization (√252) cannot be correctly applied.

        Sharpe here = mean(returns) / std(returns), normalized for event scale.
        For annual Sharpe, Phase 3+ needs observation-based equity updates.
        """
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        excess_returns = returns - (risk_free_rate / len(returns))
        return float(np.mean(excess_returns) / np.std(excess_returns))

    def _calculate_profit_factor(self) -> float:
        """Calculate profit factor from trade_log."""
        gross_profit = sum(t["pnl"] for t in self.trade_log if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in self.trade_log if t["pnl"] < 0))
        return gross_profit / (gross_loss + 1e-6) if gross_loss > 0 else 0.0

    def get_portfolio_state(self) -> PortfolioState:
        """Get current portfolio state.

        Returns:
            PortfolioState.
        """
        return self.portfolio

    def backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float,
    ) -> BacktestMetrics:
        """Run backtest.

        Args:
            start_date: Start date.
            end_date: End date.
            initial_capital: Starting capital.

        Returns:
            BacktestMetrics with real metrics calculated from equity curve.
        """
        if start_date >= end_date:
            raise ValueError("start_date must be < end_date")

        if initial_capital <= 0:
            raise ValueError("initial_capital must be positive")

        return self._calculate_metrics()

    def get_metrics(self) -> BacktestMetrics:
        """Get metrics.

        Returns:
            BacktestMetrics with real metrics from equity curve.
        """
        return self._calculate_metrics()

    def close(self) -> None:
        """Clean up resources."""
        pass
