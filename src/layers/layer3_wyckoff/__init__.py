"""Layer 3 — Wyckoff Intelligence & BCE.

Bottom Confirmation Engine (BCE) validates entry signals.
Combines: Wyckoff structure, volume, selling exhaustion,
smart money accumulation, market structure, momentum.

Phase 3: Walk-Forward Validation (6 rolling 6-month windows, F1 ≥ 0.55).
Phase 4: Ablation Analysis (component criticality evaluation).
"""

from .bce_engine import BottomConfirmationEngine
from .bce_analyzer import BCEAnalyzer, BCEAnalysisReport
from .walkforward_validator import WalkForwardValidator, WFVReport, WindowResult
from .ablation_analyzer import AblationAnalyzer, AblationReport, ComponentCriticality

__all__ = [
    "BottomConfirmationEngine",
    "BCEAnalyzer",
    "BCEAnalysisReport",
    "WalkForwardValidator",
    "WFVReport",
    "WindowResult",
    "AblationAnalyzer",
    "AblationReport",
    "ComponentCriticality",
]
