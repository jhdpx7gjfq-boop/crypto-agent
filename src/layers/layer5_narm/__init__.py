"""Layer 5 — NARM-P+ Engine.

Narrative Adoption Rotation Model Plus.
Scores narrative strength, adoption, capital rotation.
Detects rotation, validates capital flows, integrates with Layers 3-4.
"""

from .narm_engine import NARMEngine, NARMAnalysisReport
from .sector_rotation import SectorRotationTracker, SectorRotationSignal, SectorMetrics
from .narrative_trends import NarrativeTrendAnalyzer, NarrativeTrendReport
from .capital_flow_validator import CapitalFlowValidator, CapitalFlowValidation
from .layer5_integration import Layer5IntegrationScorer, Layer5DecisionSignal, Layer5Decision

__all__ = [
    "NARMEngine",
    "NARMAnalysisReport",
    "SectorRotationTracker",
    "SectorRotationSignal",
    "SectorMetrics",
    "NarrativeTrendAnalyzer",
    "NarrativeTrendReport",
    "CapitalFlowValidator",
    "CapitalFlowValidation",
    "Layer5IntegrationScorer",
    "Layer5DecisionSignal",
    "Layer5Decision",
]
