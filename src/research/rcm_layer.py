"""
Phase B-004: RCM (Rotation Confirmation Model) Layer

Confirms RPM signal with regime alignment.

RCM output: regime-weighted RPM signal ([-1, +1])
  Regime alignment weights:
  - Bull: +1.2 (trust RPM)
  - Accumulation: +0.8 (ambiguous)
  - Bear: +0.5 (hedging signal, inverse logic)
"""

import pandas as pd
import numpy as np
from typing import Tuple
from dataclasses import dataclass


@dataclass
class RCMSignal:
    """RCM signal with regime context."""
    timestamp: pd.Timestamp
    rpm_signal: float
    regime: str
    regime_alignment_factor: float
    rcm_signal: float  # regime-weighted RPM, clipped to [-1, +1]


class RCMLayer:
    """
    Rotation Confirmation Model for regime-aligned RPM.

    Regime alignment factors (frozen per B-004_SPEC.md):
    - Bull: 1.2
    - Accumulation: 0.8
    - Bear: 0.5
    """

    REGIME_ALIGNMENT = {
        'Bull': 1.2,
        'Accumulation': 0.8,
        'Bear': 0.5,
    }

    def __init__(self):
        """Initialize RCM layer."""
        pass

    def compute_signal(
        self, rpm_signals: list, regime_series: pd.Series
    ) -> list:
        """
        Compute RCM signal for entire dataset.

        Args:
            rpm_signals: List of RPMSignal objects
            regime_series: pd.Series with regime labels at each timestamp

        Returns:
            List of RCMSignal objects
        """
        results = []

        for i, rpm_sig in enumerate(rpm_signals):
            ts = rpm_sig.timestamp

            # Align timestamp to regime series
            regime = regime_series.loc[ts] if ts in regime_series.index else 'Bull'

            # Get alignment factor
            alignment_factor = self.REGIME_ALIGNMENT.get(regime, 1.0)

            # Apply regime weighting
            rcm_score = rpm_sig.rpm_signal * alignment_factor
            rcm_signal = np.clip(rcm_score, -1.0, 1.0)

            signal_obj = RCMSignal(
                timestamp=ts,
                rpm_signal=rpm_sig.rpm_signal,
                regime=regime,
                regime_alignment_factor=alignment_factor,
                rcm_signal=rcm_signal,
            )
            results.append(signal_obj)

        return results
