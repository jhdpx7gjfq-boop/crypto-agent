"""Rotation Confirmation Model (RPM/RCM) implementation.

Frozen per B-004_SPEC sections 2.1-2.3.
"""

from datetime import datetime

from src.utils.logging import get_logger

from .base import RPMConfig, RPMPrediction, RPMSignal

logger = get_logger(__name__)


class RotationConfirmationModel:
    """RPM/RCM: Rotation Confirmation Model for capital rotation detection."""

    def __init__(self, config: RPMConfig | None = None) -> None:
        """Initialize RPM/RCM with frozen configuration.

        Args:
            config: RPMConfig (defaults to B-004_SPEC frozen weights).

        Raises:
            ValueError: If weights don't sum to 1.0.
        """
        self.config = config or RPMConfig()
        self.config.validate_weights()
        self.train_period: tuple[datetime, datetime] | None = None
        self.feature_set_hash = ""
        logger.info(
            "RPM/RCM initialized",
            extra={
                "extra_fields": {
                    "version": self.config.model_version,
                    "lookback_days": self.config.lookback_days,
                }
            },
        )

    def score(self, signal: RPMSignal) -> float:
        """Calculate aggregate RPM score from components.

        Per B-004_SPEC section 2.2:
        rpm_score = 0.25*CF + 0.25*RS + 0.20*NA + 0.20*FC + 0.10*DS

        Args:
            signal: RPMSignal with component scores.

        Returns:
            Aggregate score [0, 1].

        Raises:
            ValueError: If lookahead_flag is True.
        """
        if signal.lookahead_flag:
            raise ValueError("Lookahead flag must be False (point-in-time violation)")

        score = (
            self.config.capital_flow_weight * signal.capital_flow
            + self.config.relative_strength_weight * signal.relative_strength
            + self.config.narrative_acceleration_weight
            * signal.narrative_acceleration
            + self.config.fundamental_confirmation_weight
            * signal.fundamental_confirmation
            + self.config.derivatives_structure_weight * signal.derivatives_structure
        )
        return float(score)

    def direction(self, rpm_score: float) -> str:
        """Map RPM score to direction prediction.

        Per B-004_SPEC section 2.2:
        - LONG if score >= 0.60
        - NEUTRAL if 0.40 <= score < 0.60
        - SHORT if score < 0.40

        Args:
            rpm_score: Aggregate RPM score [0, 1].

        Returns:
            Direction: "LONG", "NEUTRAL", or "SHORT".
        """
        if rpm_score >= self.config.long_threshold:
            return "LONG"
        elif rpm_score >= self.config.neutral_threshold:
            return "NEUTRAL"
        else:
            return "SHORT"

    def predict(
        self,
        signal: RPMSignal,
        predicted_return: float | None = None,
    ) -> RPMPrediction:
        """Generate RPM/RCM prediction from signal.

        Args:
            signal: RPMSignal with component scores.
            predicted_return: Optional predicted in-period return %.
                If None, derived from rpm_score (linear interpolation).

        Returns:
            RPMPrediction with direction and confidence.

        Raises:
            ValueError: If lookahead_flag is True.
        """
        if signal.lookahead_flag:
            raise ValueError("Lookahead flag must be False")

        rpm_score = self.score(signal)
        dir_pred = self.direction(rpm_score)

        if predicted_return is None:
            predicted_return = (rpm_score - 0.5) * 10.0

        confidence = abs(rpm_score - 0.5) * 2.0

        prediction = RPMPrediction(
            timestamp=signal.timestamp,
            asset=signal.asset,
            predicted_direction=dir_pred,
            predicted_return_pct=predicted_return,
            confidence=confidence,
            rpm_score=rpm_score,
            provenance={
                "model_version": self.config.model_version,
                "lookback_days": self.config.lookback_days,
                "train_period": (
                    self.train_period[0].isoformat(),
                    self.train_period[1].isoformat(),
                )
                if self.train_period
                else None,
                "feature_set_hash": self.feature_set_hash,
                "component_scores": {
                    "capital_flow": signal.capital_flow,
                    "relative_strength": signal.relative_strength,
                    "narrative_acceleration": signal.narrative_acceleration,
                    "fundamental_confirmation": signal.fundamental_confirmation,
                    "derivatives_structure": signal.derivatives_structure,
                },
            },
        )

        logger.info(
            "RPM prediction generated",
            extra={
                "extra_fields": {
                    "asset": signal.asset,
                    "rpm_score": rpm_score,
                    "direction": dir_pred,
                    "confidence": confidence,
                }
            },
        )

        return prediction

    def batch_predict(
        self, signals: list[RPMSignal]
    ) -> list[RPMPrediction]:
        """Generate predictions for multiple signals.

        Args:
            signals: List of RPMSignal.

        Returns:
            List of RPMPrediction (same order).
        """
        return [self.predict(sig) for sig in signals]

    def set_train_period(self, start: datetime, end: datetime) -> None:
        """Set train period for provenance tracking.

        Args:
            start: Train period start (UTC).
            end: Train period end (UTC).
        """
        self.train_period = (start, end)

    def set_feature_hash(self, feature_hash: str) -> None:
        """Set feature set hash for reproducibility.

        Args:
            feature_hash: Hash of feature computation (e.g., SHA256).
        """
        self.feature_set_hash = feature_hash
