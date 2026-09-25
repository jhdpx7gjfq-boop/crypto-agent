"""Baseline Predictor (Model A: No Spring, No Context)

Simple model: recent momentum direction.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


class BaselinePredictor:
    """Baseline: momentum-only predictor, no Spring."""

    def __init__(self, lookback: int = 5):
        self.lookback = lookback

    def predict(self, df: pd.DataFrame, pit_idx: int) -> float:
        """
        Predict next-candle return direction at pit_idx.

        Uses ONLY data before pit_idx (PIT-safe).

        Returns:
            score in [-1, 1]: negative = expect down, positive = expect up
        """
        if pit_idx < self.lookback:
            return 0.0  # Insufficient data

        # Use only data up to pit_idx
        pit_data = df.iloc[:pit_idx + 1]

        # Recent momentum: close slope over lookback
        closes = pit_data["close"].iloc[-self.lookback:].values
        if len(closes) < 2:
            return 0.0

        # Simple linear slope
        x = np.arange(len(closes))
        slope = np.polyfit(x, closes, 1)[0]

        # Normalize to [-1, 1]
        recent_price = closes[-1]
        volatility = np.std(closes) if np.std(closes) > 0 else 1.0
        normalized = slope / volatility * recent_price
        clamped = np.clip(normalized, -1, 1)

        return float(clamped)

    def batch_predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict for entire series (PIT-safe per row)."""
        predictions = []
        for idx in range(len(df)):
            pred = self.predict(df, idx)
            predictions.append(pred)
        return np.array(predictions)

    def score_window(self, df: pd.DataFrame, window_start_idx: int, window_end_idx: int) -> Dict:
        """
        Score on a test window.

        Returns:
            {
                "predictions": [score, ...],
                "actuals": [return_pct, ...],
                "n_predictions": int
            }
        """
        predictions = []
        actuals = []

        for test_idx in range(window_start_idx, window_end_idx):
            if test_idx >= len(df) - 1:
                break

            # Predict using data strictly before test_idx
            pred = self.predict(df, test_idx)
            predictions.append(pred)

            # Actual: next-candle return
            current_close = df["close"].iloc[test_idx]
            next_close = df["close"].iloc[test_idx + 1]
            actual_return = (next_close - current_close) / current_close
            actuals.append(actual_return)

        return {
            "predictions": np.array(predictions),
            "actuals": np.array(actuals),
            "n_predictions": len(predictions)
        }
