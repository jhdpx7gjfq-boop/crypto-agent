"""NARM-P+ (Narrative Adoption Rotation Model Plus) contracts and scoring."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NARMSignal(BaseModel):
    """Input signal for NARM-P+ narrative analysis."""

    timestamp: datetime = Field(..., description="Observation timestamp (UTC)")
    asset_id: str = Field(..., description="Asset identifier")
    narrative_category: str = Field(..., description="Narrative sector (AI, RWA, DeFi, etc)")
    attention_score: float = Field(..., ge=0, le=100, description="Current attention level")
    attention_growth_1m: float = Field(..., description="1-month attention growth (%)")
    attention_growth_3m: float = Field(..., description="3-month attention growth (%)")
    social_volume_rank: int = Field(..., ge=1, description="Rank in social volume")
    sentiment_score: float = Field(..., ge=-100, le=100, description="Sentiment -100 to +100")
    adoption_rate: float = Field(..., description="Active users/addresses growth (% can be negative)")
    network_value: float = Field(..., ge=0, description="NVT ratio or similar metric")
    capital_inflow: float = Field(..., description="Capital inflow (%)")
    lookback_days: int = Field(default=60, ge=1, description="Lookback window")

    model_config = ConfigDict(use_enum_values=True)


@dataclass
class NARMComponents:
    """NARM-P+ scoring components (100-point system)."""

    narrative_strength: int  # [0, 25]: Narrative clarity + uniqueness
    adoption_momentum: int  # [0, 25]: Adoption acceleration + growth
    capital_rotation: int  # [0, 25]: Capital flowing into narrative
    sentiment_alignment: int  # [0, 15]: Positive sentiment + momentum
    network_effects: int  # [0, 10]: Network growth + virality


@dataclass
class NARMVerdict:
    """NARM-P+ scoring verdict."""

    timestamp: datetime
    asset_id: str
    narrative_category: str
    total_score: int  # [0, 100]
    components: NARMComponents
    percentile: float  # [0, 1]: Where this ranks vs all narratives
    rotation_signal: str  # EMERGING / ACCELERATING / MATURE / DECLINING
    confidence: float  # [0, 1]
    reasoning: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
