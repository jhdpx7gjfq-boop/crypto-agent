"""
Multi-Timeframe Confirmation Engine (Phase 3 Component 2)
Version: 1.0.0

Validates BCE signals across multiple timeframes:
- 1d (Daily): Foundation signal
- 4h (4-hour): Confirmation layer
- 1h (1-hour): Entry timing validation

Logic:
  IF (1d_bce >= 5/6) THEN
    IF (4h_bce >= 4/6) AND (4h_aligns_1d) THEN
      IF (1h_has_entry_structure) AND (1h_momentum_ok) THEN
        SIGNAL_VALID with confidence
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd
import numpy as np

from src.core.models import OHLCV, WyckoffSignal
from src.layers.layer3_wyckoff.wyckoff_v2 import WyckoffBCEv2

logger = logging.getLogger(__name__)

VERSION = "1.0.0"


class TimeframeAlignment(str, Enum):
    """Timeframe alignment status."""
    ALIGNED = "aligned"
    CONFLICTING = "conflicting"
    UNCLEAR = "unclear"


@dataclass
class TimeframeScore:
    """BCE score for a single timeframe."""

    timeframe: str  # "1d", "4h", "1h"
    bce_score: float  # 0-1
    components: Dict[str, float] = field(default_factory=dict)
    valid: bool = False
    confidence: int = 0
    trend: str = "unknown"  # "up", "down", "sideways"
    momentum: float = 0.0  # -1 to +1


@dataclass
class MultiTimeframeSignal:
    """Multi-timeframe confirmation result."""

    asset: str
    timestamp: int

    # Individual timeframe scores
    timeframe_1d: TimeframeScore
    timeframe_4h: Optional[TimeframeScore] = None
    timeframe_1h: Optional[TimeframeScore] = None

    # Confirmation results
    alignment_1d_4h: TimeframeAlignment = TimeframeAlignment.UNCLEAR
    alignment_4h_1h: TimeframeAlignment = TimeframeAlignment.UNCLEAR

    # Final signal
    is_valid: bool = False
    final_confidence: int = 0  # 0-100
    entry_ready: bool = False  # 1h entry structure ready

    # Reasoning
    rejection_reason: str = ""
    strength_factors: List[str] = field(default_factory=list)


class MultiTimeframeConfirmation:
    """
    Validates BCE signals across 1d, 4h, 1h timeframes.

    Requirements for valid signal:
    1. 1d: BCE >= 5/6 (strong foundation)
    2. 4h: BCE >= 4/6 (confirmation required)
    3. 4h trend aligns with 1d
    4. 1h: Valid entry structure present
    5. 1h: Momentum not oversold (RSI > 30 preferred)

    Confidence = weighted average of timeframes
      1d: 50% weight (foundation)
      4h: 30% weight (confirmation)
      1h: 20% weight (entry timing)
    """

    def __init__(self):
        self.bce_v2 = WyckoffBCEv2()
        self.trend_threshold_rsi = 40  # RSI above this = uptrend bias
        self.oversold_threshold = 30  # RSI below this = oversold

    def confirm_signal(
        self,
        asset: str,
        ohlcv_1d: List[OHLCV],
        ohlcv_4h: Optional[List[OHLCV]] = None,
        ohlcv_1h: Optional[List[OHLCV]] = None,
    ) -> MultiTimeframeSignal:
        """
        Validate BCE signal across multiple timeframes.

        Args:
            asset: Symbol (e.g., "BTC")
            ohlcv_1d: Daily candles (required, minimum 60)
            ohlcv_4h: 4-hour candles (optional, but recommended)
            ohlcv_1h: 1-hour candles (optional, for entry timing)

        Returns:
            MultiTimeframeSignal with validation results
        """
        if not ohlcv_1d or len(ohlcv_1d) < 60:
            logger.error(f"{asset}: Insufficient 1d data ({len(ohlcv_1d) if ohlcv_1d else 0} candles)")
            return self._create_invalid_signal(asset, ohlcv_1d, "Insufficient 1d data")

        timestamp = ohlcv_1d[-1].timestamp

        # Step 1: Score 1d (foundation)
        logger.info(f"{asset}: Analyzing 1d foundation...")
        signal_1d = self.bce_v2.analyze_single_timeframe(asset, ohlcv_1d, "1d")
        score_1d = self._convert_to_timeframe_score(signal_1d, "1d", ohlcv_1d)

        # Gate 1: 1d must be >= 5/6
        if not score_1d.valid or score_1d.bce_score < (5.0 / 6.0):
            reason = f"1d BCE insufficient: {score_1d.bce_score:.3f} < 0.833"
            logger.warning(f"{asset}: {reason}")
            return self._create_invalid_signal_with_1d(asset, timestamp, score_1d, reason)

        logger.info(f"{asset}: ✓ 1d foundation strong ({score_1d.bce_score:.3f}/1.0)")

        # Step 2: Score 4h (confirmation)
        score_4h = None
        alignment_1d_4h = TimeframeAlignment.UNCLEAR

        if ohlcv_4h and len(ohlcv_4h) >= 60:
            logger.info(f"{asset}: Analyzing 4h confirmation...")
            signal_4h = self.bce_v2.analyze_single_timeframe(asset, ohlcv_4h, "4h")
            score_4h = self._convert_to_timeframe_score(signal_4h, "4h", ohlcv_4h)

            # Gate 2: 4h must be >= 4/6
            if score_4h.bce_score < (4.0 / 6.0):
                reason = f"4h BCE insufficient: {score_4h.bce_score:.3f} < 0.667"
                logger.warning(f"{asset}: {reason}")
                return self._create_invalid_signal_with_timeframes(
                    asset, timestamp, score_1d, score_4h, score_1h=None, rejection_reason=reason
                )

            # Gate 3: 4h trend must align with 1d
            alignment_1d_4h = self._check_timeframe_alignment(score_1d, score_4h)
            if alignment_1d_4h == TimeframeAlignment.CONFLICTING:
                reason = f"4h trend conflicts with 1d ({score_1d.trend} vs {score_4h.trend})"
                logger.warning(f"{asset}: {reason}")
                return self._create_invalid_signal_with_timeframes(
                    asset, timestamp, score_1d, score_4h, score_1h=None, rejection_reason=reason
                )

            logger.info(
                f"{asset}: ✓ 4h confirmation valid ({score_4h.bce_score:.3f}/1.0, "
                f"alignment={alignment_1d_4h})"
            )
        else:
            logger.warning(f"{asset}: 4h data insufficient, using 1d only")
            # 4h not available - less confidence but still valid if 1d is strong

        # Step 3: Score 1h (entry timing)
        score_1h = None
        entry_ready = False
        alignment_4h_1h = TimeframeAlignment.UNCLEAR

        if ohlcv_1h and len(ohlcv_1h) >= 20:
            logger.info(f"{asset}: Analyzing 1h entry structure...")
            signal_1h = self.bce_v2.analyze_single_timeframe(asset, ohlcv_1h, "1h")
            score_1h = self._convert_to_timeframe_score(signal_1h, "1h", ohlcv_1h)

            # Entry readiness: 1h has valid structure + not oversold
            entry_ready = score_1h.valid and score_1h.momentum >= -0.3

            if score_4h:
                alignment_4h_1h = self._check_timeframe_alignment(score_4h, score_1h)

            logger.info(
                f"{asset}: 1h status - entry_ready={entry_ready}, "
                f"momentum={score_1h.momentum:.2f}"
            )
        else:
            logger.warning(f"{asset}: 1h data insufficient, entry timing not validated")
            # 1h not critical for signal validity, but improves confidence

        # Step 4: Calculate final confidence and validity
        is_valid = score_1d.valid and (score_4h is None or score_4h.valid)
        final_confidence = self._calculate_final_confidence(score_1d, score_4h, score_1h)

        strength_factors = []
        if score_1d.bce_score >= 0.9:
            strength_factors.append("very_strong_1d")
        if score_4h and score_4h.bce_score >= 0.9:
            strength_factors.append("very_strong_4h")
        if entry_ready:
            strength_factors.append("entry_ready")
        if alignment_1d_4h == TimeframeAlignment.ALIGNED and alignment_4h_1h == TimeframeAlignment.ALIGNED:
            strength_factors.append("all_aligned")

        # Build result
        result = MultiTimeframeSignal(
            asset=asset,
            timestamp=timestamp,
            timeframe_1d=score_1d,
            timeframe_4h=score_4h,
            timeframe_1h=score_1h,
            alignment_1d_4h=alignment_1d_4h,
            alignment_4h_1h=alignment_4h_1h,
            is_valid=is_valid,
            final_confidence=final_confidence,
            entry_ready=entry_ready,
            strength_factors=strength_factors,
        )

        logger.info(
            f"{asset}: ✓ Signal valid={is_valid}, confidence={final_confidence}%, "
            f"entry_ready={entry_ready}"
        )

        return result

    def _convert_to_timeframe_score(
        self,
        signal: WyckoffSignal,
        timeframe: str,
        ohlcv: List[OHLCV],
    ) -> TimeframeScore:
        """Convert WyckoffSignal to TimeframeScore with trend/momentum analysis."""
        components = {
            "wyckoff_structure": signal.wyckoff_structure,
            "volume_analysis": signal.volume_analysis,
            "selling_exhaustion": signal.selling_exhaustion,
            "smart_money_accumulation": signal.smart_money_accumulation,
            "market_structure": signal.market_structure,
            "momentum_confirmation": signal.momentum_confirmation,
        }

        # Analyze trend from recent candles
        trend = self._analyze_trend(ohlcv[-20:])

        # Calculate momentum (-1 to +1)
        momentum = self._calculate_momentum(ohlcv[-20:])

        # Confidence based on component consistency
        confidence = self._calculate_confidence(components)

        return TimeframeScore(
            timeframe=timeframe,
            bce_score=signal.bce_score,
            components=components,
            valid=signal.valid,
            confidence=confidence,
            trend=trend,
            momentum=momentum,
        )

    def _analyze_trend(self, recent_ohlcv: List[OHLCV]) -> str:
        """Analyze trend from recent candles (up/down/sideways)."""
        if not recent_ohlcv or len(recent_ohlcv) < 5:
            return "unknown"

        closes = [c.close for c in recent_ohlcv]

        # Simple trend: compare recent close to 5-candle average
        recent_close = closes[-1]
        avg_5 = np.mean(closes[-5:])

        if recent_close > avg_5 * 1.02:
            return "up"
        elif recent_close < avg_5 * 0.98:
            return "down"
        else:
            return "sideways"

    def _calculate_momentum(self, recent_ohlcv: List[OHLCV]) -> float:
        """
        Calculate momentum (-1 to +1).

        Returns:
          +1.0: Strong upward momentum
           0.0: Neutral
          -1.0: Strong downward momentum
        """
        if not recent_ohlcv or len(recent_ohlcv) < 14:
            return 0.0

        closes = np.array([c.close for c in recent_ohlcv])

        # RSI-based momentum
        deltas = np.diff(closes)
        gains = deltas[deltas > 0].sum() / 14 if len(deltas[deltas > 0]) > 0 else 0
        losses = abs(deltas[deltas < 0].sum()) / 14 if len(deltas[deltas < 0]) > 0 else 0

        if losses > 0:
            rs = gains / losses
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 100 if gains > 0 else 50

        # Convert RSI (0-100) to momentum (-1 to +1)
        # RSI 50 = 0 momentum
        # RSI 100 = +1 momentum (very overbought)
        # RSI 0 = -1 momentum (very oversold)
        momentum = (rsi - 50) / 50

        return max(-1.0, min(1.0, momentum))

    def _calculate_confidence(self, components: Dict[str, float]) -> int:
        """Calculate confidence (0-100) based on component consistency."""
        scores = list(components.values())

        # Base confidence on average score
        avg_score = np.mean(scores)
        base_confidence = avg_score * 100

        # Consistency bonus (low std dev = high consistency)
        std_dev = np.std(scores)
        consistency_bonus = max(0, 15 - (std_dev * 50))

        confidence = int(base_confidence + consistency_bonus)
        return max(0, min(100, confidence))

    def _check_timeframe_alignment(
        self,
        timeframe_a: TimeframeScore,
        timeframe_b: TimeframeScore,
    ) -> TimeframeAlignment:
        """
        Check if two timeframes align (same trend direction).

        Returns: ALIGNED, CONFLICTING, or UNCLEAR
        """
        if timeframe_a.trend == "unknown" or timeframe_b.trend == "unknown":
            return TimeframeAlignment.UNCLEAR

        # Same trend = aligned
        if timeframe_a.trend == timeframe_b.trend:
            return TimeframeAlignment.ALIGNED

        # Opposite trends = conflicting (unless one is sideways)
        if timeframe_a.trend == "sideways" or timeframe_b.trend == "sideways":
            return TimeframeAlignment.UNCLEAR

        return TimeframeAlignment.CONFLICTING

    def _calculate_final_confidence(
        self,
        score_1d: TimeframeScore,
        score_4h: Optional[TimeframeScore],
        score_1h: Optional[TimeframeScore],
    ) -> int:
        """
        Calculate final confidence with timeframe weighting:
        - 1d: 50% (foundation)
        - 4h: 30% (confirmation)
        - 1h: 20% (entry timing)
        """
        total_confidence = score_1d.confidence * 0.50

        if score_4h:
            total_confidence += score_4h.confidence * 0.30

        if score_1h:
            total_confidence += score_1h.confidence * 0.20

        return int(total_confidence)

    def _create_invalid_signal(
        self,
        asset: str,
        ohlcv_1d: List[OHLCV],
        reason: str,
    ) -> MultiTimeframeSignal:
        """Create invalid signal (empty 1d, no confirmation)."""
        timestamp = ohlcv_1d[-1].timestamp if ohlcv_1d else 0
        empty_score = TimeframeScore(
            timeframe="1d",
            bce_score=0.0,
            valid=False,
            confidence=0,
        )
        return MultiTimeframeSignal(
            asset=asset,
            timestamp=timestamp,
            timeframe_1d=empty_score,
            is_valid=False,
            final_confidence=0,
            rejection_reason=reason,
        )

    def _create_invalid_signal_with_1d(
        self,
        asset: str,
        timestamp: int,
        score_1d: TimeframeScore,
        reason: str,
    ) -> MultiTimeframeSignal:
        """Create invalid signal with 1d score."""
        return MultiTimeframeSignal(
            asset=asset,
            timestamp=timestamp,
            timeframe_1d=score_1d,
            is_valid=False,
            final_confidence=score_1d.confidence,
            rejection_reason=reason,
        )

    def _create_invalid_signal_with_timeframes(
        self,
        asset: str,
        timestamp: int,
        score_1d: TimeframeScore,
        score_4h: TimeframeScore,
        score_1h: Optional[TimeframeScore],
        rejection_reason: str,
    ) -> MultiTimeframeSignal:
        """Create invalid signal with all timeframe scores."""
        final_confidence = self._calculate_final_confidence(score_1d, score_4h, score_1h)
        return MultiTimeframeSignal(
            asset=asset,
            timestamp=timestamp,
            timeframe_1d=score_1d,
            timeframe_4h=score_4h,
            timeframe_1h=score_1h,
            is_valid=False,
            final_confidence=final_confidence,
            rejection_reason=rejection_reason,
        )

    def format_confirmation_report(self, signal: MultiTimeframeSignal) -> str:
        """Generate formatted confirmation report."""
        report = f"""
{'='*70}
MULTI-TIMEFRAME CONFIRMATION REPORT
{'='*70}

