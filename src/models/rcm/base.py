"""Rotation Confirmation Model base classes and contracts."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RPMSignal(BaseModel):  # type: ignore[misc]
    """Input signal from rotation detection component.

    Frozen per B-004_SPEC section 2.1
    """

    timestamp: datetime = Field(..., description="Signal UTC timestamp (point-in-time)")
    asset: str = Field(..., description="Asset (BTC, ETH, etc.)")

    capital_flow: float = Field(
        ..., ge=0.0, le=1.0, description="Capital flow score [0, 1]"
    )
    relative_strength: float = Field(
        ..., ge=0.0, le=1.0, description="Relative strength score [0, 1]"
    )
    narrative_acceleration: float = Field(
        ..., ge=0.0, le=1.0, description="Narrative acceleration score [0, 1]"
    )
    fundamental_confirmation: float = Field(
        ..., ge=0.0, le=1.0, description="Fundamental confirmation score [0, 1]"
    )
    derivatives_structure: float = Field(
        ..., ge=0.0, le=1.0, description="Derivatives structure score [0, 1]"
    )

    lookahead_flag: bool = Field(
        default=False, description="Must be False (no forward-looking data)"
    )


class RPMPrediction(BaseModel):  # type: ignore[misc]
    """RPM/RCM prediction output.

    Frozen per B-004_SPEC section 2.1
    """

    timestamp: datetime = Field(
        ..., description="Prediction timestamp (must be <= observation window end)"
    )
    asset: str = Field(..., description="Asset")

    predicted_direction: Literal["LONG", "NEUTRAL", "SHORT"] = Field(
        ..., description="Predicted direction based on RPM score"
    )
    predicted_return_pct: float = Field(
        ..., description="Predicted return % (in-period, NOT annualized)"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence level [0, 1]"
    )

    rpm_score: float = Field(
        ..., ge=0.0, le=1.0, description="Aggregate RPM/RCM score [0, 1]"
    )

    provenance: dict[str, Any] = Field(
        default_factory=dict,
        description="Model version, feature hash, train period, lookback",
    )


class RPMConfig(BaseModel):  # type: ignore[misc]
    """RPM/RCM configuration (frozen per B-004_SPEC section 2.2)."""

    capital_flow_weight: float = Field(
        default=0.25, ge=0.0, le=1.0, description="Weight for capital_flow"
    )
    relative_strength_weight: float = Field(
        default=0.25, ge=0.0, le=1.0, description="Weight for relative_strength"
    )
    narrative_acceleration_weight: float = Field(
        default=0.20, ge=0.0, le=1.0, description="Weight for narrative_acceleration"
    )
    fundamental_confirmation_weight: float = Field(
        default=0.20, ge=0.0, le=1.0, description="Weight for fundamental_confirmation"
    )
    derivatives_structure_weight: float = Field(
        default=0.10, ge=0.0, le=1.0, description="Weight for derivatives_structure"
    )

    long_threshold: float = Field(
        default=0.60, ge=0.0, le=1.0, description="Threshold for LONG prediction"
    )
    neutral_threshold: float = Field(
        default=0.40, ge=0.0, le=1.0, description="Threshold for NEUTRAL prediction"
    )

    lookback_days: int = Field(
        default=60, ge=1, description="Lookback window in calendar days (frozen)"
    )

    model_version: str = Field(
        default="1.0", description="Model version (for provenance)"
    )

    def validate_weights(self) -> None:
        """Ensure weights sum to 1.0."""
        total = (
            self.capital_flow_weight
            + self.relative_strength_weight
            + self.narrative_acceleration_weight
            + self.fundamental_confirmation_weight
            + self.derivatives_structure_weight
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
