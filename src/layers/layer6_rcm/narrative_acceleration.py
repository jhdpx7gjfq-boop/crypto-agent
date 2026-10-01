"""Narrative Acceleration Engine for Phase 6 RCM/RPM.

Tracks NARM growth rate, social volume acceleration, and funding rate alignment.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import statistics


@dataclass
class NARMAcceleration:
    """NARM score acceleration metrics."""

    current_narm: float  # Latest NARM score (0-100)
    narm_7d_change: float  # Change over 7 days
    narm_acceleration: float  # Second derivative (rate of change of change)
    narm_momentum: str  # "accelerating", "stable", "decelerating"
    score: float  # 0-100


@dataclass
class SocialMomentum:
    """Social volume and sentiment metrics."""

    social_volume_7d_change: float  # % change in social mentions
    social_volume_acceleration: float  # Rate of volume change
    sentiment_score: float  # 0-100 (bullish)
    influencer_mentions: int  # Count of key influencer mentions
    ecosystem_development_activity: float  # Dev activity score
    score: float  # 0-100


@dataclass
class FundingRateStructure:
    """Derivatives funding rate alignment."""

    current_funding_rate: float  # % per 8 hours (can be negative)
    funding_rate_trend: str  # "rising", "stable", "falling"
    open_interest_change: float  # OI change % (7d)
    long_short_ratio: float  # Long positions / short
    liquidation_cascade_risk: float  # 0-1 (likelihood of cascade)
    mean_reversion_signal: bool  # Extreme funding suggests reversal
    score: float  # 0-100


@dataclass
class NarrativeAccelerationAnalysis:
    """Complete narrative acceleration analysis."""

    asset: str
    timestamp: datetime
    narm_acceleration: NARMAcceleration
    social_momentum: SocialMomentum
    funding_structure: FundingRateStructure
    narrative_acceleration_score: float  # Weighted 0-100
    acceleration_phase: str  # "early", "explosive", "mature", "declining"
    estimated_peak_days: Optional[int]  # Days until estimated peak


class NarrativeAccelerationEngine:
    """Analyzes narrative growth rates and market structure alignment."""

    def __init__(self):
        """Initialize engine."""
        self.analysis_history: Dict[str, List[NarrativeAccelerationAnalysis]] = {}

    def analyze_narrative_acceleration(
        self,
        asset: str,
        narm_history: List[float],
        social_data: Dict,
        funding_data: Dict,
    ) -> NarrativeAccelerationAnalysis:
        """
        Analyze narrative acceleration from multiple angles.

        Args:
            asset: Asset symbol
            narm_history: Historical NARM scores [oldest ... newest]
            social_data: {social_volume_7d_change, sentiment_score, mentions, dev_activity}
            funding_data: {current_funding_rate, oi_change_7d, long_short_ratio, liquidation_risk}

        Returns:
            NarrativeAccelerationAnalysis with phase identification
        """
        narm_accel = self._analyze_narm_acceleration(narm_history)
        social = self._analyze_social_momentum(asset, social_data)
        funding = self._analyze_funding_structure(funding_data)

        # Calculate weighted score
        narrative_score = (
            narm_accel.score * 0.40
            + social.score * 0.35
            + funding.score * 0.25
        )
        narrative_score = min(100, max(0, narrative_score))

        # Identify acceleration phase
        phase = self._identify_acceleration_phase(
            narm_accel, social, funding
        )

        # Estimate days to peak
        peak_days = self._estimate_peak_days(
            narm_history, narm_accel, phase
        )

        analysis = NarrativeAccelerationAnalysis(
            asset=asset,
            timestamp=datetime.utcnow(),
            narm_acceleration=narm_accel,
            social_momentum=social,
            funding_structure=funding,
            narrative_acceleration_score=narrative_score,
            acceleration_phase=phase,
            estimated_peak_days=peak_days,
        )

        # Track history
        if asset not in self.analysis_history:
            self.analysis_history[asset] = []
        self.analysis_history[asset].append(analysis)

        return analysis

    def _analyze_narm_acceleration(
        self, narm_history: List[float]
    ) -> NARMAcceleration:
        """Analyze NARM score acceleration."""
        if len(narm_history) < 1:
            return NARMAcceleration(
                current_narm=0,
                narm_7d_change=0,
                narm_acceleration=0,
                narm_momentum="unknown",
                score=0,
            )

        current = narm_history[-1]

        # Calculate 7-day change
        if len(narm_history) >= 7:
            prev_7d = narm_history[-7]
            change_7d = current - prev_7d
        else:
            change_7d = current - (narm_history[0] if narm_history else 0)

        # Calculate acceleration (second derivative)
        if len(narm_history) >= 14:
            # Change in first 7 days
            change_days_1_7 = narm_history[-7] - narm_history[-14]
            # Change in last 7 days
            change_days_8_14 = current - narm_history[-7]
            # Acceleration
            acceleration = change_days_8_14 - change_days_1_7
        else:
            acceleration = 0

        # Determine momentum
        if acceleration > 2:
            momentum = "accelerating"
        elif acceleration < -2:
            momentum = "decelerating"
        else:
            momentum = "stable"

        # Score based on change and acceleration
        if change_7d > 15:
            score = min(100, 80 + (change_7d - 15) * 0.5)
        elif change_7d > 10:
            score = min(100, 70 + (change_7d - 10))
        elif change_7d > 5:
            score = min(100, 55 + (change_7d - 5) * 3)
        elif change_7d > 0:
            score = 40 + (change_7d * 2)
        else:
            score = max(0, 30 + (change_7d))

        # Boost for acceleration
        if acceleration > 0:
            score = min(100, score + (acceleration * 5))

        return NARMAcceleration(
            current_narm=current,
            narm_7d_change=change_7d,
            narm_acceleration=acceleration,
            narm_momentum=momentum,
            score=max(0, min(100, score)),
        )

    def _analyze_social_momentum(
        self, asset: str, social_data: Dict
    ) -> SocialMomentum:
        """Analyze social volume and sentiment."""
        vol_change = social_data.get("social_volume_7d_change", 0)
        vol_accel = social_data.get("social_volume_acceleration", 0)
        sentiment = social_data.get("sentiment_score", 50)
        mentions = social_data.get("influencer_mentions", 0)
        dev_activity = social_data.get("ecosystem_development_activity", 0)

        # Base score on volume change
        if vol_change > 300:
            score = min(100, 80 + (vol_change - 300) * 0.1)
        elif vol_change > 100:
            score = min(100, 70 + (vol_change - 100) * 0.1)
        elif vol_change > 30:
            score = min(100, 55 + (vol_change - 30) * 0.5)
        elif vol_change > 0:
            score = 40 + (vol_change * 0.5)
        else:
            score = max(0, 30 + (vol_change * 0.5))

        # Add sentiment
        if sentiment > 70:
            score = min(100, score + (sentiment - 70) * 0.5)
        elif sentiment < 40:
            score = max(0, score - (40 - sentiment) * 0.5)

        # Influencer mentions boost
        if mentions > 10:
            score = min(100, score + 15)
        elif mentions > 5:
            score = min(100, score + 10)

        # Dev activity confirms
        if dev_activity > 0.7:
            score = min(100, score + 10)

        return SocialMomentum(
            social_volume_7d_change=vol_change,
            social_volume_acceleration=vol_accel,
            sentiment_score=sentiment,
            influencer_mentions=mentions,
            ecosystem_development_activity=dev_activity,
            score=max(0, min(100, score)),
        )

    def _analyze_funding_structure(
        self, funding_data: Dict
    ) -> FundingRateStructure:
        """Analyze derivatives funding rate alignment."""
        funding_rate = funding_data.get("current_funding_rate", 0)
        oi_change = funding_data.get("open_interest_change_7d", 0)
        ls_ratio = funding_data.get("long_short_ratio", 1.0)
        liquidation_risk = funding_data.get("liquidation_cascade_risk", 0)

        # Funding rate trend
        prev_funding = funding_data.get("previous_funding_rate", funding_rate)
        if funding_rate > prev_funding:
            trend = "rising"
        elif funding_rate < prev_funding:
            trend = "falling"
        else:
            trend = "stable"

        # Extreme funding signals mean-reversion
        mean_reversion = abs(funding_rate) > 0.15

        # Score based on funding alignment
        # Positive funding = bullish (longs paying shorts)
        if 0.05 < funding_rate < 0.15:
            score = 70  # Healthy bullish
        elif funding_rate > 0.15:
            score = 60  # Strong bullish, potential reversal
        elif -0.05 < funding_rate <= 0.05:
            score = 50  # Neutral
        elif -0.15 < funding_rate <= -0.05:
            score = 40  # Bearish
        else:
            score = 30  # Strong bearish

        # OI change confirms
        if oi_change > 20:
            score = min(100, score + 15)
        elif oi_change < -20:
            score = max(0, score - 15)

        # Long/short ratio
        if ls_ratio > 1.5:
            score = min(100, score + 10)  # Heavy longs = potential exhaustion
        elif ls_ratio < 0.7:
            score = max(0, score - 10)  # Heavy shorts

        # Liquidation cascade risk
        if liquidation_risk > 0.7:
            score = max(0, score - 15)

        return FundingRateStructure(
            current_funding_rate=funding_rate,
            funding_rate_trend=trend,
            open_interest_change=oi_change,
            long_short_ratio=ls_ratio,
            liquidation_cascade_risk=liquidation_risk,
            mean_reversion_signal=mean_reversion,
            score=max(0, min(100, score)),
        )

    def _identify_acceleration_phase(
        self,
        narm_accel: NARMAcceleration,
        social: SocialMomentum,
        funding: FundingRateStructure,
    ) -> str:
        """Identify which phase of acceleration narrative is in."""
        narm_score = narm_accel.score
        social_score = social.score
        funding_score = funding.score

        # Early: NARM rising, social growing, funding moderate
        if (
            narm_score < 60
            and narm_accel.narm_momentum == "accelerating"
            and social_score > 40
        ):
            return "early"

        # Explosive: NARM >70, strong acceleration, high social, elevated funding
        if (
            narm_score > 70
            and narm_accel.narm_momentum == "accelerating"
            and social_score > 70
            and funding.current_funding_rate > 0.1
        ):
            return "explosive"

        # Mature: NARM high but acceleration slowing, social stabilizing
        if (
            narm_score > 70
            and narm_accel.narm_momentum == "stable"
            and social_score > 50
        ):
            return "mature"

        # Declining: NARM declining, social falling, funding turning negative
        if (
            narm_accel.narm_momentum == "decelerating"
            and social_score < 50
            and funding.current_funding_rate < 0
        ):
            return "declining"

        return "stable"

    def _estimate_peak_days(
        self,
        narm_history: List[float],
        narm_accel: NARMAcceleration,
        phase: str,
    ) -> Optional[int]:
        """Estimate days until narrative peak."""
        if phase == "declining":
            return None  # Already peaked
        if phase == "early":
            return 14  # Early phases typically take 2 weeks to mature
        if phase == "explosive":
            return 7  # Explosive phases peak quickly
        if phase == "mature":
            return 3  # Peak likely within days
        return None  # Unknown

    def audit_narrative_acceleration(self, asset: str) -> Dict:
        """Audit narrative acceleration history."""
        if asset not in self.analysis_history:
            return {
                "asset": asset,
                "analyses": 0,
                "avg_score": 0.0,
                "phase_transitions": [],
            }

        history = self.analysis_history[asset]
        scores = [a.narrative_acceleration_score for a in history]
        phases = [a.acceleration_phase for a in history]

        # Track phase transitions
        transitions = []
        for i in range(1, len(phases)):
            if phases[i] != phases[i - 1]:
                transitions.append(
                    {
                        "from": phases[i - 1],
                        "to": phases[i],
                        "timestamp": history[i].timestamp,
                    }
                )

        return {
            "asset": asset,
            "analyses": len(history),
            "avg_score": statistics.mean(scores) if scores else 0.0,
            "latest_score": scores[-1] if scores else 0.0,
            "current_phase": phases[-1] if phases else "unknown",
            "phase_transitions": transitions,
            "latest_peak_estimate": (
                history[-1].estimated_peak_days if history else None
            ),
        }
