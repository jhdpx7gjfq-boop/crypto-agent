"""RCM/RPM Engine: Rotation Confirmation Model — Layer 6 implementation."""

from typing import Literal

import numpy as np

from src.utils.logging import get_logger

from .base import RCMComponents, RCMSignal, RCMVerdict

logger = get_logger(__name__)


class RCMEngine:
    """Confirm capital rotation hypothesis across 5 weighted components."""

    # Thresholds for confirmation
    CONFIRMATION_THRESHOLD = 0.65

    def __init__(self) -> None:
        """Initialize RCM engine."""
        self.history: list[RCMVerdict] = []

    def evaluate(self, signal: RCMSignal) -> RCMVerdict:
        """Evaluate rotation confirmation.

        Args:
            signal: RCMSignal with component scores

        Returns:
            RCMVerdict with composite score and confirmation status
        """
        components = self._normalize_components(signal)
        rcm_score = self._calculate_composite(components)
        rotation_confirmed = rcm_score >= self.CONFIRMATION_THRESHOLD
        confirmation_strength = self._classify_strength(rcm_score)
        confidence = self._calculate_confidence(components, rcm_score)
        reasoning = self._generate_reasoning(signal, components, rcm_score)

        verdict = RCMVerdict(
            timestamp=signal.timestamp,
            asset_id=signal.asset_id,
            rcm_score=rcm_score,
            components=components,
            rotation_confirmed=rotation_confirmed,
            confirmation_strength=confirmation_strength,
            confidence=confidence,
            reasoning=reasoning,
            metadata={
                "threshold": self.CONFIRMATION_THRESHOLD,
                "component_weights": {
                    "capital_flow": 0.25,
                    "relative_strength": 0.25,
                    "narrative_acceleration": 0.20,
                    "fundamental_confirmation": 0.20,
                    "derivatives_structure": 0.10,
                },
            },
        )

        self.history.append(verdict)
        logger.info(
            f"RCM evaluated: {signal.asset_id}",
            extra={
                "extra_fields": {
                    "asset_id": signal.asset_id,
                    "score": rcm_score,
                    "confirmed": rotation_confirmed,
                }
            },
        )

        return verdict

    @staticmethod
    def _normalize_components(signal: RCMSignal) -> RCMComponents:
        """Normalize and validate signal components to [0, 1]."""
        capital_flow = float(np.clip((signal.capital_flow_score + 1) / 2, 0, 1))
        relative_strength = float(np.clip(signal.relative_strength, 0, 1))
        narrative_acceleration = float(
            np.clip((signal.narrative_acceleration + 1) / 2, 0, 1)
        )
        fundamental_confirmation = float(
            np.clip(signal.fundamental_confirmation, 0, 1)
        )

        derivative_score = 0.5 + min(0.5, max(-0.5, signal.derivative_funding / 4.0))
        oi_score = min(1.0, max(0.0, signal.open_interest_change / 50.0))
        derivatives_structure = float(
            np.clip((derivative_score + oi_score) / 2, 0, 1)
        )

        return RCMComponents(
            capital_flow=capital_flow,
            relative_strength=relative_strength,
            narrative_acceleration=narrative_acceleration,
            fundamental_confirmation=fundamental_confirmation,
            derivatives_structure=derivatives_structure,
        )

    @staticmethod
    def _calculate_composite(components: RCMComponents) -> float:
        """Calculate weighted composite RCM score."""
        weighted_score = (
            components.capital_flow * 0.25
            + components.relative_strength * 0.25
            + components.narrative_acceleration * 0.20
            + components.fundamental_confirmation * 0.20
            + components.derivatives_structure * 0.10
        )
        return float(np.clip(weighted_score, 0, 1))

    @staticmethod
    def _classify_strength(
        rcm_score: float,
    ) -> Literal["WEAK", "MODERATE", "STRONG", "VERY_STRONG"]:
        """Classify confirmation strength."""
        if rcm_score >= 0.85:
            return "VERY_STRONG"
        if rcm_score >= 0.70:
            return "STRONG"
        if rcm_score >= 0.50:
            return "MODERATE"
        return "WEAK"

    @staticmethod
    def _calculate_confidence(components: RCMComponents, rcm_score: float) -> float:
        """Calculate overall confidence in RCM assessment."""
        all_components = [
            components.capital_flow,
            components.relative_strength,
            components.narrative_acceleration,
            components.fundamental_confirmation,
            components.derivatives_structure,
        ]

        consistency = 1.0 - np.std(all_components)
        score_factor = rcm_score

        confidence = consistency * 0.5 + score_factor * 0.5
        return float(np.clip(confidence, 0, 1))

    @staticmethod
    def _generate_reasoning(
        signal: RCMSignal,
        components: RCMComponents,
        rcm_score: float,
    ) -> list[str]:
        """Generate human-readable reasoning."""
        reasoning = []

        if components.capital_flow > 0.65:
            direction = "inflow" if signal.capital_flow_score > 0 else "outflow"
            reasoning.append(f"Strong capital {direction}: {signal.capital_flow_score:.2f}")

        if components.relative_strength > 0.65:
            reasoning.append(
                f"Asset outperforming peers: {components.relative_strength:.2f}"
            )

        if components.narrative_acceleration > 0.65:
            reasoning.append(
                f"Narrative accelerating: {signal.narrative_acceleration:.2f}"
            )

        if components.fundamental_confirmation > 0.65:
            reasoning.append(
                f"Fundamentals confirming: {components.fundamental_confirmation:.2f}"
            )

        if components.derivatives_structure > 0.65:
            if signal.derivative_funding > 0.02:
                reasoning.append(f"High positive funding: {signal.derivative_funding:.3f}%")
            if signal.open_interest_change > 20:
                reasoning.append(f"OI expanding: +{signal.open_interest_change:.1f}%")

        if rcm_score >= 0.65:
            reasoning.append("Rotation hypothesis CONFIRMED by RCM")
        elif rcm_score >= 0.50:
            reasoning.append("Moderate rotation signal - monitor for confirmation")
        else:
            reasoning.append("Insufficient confirmation - wait for stronger signal")

        return reasoning
