"""Revival Detector — Core RRP engine.

Identifies tokens showing early signs of resurrection.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class RevivalSignal:
    """Early revival signal detection."""

    score: float  # 0-100
    confidence: float  # 0-1
    dormancy_days: int
    acceleration_rate: float  # Growth rate of revival signal
    momentum_direction: str  # "accelerating", "stable", "decelerating"


@dataclass
class VolumeAnalysis:
    """Volume behavior during revival phase."""

    current_volume_7d: float
    historical_avg_volume: float
    volume_ratio: float  # current / avg
    volume_acceleration: float  # % change 7d vs 14d
    score: float


@dataclass
class OnChainActivity:
    """On-chain metrics showing revival."""

    dau_current: int  # Daily active users
    dau_previous: int
    dau_growth_rate: float  # % change
    transaction_volume: float
    tx_growth_rate: float
    whale_activity_change: float  # % change
    score: float


@dataclass
class SocialMomentum:
    """Social/attention signals."""

    mentions_7d: int
    mentions_14d_prior: int
    attention_acceleration: float  # % change
    sentiment_score: float  # -100 to +100
    influencer_activity: bool
    score: float


@dataclass
class PriceStructure:
    """Price formation during revival."""

    current_price: float
    base_price: float  # Lowest recent support
    months_since_bottom: int
    base_formation_strength: str  # "weak", "moderate", "strong"
    breakout_probability: float  # 0-1
    score: float


@dataclass
class RevivalAnalysis:
    """Complete revival analysis for an asset."""

    asset: str
    timestamp: datetime
    revival_signal: RevivalSignal
    volume_analysis: VolumeAnalysis
    on_chain_activity: OnChainActivity
    social_momentum: SocialMomentum
    price_structure: PriceStructure
    overall_revival_score: float  # Weighted 0-100
    revival_stage: str  # "dormant", "early_signs", "emerging", "confirmed"
    estimated_peak_days: Optional[int]


class RevivalDetector:
    """Detects tokens transitioning from dormancy to revival."""

    def __init__(self):
        """Initialize detector."""
        self.analysis_history: Dict[str, list] = {}
        self.latest_signals: Dict[str, RevivalAnalysis] = {}

    def detect_revival(
        self,
        asset: str,
        current_metrics: Dict,
        historical_metrics: Dict,
        social_data: Dict,
        price_data: Dict,
    ) -> RevivalAnalysis:
        """
        Detect early revival signals.

        Args:
            asset: Asset symbol
            current_metrics: {volume_7d, dau, tx_volume, whale_activity}
            historical_metrics: {avg_volume, baseline_dau, baseline_tx}
            social_data: {mentions_7d, mentions_14d_prior, sentiment}
            price_data: {current, base_price, months_since_bottom}

        Returns:
            RevivalAnalysis with component scores
        """
        volume = self._analyze_volume(current_metrics, historical_metrics)
        on_chain = self._analyze_on_chain(current_metrics, historical_metrics)
        social = self._analyze_social(social_data)
        price = self._analyze_price_structure(price_data)

        # Calculate revival signal
        dormancy_days = self._estimate_dormancy(historical_metrics)
        acceleration = self._calculate_acceleration(volume, on_chain, social)
        revival_score = (
            volume.score * 0.25 + on_chain.score * 0.30 + social.score * 0.20 + price.score * 0.25
        )
        revival_score = min(100, max(0, revival_score))

        signal = RevivalSignal(
            score=revival_score,
            confidence=self._calculate_confidence(volume, on_chain, social),
            dormancy_days=dormancy_days,
            acceleration_rate=acceleration,
            momentum_direction=self._determine_momentum_direction(volume, on_chain),
        )

        # Determine revival stage
        stage = self._determine_revival_stage(revival_score, signal.momentum_direction)
        estimated_peak = self._estimate_peak_days(stage, signal.acceleration_rate)

        analysis = RevivalAnalysis(
            asset=asset,
            timestamp=datetime.utcnow(),
            revival_signal=signal,
            volume_analysis=volume,
            on_chain_activity=on_chain,
            social_momentum=social,
            price_structure=price,
            overall_revival_score=revival_score,
            revival_stage=stage,
            estimated_peak_days=estimated_peak,
        )

        # Track history
        if asset not in self.analysis_history:
            self.analysis_history[asset] = []
        self.analysis_history[asset].append(analysis)
        self.latest_signals[asset] = analysis

        return analysis

    def _analyze_volume(self, current: Dict, historical: Dict) -> VolumeAnalysis:
        """Analyze volume revival signals."""
        vol_7d = current.get("volume_7d", 0)
        avg_vol = historical.get("avg_volume", vol_7d or 1)
        vol_14d_prior = current.get("volume_14d_prior", vol_7d)

        ratio = vol_7d / avg_vol if avg_vol > 0 else 1.0
        accel = ((vol_7d - vol_14d_prior) / vol_14d_prior * 100) if vol_14d_prior > 0 else 0

        # Score based on volume acceleration
        if accel > 200:
            score = min(100, 80 + (accel - 200) * 0.05)
        elif accel > 100:
            score = 70 + (accel - 100) * 0.1
        elif accel > 50:
            score = 60 + (accel - 50) * 0.2
        elif accel > 0:
            score = 50 + (accel * 0.2)
        else:
            score = max(0, 40 + accel * 0.2)

        return VolumeAnalysis(
            current_volume_7d=vol_7d,
            historical_avg_volume=avg_vol,
            volume_ratio=ratio,
            volume_acceleration=accel,
            score=score,
        )

    def _analyze_on_chain(self, current: Dict, historical: Dict) -> OnChainActivity:
        """Analyze on-chain activity revival."""
        dau_curr = current.get("dau", 0)
        dau_prev = historical.get("baseline_dau", dau_curr or 1)
        dau_growth = ((dau_curr - dau_prev) / dau_prev * 100) if dau_prev > 0 else 0

        tx_curr = current.get("transaction_volume", 0)
        tx_baseline = historical.get("baseline_tx", tx_curr or 1)
        tx_growth = ((tx_curr - tx_baseline) / tx_baseline * 100) if tx_baseline > 0 else 0

        whale_change = current.get("whale_activity_change", 0)

        # Score based on on-chain growth
        combined_growth = (dau_growth + tx_growth) / 2
        if combined_growth > 150:
            score = min(100, 80 + (combined_growth - 150) * 0.1)
        elif combined_growth > 100:
            score = 75 + (combined_growth - 100) * 0.1
        elif combined_growth > 50:
            score = 65 + (combined_growth - 50) * 0.2
        elif combined_growth > 0:
            score = 55 + (combined_growth * 0.2)
        else:
            score = max(0, 40 + combined_growth * 0.1)

        if whale_change > 50:
            score = min(100, score + 15)

        return OnChainActivity(
            dau_current=dau_curr,
            dau_previous=dau_prev,
            dau_growth_rate=dau_growth,
            transaction_volume=tx_curr,
            tx_growth_rate=tx_growth,
            whale_activity_change=whale_change,
            score=score,
        )

    def _analyze_social(self, social_data: Dict) -> SocialMomentum:
        """Analyze social momentum during revival."""
        mentions_7d = social_data.get("mentions_7d", 0)
        mentions_14d_prior = social_data.get("mentions_14d_prior", mentions_7d or 1)
        attention_accel = (
            ((mentions_7d - mentions_14d_prior) / mentions_14d_prior * 100)
            if mentions_14d_prior > 0
            else 0
        )
        sentiment = social_data.get("sentiment_score", 0)
        influencer = social_data.get("influencer_activity", False)

        # Score based on attention acceleration, but require meaningful baseline
        if mentions_7d < 20:
            # Very low mention count - high % changes unreliable
            score = 30 + max(0, (mentions_7d - 5) * 2)
        elif attention_accel > 300:
            score = min(100, 75 + (attention_accel - 300) * 0.05)
        elif attention_accel > 150:
            score = 65 + (attention_accel - 150) * 0.1
        elif attention_accel > 50:
            score = 55 + (attention_accel - 50) * 0.2
        elif attention_accel > 0:
            score = 45 + (attention_accel * 0.2)
        else:
            score = max(0, 30 + attention_accel * 0.1)

        if sentiment > 50:
            score = min(100, score + 10)
        if influencer:
            score = min(100, score + 15)

        return SocialMomentum(
            mentions_7d=mentions_7d,
            mentions_14d_prior=mentions_14d_prior,
            attention_acceleration=attention_accel,
            sentiment_score=sentiment,
            influencer_activity=influencer,
            score=score,
        )

    def _analyze_price_structure(self, price_data: Dict) -> PriceStructure:
        """Analyze price formation during revival."""
        current = price_data.get("current_price", 0)
        base = price_data.get("base_price", current or 1)
        months_since = price_data.get("months_since_bottom", 0)
        formation = price_data.get("formation_strength", "weak")

        recovery_pct = ((current - base) / base * 100) if base > 0 else 0

        # Score based on base formation and recovery
        if formation == "strong":
            base_score = 70
        elif formation == "moderate":
            base_score = 50
        else:
            base_score = 30

        if recovery_pct > 100:
            score = min(100, base_score + 20)
        elif recovery_pct > 50:
            score = base_score + 15
        elif recovery_pct > 0:
            score = base_score + 5
        else:
            score = max(0, base_score - 10)

        # Estimate breakout probability
        if formation == "strong" and recovery_pct > 20:
            breakout_prob = 0.7
        elif formation == "moderate" and recovery_pct > 0:
            breakout_prob = 0.5
        else:
            breakout_prob = 0.3

        return PriceStructure(
            current_price=current,
            base_price=base,
            months_since_bottom=months_since,
            base_formation_strength=formation,
            breakout_probability=breakout_prob,
            score=score,
        )

    def _estimate_dormancy(self, historical: Dict) -> int:
        """Estimate how many days dormant."""
        return historical.get("dormancy_days", 180)

    def _calculate_acceleration(
        self, volume: VolumeAnalysis, on_chain: OnChainActivity, social: SocialMomentum
    ) -> float:
        """Calculate overall acceleration rate."""
        return (volume.volume_acceleration + on_chain.dau_growth_rate + social.attention_acceleration) / 3

    def _calculate_confidence(
        self, volume: VolumeAnalysis, on_chain: OnChainActivity, social: SocialMomentum
    ) -> float:
        """Calculate signal confidence."""
        signal_count = sum(
            [
                volume.volume_acceleration > 0,
                on_chain.dau_growth_rate > 0,
                social.attention_acceleration > 0,
            ]
        )
        return min(1.0, 0.4 + (signal_count * 0.3))

    def _determine_momentum_direction(
        self, volume: VolumeAnalysis, on_chain: OnChainActivity
    ) -> str:
        """Determine if momentum is accelerating, stable, or decelerating."""
        avg_accel = (volume.volume_acceleration + on_chain.dau_growth_rate) / 2
        if avg_accel > 50:
            return "accelerating"
        elif avg_accel > -20:
            return "stable"
        else:
            return "decelerating"

    def _determine_revival_stage(self, score: float, momentum: str) -> str:
        """Determine revival stage."""
        if score < 30 or momentum == "decelerating":
            return "dormant"
        elif score < 50 and momentum == "accelerating":
            return "early_signs"
        elif score < 70:
            return "emerging"
        elif score >= 75 and momentum in ["accelerating", "stable"]:
            return "confirmed"
        else:
            return "emerging"

    def _estimate_peak_days(self, stage: str, acceleration: float) -> Optional[int]:
        """Estimate days until peak."""
        if stage == "dormant":
            return None
        elif stage == "early_signs":
            return 60
        elif stage == "emerging":
            return 30
        else:
            return 14
