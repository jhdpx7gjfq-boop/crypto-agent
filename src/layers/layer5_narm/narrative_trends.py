"""
Phase 5: Narrative Trend Analyzer for NARM-P+

Analyzes adoption lifecycle and narrative strength trends:
- Adoption acceleration detection
- Narrative peak identification
- Reversal signals
- Lifecycle stage progression
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from statistics import mean, stdev

logger = logging.getLogger(__name__)


@dataclass
class TrendMetrics:
    """Trend metrics for narrative adoption."""

    asset: str
    period: str  # daily/weekly/monthly
    current_narm: float
    previous_narm: float
    narm_change_pct: float
    adoption_acceleration: float  # Second derivative (velocity of change)
    narrative_momentum: str  # accelerating/stable/decelerating
    trend_direction: str  # up/down/sideways
    volatility: float  # σ of NARM scores
    score_ma_short: float  # 5-period MA
    score_ma_long: float  # 20-period MA


@dataclass
class PeakDetection:
    """Peak identification in narrative strength."""

    asset: str
    peak_date: datetime
    peak_narm: float
    peak_period_type: str  # early_peak/mid_peak/major_peak
    days_from_peak: int
    expected_reversal_days: int  # Estimated days to reversal
    reversal_probability: float  # 0-1
    reasoning: List[str]


@dataclass
class ReversalSignal:
    """Signal for narrative reversal/decline."""

    asset: str
    reversal_detected: bool
    confidence: float  # 0-1
    reversal_type: str  # sharp/gradual
    adoption_decline_rate: float  # % per period
    narrative_weakness_signals: List[str]
    estimated_recovery: Optional[str]  # early/mid/late


@dataclass
class NarrativeTrendReport:
    """Complete narrative trend analysis."""

    asset: str
    current_stage: str  # early/mid/late/declining
    trend_metrics: TrendMetrics
    peak_detection: Optional[PeakDetection]
    reversal_signal: ReversalSignal
    lifecycle_position: float  # 0-1, position in cycle
    momentum_bars: int  # Number of consecutive up/down periods
    expected_next_move: str  # up/down/consolidation
    confidence_score: float  # 0-1
    reasoning: List[str]


class NarrativeTrendAnalyzer:
    """Analyze adoption lifecycle and narrative strength trends."""

    # Acceleration thresholds
    STRONG_ACCELERATION = 10.0  # % change in adoption
    DECELERATION = -5.0  # % decline in adoption
    PEAK_THRESHOLD = 75.0  # NARM score considered peak
    REVERSAL_ACCELERATION = -15.0  # Sharp decline detection

    def __init__(self, min_history: int = 20):
        """
        Initialize analyzer.

        Args:
            min_history: Minimum NARM signals required for analysis
        """
        self.min_history = min_history
        self.peak_history: Dict[str, List[PeakDetection]] = {}
        self.trend_history: Dict[str, List[TrendMetrics]] = {}

    def track_narrative_progression(
        self,
        asset: str,
        historical_narm: List[float],
        historical_adoption: Optional[List[float]] = None,
        period: str = "daily",
    ) -> NarrativeTrendReport:
        """
        Track narrative from early→mid→late stage.

        Args:
            asset: Asset symbol
            historical_narm: Historical NARM scores [oldest → newest]
            historical_adoption: Historical adoption velocities
            period: Period type (daily/weekly/monthly)

        Returns:
            NarrativeTrendReport with full analysis
        """
        if len(historical_narm) < self.min_history:
            return self._create_invalid_report(
                asset, "Insufficient historical data"
            )

        # Calculate trend metrics
        current_narm = historical_narm[-1]
        previous_narm = historical_narm[-2] if len(historical_narm) > 1 else current_narm
        narm_change_pct = (
            (current_narm - previous_narm) / max(previous_narm, 0.1) * 100
            if previous_narm > 0
            else 0
        )

        # Calculate acceleration (second derivative)
        acceleration = self._calculate_acceleration(historical_narm)

        # Determine momentum direction
        if acceleration > self.STRONG_ACCELERATION:
            momentum = "accelerating"
        elif acceleration < self.DECELERATION:
            momentum = "decelerating"
        else:
            momentum = "stable"

        # Trend direction
        if narm_change_pct > 2:
            direction = "up"
        elif narm_change_pct < -2:
            direction = "down"
        else:
            direction = "sideways"

        # Calculate volatility
        volatility = stdev(historical_narm) if len(historical_narm) > 1 else 0

        # Moving averages
        ma_short = mean(historical_narm[-5:]) if len(historical_narm) >= 5 else current_narm
        ma_long = mean(historical_narm[-20:]) if len(historical_narm) >= 20 else current_narm

        trend_metrics = TrendMetrics(
            asset=asset,
            period=period,
            current_narm=current_narm,
            previous_narm=previous_narm,
            narm_change_pct=narm_change_pct,
            adoption_acceleration=acceleration,
            narrative_momentum=momentum,
            trend_direction=direction,
            volatility=volatility,
            score_ma_short=ma_short,
            score_ma_long=ma_long,
        )

        # Store in history
        if asset not in self.trend_history:
            self.trend_history[asset] = []
        self.trend_history[asset].append(trend_metrics)

        # Detect peaks
        peak_detection = self._detect_peaks(asset, historical_narm)

        # Detect reversals
        reversal_signal = self._detect_reversal(
            asset, historical_narm, historical_adoption or []
        )

        # Determine lifecycle stage
        stage = self._determine_lifecycle_stage(current_narm, acceleration, peak_detection)
        lifecycle_position = self._calculate_lifecycle_position(
            current_narm, acceleration
        )

        # Momentum bars (consecutive up/down periods)
        momentum_bars = self._count_momentum_bars(historical_narm[-10:])

        # Expected next move
        expected_move = self._forecast_next_move(
            direction, momentum, ma_short, ma_long, acceleration
        )

        # Confidence score
        confidence = self._calculate_confidence(
            len(historical_narm), volatility, momentum
        )

        # Build reasoning
        reasoning = [
            f"Current NARM: {current_narm:.1f} (change: {narm_change_pct:+.1f}%)",
            f"Adoption acceleration: {acceleration:+.1f}%",
            f"Momentum: {momentum}",
            f"Volatility: {volatility:.2f}",
            f"SMA 5: {ma_short:.1f}, SMA 20: {ma_long:.1f}",
            f"Trend direction: {direction}",
            f"Expected move: {expected_move}",
        ]

        if peak_detection:
            reasoning.append(
                f"Peak detected: {peak_detection.peak_narm:.1f} ({peak_detection.peak_period_type})"
            )

        if reversal_signal.reversal_detected:
            reasoning.append(
                f"⚠️ REVERSAL SIGNAL: {reversal_signal.reversal_type} decline"
            )

        return NarrativeTrendReport(
            asset=asset,
            current_stage=stage,
            trend_metrics=trend_metrics,
            peak_detection=peak_detection,
            reversal_signal=reversal_signal,
            lifecycle_position=lifecycle_position,
            momentum_bars=momentum_bars,
            expected_next_move=expected_move,
            confidence_score=confidence,
            reasoning=reasoning,
        )

    def _calculate_acceleration(self, scores: List[float]) -> float:
        """Calculate adoption acceleration (second derivative)."""
        if len(scores) < 3:
            return 0.0

        # First derivative (velocity)
        velocities = [
            (scores[i] - scores[i - 1]) for i in range(1, len(scores))
        ]

        if len(velocities) < 2:
            return 0.0

        # Second derivative (acceleration)
        acceleration = velocities[-1] - velocities[-2]
        return acceleration

    def _detect_peaks(
        self,
        asset: str,
        historical_narm: List[float],
    ) -> Optional[PeakDetection]:
        """Detect peaks in narrative strength."""
        if len(historical_narm) < 5:
            return None

        # Find local maxima in last 20 periods
        recent_window = historical_narm[-20:]
        max_idx = recent_window.index(max(recent_window))
        max_score = recent_window[max_idx]
        max_pos = len(historical_narm) - (20 - max_idx)

        if max_score < self.PEAK_THRESHOLD:
            return None

        # Days from peak
        days_from_peak = len(historical_narm) - max_pos - 1

        # Classify peak type
        if days_from_peak == 0:
            peak_type = "major_peak"  # Current bar
            expected_reversal = 5  # Expect 5-10 day reversal
        elif days_from_peak < 5:
            peak_type = "mid_peak"
            expected_reversal = 7
        else:
            peak_type = "early_peak"
            expected_reversal = 10

        # Reversal probability (based on distance from peak)
        reversal_prob = min(days_from_peak / 10.0, 1.0)

        peak = PeakDetection(
            asset=asset,
            peak_date=datetime.utcnow() - timedelta(days=days_from_peak),
            peak_narm=max_score,
            peak_period_type=peak_type,
            days_from_peak=days_from_peak,
            expected_reversal_days=expected_reversal,
            reversal_probability=reversal_prob,
            reasoning=[
                f"Peak identified: {max_score:.1f}",
                f"Peak type: {peak_type}",
                f"Days from peak: {days_from_peak}",
                f"Reversal probability: {reversal_prob*100:.0f}%",
            ],
        )

        if asset not in self.peak_history:
            self.peak_history[asset] = []
        self.peak_history[asset].append(peak)

        return peak

    def _detect_reversal(
        self,
        asset: str,
        historical_narm: List[float],
        historical_adoption: List[float],
    ) -> ReversalSignal:
        """Detect narrative reversal or decline."""
        if len(historical_narm) < 5:
            return ReversalSignal(
                asset=asset,
                reversal_detected=False,
                confidence=0.0,
                reversal_type="none",
                adoption_decline_rate=0.0,
                narrative_weakness_signals=[],
                estimated_recovery=None,
            )

        # Check for sharp decline
        recent = historical_narm[-5:]
        decline_rate = (recent[-1] - recent[0]) / max(recent[0], 0.1) * 100

        # Weakness signals
        weakness_signals = []

        if decline_rate < self.REVERSAL_ACCELERATION:
            weakness_signals.append("Sharp NARM decline detected")
            reversal_type = "sharp"
        elif decline_rate < self.DECELERATION:
            weakness_signals.append("Gradual NARM decline")
            reversal_type = "gradual"
        else:
            reversal_type = "none"

        # Check adoption weakness
        if historical_adoption and len(historical_adoption) >= 3:
            adoption_decline = (
                historical_adoption[-1] - historical_adoption[-3]
            ) / max(historical_adoption[-3], 0.1)
            if adoption_decline < -0.15:
                weakness_signals.append("Adoption velocity declining sharply")

        # Detect plateauing (volatility collapse)
        if len(historical_narm) >= 10:
            recent_vol = stdev(historical_narm[-5:]) if len(historical_narm[-5:]) > 1 else 0
            prev_vol = stdev(historical_narm[-10:-5]) if len(historical_narm[-10:-5]) > 1 else 0
            if prev_vol > 0 and recent_vol < prev_vol * 0.5:
                weakness_signals.append("Momentum volatility collapsing (plateauing)")

        # Calculate confidence
        confidence = 0.0
        if decline_rate < self.REVERSAL_ACCELERATION:
            confidence = 0.8
        elif decline_rate < self.DECELERATION:
            confidence = 0.5

        # Estimate recovery (if reversing)
        recovery_estimate = "mid" if confidence > 0.5 else None

        return ReversalSignal(
            asset=asset,
            reversal_detected=len(weakness_signals) > 0,
            confidence=confidence,
            reversal_type=reversal_type,
            adoption_decline_rate=decline_rate,
            narrative_weakness_signals=weakness_signals,
            estimated_recovery=recovery_estimate,
        )

    def _determine_lifecycle_stage(
        self,
        current_narm: float,
        acceleration: float,
        peak_detection: Optional[PeakDetection],
    ) -> str:
        """Determine lifecycle stage (early/mid/late/declining)."""
        if peak_detection and peak_detection.reversal_probability > 0.6:
            return "declining"

        if current_narm < 40:
            return "early"
        elif current_narm < 65:
            return "mid"
        elif acceleration > 0:
            return "late"
        else:
            return "declining"

    def _calculate_lifecycle_position(
        self,
        current_narm: float,
        acceleration: float,
    ) -> float:
        """Calculate position in adoption cycle (0-1)."""
        base_position = min(current_narm / 100.0, 1.0)
        accel_adjustment = max(acceleration / 50.0, -0.2)
        return max(0.0, min(1.0, base_position + accel_adjustment * 0.1))

    def _count_momentum_bars(self, recent_scores: List[float]) -> int:
        """Count consecutive up/down periods."""
        if len(recent_scores) < 2:
            return 0

        count = 0
        direction = 1 if recent_scores[-1] > recent_scores[-2] else -1

        for i in range(len(recent_scores) - 1, 0, -1):
            current_dir = 1 if recent_scores[i] > recent_scores[i - 1] else -1
            if current_dir == direction:
                count += 1
            else:
                break

        return count * direction

    def _forecast_next_move(
        self,
        direction: str,
        momentum: str,
        ma_short: float,
        ma_long: float,
        acceleration: float,
    ) -> str:
        """Forecast next price move."""
        if momentum == "accelerating" and direction == "up":
            return "up"
        elif momentum == "decelerating" or direction == "down":
            return "down"
        elif abs(ma_short - ma_long) < 5:
            return "consolidation"
        else:
            return "up" if ma_short > ma_long else "down"

    def _calculate_confidence(
        self,
        data_points: int,
        volatility: float,
        momentum: str,
    ) -> float:
        """Calculate confidence in trend forecast."""
        data_confidence = min(data_points / 30.0, 1.0)
        vol_confidence = 1.0 - min(volatility / 50.0, 1.0)
        momentum_confidence = 0.8 if momentum == "accelerating" else 0.6

        return (data_confidence * 0.3 + vol_confidence * 0.3 + momentum_confidence * 0.4)

    def _create_invalid_report(
        self,
        asset: str,
        reason: str,
    ) -> NarrativeTrendReport:
        """Create invalid report."""
        return NarrativeTrendReport(
            asset=asset,
            current_stage="unknown",
            trend_metrics=TrendMetrics(
                asset=asset,
                period="unknown",
                current_narm=0,
                previous_narm=0,
                narm_change_pct=0,
                adoption_acceleration=0,
                narrative_momentum="unknown",
                trend_direction="unknown",
                volatility=0,
                score_ma_short=0,
                score_ma_long=0,
            ),
            peak_detection=None,
            reversal_signal=ReversalSignal(
                asset=asset,
                reversal_detected=False,
                confidence=0.0,
                reversal_type="none",
                adoption_decline_rate=0.0,
                narrative_weakness_signals=[reason],
                estimated_recovery=None,
            ),
            lifecycle_position=0.0,
            momentum_bars=0,
            expected_next_move="unknown",
            confidence_score=0.0,
            reasoning=[reason],
        )
