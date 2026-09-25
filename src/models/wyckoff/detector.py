"""Wyckoff cycle detector and Bottom Confirmation Engine — Layer 3 implementation."""

from typing import Literal

import numpy as np

from src.utils.logging import get_logger

from .base import BCE_Signal, BCE_Verdict, WyckoffPhase, WyckoffSignal

logger = get_logger(__name__)


class WyckoffDetector:
    """Detect Wyckoff market phase from price action and volume."""

    def __init__(self) -> None:
        """Initialize detector."""
        self.history: list[WyckoffPhase] = []

    def detect(self, signal: WyckoffSignal) -> WyckoffPhase:
        """Detect current Wyckoff phase.

        Args:
            signal: WyckoffSignal with price, volume, technical indicators

        Returns:
            WyckoffPhase with name, confidence, duration, price_range
        """
        phase_name, confidence = self._classify_phase(signal)
        price_range = self._calculate_price_range(signal)

        phase = WyckoffPhase(
            name=phase_name,
            confidence=confidence,
            duration_periods=0,
            price_range=price_range,
        )

        self.history.append(phase)
        logger.info(
            f"Wyckoff phase detected: {phase_name}",
            extra={
                "extra_fields": {
                    "phase": phase_name,
                    "confidence": confidence,
                    "price_range": price_range,
                }
            },
        )

        return phase

    def _classify_phase(
        self, signal: WyckoffSignal
    ) -> tuple[Literal["ACCUMULATION", "MARKUP", "DISTRIBUTION", "MARKDOWN"], float]:
        """Classify phase based on price, volume, and technical indicators.

        Returns:
            (phase_name, confidence)
        """
        accumulation_score = self._score_accumulation(signal)
        markup_score = self._score_markup(signal)
        distribution_score = self._score_distribution(signal)
        markdown_score = self._score_markdown(signal)

        scores: dict[str, float] = {
            "ACCUMULATION": accumulation_score,
            "MARKUP": markup_score,
            "DISTRIBUTION": distribution_score,
            "MARKDOWN": markdown_score,
        }

        phase_name_str = max(scores, key=lambda k: scores[k])
        if phase_name_str not in ("ACCUMULATION", "MARKUP", "DISTRIBUTION", "MARKDOWN"):
            phase_name_str = "ACCUMULATION"  # fallback (should never happen)
        phase_name: Literal["ACCUMULATION", "MARKUP", "DISTRIBUTION", "MARKDOWN"] = phase_name_str  # type: ignore[assignment]
        confidence = float(np.clip(scores[phase_name], 0, 1))

        return phase_name, confidence

    @staticmethod
    def _score_accumulation(signal: WyckoffSignal) -> float:
        """Score likelihood of accumulation phase."""
        price_position = (signal.price - signal.low_52w) / (
            signal.high_52w - signal.low_52w + 1e-8
        )
        rsi_oversold = 1.0 - (signal.rsi_14 / 100.0)
        recent_trend_weak = abs(signal.price_change_7d) / (abs(signal.price_change_30d) + 1e-8)

        return float(
            np.clip((1.0 - price_position) * 0.4 + rsi_oversold * 0.4 + recent_trend_weak * 0.2, 0, 1)
        )

    @staticmethod
    def _score_markup(signal: WyckoffSignal) -> float:
        """Score likelihood of markup phase."""
        price_position = (signal.price - signal.low_52w) / (
            signal.high_52w - signal.low_52w + 1e-8
        )
        rsi_rising = max(0, (signal.rsi_14 - 30) / 40.0)
        recent_trend_strong = max(0, signal.price_change_7d) / (abs(signal.price_change_30d) + 1e-8)

        return float(
            np.clip(
                price_position * 0.4 + rsi_rising * 0.3 + recent_trend_strong * 0.3,
                0,
                1,
            )
        )

    @staticmethod
    def _score_distribution(signal: WyckoffSignal) -> float:
        """Score likelihood of distribution phase."""
        price_position = (signal.price - signal.low_52w) / (
            signal.high_52w - signal.low_52w + 1e-8
        )
        rsi_overbought = max(0, (signal.rsi_14 - 70) / 30.0)
        recent_trend_down_weak = (
            1.0
            if (signal.price_change_7d < 0 and signal.price_change_30d >= 0)
            else 0.0
        )

        return float(
            np.clip(
                price_position * 0.4 + rsi_overbought * 0.3 + recent_trend_down_weak * 0.3,
                0,
                1,
            )
        )

    @staticmethod
    def _score_markdown(signal: WyckoffSignal) -> float:
        """Score likelihood of markdown phase."""
        price_position = (signal.price - signal.low_52w) / (
            signal.high_52w - signal.low_52w + 1e-8
        )
        sustained_downtrend = (
            1.0 if (signal.price_change_7d < 0 and signal.price_change_30d < 0) else 0.0
        )
        rsi_dynamics = max(0, min(1.0, (signal.rsi_14 - 50) / 50.0))

        return float(
            np.clip(
                price_position * 0.3 + sustained_downtrend * 0.5 + rsi_dynamics * 0.2,
                0,
                1,
            )
        )

    @staticmethod
    def _calculate_price_range(signal: WyckoffSignal) -> tuple[float, float]:
        """Calculate effective price range for phase."""
        range_width = signal.high_52w - signal.low_52w
        center = (signal.high_52w + signal.low_52w) / 2.0
        return (
            float(center - range_width / 3.0),
            float(center + range_width / 3.0),
        )


