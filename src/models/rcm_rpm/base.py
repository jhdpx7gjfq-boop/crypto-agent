"""Rotation Confirmation Model (RCM/RPM) contracts and scoring."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RCMSignal(BaseModel):
    """Input signal for Rotation Confirmation Model."""

    timestamp: datetime = Field(..., description="Observation timestamp (UTC)")
    asset_id: str = Field(..., description="Asset identifier")
    capital_flow_score: float = Field(..., ge=-1, le=1, description="Capital inflow [-1, 1]")
    relative_strength: float = Field(..., ge=0, le=1, description="Outperformance [0, 1]")
    narrative_acceleration: float = Field(..., ge=-1, le=1, description="Narrative momentum [-1, 1]")
    fundamental_confirmation: float = Field(..., ge=0, le=1, description="Fundamentals confirm [-1, 1]")
    derivative_funding: float = Field(..., description="Perpetual funding rate (%)")
    open_interest_change: float = Field(..., description="OI change from baseline (%)")
    lookback_days: int = Field(default=60, ge=1, description="Lookback window")

    model_config = ConfigDict(use_enum_values=True)


@dataclass
class RCMComponents:
    """RCM scoring components (5 weighted elements)."""

    capital_flow: float  # [0, 1]: Capital flowing into rotation
    relative_strength: float  # [0, 1]: Relative outperformance
    narrative_acceleration: float  # [0, 1]: Narrative gaining momentum
    fundamental_confirmation: float  # [0, 1]: Fundamentals support
    derivatives_structure: float  # [0, 1]: Derivatives positioning


@dataclass
class RCMVerdict:
    """RCM verdict and confidence."""

    timestamp: datetime
    asset_id: str
    rcm_score: float  # [0, 1]: Weighted composite
    components: RCMComponents
    rotation_confirmed: bool  # score >= 0.65 (threshold)
    confirmation_strength: Literal["WEAK", "MODERATE", "STRONG", "VERY_STRONG"]
    confidence: float  # [0, 1]
    reasoning: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
