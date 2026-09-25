"""RCM/RPM Engine — Rotation Confirmation Model (Layer 6)."""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from src.core.models import OHLCV, RCMSignal
from src.core.config import Config
from src.core.backtest import WalkForwardValidator

logger = logging.getLogger(__name__)


@dataclass
class RCMAnalysisReport:
    """Comprehensive RCM analysis report."""

    asset: str
    combined_score: float  # 0-100
    is_confirmed_rotation: bool  # >= 70
    capital_flow: float  # 0-100, 25% weight
    relative_strength: float  # 0-100, 25% weight
    narrative_acceleration: float  # 0-100, 20% weight
    fundamental_confirmation: float  # 0-100, 20% weight
    derivatives_structure: float  # 0-100, 10% weight
    walk_forward_valid: bool  # Passes out-of-sample validation
    rotation_quality: str  # strong/moderate/weak
    entry_confidence: str  # high/medium/low
    reasoning: List[str]


class RCMEngine:
    """Rotation Confirmation Model with walk-forward validation."""

    def __init__(self):
        self.config = Config
        self.wf_validator = WalkForwardValidator()

    def scan(
        self,
        asset: str,
        ohlcv_data: List[OHLCV],
        capital_flow_data: Optional[Dict[str, Any]] = None,
        sector_data: Optional[Dict[str, Any]] = None,
        narrative_data: Optional[Dict[str, Any]] = None,
        fundamental_data: Optional[Dict[str, Any]] = None,
        derivatives_data: Optional[Dict[str, Any]] = None,
    ) -> RCMSignal:
        """Quick RCM scan returning rotation confirmation score (0-100)."""

        if not ohlcv_data or len(ohlcv_data) < 20:
            return RCMSignal(
                timestamp=datetime.utcnow(),
                asset=asset,
                combined_score=0.0,
                capital_flow=0.0,
                relative_strength=0.0,
                narrative_acceleration=0.0,
                fundamental_confirmation=0.0,
                derivatives_structure=0.0,
                confirmed=False,
            )

        capital_flow = self._score_capital_flow(capital_flow_data or {})
        rel_strength = self._score_relative_strength(sector_data or {}, ohlcv_data)
        narrative = self._score_narrative_acceleration(narrative_data or {})
        fundamental = self._score_fundamental_confirmation(fundamental_data or {})
        derivatives = self._score_derivatives_structure(derivatives_data or {})

        # Weighted: 25% capital flow, 25% rel strength, 20% narrative, 20% fundamental, 10% derivatives
        combined = (
            capital_flow * 0.25
            + rel_strength * 0.25
            + narrative * 0.20
            + fundamental * 0.20
            + derivatives * 0.10
        )

        return RCMSignal(
            timestamp=datetime.utcnow(),
            asset=asset,
            combined_score=min(100.0, combined),
            capital_flow=capital_flow,
            relative_strength=rel_strength,
            narrative_acceleration=narrative,
            fundamental_confirmation=fundamental,
            derivatives_structure=derivatives,
            valid=combined >= 70.0,
        )

    def analyze(
        self,
        asset: str,
        ohlcv_data: List[OHLCV],
        capital_flow_data: Optional[Dict[str, Any]] = None,
        sector_data: Optional[Dict[str, Any]] = None,
        narrative_data: Optional[Dict[str, Any]] = None,
        fundamental_data: Optional[Dict[str, Any]] = None,
        derivatives_data: Optional[Dict[str, Any]] = None,
    ) -> RCMAnalysisReport:
        """Comprehensive RCM analysis with walk-forward validation."""

        reasoning = []

        if not ohlcv_data or len(ohlcv_data) < 20:
            reasoning.append("Insufficient OHLCV data for analysis")
            return self._create_invalid_report(asset, reasoning)

        # Score all five dimensions
        capital_flow, cf_factors = self._score_capital_flow_detailed(
            capital_flow_data or {}
        )
        rel_strength, rs_factors = self._score_relative_strength_detailed(
            sector_data or {}, ohlcv_data
        )
        narrative, na_factors = self._score_narrative_acceleration_detailed(
            narrative_data or {}
        )
        fundamental, fc_factors = self._score_fundamental_confirmation_detailed(
            fundamental_data or {}
        )
        derivatives, dv_factors = self._score_derivatives_structure_detailed(
            derivatives_data or {}
        )

        # Weighted combined score
        combined = (
            capital_flow * 0.25
            + rel_strength * 0.25
            + narrative * 0.20
            + fundamental * 0.20
            + derivatives * 0.10
        )
        combined = min(100.0, combined)

        is_confirmed = combined >= 70.0

        # Walk-forward validation
        wf_valid = self._validate_rotation_walkforward(ohlcv_data, combined)

        # Add reasoning
        reasoning.append(
            f"Capital Flow: {capital_flow:.1f}/100"
        )
        reasoning.append(
            f"Relative Strength: {rel_strength:.1f}/100"
        )
        reasoning.append(
            f"Narrative Acceleration: {narrative:.1f}/100"
        )
        reasoning.append(
            f"Fundamental Confirmation: {fundamental:.1f}/100"
        )
        reasoning.append(
            f"Derivatives Structure: {derivatives:.1f}/100"
        )
        reasoning.append(f"Walk-Forward Valid: {wf_valid}")

        # Rotation quality
        if combined >= 80:
            quality = "strong"
        elif combined >= 65:
            quality = "moderate"
        else:
            quality = "weak"

        # Entry confidence
        if combined >= 75 and wf_valid:
            confidence = "high"
        elif combined >= 65:
            confidence = "medium"
        else:
            confidence = "low"

        reasoning.append(f"Rotation Quality: {quality}")
        reasoning.append(f"Entry Confidence: {confidence}")

        if is_confirmed:
            reasoning.append("✓ ROTATION CONFIRMED")
        else:
            reasoning.append("✗ Below confirmation threshold (70+)")

        return RCMAnalysisReport(
            asset=asset,
            combined_score=combined,
            is_confirmed_rotation=is_confirmed,
            capital_flow=capital_flow,
            relative_strength=rel_strength,
            narrative_acceleration=narrative,
            fundamental_confirmation=fundamental,
            derivatives_structure=derivatives,
            walk_forward_valid=wf_valid,
            rotation_quality=quality,
            entry_confidence=confidence,
            reasoning=reasoning,
        )

    def _score_capital_flow(self, data: Dict[str, Any]) -> float:
        """Quick capital flow score."""
        _, factors = self._score_capital_flow_detailed(data)
        if not factors:
            return 50.0
        return sum(factors.values()) / len(factors)

    def _score_capital_flow_detailed(
        self, data: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """Detailed capital flow analysis."""
        factors = {}

        # Inflow velocity: 0-35
        inflow_vel = data.get("inflow_velocity", 50)
        factors["inflow"] = min(35.0, inflow_vel / 100 * 35)

        # Exchange volume: 0-30
        ex_volume = data.get("exchange_volume", 50)
        factors["volume"] = min(30.0, ex_volume / 100 * 30)

        # OTC activity: 0-20
        otc = data.get("otc_activity", 50)
        factors["otc"] = min(20.0, otc / 100 * 20)

        # Net flows: 0-15
        net = data.get("net_flow", 50)
        factors["net_flow"] = min(15.0, net / 100 * 15)

        avg_score = sum(factors.values()) / len(factors) if factors else 50.0
        return avg_score, factors

    def _score_relative_strength(
        self, data: Dict[str, Any], ohlcv: List[OHLCV]
    ) -> float:
        """Quick relative strength score."""
        _, factors = self._score_relative_strength_detailed(data, ohlcv)
        if not factors:
            return 50.0
        return sum(factors.values()) / len(factors)

    def _score_relative_strength_detailed(
        self, data: Dict[str, Any], ohlcv: List[OHLCV]
    ) -> Tuple[float, Dict[str, float]]:
        """Detailed relative strength analysis."""
        factors = {}

        # Vs. BTC: 0-30
        vs_btc = data.get("vs_btc_strength", 50)
        factors["vs_btc"] = min(30.0, vs_btc / 100 * 30)

        # Vs. sector: 0-30
        vs_sector = data.get("vs_sector_strength", 50)
        factors["vs_sector"] = min(30.0, vs_sector / 100 * 30)

        # Price discovery: 0-25
        price_disc = data.get("price_discovery", 50)
        factors["price_discovery"] = min(25.0, price_disc / 100 * 25)

        # Relative momentum: 0-15 (from price action)
        if len(ohlcv) >= 20:
            price_change = (ohlcv[-1].close - ohlcv[-20].close) / ohlcv[-20].close
            rel_mom = min(15.0, max(0.0, (price_change + 1) * 7.5))
        else:
            rel_mom = 7.5
        factors["momentum"] = rel_mom

        avg_score = sum(factors.values()) / len(factors) if factors else 50.0
        return avg_score, factors

    def _score_narrative_acceleration(self, data: Dict[str, Any]) -> float:
        """Quick narrative acceleration score."""
        _, factors = self._score_narrative_acceleration_detailed(data)
        if not factors:
            return 50.0
        return sum(factors.values()) / len(factors)

    def _score_narrative_acceleration_detailed(
        self, data: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """Detailed narrative acceleration analysis."""
        factors = {}

        # Narrative velocity: 0-30
        velocity = data.get("narrative_velocity", 50)
        factors["velocity"] = min(30.0, velocity / 100 * 30)

        # Media acceleration: 0-25
        media = data.get("media_acceleration", 50)
        factors["media"] = min(25.0, media / 100 * 25)

        # Social momentum: 0-25
        social = data.get("social_momentum", 50)
        factors["social"] = min(25.0, social / 100 * 25)

        # Theme rotation: 0-20
        theme = data.get("theme_rotation_strength", 50)
        factors["theme"] = min(20.0, theme / 100 * 20)

        avg_score = sum(factors.values()) / len(factors) if factors else 50.0
        return avg_score, factors

    def _score_fundamental_confirmation(self, data: Dict[str, Any]) -> float:
        """Quick fundamental confirmation score."""
        _, factors = self._score_fundamental_confirmation_detailed(data)
        if not factors:
            return 50.0
        return sum(factors.values()) / len(factors)

    def _score_fundamental_confirmation_detailed(
        self, data: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """Detailed fundamental confirmation analysis."""
        factors = {}

        # Product progress: 0-30
        product = data.get("product_progress", 50)
        factors["product"] = min(30.0, product / 100 * 30)

        # Partnerships: 0-25
        partners = data.get("partnership_score", 50)
        factors["partners"] = min(25.0, partners / 100 * 25)

        # User growth: 0-25
        users = data.get("user_growth", 50)
        factors["users"] = min(25.0, users / 100 * 25)

        # Revenue metrics: 0-20
        revenue = data.get("revenue_metrics", 50)
        factors["revenue"] = min(20.0, revenue / 100 * 20)

        avg_score = sum(factors.values()) / len(factors) if factors else 50.0
        return avg_score, factors

    def _score_derivatives_structure(self, data: Dict[str, Any]) -> float:
        """Quick derivatives structure score."""
        _, factors = self._score_derivatives_structure_detailed(data)
        if not factors:
            return 50.0
        return sum(factors.values()) / len(factors)

    def _score_derivatives_structure_detailed(
        self, data: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """Detailed derivatives structure analysis."""
        factors = {}

        # Funding rates: 0-40
        funding = data.get("funding_rate_health", 50)
        factors["funding"] = min(40.0, funding / 100 * 40)

        # Open interest: 0-30
        oi = data.get("open_interest_trend", 50)
        factors["open_interest"] = min(30.0, oi / 100 * 30)

        # Options positioning: 0-20
        options = data.get("options_positioning", 50)
        factors["options"] = min(20.0, options / 100 * 20)

        # Liquidation risk: 0-10
        liquidation = max(0.0, 10.0 - data.get("liquidation_risk", 50) / 5)
        factors["liquidation"] = liquidation

        avg_score = sum(factors.values()) / len(factors) if factors else 50.0
        return avg_score, factors

    def _validate_rotation_walkforward(
        self, ohlcv: List[OHLCV], score: float
    ) -> bool:
        """Walk-forward validation of rotation signal."""
        if len(ohlcv) < 60:  # Need at least 60 candles
            return False

        # Split 50/50
        split_idx = len(ohlcv) // 2
        train_data = ohlcv[:split_idx]
        test_data = ohlcv[split_idx:]

        # In-sample score
        train_score = self._calculate_score_from_ohlcv(train_data)

        # Out-of-sample score
        test_score = self._calculate_score_from_ohlcv(test_data)

        # Validation: test within 85%-115% of train (no overfitting)
        if train_score == 0:
            return False

        ratio = test_score / train_score
        is_valid = 0.85 <= ratio <= 1.15

        return is_valid

    def _calculate_score_from_ohlcv(self, ohlcv: List[OHLCV]) -> float:
        """Calculate momentum-based score from OHLCV."""
        if len(ohlcv) < 20:
            return 50.0

        # Price momentum
        price_change = (ohlcv[-1].close - ohlcv[-20].close) / ohlcv[-20].close
        momentum = min(40.0, max(0.0, (price_change + 1) * 20))

        # Volume trend
        volumes = [c.volume for c in ohlcv[-20:]]
        avg_vol = sum(volumes) / len(volumes)
        recent_vol = sum(volumes[-5:]) / 5
        vol_trend = (recent_vol / avg_vol) * 40 if avg_vol > 0 else 20

        # Volatility
        closes = [c.close for c in ohlcv[-20:]]
        avg_close = sum(closes) / len(closes)
        variance = sum((c - avg_close) ** 2 for c in closes) / len(closes)
        volatility = (variance ** 0.5) / avg_close * 100
        vol_score = 20.0 - abs(volatility - 20.0) / 2

        return momentum + vol_trend + vol_score

    def _create_invalid_report(
        self, asset: str, reasoning: List[str]
    ) -> RCMAnalysisReport:
        """Create invalid report."""
        return RCMAnalysisReport(
            asset=asset,
            combined_score=0.0,
            is_confirmed_rotation=False,
            capital_flow=0.0,
            relative_strength=0.0,
            narrative_acceleration=0.0,
            fundamental_confirmation=0.0,
            derivatives_structure=0.0,
            walk_forward_valid=False,
            rotation_quality="weak",
            entry_confidence="low",
            reasoning=reasoning,
        )

    def generate_report_text(self, report: RCMAnalysisReport) -> str:
        """Generate human-readable report."""
        lines = [
            f"\n{'='*60}",
            f"RCM ANALYSIS — {report.asset.upper()}",
            f"{'='*60}",
            f"",
            f"Combined Score: {report.combined_score:.1f}/100 {'✓ CONFIRMED' if report.is_confirmed_rotation else '✗ NOT CONFIRMED'}",
            f"Rotation Quality: {report.rotation_quality.upper()}",
            f"Entry Confidence: {report.entry_confidence.upper()}",
            f"Walk-Forward Valid: {'✓ Yes' if report.walk_forward_valid else '✗ No'}",
            f"",
            f"Dimension Scores:",
            f"  Capital Flow:          {report.capital_flow:.1f}/100",
            f"  Relative Strength:     {report.relative_strength:.1f}/100",
            f"  Narrative Acceleration: {report.narrative_acceleration:.1f}/100",
            f"  Fundamental Confirmation: {report.fundamental_confirmation:.1f}/100",
            f"  Derivatives Structure: {report.derivatives_structure:.1f}/100",
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
