"""Revival Radar Pipeline (RRP) contracts for dead token renaissance detection."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RRPSnapshot(BaseModel):
    """Point-in-time snapshot of token revival metrics."""

    timestamp: datetime = Field(..., description="Snapshot timestamp (UTC)")
    asset_id: str = Field(..., description="Asset identifier")
    dormancy_days: int = Field(..., ge=0, description="Days since last activity spike")
    price_change_30d: float = Field(..., description="30-day price change (%)")
    volume_24h: float = Field(..., ge=0, description="24h trading volume")
    volume_ma_90: float = Field(..., ge=0, description="90-day average volume")
    holders_count: int = Field(..., ge=0, description="Active holders")
    holders_growth_30d: float = Field(..., description="Holders growth 30d (%)")
    social_mentions: int = Field(..., ge=0, description="Social mentions count")
    social_growth_30d: float = Field(..., description="Social mentions growth (%)")
    whale_accumulation: float = Field(..., ge=0, le=1, description="Whale buying intensity")
    lookback_days: int = Field(default=60, ge=1, description="Lookback window")

    model_config = ConfigDict(use_enum_values=True)


@dataclass
class RRPMetrics:
    """Revival radar metrics."""

    dormancy_score: float  # [0, 1]: How dormant (1 = most dormant)
    activation_signal: float  # [0, 1]: Signs of awakening
    fundamental_shift: float  # [0, 1]: Growth in users/holders
    social_momentum: float  # [0, 1]: Social attention increase
    whale_signal: float  # [0, 1]: Large holder accumulation
    recovery_probability: float  # [0, 1]: Probability of sustained revival


@dataclass
class RRPVerdict:
    """Revival Radar Pipeline verdict."""

    timestamp: datetime
    asset_id: str
    dormancy_days: int
    revival_score: float  # [0, 1]: Overall revival potential
    metrics: RRPMetrics
    revival_stage: Literal["DEAD", "STIRRING", "AWAKENING", "REVIVING"]
    confidence: float  # [0, 1]
    reasoning: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
