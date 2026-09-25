"""Flow Predictor (Models D + G)

Combines baseline momentum with capital flow signals.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

from src.research.baseline_predictor import BaselinePredictor
from src.research.market_regime_detector import MarketRegimeDetector
from src.research.flow_data_layer import FlowIndicators
from src.data.spring_detector_p05_temporal import SpringDetector


class FlowPredictor:
    """Predicts using Flow signals (optional Regime + Spring)."""

    def __init__(self, use_regime: bool = False, use_spring: bool = False):
        self.use_regime = use_regime
        self.use_spring = use_spring
        self.baseline = BaselinePredictor()
        self.regime = MarketRegimeDetector() if use_regime else None
        self.spring = SpringDetector() if use_spring else None

    def predict(self, df: pd.DataFrame, pit_idx: int) -> float:
        """
        Multi-factor prediction with Flow (PIT-safe).

        Blend:
        - 50% Baseline momentum
        - 30% OI change
        - 15% Funding rate
        - 5% Liquidations
        + Optional Regime filter
        + Optional Spring signal
        """
        if pit_idx < 1:
            return 0.0

        pit_data = df.iloc[:pit_idx + 1]

        # Baseline: 50%
        base_score = self.baseline.predict(pit_data, len(pit_data) - 1)
        score = 0.5 * base_score

        # Flow components
        flow_features = FlowIndicators.compute_flow_features(pit_data, len(pit_data) - 1)

        # OI change: 30%
        # Positive OI change suggests bullish sentiment
        oi_signal = np.tanh(flow_features['oi_change_pct'] * 100)  # Map to [-1, 1]
        score += 0.3 * oi_signal

        # Funding rate: 15%
        # High positive funding suggests euphoric longs (reversal risk, but trend-following)
        funding_signal = np.tanh(flow_features['funding_rate_7d_avg'] * 100)  # Map to [-1, 1]
        score += 0.15 * funding_signal

        # Liquidations: 5%
        liq_signal = -np.tanh(flow_features['liquidation_pct'] * 10)  # Cascade = risk off
        score += 0.05 * liq_signal

        # Apply Regime filter if enabled
        if self.use_regime and self.regime:
            try:
                from src.research.market_regime_detector import Trend, VolRegime
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
                    spring_signal = 0.4
                elif spring_result.state == "BREAKDOWN":
                    spring_signal = -0.3

                score = 0.75 * score + 0.25 * spring_signal  # Spring: 25% weight if enabled
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
def model_d(df: pd.DataFrame) -> FlowPredictor:
    """D: Baseline + Flow."""
    return FlowPredictor(use_regime=False, use_spring=False)


def model_g(df: pd.DataFrame) -> FlowPredictor:
    """G: Baseline + Flow + Regime + Spring (full stack)."""
    return FlowPredictor(use_regime=True, use_spring=True)
