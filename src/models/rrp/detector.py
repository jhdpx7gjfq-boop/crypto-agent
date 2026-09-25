"""Revival Radar Pipeline: Dead token renaissance detection — Layer 7 implementation."""

from typing import Literal

import numpy as np

from src.utils.logging import get_logger

from .base import RRPMetrics, RRPSnapshot, RRPVerdict

logger = get_logger(__name__)


class RRPEngine:
    """Detect revival signals in dormant (dead) tokens."""

    # Thresholds for stage classification
    STIRRING_THRESHOLD = 0.3
    AWAKENING_THRESHOLD = 0.55
    REVIVING_THRESHOLD = 0.75

    def __init__(self) -> None:
        """Initialize RRP engine."""
        self.history: list[RRPVerdict] = []
        self.snapshots: dict[str, list[RRPSnapshot]] = {}

    def evaluate(self, snapshot: RRPSnapshot) -> RRPVerdict:
        """Evaluate token revival potential.

        Args:
            snapshot: RRPSnapshot with dormancy and activation metrics

        Returns:
            RRPVerdict with revival score and stage classification
        """
        metrics = self._calculate_metrics(snapshot)
        revival_score = self._calculate_composite(metrics)
        revival_stage = self._classify_stage(revival_score, snapshot.dormancy_days)
        confidence = self._calculate_confidence(metrics, revival_score)
        reasoning = self._generate_reasoning(snapshot, metrics, revival_score)

        verdict = RRPVerdict(
            timestamp=snapshot.timestamp,
            asset_id=snapshot.asset_id,
            dormancy_days=snapshot.dormancy_days,
            revival_score=revival_score,
            metrics=metrics,
            revival_stage=revival_stage,
            confidence=confidence,
            reasoning=reasoning,
            metadata={
                "volume_ratio": snapshot.volume_24h / (snapshot.volume_ma_90 + 1e-8),
                "holders_change": snapshot.holders_growth_30d,
                "social_change": snapshot.social_growth_30d,
                "whale_activity": snapshot.whale_accumulation,
            },
        )

        self.history.append(verdict)
        if snapshot.asset_id not in self.snapshots:
            self.snapshots[snapshot.asset_id] = []
        self.snapshots[snapshot.asset_id].append(snapshot)

        logger.info(
            f"RRP evaluated: {snapshot.asset_id}",
            extra={
                "extra_fields": {
                    "asset_id": snapshot.asset_id,
                    "score": revival_score,
                    "stage": revival_stage,
                }
            },
        )

        return verdict

    @staticmethod
    def _calculate_metrics(snapshot: RRPSnapshot) -> RRPMetrics:
        """Calculate RRP metrics from snapshot."""
        dormancy_score = min(1.0, snapshot.dormancy_days / 365.0)

        volume_spike = min(1.0, snapshot.volume_24h / (snapshot.volume_ma_90 + 1e-8))
        price_signal = max(0.0, min(1.0, (snapshot.price_change_30d + 50) / 100.0))
        activation_signal = float(np.clip((volume_spike + price_signal) / 2, 0, 1))

        holders_growth = max(0.0, min(1.0, snapshot.holders_growth_30d / 50.0))
        fundamental_shift = float(np.clip(holders_growth, 0, 1))

        social_momentum = float(
            np.clip(min(1.0, snapshot.social_growth_30d / 100.0), 0, 1)
        )

        whale_signal = float(np.clip(snapshot.whale_accumulation, 0, 1))

        recovery_prob = float(
            np.clip(
                (activation_signal + holders_growth + social_momentum + whale_signal)
                / 4.0,
                0,
                1,
            )
        )

        return RRPMetrics(
            dormancy_score=float(dormancy_score),
            activation_signal=float(activation_signal),
            fundamental_shift=fundamental_shift,
            social_momentum=social_momentum,
            whale_signal=whale_signal,
            recovery_probability=recovery_prob,
        )

    @staticmethod
    def _calculate_composite(metrics: RRPMetrics) -> float:
        """Calculate composite revival score."""
        activation_weight = 0.30
        fundamental_weight = 0.25
        social_weight = 0.20
        whale_weight = 0.15
        recovery_weight = 0.10

        composite = (
            metrics.activation_signal * activation_weight
            + metrics.fundamental_shift * fundamental_weight
            + metrics.social_momentum * social_weight
            + metrics.whale_signal * whale_weight
            + metrics.recovery_probability * recovery_weight
        )

        dormancy_penalty = metrics.dormancy_score * 0.2
        adjusted_score = max(0.0, composite - dormancy_penalty)

        return float(np.clip(adjusted_score, 0, 1))

    @staticmethod
    def _classify_stage(
        revival_score: float, dormancy_days: int
    ) -> Literal["DEAD", "STIRRING", "AWAKENING", "REVIVING"]:
        """Classify revival stage."""
        if dormancy_days > 365 and revival_score < RRPEngine.STIRRING_THRESHOLD:
            return "DEAD"
        if revival_score < RRPEngine.STIRRING_THRESHOLD:
            return "DEAD"
        if revival_score < RRPEngine.AWAKENING_THRESHOLD:
            return "STIRRING"
        if revival_score < RRPEngine.REVIVING_THRESHOLD:
            return "AWAKENING"
        return "REVIVING"

    @staticmethod
    def _calculate_confidence(metrics: RRPMetrics, revival_score: float) -> float:
        """Calculate confidence in revival assessment."""
        all_signals = [
            metrics.activation_signal,
            metrics.fundamental_shift,
            metrics.social_momentum,
            metrics.whale_signal,
            metrics.recovery_probability,
        ]

        consistency = 1.0 - np.std(all_signals)
        score_factor = max(revival_score, 0.3)

        confidence = consistency * 0.6 + score_factor * 0.4
        return float(np.clip(confidence, 0, 1))

    @staticmethod
    def _generate_reasoning(
        snapshot: RRPSnapshot,
        metrics: RRPMetrics,
        revival_score: float,
    ) -> list[str]:
        """Generate human-readable reasoning."""
        reasoning = []

        if snapshot.dormancy_days > 180:
            reasoning.append(f"Long dormancy: {snapshot.dormancy_days} days")

        if metrics.activation_signal > 0.6:
            vol_ratio = snapshot.volume_24h / (snapshot.volume_ma_90 + 1e-8)
            reasoning.append(f"Volume spike: {vol_ratio:.2f}x average")

        if snapshot.holders_growth_30d > 10:
            reasoning.append(f"Holder growth: +{snapshot.holders_growth_30d:.1f}%")

        if snapshot.social_growth_30d > 20:
            reasoning.append(f"Social momentum: +{snapshot.social_growth_30d:.1f}%")

        if metrics.whale_signal > 0.6:
            reasoning.append(f"Whale accumulation detected: {snapshot.whale_accumulation:.2f}")

        if revival_score >= 0.75:
            reasoning.append("Strong revival signal - breakout potential")
        elif revival_score >= 0.55:
            reasoning.append("Moderate revival - monitor for acceleration")
        elif revival_score >= 0.30:
            reasoning.append("Early stirring - confirm with more data")
        else:
            reasoning.append("Still dormant - no immediate revival signal")

        return reasoning
