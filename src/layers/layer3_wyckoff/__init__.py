"""Layer 3 — Wyckoff Intelligence & BCE.

Bottom Confirmation Engine (BCE) validates entry signals.
Combines: Wyckoff structure, volume, selling exhaustion, 
smart money accumulation, market structure, momentum.

Min score: 5/6 required for entry.
"""

from .bce_engine import BottomConfirmationEngine

__all__ = ["BottomConfirmationEngine"]
