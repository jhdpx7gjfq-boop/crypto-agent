"""Phase B Research Framework

Ablation studies, multi-factor testing, statistical validation.
"""

from .market_regime_detector import MarketRegimeDetector, Trend, VolRegime
from .baseline_predictor import BaselinePredictor
from .ablation_framework import AblationFramework, AblationMetrics
from .spring_context_predictor import SpringContextPredictor

__all__ = [
    "MarketRegimeDetector",
    "Trend",
    "VolRegime",
    "BaselinePredictor",
    "AblationFramework",
    "AblationMetrics",
    "SpringContextPredictor",
]
