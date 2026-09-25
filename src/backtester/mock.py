"""Mock Backtester implementation for testing."""

from datetime import datetime
from typing import Any

import pandas as pd

from src.utils.logging import get_logger

from .base import Backtester, BacktestMetrics, BacktestSignal, PortfolioState

logger = get_logger(__name__)


class MockBacktester(Backtester):
    """Simple mock backtester: BUY-HOLD-SELL on threshold."""

    def __init__(self) -> None:
        """Initialize mock backtester."""
        self.config: dict[str, Any] = {}
        self.portfolio = PortfolioState(
            timestamp=datetime.now(),
            positions={},
            cash=10000.0,
            equity=10000.0,
        )
        self.equity_curve: list[float] = [10000.0]
        self.trade_log: list[dict[str, Any]] = []
        self.active_trades: dict[str, dict[str, Any]] = {}

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

        Args:
            features: Dict mapping asset -> DataFrame.
            timestamp: Current timestamp.

        Returns:
            List of signals.
        """
        signals = []

        for asset, df in features.items():
            if df.empty or "raw_price" not in df.columns:
                continue

            current_price = df["raw_price"].iloc[-1]

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

            self.trade_log.append(
                {
                    "asset": signal.asset,
                    "entry_price": trade["entry_price"],
                    "exit_price": signal.exit_price,
                    "quantity": trade["quantity"],
                    "pnl": pnl,
                    "entry_time": trade["entry_time"],
                    "exit_time": signal.timestamp,
                }
            )

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
        """Run backtest (placeholder).

        Args:
            start_date: Start date.
            end_date: End date.
            initial_capital: Starting capital.

        Returns:
            BacktestMetrics (mocked).
        """
        if start_date >= end_date:
            raise ValueError("start_date must be < end_date")

        if initial_capital <= 0:
            raise ValueError("initial_capital must be positive")

        total_pnl = sum(t["pnl"] for t in self.trade_log)
        total_return = (total_pnl / initial_capital) * 100

        win_count = sum(1 for t in self.trade_log if t["pnl"] > 0)
        win_rate = win_count / len(self.trade_log) if self.trade_log else 0.0

        profit_factor = (
            sum(t["pnl"] for t in self.trade_log if t["pnl"] > 0)
            / abs(sum(t["pnl"] for t in self.trade_log if t["pnl"] < 0))
            if any(t["pnl"] < 0 for t in self.trade_log)
            else 0.0
        )

        return BacktestMetrics(
            total_return=total_return,
            annual_return=total_return / 1.0,
            max_drawdown=-5.0,
            sharpe_ratio=1.5,
            profit_factor=profit_factor,
            trade_count=len(self.trade_log),
            win_rate=win_rate,
            equity_curve=self.equity_curve,
            trade_log=self.trade_log,
        )

    def get_metrics(self) -> BacktestMetrics:
        """Get metrics.

        Returns:
            BacktestMetrics.
        """
        total_pnl = sum(t["pnl"] for t in self.trade_log)
        total_return = (total_pnl / 10000.0) * 100

        win_count = sum(1 for t in self.trade_log if t["pnl"] > 0)
        win_rate = win_count / len(self.trade_log) if self.trade_log else 0.0

        profit_factor = (
            sum(t["pnl"] for t in self.trade_log if t["pnl"] > 0)
            / abs(sum(t["pnl"] for t in self.trade_log if t["pnl"] < 0))
            if any(t["pnl"] < 0 for t in self.trade_log)
            else 0.0
        )

        return BacktestMetrics(
            total_return=total_return,
            annual_return=total_return,
            max_drawdown=-5.0,
            sharpe_ratio=1.5,
            profit_factor=profit_factor,
            trade_count=len(self.trade_log),
            win_rate=win_rate,
            equity_curve=self.equity_curve,
            trade_log=self.trade_log,
        )

    def close(self) -> None:
        """Clean up resources."""
        pass
