"""Dashboard API response models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class SignalType(str, Enum):
    """Signal types across layers."""
    BCE = "bce"
    X20 = "x20"
    RRP = "rrp"
    RCM = "rcm"
    REGIME = "regime"


class ActionType(str, Enum):
    """Recommended action."""
    ENTRY_READY = "entry_ready"
    HOLD = "hold"
    RESEARCH = "research"
    AVOID = "avoid"


class Severity(str, Enum):
    """Alert severity."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RegimeType(str, Enum):
    """Market regime."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGING = "ranging"
    VOLATILE = "volatile"


@dataclass
class SignalAlert:
    """Individual signal alert."""
    asset: str
    signal_type: SignalType
    score: float  # 0-100
    confidence: float  # 0-1
    reasoning: str
    action: ActionType
    timestamp: datetime
    severity: Severity
    next_action: str = ""


@dataclass
class MarketRegimeInfo:
    """Current market regime."""
    regime_type: RegimeType
    confidence: float  # 0-1
    expected_duration_days: int
    days_in_regime: int


@dataclass
class DashboardSummary:
    """Dashboard overview."""
    timestamp: datetime
    market_regime: MarketRegimeInfo
    top_signals: List[SignalAlert]
    critical_alerts: int
    assets_under_watch: int
    last_update: str = ""


@dataclass
class BCEComponent:
    """Individual BCE component score."""
    name: str
    score: float  # 0-1 normalized
    weight: float  # Component weight
    description: str


@dataclass
class BCEAnalysis:
    """BCE analysis for asset."""
    asset: str
    overall_score: float  # 0-6
    validity: bool  # >= 5
    confidence: float  # 0-1
    components: List[BCEComponent]
    stage: str  # accumulation|uptrend|downtrend|mixed
    reasoning: str
    entry_ready: bool
    risk_rating: str  # low|medium|high
    timestamp: datetime


@dataclass
class X20Opportunity:
    """X20 scoring result."""
    asset: str
    score: float  # 0-100
    rank: int
    fundamental_score: float  # 0-100
    narrative_score: float  # 0-100
    quantitative_score: float  # 0-100
    asymmetric_potential: float  # X multiplier
    momentum: str  # accelerating|stable|decelerating
    recommendation: str


@dataclass
class X20Report:
    """Top X20 opportunities."""
    timestamp: datetime
    opportunities: List[X20Opportunity]
    total_tracked: int


@dataclass
class RRPCandidate:
    """Revival radar candidate."""
    asset: str
    score: float  # 0-100
    confidence: float  # 0-1
    stage: str  # dormant|early_signs|emerging|confirmed
    dormancy_days: int
    acceleration_rate: float
    estimated_peak_days: Optional[int]
    momentum_direction: str  # accelerating|stable|decelerating


@dataclass
class RRPReport:
    """Revival radar pipeline results."""
    timestamp: datetime
    by_stage: Dict[str, List[RRPCandidate]]
    total_candidates: int


@dataclass
class RCMRotation:
    """Capital rotation signal."""
    asset: str
    rotation_type: str  # inflow|outflow|accumulation|distribution
    confidence: float  # 0-1
    capital_flow_strength: float  # -1 to +1
    duration_days: int
    next_trigger: str


@dataclass
class RCMReport:
    """RCM rotation signals."""
    timestamp: datetime
    active_rotations: List[RCMRotation]
    key_signals: List[str]


@dataclass
class AlertSummary:
    """Alert stream summary."""
    timestamp: datetime
    total_alerts: int
    by_severity: Dict[str, int]
    latest: List[SignalAlert]


@dataclass
class PortfolioMetric:
    """Portfolio tracking metric."""
    asset: str
    watch_status: str  # watching|research|ready|hold
    entry_price: Optional[float]
    current_observation: str
    note: str = ""


@dataclass
class PortfolioReport:
    """Portfolio tracking."""
    timestamp: datetime
    watchlist: List[PortfolioMetric]
    total_positions: int
