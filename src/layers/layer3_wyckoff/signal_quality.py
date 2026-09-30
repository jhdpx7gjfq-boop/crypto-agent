"""
Signal Quality Filter for Phase 3 BCE Engine.

Implements confidence scoring, signal clustering detection, and win probability
estimation to reduce false positives and improve signal reliability.

Author: Claude Haiku 4.5
Version: 1.0
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


@dataclass
class SignalQuality:
    """Quality metrics for a BCE signal."""
    asset: str
    timestamp: datetime
    bce_score: float

    # Confidence components
    component_consistency: float  # 0-100: How aligned are the 6 components
    pattern_strength: float  # 0-100: Strength of the detected pattern
    volume_confirmation: float  # 0-100: Volume profile alignment
    timeframe_alignment: float  # 0-100: Multi-timeframe consistency

    # Overall quality
    confidence: float  # 0-100: Final confidence score

    # Regime context
    regime_context: str  # 'risk_on', 'risk_off', 'neutral'
    regime_score: float  # 0-1: Strength of regime signal

    # Win probability estimate
    win_probability: float  # 0-1: Estimated probability of profitable trade

    # Clustering info
    is_clustered: bool = False
    cluster_id: Optional[str] = None
    time_since_last_signal: Optional[float] = None  # minutes

    # Rejection details
    is_rejected: bool = False
    rejection_reasons: List[str] = field(default_factory=list)

    def is_valid_for_entry(self, min_confidence: float = 70.0) -> bool:
        """Check if signal meets entry quality threshold."""
        return (
            not self.is_rejected
            and self.confidence >= min_confidence
            and not self.is_clustered
            and self.regime_context == 'risk_on'
        )


@dataclass
class ClusterEvent:
    """Represents a cluster of signals close in time."""
    cluster_id: str
    asset: str
    start_time: datetime
    end_time: datetime
    signal_count: int
    average_confidence: float
    best_signal_idx: int


class SignalQualityFilter:
    """
    Filters BCE signals by quality metrics and reduces false positives.

    Implements:
    - Confidence scoring from component alignment and pattern strength
    - Signal clustering detection to avoid repeat entries
    - Win probability estimation based on signal characteristics
    - Regime filtering (risk-on/risk-off context)
    """

    # Quality thresholds
    HIGH_CONFIDENCE_THRESHOLD = 75.0
    MEDIUM_CONFIDENCE_THRESHOLD = 60.0

    # Clustering parameters
    CLUSTER_WINDOW_MINUTES = 60  # Group signals within 1 hour
    MIN_CLUSTER_SIZE = 2

    # Regime detection thresholds
    RISK_ON_THRESHOLD = 0.6
    RISK_OFF_THRESHOLD = 0.4

    def __init__(self, regime_filter: Optional['RegimeFilter'] = None):
        """
        Initialize quality filter.

        Args:
            regime_filter: Optional RegimeFilter instance for regime context
        """
        self.regime_filter = regime_filter
        self.signal_history: List[SignalQuality] = []
        self.active_clusters: List[ClusterEvent] = []

    def evaluate_signal(
        self,
        asset: str,
        timestamp: datetime,
        bce_score: float,
        components: dict,
        timeframe_alignment: float = 0.8,
        recent_signals: Optional[List[datetime]] = None,
    ) -> SignalQuality:
        """
        Evaluate and score a BCE signal for quality.

        Args:
            asset: Asset symbol (e.g., 'BTCUSDT')
            timestamp: Signal timestamp
            bce_score: BCE score (0-1)
            components: Dict with 6 BCE component scores (0-1 each)
            timeframe_alignment: Multi-timeframe confidence (0-1)
            recent_signals: List of recent signal timestamps for clustering

        Returns:
            SignalQuality object with all metrics
        """
        # Calculate component consistency
        comp_values = [
            components.get('wyckoff_structure', 0),
            components.get('volume_analysis', 0),
            components.get('selling_exhaustion', 0),
            components.get('smart_money_accumulation', 0),
            components.get('market_structure', 0),
            components.get('momentum_confirmation', 0),
        ]
        component_consistency = self._calculate_component_consistency(comp_values)

        # Calculate pattern strength
        pattern_strength = self._calculate_pattern_strength(bce_score, comp_values)

        # Calculate volume confirmation (from components)
        volume_confirmation = (components.get('volume_analysis', 0) +
                              components.get('smart_money_accumulation', 0)) / 2 * 100

        # Timeframe alignment score
        timeframe_score = timeframe_alignment * 100

        # Overall confidence
        confidence = (
            component_consistency * 0.35 +
            pattern_strength * 0.30 +
            volume_confirmation * 0.20 +
            timeframe_score * 0.15
        )

        # Regime context
        regime_context = 'neutral'
        regime_score = 0.5
        if self.regime_filter:
            # Use existing regime if recent, otherwise assess with defaults
            if self.regime_filter.regime_history:
                last_time, last_context, last_score = self.regime_filter.regime_history[-1]
                if (timestamp - last_time).total_seconds() < 3600:  # < 1 hour old
                    regime_context = last_context
                    regime_score = last_score
                else:
                    regime_context, regime_score = self.regime_filter.assess_regime(timestamp)
            else:
                regime_context, regime_score = self.regime_filter.assess_regime(timestamp)

        # Win probability estimate
        win_probability = self._estimate_win_probability(
            bce_score, confidence, regime_score, comp_values
        )

        # Check for clustering
        is_clustered = False
        cluster_id = None
        time_since_last = None

        if recent_signals:
            is_clustered, cluster_id, time_since_last = self._check_clustering(
                asset, timestamp, recent_signals
            )

        # Create signal quality object
        signal = SignalQuality(
            asset=asset,
            timestamp=timestamp,
            bce_score=bce_score,
            component_consistency=component_consistency,
            pattern_strength=pattern_strength,
            volume_confirmation=volume_confirmation,
            timeframe_alignment=timeframe_score,
            confidence=confidence,
            regime_context=regime_context,
            regime_score=regime_score,
            win_probability=win_probability,
            is_clustered=is_clustered,
            cluster_id=cluster_id,
            time_since_last_signal=time_since_last,
        )

        # Apply rejection filters
        self._apply_rejection_filters(signal, regime_context)

        # Track in history
        self.signal_history.append(signal)

        return signal

    def _calculate_component_consistency(self, components: List[float]) -> float:
        """
        Calculate how aligned the 6 components are (0-100).

        High consistency = components agree (low variance).
        Low consistency = components disagree (high variance).
        """
        if not components:
            return 0.0

        components_array = np.array(components)
        mean_comp = np.mean(components_array)
        std_comp = np.std(components_array)

        # Convert std to consistency (lower std = higher consistency)
        # Max std for 6 values ranging 0-1 is ~0.5
        consistency = max(0, 100 * (1 - std_comp / 0.5))

        return min(100, consistency)

    def _calculate_pattern_strength(
        self,
        bce_score: float,
        components: List[float]
    ) -> float:
        """
        Calculate pattern strength (0-100) from BCE score and components.

        Considers:
        - Overall BCE score
        - Number of strong components (>= 0.6)
        - Strength of weakest component (bottleneck)
        """
        strong_components = sum(1 for c in components if c >= 0.6)
        weakest = min(components) if components else 0

        # Pattern strength = weighted combination
        strength = (
            bce_score * 100 * 0.5 +  # BCE score weight
            (strong_components / 6) * 100 * 0.3 +  # Strong component count
            weakest * 100 * 0.2  # Weakest component (quality floor)
        )

        return min(100, strength)

    def _estimate_win_probability(
        self,
        bce_score: float,
        confidence: float,
        regime_score: float,
        components: List[float]
    ) -> float:
        """
        Estimate win probability (0-1) based on signal characteristics.

        Incorporates:
        - BCE score (foundation strength)
        - Overall confidence
        - Regime alignment
        - Component strength
        """
        # Base probability from BCE score
        # BCE >= 5/6 (0.833) maps to higher probability
        base_prob = min(1.0, bce_score / 0.833 * 0.7)

        # Confidence contribution
        conf_prob = (confidence / 100) * 0.2

        # Regime contribution
        regime_prob = regime_score * 0.1

        # Probability estimate
        win_prob = base_prob + conf_prob + regime_prob

        return min(1.0, win_prob)

    def _check_clustering(
        self,
        asset: str,
        timestamp: datetime,
        recent_signals: List[datetime]
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Detect if signal is part of a cluster (multiple signals close in time).

        Returns:
            (is_clustered, cluster_id, minutes_since_last_signal)
        """
        if not recent_signals:
            return False, None, None

        # Find signals within cluster window
        window_start = timestamp - timedelta(minutes=self.CLUSTER_WINDOW_MINUTES)
        signals_in_window = [
            s for s in recent_signals
            if window_start <= s <= timestamp
        ]

        # Find time to most recent prior signal
        prior_signals = [s for s in recent_signals if s < timestamp]
        time_since_last = None
        if prior_signals:
            last_signal = max(prior_signals)
            time_since_last = (timestamp - last_signal).total_seconds() / 60

        # Clustering check: current signal + at least one prior within window = cluster
        is_clustered = len(signals_in_window) >= 1  # At least one prior signal in window
        cluster_id = f"{asset}_{window_start.isoformat()}" if is_clustered else None

        return is_clustered, cluster_id, time_since_last

    def _apply_rejection_filters(
        self,
        signal: SignalQuality,
        regime_context: str
    ) -> None:
        """Apply filtering rules that may cause rejection."""
        reasons = []

        # Confidence threshold
        if signal.confidence < self.MEDIUM_CONFIDENCE_THRESHOLD:
            reasons.append(
                f"Low confidence ({signal.confidence:.1f}% < {self.MEDIUM_CONFIDENCE_THRESHOLD}%)"
            )

        # Regime filter
        if regime_context == 'risk_off':
            reasons.append("Regime is risk-off (unfavorable macro environment)")

        # Component agreement
        if signal.component_consistency < 40:
            reasons.append(
                f"Poor component alignment ({signal.component_consistency:.1f}% < 40%)"
            )

        if reasons:
            signal.is_rejected = True
            signal.rejection_reasons = reasons

    def filter_signals(
        self,
        signals: List[SignalQuality],
        min_confidence: float = 70.0,
        require_regime_alignment: bool = True,
        allow_clustering: bool = False,
    ) -> List[SignalQuality]:
        """
        Filter signals to return only high-quality candidates.

        Args:
            signals: List of SignalQuality objects
            min_confidence: Minimum confidence threshold (0-100)
            require_regime_alignment: Require regime context to be 'risk_on'
            allow_clustering: Allow clustered signals (default: remove them)

        Returns:
            List of signals passing all filters
        """
        valid_signals = []

        for signal in signals:
            if signal.is_rejected:
                continue

            if signal.confidence < min_confidence:
                continue

            if require_regime_alignment and signal.regime_context != 'risk_on':
                continue

            if not allow_clustering and signal.is_clustered:
                continue

            valid_signals.append(signal)

        return valid_signals

    def get_best_signal_per_asset(
        self,
        signals: List[SignalQuality]
    ) -> dict:
        """
        From a set of signals (potentially clustered), select best per asset.

        Args:
            signals: List of SignalQuality objects (may include clusters)

        Returns:
            Dict mapping asset -> best SignalQuality
        """
        best_by_asset = {}

        for signal in signals:
            asset = signal.asset

            if asset not in best_by_asset:
                best_by_asset[asset] = signal
            else:
                # Prefer higher confidence
                if signal.confidence > best_by_asset[asset].confidence:
                    best_by_asset[asset] = signal

        return best_by_asset

    def format_quality_report(self, signal: SignalQuality) -> str:
        """Format signal quality into human-readable report."""
        status = "✓ VALID" if not signal.is_rejected else "✗ REJECTED"

        report = f"""
{status} Signal Quality Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Asset: {signal.asset}
Timestamp: {signal.timestamp.isoformat()}
BCE Score: {signal.bce_score:.3f}

Quality Metrics:
  • Component Consistency: {signal.component_consistency:.1f}%
  • Pattern Strength: {signal.pattern_strength:.1f}%
  • Volume Confirmation: {signal.volume_confirmation:.1f}%
  • Timeframe Alignment: {signal.timeframe_alignment:.1f}%

Overall Confidence: {signal.confidence:.1f}%
Win Probability Estimate: {signal.win_probability:.1%}

Regime Context: {signal.regime_context} (strength: {signal.regime_score:.2f})

Clustering:
  • Clustered: {'Yes' if signal.is_clustered else 'No'}
  • Time Since Last Signal: {f'{signal.time_since_last_signal:.1f} min' if signal.time_since_last_signal else 'N/A'}

Entry Readiness: {'✓ Ready' if signal.is_valid_for_entry() else '✗ Not Ready'}
"""

        if signal.rejection_reasons:
            report += "\nRejection Reasons:\n"
            for reason in signal.rejection_reasons:
                report += f"  • {reason}\n"

        return report


