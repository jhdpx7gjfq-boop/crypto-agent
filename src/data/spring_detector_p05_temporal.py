"""Spring Detector P0.5 — Temporal Causality Refactored

ARCHITECTURE TEMPORELLE EXPLICITE (pas d'heuristiques)

Principe:
  T0 ──────── T_range ─── T_sweep_start ─── T_sweep_end ─── T_reclaim ─── T_now
       RANGE      |            SWEEP              |           CONFIRMATION
      (observé)   |         (événement)           |          (événement)
                  └─ JAMAIS contaminer range ────┘

Détection:
  1. Trouver le plus récent sweep (première violation du support)
  2. Définir range_end = timestamp du premier candle avec low < support
  3. Calculer range uniquement sur [oldest_in_lookback : range_end]
  4. Chercher reclaim uniquement après range_end

Avantage:
  - Pas d'heuristique empirique
  - Séparation temporelle stricte
  - Pas de contamination possible
  - PIT naturellement
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List
from pydantic import BaseModel, field_validator


class SpringDetectorError(Exception):
    pass


class DataQualityError(SpringDetectorError):
    pass


class SpringDetectorOutput(BaseModel):
    """Machine-readable output."""
    symbol: str
    timestamp: datetime
    state: str
    evidence: Dict[str, Any]
    signal_timestamp: Optional[datetime] = None


class TemporalRangeDetector:
    """
    Détecte une range sans contamination temporelle.

    Stratégie:
      1. Identifier le premier candle où low < support_candidate
      2. Cet instant marque T_range_end
      3. Calculer range en utilisant SEULEMENT les données avant T_range_end
    """

    def __init__(self, lookback: int = 30, min_width: float = 2.0, max_width: float = 25.0):
        self.lookback = lookback
        self.min_width = min_width
        self.max_width = max_width

    def find_range_end_idx(self, df: pd.DataFrame, start_idx: int = 0) -> int:
        """
        Trouve l'index du premier candle avec violation majeure de support.

        Stratégie temporelle:
          1. Récent lookback: identifier la "plage consolidée" (stats sur TOUS les N)
          2. Chercher le premier breakdown en remontant d'avant vers maintenant
          3. Si trouvé: range_end = position du breakdown
          4. Si non trouvé: range_end = now (consolidation stable)

        Returns:
            Index du dernier candle "avant la violation", ou len(df)-1 si pas de violation
        """
        if len(df) < self.lookback:
            return len(df) - 1

        # Prendre les derniers lookback candles
        recent = df.tail(self.lookback).copy()
        recent_idx_start = len(df) - self.lookback

        # Support de la consolidation = min des lows RÉCENTS
        support = recent["low"].min()

        # Chercher violation majeure (>1%) en remontant depuis le début du lookback
        violation_threshold = support * 0.99

        # Forward scan: trouver PREMIER breakdown
        first_breakdown_idx = None
        for i in range(len(recent)):
            if recent["low"].iloc[i] < violation_threshold:
                # Première violation trouvée
                first_breakdown_idx = i
                break

        if first_breakdown_idx is None:
            # Pas de violation - range stable jusqu'à maintenant
            return len(df) - 1

        # Trouvé une violation. Range finit juste AVANT cette violation.
        range_end_idx = recent_idx_start + first_breakdown_idx - 1
        return max(range_end_idx, self.lookback // 2)  # Au moins lookback/2

    def detect(self, df: pd.DataFrame) -> Tuple[Optional[float], Optional[float], Optional[float], bool, int]:
        """
        Détecte range sans contamination.

        Returns:
            (range_high, range_low, width_pct, is_valid, range_end_idx)
        """
        if len(df) < self.lookback:
            return None, None, None, False, len(df) - 1

        if df["high"].isna().any() or df["low"].isna().any():
            raise DataQualityError("NaN in high/low")

        # Trouver où la range se termine (avant le sweep)
        range_end_idx = self.find_range_end_idx(df)

        # Calculer range UNIQUEMENT jusqu'à range_end
        range_data = df.iloc[range_end_idx - self.lookback + 1:range_end_idx + 1]

        if len(range_data) < self.lookback // 2:
            return None, None, None, False, range_end_idx

        range_high = range_data["high"].max()
        range_low = range_data["low"].min()

        if range_low <= 0:
            return None, None, None, False, range_end_idx

        width_pct = (range_high - range_low) / range_low * 100
        is_valid = self.min_width <= width_pct <= self.max_width

        return range_high, range_low, width_pct, is_valid, range_end_idx


class TemporalSweepDetector:
    """
    Détecte sweep APRÈS la range.

    Cherche le premier candle où low < range_low,
    uniquement dans la portion après T_range_end.
    """

    def detect(self,
               df: pd.DataFrame,
               range_low: float,
               range_end_idx: int,
               lookback: int = 30) -> Tuple[Optional[int], Optional[float], Optional[float], Optional[int]]:
        """
        Détecte sweep après range_end.

        Returns:
            (sweep_idx, sweep_low, sweep_depth_pct, sweep_candles)
        """
        if range_low is None:
            return None, None, None, None

        # Chercher APRÈS range_end
        search_start = range_end_idx + 1
        if search_start >= len(df):
            return None, None, None, None

        search_data = df.iloc[search_start:]

        # Trouver le premier candle où low < range_low
        violation_idx = None
        for i, (idx, row) in enumerate(search_data.iterrows()):
            if row["low"] < range_low:
                violation_idx = search_start + i
                break

        if violation_idx is None:
            return None, None, None, None

        # Mesurer la profondeur du sweep
        sweep_section = df.iloc[violation_idx:]
        sweep_low = sweep_section["low"].min()
        sweep_depth_pct = (range_low - sweep_low) / range_low * 100
        sweep_candles = len(df) - violation_idx

        return violation_idx, sweep_low, sweep_depth_pct, sweep_candles


class TemporalReclaimDetector:
    """
    Détecte reclaim APRÈS le sweep.

    Cherche un close > range_low dans la fenêtre [sweep_start, sweep_start + window].
    """

    def detect(self,
               df: pd.DataFrame,
               sweep_start_idx: int,
               range_low: float,
               window_candles: int = 10) -> Tuple[Optional[int], Optional[datetime], Optional[float], Optional[int]]:
        """
        Détecte reclaim dans la fenêtre après le sweep.

        Returns:
            (reclaim_idx, reclaim_timestamp, reclaim_close, candles_to_reclaim)
        """
        if sweep_start_idx is None or range_low is None:
            return None, None, None, None

        search_end = min(sweep_start_idx + window_candles, len(df))
        search_data = df.iloc[sweep_start_idx:search_end]

        for i, (idx, row) in enumerate(search_data.iterrows()):
            if row["close"] > range_low:
                candles_elapsed = i
                return (
                    sweep_start_idx + i,
                    idx,
                    float(row["close"]),
                    candles_elapsed
                )

        return None, None, None, None


class SpringStateMachine:
    """
    État machine pour Spring Detector (architecture temporelle).

    Logique stricte, pas d'heuristiques.
    """

    def __init__(self, reclaim_window_candles: int = 10):
        self._range_detector = TemporalRangeDetector()
        self._sweep_detector = TemporalSweepDetector()
        self._reclaim_detector = TemporalReclaimDetector()
        self.reclaim_window_candles = reclaim_window_candles

    def classify(self, symbol: str, df: pd.DataFrame) -> Tuple[str, Dict[str, Any], Optional[datetime]]:
        """
        Classifie en 5 états selon architecture temporelle stricte.

        Pas de contamination, pas d'heuristique.
        """
        if len(df) < 30:
            return "NO_SPRING", {"reason": "insufficient_data"}, None

        current_close = df["close"].iloc[-1]

        # STEP 1: Détecter la range (avant contamination)
        range_high, range_low, range_width, range_valid, range_end_idx = (
            self._range_detector.detect(df)
        )

        if not range_valid:
            return "NO_SPRING", {"reason": "no_identifiable_range"}, None

        # STEP 2: Prix au-dessus de la range?
        if current_close > range_high:
            return "NO_SPRING", {"reason": "price_above_range", "current_close": current_close}, None

        # STEP 3: Détecter sweep APRÈS range_end
        sweep_idx, sweep_low, sweep_depth, sweep_candles = (
            self._sweep_detector.detect(df, range_low, range_end_idx)
        )

        if sweep_idx is None:
            # Pas de sweep, juste une range
            return "RANGE", {
                "range_high": range_high,
                "range_low": range_low,
                "range_width": range_width,
            }, None

        # STEP 4: Détecter reclaim APRÈS sweep
        reclaim_idx, reclaim_ts, reclaim_close, candles_to_reclaim = (
            self._reclaim_detector.detect(df, sweep_idx, range_low, self.reclaim_window_candles)
        )

        if reclaim_idx is not None:
            # Sweep + Reclaim → SPRING_CANDIDATE
            recovery_pct = (reclaim_close - sweep_low) / sweep_low * 100 if sweep_low > 0 else 0
            return "SPRING_CANDIDATE", {
                "range_high": range_high,
                "range_low": range_low,
                "range_width": range_width,
                "sweep_low": sweep_low,
                "sweep_depth": sweep_depth,
                "recovery_pct": recovery_pct,
                "reclaim_close": reclaim_close,
                "candles_to_reclaim": candles_to_reclaim,
            }, reclaim_ts

        # STEP 5: Reclaim window fermée sans reclaim?
        if sweep_idx + self.reclaim_window_candles < len(df):
            # Fenêtre fermée
            sweep_window = df.iloc[sweep_idx:sweep_idx + self.reclaim_window_candles]
            post_window = df.iloc[sweep_idx + self.reclaim_window_candles:]

            sweep_low_in_window = sweep_window["low"].min()
            new_low_after_window = post_window["low"].min()

            if new_low_after_window < sweep_low_in_window:
                # Continuation de la faiblesse → BREAKDOWN
                return "BREAKDOWN", {
                    "sweep_low": sweep_low,
                    "breakdown_low": new_low_after_window,
                    "reason": "continued_weakness"
                }, None

        # Sinon: en attente du reclaim
        recovery_pct = (current_close - sweep_low) / sweep_low * 100 if sweep_low > 0 else 0
        return "SWEEP", {
            "range_low": range_low,
            "sweep_low": sweep_low,
            "sweep_depth": sweep_depth,
            "recovery_pct": recovery_pct,
            "candles_since_sweep": sweep_candles,
            "reclaim_window_remaining": max(0, self.reclaim_window_candles - sweep_candles),
        }, None


class SpringDetector:
    """Public API pour Spring Detector P0.5."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.machine = SpringStateMachine(
            reclaim_window_candles=config.get("reclaim_window_candles", 10)
        )

    def classify(self, symbol: str, df: pd.DataFrame) -> SpringDetectorOutput:
        """Classify une série temporelle."""
        state, evidence, signal_ts = self.machine.classify(symbol, df)

        return SpringDetectorOutput(
            symbol=symbol,
            timestamp=df.index[-1] if len(df) > 0 else datetime.now(),
            state=state,
            evidence=evidence,
            signal_timestamp=signal_ts,
        )
