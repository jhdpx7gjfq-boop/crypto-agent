"""Layer 2 — Market Regime Engine.

Detects current market context (bull, bear, sideways, transition).
Monitors macro conditions, funding rates, open interest.
"""

from .regime_engine import MarketRegimeDetector

__all__ = ["MarketRegimeDetector"]
