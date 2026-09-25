"""NARM-P+ Engine — Narrative Adoption Rotation Model (Layer 5)."""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from src.core.models import OHLCV, NARMSignal
from src.core.config import Config

logger = logging.getLogger(__name__)


@dataclass
class NARMAnalysisReport:
    """Comprehensive NARM-P+ analysis report."""

    asset: str
    combined_score: float  # 0-100
    is_rotation_candidate: bool  # >= 65
    narrative_strength: float  # 0-100
    adoption_velocity: float  # 0-100
    capital_rotation: float  # 0-100
    momentum_score: float  # 0-100
    narrative_factors: Dict[str, float]
    adoption_factors: Dict[str, float]
    rotation_factors: Dict[str, float]
    momentum_factors: Dict[str, float]
    rotation_confidence: str  # high/medium/low
    timing_assessment: str  # early/mid/late stage
    reasoning: List[str]


class NARMEngine:
    """Narrative Adoption Rotation Model + Premium (NARM-P+)."""

    def __init__(self):
        self.config = Config

    def scan(
        self,
        asset: str,
        ohlcv_data: List[OHLCV],
        narrative_data: Optional[Dict[str, Any]] = None,
        adoption_data: Optional[Dict[str, Any]] = None,
        capital_flow_data: Optional[Dict[str, Any]] = None,
    ) -> NARMSignal:
        """Quick NARM scan returning rotation score (0-100)."""

        if not ohlcv_data or len(ohlcv_data) < 20:
            return NARMSignal(
                timestamp=datetime.utcnow(),
                asset=asset,
                narm_score=0.0,
                narrative_strength=0.0,
                adoption_velocity=0.0,
                capital_rotation=0.0,
                rotation_valid=False,
            )

        narrative = self._score_narrative(narrative_data or {})
        adoption = self._score_adoption(adoption_data or {})
        rotation = self._score_capital_rotation(capital_flow_data or {})
        momentum = self._score_momentum(ohlcv_data)

        # Weighted: 30% narrative, 25% adoption, 25% capital rotation, 20% momentum
        combined = (
            narrative * 0.30 + adoption * 0.25 + rotation * 0.25 + momentum * 0.20
        )

        return NARMSignal(
            timestamp=datetime.utcnow(),
            asset=asset,
            narm_score=min(100.0, combined),
            narrative_strength=narrative,
            adoption_velocity=adoption,
            capital_rotation=rotation,
            rotation_valid=combined >= 65.0,
        )

    def analyze(
        self,
        asset: str,
        ohlcv_data: List[OHLCV],
        narrative_data: Optional[Dict[str, Any]] = None,
        adoption_data: Optional[Dict[str, Any]] = None,
        capital_flow_data: Optional[Dict[str, Any]] = None,
    ) -> NARMAnalysisReport:
        """Comprehensive NARM-P+ analysis with reasoning."""

        reasoning = []

        if not ohlcv_data or len(ohlcv_data) < 20:
            reasoning.append("Insufficient OHLCV data for analysis")
            return self._create_invalid_report(asset, reasoning)

        # Score all four dimensions
        narrative, narrative_factors = self._score_narrative_detailed(
            narrative_data or {}
        )
        adoption, adoption_factors = self._score_adoption_detailed(
            adoption_data or {}
        )
        rotation, rotation_factors = self._score_capital_rotation_detailed(
            capital_flow_data or {}
        )
        momentum, momentum_factors = self._score_momentum_detailed(ohlcv_data)

        # Weighted combined score
        combined = (
            narrative * 0.30 + adoption * 0.25 + rotation * 0.25 + momentum * 0.20
        )
        combined = min(100.0, combined)

        is_rotation = combined >= 65.0

        # Add reasoning
        reasoning.append(
            f"Narrative Strength: {narrative:.1f}/100 ({', '.join([f'{k}: {v:.0f}' for k, v in narrative_factors.items()])})"
        )
        reasoning.append(
            f"Adoption Velocity: {adoption:.1f}/100 ({', '.join([f'{k}: {v:.0f}' for k, v in adoption_factors.items()])})"
        )
        reasoning.append(
            f"Capital Rotation: {rotation:.1f}/100 ({', '.join([f'{k}: {v:.0f}' for k, v in rotation_factors.items()])})"
        )
        reasoning.append(
            f"Momentum Score: {momentum:.1f}/100 ({', '.join([f'{k}: {v:.0f}' for k, v in momentum_factors.items()])})"
        )

        # Rotation confidence
        if combined >= 75:
            confidence = "high"
        elif combined >= 60:
            confidence = "medium"
        else:
            confidence = "low"

        # Timing assessment (based on adoption + narrative)
        if adoption >= 70 and narrative >= 70:
            timing = "late"  # Strong adoption and narrative = late stage
        elif adoption >= 50 or narrative >= 60:
            timing = "mid"  # Moderate adoption/narrative = mid stage
        else:
            timing = "early"  # Low adoption/narrative = early stage

        reasoning.append(f"Rotation Confidence: {confidence}")
        reasoning.append(f"Timing Assessment: {timing} stage")

        if is_rotation:
            reasoning.append("✓ ROTATION CANDIDATE DETECTED")
        else:
            reasoning.append("✗ Below rotation threshold (65+)")

        return NARMAnalysisReport(
            asset=asset,
            combined_score=combined,
            is_rotation_candidate=is_rotation,
            narrative_strength=narrative,
            adoption_velocity=adoption,
            capital_rotation=rotation,
            momentum_score=momentum,
            narrative_factors=narrative_factors,
            adoption_factors=adoption_factors,
            rotation_factors=rotation_factors,
            momentum_factors=momentum_factors,
            rotation_confidence=confidence,
            timing_assessment=timing,
            reasoning=reasoning,
        )

    def _score_narrative(self, data: Dict[str, Any]) -> float:
        """Quick narrative strength score (0-100)."""
        _, factors = self._score_narrative_detailed(data)
        if not factors:
            return 50.0
        return sum(factors.values()) / len(factors)

    def _score_narrative_detailed(
        self, data: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """Detailed narrative strength analysis."""
        factors = {}

        # Narrative momentum: 0-30
        momentum = data.get("narrative_momentum", 50)
        factors["momentum"] = min(30.0, momentum / 100 * 30)

        # Media sentiment: 0-25
        sentiment = data.get("media_sentiment", 50)
        if isinstance(sentiment, str):
            sentiment_map = {"bullish": 75, "neutral": 50, "bearish": 25}
            sentiment = sentiment_map.get(sentiment.lower(), 50)
        factors["sentiment"] = min(25.0, sentiment / 100 * 25)

        # Community engagement: 0-25
        engagement = data.get("community_engagement", 50)
        factors["engagement"] = min(25.0, engagement / 100 * 25)

        # Story compellingness: 0-20
        story = data.get("narrative_clarity", 50)
        factors["story_strength"] = min(20.0, story / 100 * 20)

        avg_score = sum(factors.values()) / len(factors) if factors else 50.0
        return avg_score, factors

    def _score_adoption(self, data: Dict[str, Any]) -> float:
        """Quick adoption velocity score (0-100)."""
        _, factors = self._score_adoption_detailed(data)
        if not factors:
            return 50.0
        return sum(factors.values()) / len(factors)

    def _score_adoption_detailed(
        self, data: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """Detailed adoption velocity analysis."""
        factors = {}

        # User growth: 0-30
        user_growth = data.get("user_growth_rate", 50)
        factors["user_growth"] = min(30.0, user_growth / 100 * 30)

        # Developer activity: 0-25
        dev_activity = data.get("developer_activity", 50)
        factors["dev_activity"] = min(25.0, dev_activity / 100 * 25)

        # Transaction volume growth: 0-25
        tx_growth = data.get("transaction_growth", 50)
        factors["tx_growth"] = min(25.0, tx_growth / 100 * 25)

        # Network effects: 0-20
        network = data.get("network_effects", 50)
        factors["network_effects"] = min(20.0, network / 100 * 20)

        avg_score = sum(factors.values()) / len(factors) if factors else 50.0
        return avg_score, factors

    def _score_capital_rotation(self, data: Dict[str, Any]) -> float:
        """Quick capital rotation score (0-100)."""
        _, factors = self._score_capital_rotation_detailed(data)
        if not factors:
            return 50.0
        return sum(factors.values()) / len(factors)

    def _score_capital_rotation_detailed(
        self, data: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """Detailed capital rotation analysis."""
        factors = {}

        # Inflow detection: 0-30
        inflow = data.get("capital_inflow_rate", 50)
        factors["inflow"] = min(30.0, inflow / 100 * 30)

        # Sector rotation: 0-25
        sector_rot = data.get("sector_rotation_score", 50)
        factors["sector_rotation"] = min(25.0, sector_rot / 100 * 25)

        # Whale accumulation: 0-25
        whale = data.get("whale_accumulation", 50)
        factors["whale_accumulation"] = min(25.0, whale / 100 * 25)

        # Fund flows: 0-20
        funds = data.get("institutional_interest", 50)
        factors["institutional_flow"] = min(20.0, funds / 100 * 20)

        avg_score = sum(factors.values()) / len(factors) if factors else 50.0
        return avg_score, factors

    def _score_momentum(self, ohlcv: List[OHLCV]) -> float:
        """Quick momentum score (0-100)."""
        _, factors = self._score_momentum_detailed(ohlcv)
        if not factors:
            return 50.0
        return sum(factors.values()) / len(factors)

    def _score_momentum_detailed(
        self, ohlcv: List[OHLCV]
    ) -> Tuple[float, Dict[str, float]]:
        """Detailed momentum analysis from price action."""
        factors = {}

        if len(ohlcv) < 20:
            return 50.0, {"insufficient_data": 50.0}

        # Price momentum: 0-30 (20-period change)
        price_change = (ohlcv[-1].close - ohlcv[-20].close) / ohlcv[-20].close
        momentum_score = min(30.0, max(0.0, (price_change + 1) * 15))
        factors["price_momentum"] = momentum_score

        # Volume trend: 0-25 (recent vs historical)
        volumes = [c.volume for c in ohlcv[-20:]]
        avg_vol = sum(volumes) / len(volumes)
        recent_vol = sum(volumes[-5:]) / 5
        vol_trend = (recent_vol / avg_vol) * 25 if avg_vol > 0 else 12.5
        factors["volume_trend"] = max(0.0, min(25.0, vol_trend))

        # Volatility expansion: 0-25
        closes = [c.close for c in ohlcv[-20:]]
        avg_close = sum(closes) / len(closes)
        variance = sum((c - avg_close) ** 2 for c in closes) / len(closes)
        volatility = (variance ** 0.5) / avg_close * 100
        # Moderate volatility expansion = good momentum
        vol_score = 25.0 - abs(volatility - 20.0) / 2
        factors["volatility_expansion"] = max(0.0, min(25.0, vol_score))

        # Breakout strength: 0-20
        recent_high = max(c.high for c in ohlcv[-10:])
        historical_high = max(c.high for c in ohlcv[-40:-10])
        breakout = 20.0 if recent_high > historical_high else 5.0
        factors["breakout_strength"] = breakout

        avg_score = sum(factors.values()) / len(factors) if factors else 50.0
        return avg_score, factors

    def _create_invalid_report(
        self, asset: str, reasoning: List[str]
    ) -> NARMAnalysisReport:
        """Create invalid report."""
        return NARMAnalysisReport(
            asset=asset,
            combined_score=0.0,
            is_rotation_candidate=False,
            narrative_strength=0.0,
            adoption_velocity=0.0,
            capital_rotation=0.0,
            momentum_score=0.0,
            narrative_factors={},
            adoption_factors={},
            rotation_factors={},
            momentum_factors={},
            rotation_confidence="low",
            timing_assessment="unknown",
            reasoning=reasoning,
        )

    def generate_report_text(self, report: NARMAnalysisReport) -> str:
        """Generate human-readable report."""
        lines = [
            f"\n{'='*60}",
            f"NARM-P+ ANALYSIS — {report.asset.upper()}",
            f"{'='*60}",
            f"",
            f"Combined Score: {report.combined_score:.1f}/100 {'✓ ROTATION' if report.is_rotation_candidate else '✗ NOT QUALIFIED'}",
            f"Rotation Confidence: {report.rotation_confidence.upper()}",
            f"Timing: {report.timing_assessment.upper()} STAGE",
            f"",
            f"Dimension Scores:",
            f"  Narrative Strength:   {report.narrative_strength:.1f}/100",
            f"  Adoption Velocity:    {report.adoption_velocity:.1f}/100",
            f"  Capital Rotation:     {report.capital_rotation:.1f}/100",
            f"  Momentum Score:       {report.momentum_score:.1f}/100",
            f"",
            f"Analysis:",
        ]

        for reason in report.reasoning:
            lines.append(f"  • {reason}")

        lines.extend([
            f"",
            f"{'='*60}",
            f"",
        ])

        return "\n".join(lines)
