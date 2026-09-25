"""NARM-P+ Engine: Narrative Adoption Rotation Model Plus — Layer 5 implementation."""

from typing import Literal

import numpy as np

from src.utils.logging import get_logger

from .base import NARMComponents, NARMSignal, NARMVerdict

logger = get_logger(__name__)


class NARMPEngine:
    """Score narrative strength and adoption rotation (NARM-P+: 100-point system)."""

    # Thresholds for rotation signal classification
    EMERGING_THRESHOLD = 40
    ACCELERATING_THRESHOLD = 60
    MATURE_THRESHOLD = 75

    def __init__(self) -> None:
        """Initialize NARM-P+ engine."""
        self.history: list[NARMVerdict] = []

    def evaluate(self, signal: NARMSignal) -> NARMVerdict:
        """Evaluate narrative adoption and rotation.

        Args:
            signal: NARMSignal with attention, adoption, and sentiment data

        Returns:
            NARMVerdict with 0-100 score and rotation classification
        """
        components = self._score_components(signal)
        total_score = (
            components.narrative_strength
            + components.adoption_momentum
            + components.capital_rotation
            + components.sentiment_alignment
            + components.network_effects
        )

        rotation_signal = self._classify_rotation(total_score, signal)
        percentile = self._calculate_percentile(total_score)
        confidence = self._calculate_confidence(signal, total_score)
        reasoning = self._generate_reasoning(signal, components, total_score)

        verdict = NARMVerdict(
            timestamp=signal.timestamp,
            asset_id=signal.asset_id,
            narrative_category=signal.narrative_category,
            total_score=total_score,
            components=components,
            percentile=percentile,
            rotation_signal=rotation_signal,
            confidence=confidence,
            reasoning=reasoning,
            metadata={
                "attention_score": signal.attention_score,
                "sentiment_score": signal.sentiment_score,
                "adoption_rate": signal.adoption_rate,
                "social_volume_rank": signal.social_volume_rank,
            },
        )

        self.history.append(verdict)
        logger.info(
            f"NARM-P+ evaluated: {signal.asset_id}",
            extra={
                "extra_fields": {
                    "asset_id": signal.asset_id,
                    "score": total_score,
                    "rotation": rotation_signal,
                }
            },
        )

        return verdict

    @staticmethod
    def _score_components(signal: NARMSignal) -> NARMComponents:
        """Score NARM-P+ components (0-100 total)."""
        narrative_strength = int(
            np.clip(signal.attention_score / 4.0, 0, 25)
        )

        adoption_momentum = int(
            np.clip((signal.adoption_rate / 10.0) + (signal.attention_growth_1m / 5.0), 0, 25)
        )

        capital_rotation = int(
            np.clip((signal.capital_inflow / 2.0) + (signal.attention_growth_3m / 10.0), 0, 25)
        )

        sentiment_base = (signal.sentiment_score + 100) / 200.0
        sentiment_alignment = int(np.clip(sentiment_base * 15.0, 0, 15))

        network_effect = 0
        if signal.network_value > 0:
            nvt_score = min(1.0, 10.0 / signal.network_value)
            network_effect = int(nvt_score * 10.0)
        else:
            network_effect = int(np.clip(signal.adoption_rate / 100.0, 0, 10))

        return NARMComponents(
            narrative_strength=narrative_strength,
            adoption_momentum=adoption_momentum,
            capital_rotation=capital_rotation,
            sentiment_alignment=sentiment_alignment,
            network_effects=network_effect,
        )

    @staticmethod
    def _classify_rotation(
        total_score: int, signal: NARMSignal
    ) -> Literal["EMERGING", "ACCELERATING", "MATURE", "DECLINING"]:
        """Classify rotation phase based on score and momentum."""
        if signal.attention_growth_1m < -10 and total_score < NARMPEngine.EMERGING_THRESHOLD:
            return "DECLINING"
        if total_score < NARMPEngine.EMERGING_THRESHOLD:
            return "EMERGING"
        if total_score < NARMPEngine.MATURE_THRESHOLD:
            return "ACCELERATING"
        return "MATURE"

    @staticmethod
    def _calculate_percentile(total_score: int) -> float:
        """Calculate percentile ranking (0-1) based on score."""
        return float(np.clip(total_score / 100.0, 0, 1))

    @staticmethod
    def _calculate_confidence(signal: NARMSignal, total_score: int) -> float:
        """Calculate confidence in NARM-P+ assessment."""
        attention_confidence = min(1.0, signal.attention_score / 50.0)
        adoption_confidence = min(1.0, abs(signal.adoption_rate) / 20.0)
        capital_confidence = min(1.0, abs(signal.capital_inflow) / 20.0)

        avg_confidence = (
            attention_confidence + adoption_confidence + capital_confidence
        ) / 3.0

        score_factor = 1.0 if 30 <= total_score <= 75 else 0.7

        return float(np.clip(avg_confidence * score_factor, 0, 1))

    @staticmethod
    def _generate_reasoning(
        signal: NARMSignal, components: NARMComponents, total_score: int
    ) -> list[str]:
        """Generate human-readable reasoning for NARM-P+ score."""
        reasoning = []

        if components.narrative_strength > 15:
            reasoning.append(
                f"Strong narrative presence: {signal.attention_score:.0f}/100 attention"
            )

        if signal.attention_growth_1m > 20:
            reasoning.append(f"Rapid attention growth: +{signal.attention_growth_1m:.1f}%/month")

        if signal.adoption_rate > 30:
            reasoning.append(f"High adoption momentum: +{signal.adoption_rate:.1f}%/month")

        if signal.capital_inflow > 5:
            reasoning.append(f"Capital inflow detected: +{signal.capital_inflow:.1f}%")

        if signal.sentiment_score > 30:
            reasoning.append(f"Positive sentiment: {signal.sentiment_score:.0f}")

        if signal.social_volume_rank < 20:
            reasoning.append(f"Top {signal.social_volume_rank} in social volume")

        if not reasoning:
            if total_score > 50:
                reasoning.append(
                    "Moderate narrative strength: balanced adoption and capital flows"
                )
            else:
                reasoning.append("Emerging narrative: early stage adoption")

        return reasoning