class RegimeFilter:
    """
    Detects macro regime (risk-on vs risk-off) to filter BCE signals.

    Implements:
    - Risk-on/risk-off detection based on market conditions
    - Multi-indicator regime assessment
    - Regime strength scoring
    """

    # Indicator thresholds (in real system, would use actual market data)
    RISK_ON_INDICATORS = {
        'btc_trend': 0.6,  # BTC momentum
        'funding_rate': 0.5,  # Derivative funding
        'dxy_trend': -0.4,  # DXY declining (positive for crypto)
        'volatility': 0.3,  # Moderate volatility
    }

    def __init__(self):
        """Initialize regime filter."""
        self.regime_history: List[Tuple[datetime, str, float]] = []

    def assess_regime(
        self,
        timestamp: datetime,
        btc_momentum: float = 0.0,
        funding_rate: float = 0.0,
        dxy_trend: float = 0.0,
        volatility_rank: float = 0.5,
    ) -> Tuple[str, float]:
        """
        Assess macro regime at given timestamp.

        Args:
            timestamp: Timestamp for regime assessment
            btc_momentum: BTC momentum (-1 to 1)
            funding_rate: Derivative funding rate indicator (-1 to 1)
            dxy_trend: DXY trend indicator (-1 to 1, negative is good for crypto)
            volatility_rank: Volatility rank (0-1, 0.5 is neutral)

        Returns:
            (regime_context, regime_score)
            regime_context: 'risk_on', 'risk_off', or 'neutral'
            regime_score: Strength 0-1
        """
        # Score indicators
        btc_score = max(0, min(1, btc_momentum))  # 0-1
        funding_score = max(0, min(1, funding_rate))  # 0-1
        dxy_score = max(0, min(1, -dxy_trend))  # Invert: lower DXY is better
        vol_score = max(0, 1 - abs(volatility_rank - 0.5) * 2)  # Center around 0.5

        # Weighted regime score
        regime_score = (
            btc_score * 0.35 +
            funding_score * 0.25 +
            dxy_score * 0.25 +
            vol_score * 0.15
        )

        # Classify regime
        if regime_score >= 0.6:
            regime_context = 'risk_on'
        elif regime_score <= 0.4:
            regime_context = 'risk_off'
        else:
            regime_context = 'neutral'

        # Track history
        self.regime_history.append((timestamp, regime_context, regime_score))

        return regime_context, regime_score

    def get_regime_strength(self, lookback_hours: int = 24) -> float:
        """
        Get strength of current regime over lookback period.

        Returns:
            Average regime score over period (0-1)
        """
        if not self.regime_history:
            return 0.5

        cutoff = self.regime_history[-1][0] - timedelta(hours=lookback_hours)
        recent = [score for ts, _, score in self.regime_history if ts >= cutoff]

        return np.mean(recent) if recent else 0.5