class BottomConfirmationEngine:
    """Confirm bottom accumulation zone (BCE) with 0-6 scoring."""

    # Frozen thresholds per B-004
    COMPONENT_PASS_THRESHOLD = 0.5
    VERDICT_THRESHOLD = 5

    def __init__(self) -> None:
        """Initialize BCE."""
        self.history: list[BCE_Verdict] = []

    def evaluate(self, signal: BCE_Signal) -> BCE_Verdict:
        """Evaluate bottom confirmation signal.

        Args:
            signal: BCE_Signal with 6 confirmation components

        Returns:
            BCE_Verdict with 0-6 score and component breakdown
        """
        components = self._score_components(signal)
        total_score = sum(components.values())
        confidence = float(np.clip(total_score / 6.0, 0, 1))
        verdict = total_score >= self.VERDICT_THRESHOLD

        result = BCE_Verdict(
            score=int(total_score),
            components=components,
            phase="ACCUMULATION",
            confidence=confidence,
            verdict=verdict,
            metadata={
                "threshold": self.VERDICT_THRESHOLD,
                "component_threshold": self.COMPONENT_PASS_THRESHOLD,
                "timestamp": signal.timestamp.isoformat(),
            },
        )

        self.history.append(result)
        logger.info(
            f"BCE evaluated: score={total_score}, verdict={verdict}",
            extra={
                "extra_fields": {
                    "score": total_score,
                    "confidence": confidence,
                    "verdict": verdict,
                }
            },
        )

        return result

    @staticmethod
    def _score_components(signal: BCE_Signal) -> dict[str, int]:
        """Score each BCE component 0-1, sum to 0-6.

        Components:
        1. Selling exhaustion (RSI oversold behavior)
        2. Spring detected (retest down after failed breakup)
        3. Sign of strength (retest up from spring)
        4. Volume pattern confirmation
        5. Bullish divergence
        6. Market structure quality

        Returns:
            Dict mapping component names to 0 or 1
        """
        components = {}

        components["selling_exhaustion"] = (
            1 if signal.selling_exhaustion_score >= BottomConfirmationEngine.COMPONENT_PASS_THRESHOLD else 0
        )

        components["spring"] = 1 if signal.spring_detected else 0

        components["sign_of_strength"] = 1 if signal.sign_of_strength else 0

        components["volume_pattern"] = (
            1 if signal.volume_pattern >= BottomConfirmationEngine.COMPONENT_PASS_THRESHOLD else 0
        )

        components["divergence"] = (
            1 if signal.divergence_score >= BottomConfirmationEngine.COMPONENT_PASS_THRESHOLD else 0
        )

        components["structure"] = (
            1 if signal.structure_quality >= BottomConfirmationEngine.COMPONENT_PASS_THRESHOLD else 0
        )

        return components