Asset: {signal.asset}
Status: {'✓ VALID' if signal.is_valid else '✗ INVALID'}
Final Confidence: {signal.final_confidence}%
Entry Ready: {signal.entry_ready}

1D (Foundation):
  BCE Score: {signal.timeframe_1d.bce_score:.3f}/1.0 ({'PASS' if signal.timeframe_1d.valid else 'FAIL'})
  Confidence: {signal.timeframe_1d.confidence}%
  Trend: {signal.timeframe_1d.trend}
  Momentum: {signal.timeframe_1d.momentum:+.2f}

"""
        if signal.timeframe_4h:
            report += f"""4H (Confirmation):
  BCE Score: {signal.timeframe_4h.bce_score:.3f}/1.0 ({'PASS' if signal.timeframe_4h.valid else 'FAIL'})
  Confidence: {signal.timeframe_4h.confidence}%
  Trend: {signal.timeframe_4h.trend}
  Alignment with 1D: {signal.alignment_1d_4h}

"""

        if signal.timeframe_1h:
            report += f"""1H (Entry Timing):
  BCE Score: {signal.timeframe_1h.bce_score:.3f}/1.0
  Confidence: {signal.timeframe_1h.confidence}%
  Momentum: {signal.timeframe_1h.momentum:+.2f}
  Entry Ready: {signal.entry_ready}
  Alignment with 4H: {signal.alignment_4h_1h}

"""

        if signal.rejection_reason:
            report += f"Rejection Reason: {signal.rejection_reason}\n"

        if signal.strength_factors:
            report += f"Strength Factors: {', '.join(signal.strength_factors)}\n"

        report += f"\n{'='*70}\n"
        return report
