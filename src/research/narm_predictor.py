"""NARM Predictor (Models H + I)

Macro narrative signals for price prediction.
"""

import pandas as pd
import numpy as np
from typing import Dict

from src.research.baseline_predictor import BaselinePredictor
from src.research.market_regime_detector import MarketRegimeDetector, Trend, VolRegime
from src.research.narm_data_layer import NARMDataLayer
from src.data.spring_detector_p05_temporal import SpringDetector


class NARMPredictor:
    """Predicts using macro narrative (NARM-P+)."""

    def __init__(self, use_regime: bool = False, use_spring: bool = False):
        self.use_regime = use_regime
        self.use_spring = use_spring
        self.baseline = BaselinePredictor()
        self.regime = MarketRegimeDetector() if use_regime else None
        self.spring = SpringDetector() if use_spring else None
        self.narm = NARMDataLayer()

    def predict(self, df: pd.DataFrame, pit_idx: int) -> float:
        """
        Multi-factor prediction with NARM-P+ (PIT-safe).

        Blend:
        - 50% Baseline momentum
        - 50% NARM-P+ macro signal
        + Optional Regime filter
        + Optional Spring signal
        """
        if pit_idx < 1:
            return 0.0

        pit_data = df.iloc[:pit_idx + 1]

        # Baseline: 50%
        base_score = self.baseline.predict(pit_data, len(pit_data) - 1)
        score = 0.5 * base_score

        # NARM-P+ score: 50%
        if 'sentiment_score' in pit_data.columns:
            sentiment = pit_data['sentiment_score'].iloc[-1] / 100.0 if pd.notna(pit_data['sentiment_score'].iloc[-1]) else 0.5
            adoption = 0.5  # Simplified; would compute from adoption_addresses
            rotation = 0.5  # Simplified; would compute from sector changes
            fundamentals = 0.5
            momentum = 0.5

            narm_raw = (
                0.25 * sentiment +
                0.25 * adoption +
                0.20 * rotation +
                0.20 * fundamentals +
                0.10 * momentum
            )

            # Convert NARM (0-1 range after components) to signal (-1 to +1)
            # NARM > 0.6 → bullish, NARM < 0.4 → bearish
            narm_signal = (narm_raw - 0.5) * 2.0  # Scale to [-1, +1]
            score += 0.5 * narm_signal
        else:
            # No NARM data; use baseline only
            score = base_score

        # Apply Regime filter if enabled
        if self.use_regime and self.regime:
            try:
                trend, vol_regime = self.regime.classify_row(pit_data, len(pit_data) - 1)

                if trend == Trend.BEAR:
                    score *= 0.7
                elif trend == Trend.BULL:
                    score *= 1.2

                if vol_regime == VolRegime.LOW_VOL:
                    score *= 0.8
            except Exception:
                pass

        # Apply Spring signal if enabled
        if self.use_spring and self.spring:
            try:
                spring_result = self.spring.classify("BTC", pit_data)
                spring_signal = 0.0

                if spring_result.state == "SPRING_CANDIDATE":
                    spring_signal = 0.3
                elif spring_result.state == "BREAKDOWN":
                    spring_signal = -0.2

                score = 0.85 * score + 0.15 * spring_signal  # Spring: low weight
            except Exception:
                pass

        return float(np.clip(score, -1, 1))

    def batch_predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict for entire series (PIT-safe per row)."""
        predictions = []
        for idx in range(len(df)):
            pred = self.predict(df, idx)
            predictions.append(pred)
        return np.array(predictions)

    def score_window(self, df: pd.DataFrame, window_start_idx: int, window_end_idx: int) -> Dict:
        """Score on a test window."""
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
def model_h(df: pd.DataFrame) -> NARMPredictor:
    """H: Baseline + NARM-P+."""
    return NARMPredictor(use_regime=False, use_spring=False)


def model_i(df: pd.DataFrame) -> NARMPredictor:
    """I: Baseline + NARM-P+ + Regime + Spring (full stack v2)."""
    return NARMPredictor(use_regime=True, use_spring=True)
