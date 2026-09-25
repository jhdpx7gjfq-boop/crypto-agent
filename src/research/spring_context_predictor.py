"""Spring Context Predictor (Models B-G)

Combines Spring with Regime and/or Flow context.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict
from src.data.spring_detector_p05_temporal import SpringDetector
from src.research.market_regime_detector import MarketRegimeDetector, Trend, VolRegime
from src.research.baseline_predictor import BaselinePredictor


class SpringContextPredictor:
    """Predicts using Spring + optional Regime + optional Flow."""

    def __init__(self, use_spring: bool = True, use_regime: bool = False, use_flow: bool = False):
        self.use_spring = use_spring
        self.use_regime = use_regime
        self.use_flow = use_flow

        self.spring = SpringDetector() if use_spring else None
        self.regime = MarketRegimeDetector() if use_regime else None
        self.baseline = BaselinePredictor()

    def predict(self, df: pd.DataFrame, pit_idx: int) -> float:
        """
        Multi-factor prediction at pit_idx (PIT-safe).

        Combines:
        - Baseline momentum
        - Spring signal (if enabled)
        - Regime filter (if enabled)
        - Flow (placeholder; not yet implemented)

        Returns:
            Score in [-1, 1]
        """
        if pit_idx < 5:
            return 0.0

        # Use only data before pit_idx
        pit_data = df.iloc[:pit_idx + 1]

        # Start with baseline
        base_score = self.baseline.predict(pit_data, len(pit_data) - 1)

        # Add Spring signal
        if self.use_spring:
            try:
                spring_result = self.spring.classify("BTC", pit_data)
                spring_signal = 0.0

                if spring_result.state == "SPRING_CANDIDATE":
                    # Spring suggests upside
                    sweep_depth = spring_result.evidence.get("sweep_depth", 0.0) or 0.0
                    spring_signal = 0.5 + 0.5 * min(sweep_depth / 10.0, 1.0)  # Cap at 1.0
                elif spring_result.state == "BREAKDOWN":
                    spring_signal = -0.5
                elif spring_result.state == "SWEEP":
                    spring_signal = -0.3

                # Blend with baseline
                base_score = 0.6 * base_score + 0.4 * spring_signal
            except Exception:
                pass  # If Spring fails, use baseline only

        # Apply regime filter
        if self.use_regime:
            trend, vol_regime = self.regime.classify_row(pit_data, len(pit_data) - 1)

            # In bear/low-vol, reduce bullish bias
            if trend == Trend.BEAR:
                base_score *= 0.7
            elif trend == Trend.BULL:
                base_score *= 1.2

            if vol_regime == VolRegime.LOW_VOL:
                base_score *= 0.8

        # Clamp to [-1, 1]
        return float(np.clip(base_score, -1, 1))

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

            pred = self.predict(df, test_idx)
            predictions.append(pred)

            current_close = df["close"].iloc[test_idx]
            next_close = df["close"].iloc[test_idx + 1]
            actual_return = (next_close - current_close) / current_close
            actuals.append(actual_return)

        return {
            "predictions": np.array(predictions),
            "actuals": np.array(actuals),
            "n_predictions": len(predictions)
        }


# Convenience factories
def model_a(df: pd.DataFrame) -> SpringContextPredictor:
    """A: Baseline only."""
    return SpringContextPredictor(use_spring=False, use_regime=False, use_flow=False)


def model_b(df: pd.DataFrame) -> SpringContextPredictor:
    """B: Baseline + Spring."""
    return SpringContextPredictor(use_spring=True, use_regime=False, use_flow=False)


def model_c(df: pd.DataFrame) -> SpringContextPredictor:
    """C: Baseline + Regime."""
    return SpringContextPredictor(use_spring=False, use_regime=True, use_flow=False)


def model_d(df: pd.DataFrame) -> SpringContextPredictor:
    """D: Baseline + Flow (placeholder)."""
    return SpringContextPredictor(use_spring=False, use_regime=False, use_flow=True)


def model_e(df: pd.DataFrame) -> SpringContextPredictor:
    """E: Baseline + Spring + Regime."""
    return SpringContextPredictor(use_spring=True, use_regime=True, use_flow=False)


def model_f(df: pd.DataFrame) -> SpringContextPredictor:
    """F: Baseline + Spring + Flow (placeholder)."""
    return SpringContextPredictor(use_spring=True, use_regime=False, use_flow=True)


def model_g(df: pd.DataFrame) -> SpringContextPredictor:
    """G: Baseline + Spring + Regime + Flow (placeholder)."""
    return SpringContextPredictor(use_spring=True, use_regime=True, use_flow=True)
