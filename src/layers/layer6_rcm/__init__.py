"""Layer 6 — RCM/RPM Engine.

Rotation Confirmation Model & Revival Probability Model.
Detects capital flows and sector rotations.
Walk-forward validated only.
"""

from .rcm_engine import RotationConfirmationModel

__all__ = ["RotationConfirmationModel"]
