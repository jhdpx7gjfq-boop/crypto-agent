"""Market Regime Engine contracts and base models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RegimeSignal(BaseModel):
    """Input signal for market regime detection."""

    timestamp: datetime = Field(..., description="Observation timestamp (UTC)")
    dxy: float = Field(..., ge=0, description="US Dollar Index")
    us10y: float = Field(..., ge=0, description="10-year Treasury yield (%)")
    cpi_yoy: float = Field(..., description="CPI year-over-year change (%)")
    m2_yoy: float = Field(..., description="M2 money supply YoY change (%)")
    funding_rate: float = Field(..., description="Crypto perpetual funding rate (%)")
    open_interest: float = Field(..., ge=0, description="Crypto OI (normalized 0-1)")
    btc_price: float = Field(..., ge=0, description="Bitcoin price (USD)")
    lookback_days: int = Field(default=60, ge=1, description="Lookback window for trend")

    model_config = ConfigDict(use_enum_values=True)


@dataclass
class RegimeScores:
    """Individual regime indicator scores."""

    btc_trend: float  # [-1, 1]: trend direction
    dxy_strength: float  # [0, 1]: dollar strength (risk-off)
    rates_regime: float  # [0, 1]: high rates (tightening)
    liquidity_regime: float  # [0, 1]: low liquidity (contraction)
    crypto_momentum: float  # [0, 1]: crypto momentum (risk-on)
    inflation_pressure: float  # [0, 1]: inflation hot (risk-off)


@dataclass
class RegimeContext:
    """Current market regime context."""

    timestamp: datetime
    regime: Literal["RISK_ON", "RISK_OFF", "TRANSITIONAL"]
    regime_score: float  # [-1, 1]: negative = risk-off, positive = risk-on
    confidence: float  # [0, 1]: how confident is the regime call
    scores: RegimeScores
    indicators: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
