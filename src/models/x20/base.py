"""X20 opportunity detection contracts and scoring models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class X20Signal(BaseModel):
    """Input signal for X20 opportunity analysis."""

    timestamp: datetime = Field(..., description="Observation timestamp (UTC)")
    asset_id: str = Field(..., description="Asset identifier (symbol/address)")
    price: float = Field(..., gt=0, description="Current asset price")
    market_cap: float = Field(..., ge=0, description="Market cap (USD)")
    volume_24h: float = Field(..., ge=0, description="24h trading volume")
    volatility_30d: float = Field(..., ge=0, le=1, description="30-day volatility [0, 1]")
    rsi_14: float = Field(..., ge=0, le=100, description="RSI(14)")
    momentum_score: float = Field(..., ge=-1, le=1, description="Momentum [-1, 1]")
    adoption_growth: float = Field(default=0.0, description="Adoption growth rate (%/month)")
    narrative_relevance: float = Field(default=0.5, description="Narrative relevance [0, 1]")
    lookback_days: int = Field(default=60, ge=1, description="Lookback window")

    model_config = ConfigDict(use_enum_values=True)


@dataclass
class FundamentalScore:
    """Fundamental analysis component."""

    team_quality: float  # [0, 1]: team credibility + experience
    investor_quality: float  # [0, 1]: backers + funding rounds
    tokenomics: float  # [0, 1]: distribution, vesting, incentives
    revenue_potential: float  # [0, 1]: monetization + revenue sources
    competitive_advantage: float  # [0, 1]: differentiation + moat
    adoption_trajectory: float  # [0, 1]: growth rate + market penetration

    def composite_score(self) -> float:
        """Weighted composite fundamental score."""
        return (
            self.team_quality * 0.2
            + self.investor_quality * 0.15
            + self.tokenomics * 0.15
            + self.revenue_potential * 0.2
            + self.competitive_advantage * 0.15
            + self.adoption_trajectory * 0.15
        )


@dataclass
class NarrativeScore:
    """Narrative rotation component."""

    sector_strength: float  # [0, 1]: sector momentum + capital inflows
    narrative_rotation: float  # [0, 1]: narrative gaining attention
    attention_growth: float  # [0, 1]: social/media growth rate
    theme_relevance: float  # [0, 1]: alignment with current themes (AI, RWA, DeFi)
    adoption_catalyst: float  # [0, 1]: event-driven adoption potential

    def composite_score(self) -> float:
        """Weighted composite narrative score."""
        return (
            self.sector_strength * 0.25
            + self.narrative_rotation * 0.25
            + self.attention_growth * 0.2
            + self.theme_relevance * 0.15
            + self.adoption_catalyst * 0.15
        )


@dataclass
class QuantitativeScore:
    """Quantitative analysis component."""

    momentum: float  # [0, 1]: price momentum + RSI dynamics
    relative_strength: float  # [0, 1]: outperformance vs peers + market
    volatility_regime: float  # [0, 1]: price volatility (for alpha capture)
    liquidity: float  # [0, 1]: trading liquidity + spread
    risk_reward_ratio: float  # [0, 1]: potential upside vs downside risk

    def composite_score(self) -> float:
        """Weighted composite quantitative score."""
        return (
            self.momentum * 0.25
            + self.relative_strength * 0.25
            + self.volatility_regime * 0.15
            + self.liquidity * 0.2
            + self.risk_reward_ratio * 0.15
        )


@dataclass
class X20Score:
    """X20 composite opportunity score."""

    timestamp: datetime
    asset_id: str
    fundamental_score: float  # [0, 1]
    narrative_score: float  # [0, 1]
    quantitative_score: float  # [0, 1]
    components: dict[str, Any]
    confidence: float  # [0, 1]: overall confidence
    x20_potential: Literal["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
    reasoning: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def composite_score(self) -> float:
        """Weighted composite X20 score."""
        return (
            self.fundamental_score * 0.35
            + self.narrative_score * 0.35
            + self.quantitative_score * 0.30
        )
