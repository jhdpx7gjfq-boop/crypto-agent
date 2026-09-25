"""Wyckoff cycle detection contracts and BCE models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class WyckoffSignal(BaseModel):
    """Input signal for Wyckoff analysis."""

    timestamp: datetime = Field(..., description="Observation timestamp (UTC)")
    price: float = Field(..., gt=0, description="Current asset price")
    volume: float = Field(..., ge=0, description="Trading volume")
    high_52w: float = Field(..., gt=0, description="52-week high")
    low_52w: float = Field(..., gt=0, description="52-week low")
    price_change_7d: float = Field(..., description="7-day return (%)")
    price_change_30d: float = Field(..., description="30-day return (%)")
    volume_ma_20: float = Field(..., ge=0, description="20-period MA volume")
    rsi_14: float = Field(..., ge=0, le=100, description="RSI(14)")
    macd_signal: float = Field(..., description="MACD vs Signal (histogram)")
    lookback_days: int = Field(default=60, ge=1, description="Lookback window")

    model_config = ConfigDict(use_enum_values=True)


class WyckoffPhase(BaseModel):
    """Detected Wyckoff phase."""

    name: Literal["ACCUMULATION", "MARKUP", "DISTRIBUTION", "MARKDOWN", "UNKNOWN"]
    confidence: float = Field(..., ge=0, le=1, description="Phase confidence")
    duration_periods: int = Field(default=0, ge=0, description="Phase duration")
    price_range: tuple[float, float] = Field(..., description="(low, high)")


@dataclass
class BCE_Signal:  # noqa: N801 (BCE is a technical analysis domain abbreviation)
    """Bottom Confirmation Engine signal input."""

    timestamp: datetime
    price: float
    selling_exhaustion_score: float  # [0, 1]: how exhausted sellers are
    spring_detected: bool  # Spring = retest down after failed breakup
    sign_of_strength: bool  # SOS = retest up after spring
    volume_pattern: float  # [0, 1]: volume confirmation
    divergence_score: float  # [0, 1]: bullish divergence
    structure_quality: float  # [0, 1]: market structure health


@dataclass
class BCE_Verdict:  # noqa: N801 (BCE is a technical analysis domain abbreviation)
    """Bottom Confirmation Engine verdict."""

    score: int  # [0, 6]
    components: dict[str, int]  # Individual component scores [0, 1]
    phase: str  # ACCUMULATION, etc.
    confidence: float  # [0, 1]
    verdict: bool  # score >= 5/6
    metadata: dict[str, Any] = field(default_factory=dict)
