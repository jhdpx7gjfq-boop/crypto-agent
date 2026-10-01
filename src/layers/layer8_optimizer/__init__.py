"""Layer 8 — RPM X20 Optimizer Engine.

Strategy optimization with walk-forward validation.
Regime detection, exit optimization, parameter tuning.
"""

from .regime_detector import (
    RegimeType,
    MarketRegime,
    RegimeDetector,
)
from .exit_engine import (
    ExitSignal,
    DynamicExitAnalysis,
    DynamicExitEngine,
)
from .mfe_mae_analyzer import (
    TradeExcursion,
    MFEMAEAnalysis,
    MFEMAEAnalyzer,
)
from .parameter_optimizer import (
    ParameterSet,
    OptimizationResult,
    ParameterOptimizer,
)
from .walk_forward_validator import (
    WalkForwardWindow,
    WindowResults,
    WalkForwardResults,
    WalkForwardValidator,
)
from .overfit_detector import (
    OverfitMetrics,
    OverfitDetector,
)

__all__ = [
    "RegimeType",
    "MarketRegime",
    "RegimeDetector",
    "ExitSignal",
    "DynamicExitAnalysis",
    "DynamicExitEngine",
    "TradeExcursion",
    "MFEMAEAnalysis",
    "MFEMAEAnalyzer",
    "ParameterSet",
    "OptimizationResult",
    "ParameterOptimizer",
    "WalkForwardWindow",
    "WindowResults",
    "WalkForwardResults",
    "WalkForwardValidator",
    "OverfitMetrics",
    "OverfitDetector",
]
