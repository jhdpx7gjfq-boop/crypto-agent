"""Layer 6 — RCM/RPM Engine.

Rotation Confirmation Model / Rotation Prediction Model.
5 component analyzers + integration.
Detects capital flow confirmation of Layer 5 signals.
"""

from .rcm_engine import RCMEngine, RCMSignal, RCMDecision
from .capital_flow_tracker import (
    CapitalFlowTracker,
    CapitalFlowAnalysis,
    WhaleAccumulation,
    ExchangeFlowMetrics,
    SmartMoneySignal,
)
from .relative_strength import (
    RelativeStrengthAnalyzer,
    RelativeStrengthAnalysis,
    MomentumMetrics,
    OutperformanceAnalysis,
)
from .narrative_acceleration import (
    NarrativeAccelerationEngine,
    NarrativeAccelerationAnalysis,
    NARMAcceleration,
    SocialMomentum,
    FundingRateStructure,
)
from .fundamental_analyzer import (
    FundamentalAnalyzer,
    FundamentalAnalysis,
    OnChainMetrics,
    TokenUnlockRisk,
)
from .derivatives_analyzer import (
    DerivativesAnalyzer,
    DerivativesAnalysis,
    FundingRateMetrics,
    OpenInterestAnalysis,
)

__all__ = [
    "RCMEngine",
    "RCMSignal",
    "RCMDecision",
    "CapitalFlowTracker",
    "CapitalFlowAnalysis",
    "RelativeStrengthAnalyzer",
    "RelativeStrengthAnalysis",
    "NarrativeAccelerationEngine",
    "NarrativeAccelerationAnalysis",
    "FundamentalAnalyzer",
    "FundamentalAnalysis",
    "DerivativesAnalyzer",
    "DerivativesAnalysis",
]
