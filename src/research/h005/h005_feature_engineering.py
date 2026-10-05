"""H-005 Feature Engineering: Exchange Flow Signals

Up to 6 features derived from Glassnode exchange flows.
PIT-safe: features computed from data[:idx+1] only.
"""

import pandas as pd
import numpy as np
from typing import Dict


class ExchangeFlowFeatures:
    """Extract and normalize exchange flow signals.

    Features (max 6):
    1. inflow_7d: 7-day inflow (ma)
    2. outflow_7d: 7-day outflow (ma)
    3. netflow_7d: inflow - outflow (ma)
    4. inflow_accum: cumulative inflow (30d window)
    5. outflow_accum: cumulative outflow (30d window)
    6. exchange_ratio: inflow / (inflow + outflow) ratio (normalized)
    """

    def __init__(self, lookback: int = 30):
        self.lookback = lookback

    def compute_features(self, flows_df: pd.DataFrame, pit_idx: int) -> Dict[str, float]:
        """Compute H-005 features at pit_idx (PIT-safe).

        Args:
            flows_df: DataFrame with columns [inflow, outflow] indexed by date
            pit_idx: Point-in-time index (data only up to this row)

        Returns:
            Dict with 6 features (normalized to [-1, 1])
        """
        if pit_idx < self.lookback:
            # Insufficient history
            return {
                "inflow_7d": 0.0,
                "outflow_7d": 0.0,
                "netflow_7d": 0.0,
                "inflow_accum": 0.0,
                "outflow_accum": 0.0,
                "exchange_ratio": 0.0,
            }

        # Data up to pit_idx only
        pit_data = flows_df.iloc[:pit_idx+1]

        # Feature 1: 7-day MA inflow
        inflow_ma = pit_data["inflow"].iloc[-7:].mean() if len(pit_data) >= 7 else 0.0

        # Feature 2: 7-day MA outflow
        outflow_ma = pit_data["outflow"].iloc[-7:].mean() if len(pit_data) >= 7 else 0.0

        # Feature 3: 7-day MA netflow
        netflow_ma = inflow_ma - outflow_ma

        # Feature 4: Cumulative inflow (30-day window)
        inflow_accum = pit_data["inflow"].iloc[-self.lookback:].sum()

        # Feature 5: Cumulative outflow (30-day window)
        outflow_accum = pit_data["outflow"].iloc[-self.lookback:].sum()

        # Feature 6: Exchange ratio (volume-weighted)
        total_flow = abs(inflow_accum) + abs(outflow_accum)
        exchange_ratio = inflow_accum / total_flow if total_flow > 0 else 0.5

        # Normalize to [-1, 1]
        return {
            "inflow_7d": np.clip(inflow_ma / (abs(inflow_ma) + 1e-6), -1, 1),
            "outflow_7d": np.clip(outflow_ma / (abs(outflow_ma) + 1e-6), -1, 1),
            "netflow_7d": np.clip(netflow_ma / (abs(netflow_ma) + 1e-6), -1, 1),
            "inflow_accum": np.clip(inflow_accum / (abs(inflow_accum) + 1e-6), -1, 1),
            "outflow_accum": np.clip(outflow_accum / (abs(outflow_accum) + 1e-6), -1, 1),
            "exchange_ratio": 2 * (exchange_ratio - 0.5),  # Normalize to [-1, 1]
        }


class H005SignalGenerator:
    """Combine exchange flow features into unified signal.

    Simple averaging of 6 features with equal weights (can be tuned).
    Output: score in [-1, 1] (positive = bullish, negative = bearish)
    """

    def __init__(self, feature_weights: Dict[str, float] = None):
        if feature_weights is None:
            # Equal weights by default
            feature_weights = {
                "inflow_7d": 1.0 / 6,
                "outflow_7d": 1.0 / 6,
                "netflow_7d": 1.0 / 6,
                "inflow_accum": 1.0 / 6,
                "outflow_accum": 1.0 / 6,
                "exchange_ratio": 1.0 / 6,
            }
        self.feature_weights = feature_weights

    def generate_signal(self, features: Dict[str, float]) -> float:
        """Weighted average of features.

        Args:
            features: Dict from ExchangeFlowFeatures.compute_features()

        Returns:
            Signal score in [-1, 1]
        """
        score = 0.0
        for feat_name, weight in self.feature_weights.items():
            score += features.get(feat_name, 0.0) * weight

        return float(np.clip(score, -1, 1))
