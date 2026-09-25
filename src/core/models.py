"""Core data models for IGWT-PF26."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class RegimeType(str, Enum):
    """Market regime classification."""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    TRANSITION = "transition"


class SignalType(str, Enum):
    """Signal types from decision pipeline."""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"
    HOLD = "hold"


@dataclass
class OHLCV:
    """Open-High-Low-Close-Volume candlestick."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self):
        if not (self.low <= self.high):
            raise ValueError(f"Low ({self.low}) must be <= High ({self.high})")
        if not (self.low <= self.open <= self.high and self.low <= self.close <= self.high):
            raise ValueError("Open/Close must be between Low and High")
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")


@dataclass
class MarketRegime:
    """Market regime snapshot."""
    timestamp: datetime
    regime: RegimeType
    btc_dominance: float
    funding_rate: float
    open_interest_change: float
    dxy: Optional[float] = None
    us10y: Optional[float] = None
    macro_score: float = 0.0

    def __post_init__(self):
        if not (0 <= self.btc_dominance <= 100):
            raise ValueError(f"BTC dominance must be 0-100, got {self.btc_dominance}")


@dataclass
class WyckoffSignal:
    """Bottom Confirmation Engine output."""
    timestamp: datetime
    asset: str
    bce_score: float  # 0-6
    wyckoff_structure: float
    volume_analysis: float
    selling_exhaustion: float
    smart_money_accumulation: float
    market_structure: float
    momentum_confirmation: float
    valid: bool = field(default_factory=lambda: False)

    def __post_init__(self):
        self.bce_score = sum([
            self.wyckoff_structure,
            self.volume_analysis,
            self.selling_exhaustion,
            self.smart_money_accumulation,
            self.market_structure,
            self.momentum_confirmation,
        ]) / 6
        self.valid = self.bce_score >= 5.0


@dataclass
class X20Opportunity:
    """X20 opportunity detection."""
    timestamp: datetime
    asset: str
    ticker: str
    fundamental_score: float  # 0-100
    narrative_score: float    # 0-100
    quantitative_score: float  # 0-100
    combined_score: float
    team_quality: str
    investors: List[str] = field(default_factory=list)
    tokenomics_risk: str = "medium"
    adoption_stage: str = "emerging"


@dataclass
class NARMSignal:
    """NARM-P+ narrative adoption scoring."""
    timestamp: datetime
    asset: str
    narrative_strength: float  # 0-100
    adoption: float           # 0-100
    capital_rotation: float   # 0-100
    fundamentals: float       # 0-100
    market_timing: float      # 0-100
    total_score: float = field(default_factory=lambda: 0.0)

    def __post_init__(self):
        self.total_score = (
            self.narrative_strength * 0.20 +
            self.adoption * 0.25 +
            self.capital_rotation * 0.25 +
            self.fundamentals * 0.20 +
            self.market_timing * 0.10
        )


@dataclass
class RCMSignal:
    """Rotation Confirmation Model output."""
    timestamp: datetime
    asset: str
    capital_flow: float         # 0-100, 25% weight
    relative_strength: float    # 0-100, 25% weight
    narrative_acceleration: float  # 0-100, 20% weight
    fundamental_confirmation: float  # 0-100, 20% weight
    derivatives_structure: float  # 0-100, 10% weight
    combined_score: float = field(default_factory=lambda: 0.0)
    valid: bool = field(default_factory=lambda: False)

    def __post_init__(self):
        self.combined_score = (
            self.capital_flow * 0.25 +
            self.relative_strength * 0.25 +
            self.narrative_acceleration * 0.20 +
            self.fundamental_confirmation * 0.20 +
            self.derivatives_structure * 0.10
        )
        self.valid = self.combined_score >= 70.0


@dataclass
class RRPSignal:
    """Revival Radar Pipeline detection."""
    timestamp: datetime
    asset: str
    revival_probability: float  # 0-100
    snapshot_health: float
    volume_signature: float
    community_activity: float
    technical_confirmation: float
    stage: str  # "dead", "awakening", "revival", "momentum"


@dataclass
class DecisionSignal:
    """Final decision signal from pipeline."""
    timestamp: datetime
    asset: str
    signal_type: SignalType
    confidence: float  # 0-100
    components: Dict[str, Any] = field(default_factory=dict)
    bce_score: Optional[float] = None
    x20_score: Optional[float] = None
    narm_score: Optional[float] = None
    rcm_score: Optional[float] = None
    rrp_score: Optional[float] = None
    regime: Optional[RegimeType] = None
    reason: str = ""
    risk_level: str = "medium"  # low, medium, high


@dataclass
class BacktestResult:
    """Backtest statistics."""
    strategy_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    avg_trade_return: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    walk_forward_passed: bool = False
    lookahead_bias_detected: bool = False
    notes: str = ""
