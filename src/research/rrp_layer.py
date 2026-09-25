"""
Layer 7 - RRP Layer: Revival candidate detection and ranking

Generates revival signals by scoring dormant tokens on:
- Dormancy index
- Activity acceleration
- Whale accumulation
- Developer activity
- Narrative momentum
- Liquidity rebound

Output: Ranked revival candidates with confidence [0, 100]
"""

import pandas as pd
import numpy as np
from typing import Dict, List, NamedTuple, Optional
from dataclasses import dataclass


@dataclass
class RevivalCandidate:
    """Revival candidate signal."""
    symbol: str
    revival_confidence: float
    dormancy_index: float
    activity_acceleration: float
    whale_accumulation: float
    developer_activity: float
    narrative_momentum: float
    liquidity_rebound: float
    dormancy_days: int
    recommendation: str  # 'HIGH', 'MEDIUM', 'LOW', 'SKIP'
    entry_window_start: int  # days from confirmation


class RRPLayer:
    """Revival Radar Pipeline signal generator."""

    def __init__(self):
        """Initialize RRP layer."""
        self.candidates = []

    def score_tokens(self, tokens_df: pd.DataFrame,
                    metrics: Dict[str, np.ndarray]) -> List[RevivalCandidate]:
        """
        Score dormant tokens for revival probability.

        Args:
            tokens_df: DataFrame with columns [symbol, last_activity_days, market_cap]
            metrics: Dict mapping token -> array of metric time series

        Returns:
            List of RevivalCandidate sorted by confidence (descending)
        """
        candidates = []

        for _, row in tokens_df.iterrows():
            symbol = row['symbol']
            dormancy_days = int(row['last_activity_days'])

            # Get most recent metric values (last time step)
            if symbol not in metrics:
                continue

            metric_ts = metrics[symbol]
            if len(metric_ts) == 0:
                continue

            # Use latest metric value; in production would be individual metrics
            # For now, use trajectory to estimate acceleration (second-to-last vs last)
            latest_metric = metric_ts[-1]

            # Compute individual metrics from synthetic trajectory
            # In production, these come from RRPDataLayer
            dormancy = self._compute_dormancy_index(dormancy_days)
            acceleration = self._compute_acceleration(metric_ts)
            whale = self._compute_whale_signal(latest_metric)
            dev = self._compute_dev_signal(latest_metric)
            narrative = self._compute_narrative_signal(latest_metric)
            liquidity = self._compute_liquidity_signal(latest_metric)

            # Compute final score
            confidence = self._compute_revival_confidence(
                dormancy, acceleration, whale, dev, narrative, liquidity
            )

            # Determine recommendation
            if confidence > 70:
                recommendation = 'HIGH'
                entry_window = 7
            elif confidence > 50:
                recommendation = 'MEDIUM'
                entry_window = 10
            else:
                recommendation = 'LOW'
                entry_window = 14

            # Skip if confidence too low
            if confidence < 40:
                recommendation = 'SKIP'
                entry_window = 0

            candidate = RevivalCandidate(
                symbol=symbol,
                revival_confidence=float(confidence),
                dormancy_index=float(dormancy),
                activity_acceleration=float(acceleration),
                whale_accumulation=float(whale),
                developer_activity=float(dev),
                narrative_momentum=float(narrative),
                liquidity_rebound=float(liquidity),
                dormancy_days=dormancy_days,
                recommendation=recommendation,
                entry_window_start=entry_window,
            )

            candidates.append(candidate)

        # Sort by confidence descending
        candidates.sort(key=lambda x: x.revival_confidence, reverse=True)
        self.candidates = candidates

        return candidates

    def _compute_dormancy_index(self, days: int) -> float:
        """Compute dormancy [0, 1]."""
        d = (days - 30) / (365 - 30)
        return float(np.clip(d, 0, 1))

    def _compute_acceleration(self, metric_ts: np.ndarray) -> float:
        """Estimate acceleration from trajectory."""
        if len(metric_ts) < 3:
            return 0.0

        # If trajectory shows upward trend, return positive signal
        recent_5 = metric_ts[-5:] if len(metric_ts) >= 5 else metric_ts
        trend = (recent_5[-1] - recent_5[0]) / max(abs(recent_5[-1]), 0.1)

        # Clip to [-1, 1]
        return float(np.clip(trend, -1, 1))

    def _compute_whale_signal(self, metric_value: float) -> float:
        """Extract whale signal from metric."""
        # If metric > 0.3, whale activity detected
        if metric_value > 0.3:
            return float(np.clip(metric_value, -1, 1))
        return 0.0

    def _compute_dev_signal(self, metric_value: float) -> float:
        """Extract developer signal from metric."""
        # If metric shows positive trend, dev activity present
        return float(np.clip(metric_value * 0.5, -1, 1))

    def _compute_narrative_signal(self, metric_value: float) -> float:
        """Extract narrative signal from metric."""
        # If metric > 0.2, narrative momentum detected
        if metric_value > 0.2:
            return float(np.clip(metric_value, -1, 1))
        return 0.0

    def _compute_liquidity_signal(self, metric_value: float) -> float:
        """Extract liquidity rebound from metric."""
        # Moderate positive contribution
        return float(np.clip(metric_value * 0.3, -1, 1))

    def _compute_revival_confidence(self, dormancy: float, acceleration: float,
                                   whale: float, dev: float, narrative: float,
                                   liquidity: float) -> float:
        """
        Compute Revival_Confidence [0, 100].

        Weights per spec:
        - Dormancy: 0.20
        - Acceleration: 0.25 (highest)
        - Whale: 0.15
        - Dev: 0.15
        - Narrative: 0.15
        - Liquidity: 0.10
        """
        score = (
            0.20 * dormancy +
            0.25 * acceleration +
            0.15 * whale +
            0.15 * dev +
            0.15 * narrative +
            0.10 * liquidity
        )

        # Sigmoid to [0, 100]
        confidence = (1 / (1 + np.exp(-score * 3))) * 100

        return float(confidence)

    def get_high_confidence_candidates(self, min_confidence: float = 70) -> List[RevivalCandidate]:
        """Get candidates above confidence threshold."""
        return [c for c in self.candidates if c.revival_confidence >= min_confidence]

    def rank_by_confidence(self) -> List[RevivalCandidate]:
        """Return all candidates ranked by confidence (highest first)."""
        return sorted(self.candidates, key=lambda x: x.revival_confidence, reverse=True)
