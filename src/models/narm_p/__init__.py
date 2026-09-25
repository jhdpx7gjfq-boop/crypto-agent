"""Layer 5: NARM-P+ — Narrative Adoption Rotation Model Plus."""

from .base import NARMComponents, NARMSignal, NARMVerdict
from .detector import NARMPEngine

__all__ = [
    "NARMComponents",
    "NARMPEngine",
    "NARMSignal",
    "NARMVerdict",
]
