"""Layer 3 — Wyckoff Intelligence & BCE.

Bottom Confirmation Engine (BCE) validates entry signals.
Combines: Wyckoff structure, volume, selling exhaustion,
smart money accumulation, market structure, momentum.

Phase 3: Walk-Forward Validation (6 rolling 6-month windows, F1 ≥ 0.55).
Phase 4: Ablation Analysis (component criticality evaluation).
Phase 5: Robustness Validation (7 market regimes, >75% pass rate).
Phase 6: Final Validation Gate (aggregate production readiness assessment).
"""

from .bce_engine import BottomConfirmationEngine
from .bce_analyzer import BCEAnalyzer, BCEAnalysisReport
from .walkforward_validator import WalkForwardValidator, WFVReport, WindowResult
from .ablation_analyzer import AblationAnalyzer, AblationReport, ComponentCriticality
from .robustness_validator import RobustnessValidator, RobustnessReport, MarketRegime
from .final_validation_gate import FinalValidationGate, FinalValidationReport, ProductionReadiness

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
    "RobustnessValidator",
    "RobustnessReport",
    "MarketRegime",
    "FinalValidationGate",
    "FinalValidationReport",
    "ProductionReadiness",
]
