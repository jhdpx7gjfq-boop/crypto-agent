"""Liquidation label engineering — target computation for supervised learning.

Label Definition:
- RETURN[T→T+1m]: 1-minute return from observation time T
- Computed from price data (not liquidation events)
- Window: (T, T+1m] — strictly after observation time
- PIT Compliance: Labels unavailable at observation time (computed after)

Label Computation:
- return = (price[T+1m] - price[T]) / price[T]
- sign(return) ∈ {-1, 0, +1}: down, flat, up
- Used for: Directional prediction, signal validation

Deferred (v0.2):
- Multi-step labels (5m, 15m, 1h)
- Regime-conditional labels
- Volume-weighted returns
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import numpy as np

logger = logging.getLogger(__name__)


class LiquidationLabelEngine:
    """Compute liquidation-aligned labels from price data."""

    def __init__(self, label_window_minutes: int = 1) -> None:
        """Initialize label engine.

        Args:
            label_window_minutes: Label forward window (default 1 minute)
        """
        self.label_window_minutes = label_window_minutes
        self.label_window_timedelta = timedelta(minutes=label_window_minutes)

    def compute_return(
        self,
        price_at_t: float,
        price_at_t_plus_window: float,
    ) -> float:
        """Compute simple return over label window.

        return = (price[T+window] - price[T]) / price[T]

        Args:
            price_at_t: Price at observation time T (exclusive)
            price_at_t_plus_window: Price at T+window (inclusive)

        Returns:
            Return value [-1, ∞), or 0 if price_at_t is 0
        """
        if price_at_t <= 0:
            logger.warning(f"Invalid price_at_t: {price_at_t}")
            return 0.0

        return_value = (price_at_t_plus_window - price_at_t) / price_at_t
        logger.debug(f"Return: {return_value:.4f}")
        return float(return_value)

    def compute_return_sign(
        self,
        price_at_t: float,
        price_at_t_plus_window: float,
    ) -> Literal[-1, 0, 1]:
        """Compute directional sign of return.

        sign = -1 if return < 0, 0 if return ≈ 0, +1 if return > 0
        Threshold: ±0.001 (0.1%)

        Args:
            price_at_t: Price at observation time T
            price_at_t_plus_window: Price at T+window

        Returns:
            Sign: -1 (down), 0 (flat), +1 (up)
        """
        return_value = self.compute_return(price_at_t, price_at_t_plus_window)

        # Threshold to avoid noise in flat markets
        threshold = 0.001
        if return_value < -threshold:
            sign = -1
        elif return_value > threshold:
            sign = 1
        else:
            sign = 0

        logger.debug(f"Return sign: {sign}")
        return sign  # type: ignore

    def compute_log_return(
        self,
        price_at_t: float,
        price_at_t_plus_window: float,
    ) -> float:
        """Compute log return (more robust for large moves).

        log_return = ln(price[T+window] / price[T])

        Args:
            price_at_t: Price at observation time T
            price_at_t_plus_window: Price at T+window

        Returns:
            Log return value (unbounded)
        """
        if price_at_t <= 0 or price_at_t_plus_window <= 0:
            logger.warning(f"Invalid prices: {price_at_t}, {price_at_t_plus_window}")
            return 0.0

        log_return = np.log(price_at_t_plus_window / price_at_t)
        logger.debug(f"Log return: {log_return:.6f}")
        return float(log_return)

    def compute_label(
        self,
        observation_time: datetime,
        price_at_t: float,
        price_at_t_plus_window: float,
        symbol: str = "UNKNOWN",
    ) -> dict[str, Any]:
        """Compute comprehensive label for observation time.

        Args:
            observation_time: Reference timestamp (T)
            price_at_t: Price at T (from market data, not liquidation)
            price_at_t_plus_window: Price at T+label_window
            symbol: Trading pair (for tracking)

        Returns:
            Dict with keys {timestamp, symbol, return, return_sign, log_return, window}
        """
        logger.info(
            f"Computing label for {symbol} at {observation_time.isoformat()} "
            f"(prices: {price_at_t} → {price_at_t_plus_window})"
        )

        label = {
            "timestamp": observation_time.isoformat(),
            "symbol": symbol,
            "return": self.compute_return(price_at_t, price_at_t_plus_window),
            "return_sign": self.compute_return_sign(price_at_t, price_at_t_plus_window),
            "log_return": self.compute_log_return(price_at_t, price_at_t_plus_window),
            "label_window_minutes": self.label_window_minutes,
            "price_at_t": price_at_t,
            "price_at_t_plus_window": price_at_t_plus_window,
        }

        logger.debug(f"Label: {label}")
        return label

    def batch_compute_labels(
        self,
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Compute labels for batch of observations.

        Args:
            observations: List of dicts with keys {observation_time, price_at_t, price_at_t_plus_window, symbol}

        Returns:
            List of label dicts
        """
        labels = []
        for obs in observations:
            label = self.compute_label(
                observation_time=obs["observation_time"],
                price_at_t=obs["price_at_t"],
                price_at_t_plus_window=obs["price_at_t_plus_window"],
                symbol=obs.get("symbol", "UNKNOWN"),
            )
            labels.append(label)

        logger.info(f"Batch computed {len(labels)} labels")
        return labels

    def compute_label_statistics(
        self,
        labels: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compute statistics on computed labels.

        Args:
            labels: List of label dicts

        Returns:
            Dict with statistics {count, return_mean, return_std, sign_distribution, ...}
        """
        if not labels:
            return {
                "count": 0,
                "return_mean": 0.0,
                "return_std": 0.0,
                "sign_distribution": {"down": 0, "flat": 0, "up": 0},
                "return_min": 0.0,
                "return_max": 0.0,
            }

        returns = [label.get("return", 0.0) for label in labels]
        return_signs = [label.get("return_sign", 0) for label in labels]

        return {
            "count": len(labels),
            "return_mean": float(np.mean(returns)),
            "return_std": float(np.std(returns)),
            "return_min": float(np.min(returns)),
            "return_max": float(np.max(returns)),
            "sign_distribution": {
                "down": int(sum(1 for s in return_signs if s == -1)),
                "flat": int(sum(1 for s in return_signs if s == 0)),
                "up": int(sum(1 for s in return_signs if s == 1)),
            },
        }
