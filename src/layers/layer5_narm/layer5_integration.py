"""
Phase 5: Layer 5 Integration Scorer

Combines NARM (Layer 5) + BCE (Layer 3) + X20 (Layer 4) for unified decision scoring.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class Layer5Decision(Enum):
    """Final integrated decision signal."""

    STRONG_BUY = "strong_buy"  # All conditions met
    BUY_ROTATION = "buy_rotation"  # NARM rotation + BCE valid + X20 ≥65
    RESEARCH = "research"  # NARM rotation but validation pending
    WATCHLIST = "watchlist"  # NARM rotation but BCE invalid
    HOLD = "hold"  # No rotation signal
    REJECT = "reject"  # Multiple negative signals


@dataclass
class Layer5DecisionSignal:
    """Complete Layer 5 decision output."""

    timestamp: datetime
    asset: str
    decision: Layer5Decision
    confidence_level: float  # 0-100

    # Component scores
    bce_score: float  # 0-6
    bce_valid: bool
    x20_score: float  # 0-100
    narm_score: float  # 0-100

    # Rotation signals
    is_rotation_candidate: bool
    rotation_strength: float  # 0-100
    capital_flow_confirmed: bool

    # Risk assessment
    risk_level: str  # low/medium/high
    position_size_recommendation: float  # % of portfolio

    # Reasoning trail
    reasoning: List[str]


class Layer5IntegrationScorer:
    """Integrate Layers 3, 4, 5 for unified decision scoring."""

    def __init__(self):
        """Initialize scorer."""
        self.decision_history: List[Layer5DecisionSignal] = []
        self.decision_cache: Dict[str, Layer5DecisionSignal] = {}

    def score_combined(
        self,
        asset: str,
        bce_signal: Dict,  # {bce_score, valid, components}
        x20_score: Dict,  # {x20_score, tier, confidence}
        narm_signal: Dict,  # {narm_score, narrative, adoption, capital_rotation}
        capital_flow_validated: Optional[bool] = None,
    ) -> Layer5DecisionSignal:
        """
        Combine Layer 3 (BCE) + Layer 4 (X20) + Layer 5 (NARM) scoring.

        Args:
            asset: Asset symbol
            bce_signal: BCE analysis result
            x20_score: X20 opportunity score
            narm_signal: NARM rotation signal
            capital_flow_validated: On-chain validation result

        Returns:
            Layer5DecisionSignal with final decision
        """
        timestamp = datetime.utcnow()

        # Extract scores
        bce_score = bce_signal.get("bce_score", 0.0)
        bce_valid = bce_signal.get("valid", False)
        x20_opportunity = x20_score.get("x20_opportunity_score", 0.0)
        narm_score = narm_signal.get("narm_score", 0.0)

        # Determine decision
        decision = self._determine_decision(
            bce_score=bce_score,
            bce_valid=bce_valid,
            x20_score=x20_opportunity,
            narm_score=narm_score,
            capital_flow_validated=capital_flow_validated,
        )

        # Calculate combined confidence
        confidence = self._calculate_confidence(
            decision=decision,
            bce_valid=bce_valid,
            x20_score=x20_opportunity,
            narm_score=narm_score,
        )

        # Rotation candidate if NARM ≥65
        is_rotation = narm_score >= 65.0
        rotation_strength = narm_score

        # Risk assessment
        risk_level = self._assess_risk(
            bce_score=bce_score,
            x20_score=x20_opportunity,
            narm_score=narm_score,
        )

        # Position sizing
        position_size = self._recommend_position_size(
            decision=decision,
            confidence=confidence,
            risk_level=risk_level,
        )

        # Build reasoning
        reasoning = self._build_layer5_reasoning(
            asset=asset,
            bce_score=bce_score,
            bce_valid=bce_valid,
            x20_score=x20_opportunity,
            narm_score=narm_score,
            decision=decision,
            risk_level=risk_level,
        )

        signal = Layer5DecisionSignal(
            timestamp=timestamp,
            asset=asset,
            decision=decision,
            confidence_level=confidence,
            bce_score=bce_score,
            bce_valid=bce_valid,
            x20_score=x20_opportunity,
            narm_score=narm_score,
            is_rotation_candidate=is_rotation,
            rotation_strength=rotation_strength,
            capital_flow_confirmed=capital_flow_validated or False,
            risk_level=risk_level,
            position_size_recommendation=position_size,
            reasoning=reasoning,
        )

        self.decision_history.append(signal)
        self.decision_cache[asset] = signal
        return signal

    def _determine_decision(
        self,
        bce_score: float,
        bce_valid: bool,
        x20_score: float,
        narm_score: float,
        capital_flow_validated: Optional[bool],
    ) -> Layer5Decision:
        """Determine final decision based on component scores."""

        # Decision matrix:
        # STRONG_BUY: X20≥75 + BCE≥5/6 + NARM≥65 + Capital flow confirmed
        if (
            bce_score >= 5.0
            and x20_score >= 75
            and narm_score >= 65
            and capital_flow_validated
        ):
            return Layer5Decision.STRONG_BUY

        # BUY_ROTATION: X20≥65 + BCE≥5/6 + NARM≥65 (no capital flow required)
        if bce_score >= 5.0 and x20_score >= 65 and narm_score >= 65:
            return Layer5Decision.BUY_ROTATION

        # RESEARCH: NARM≥65 + X20≥50 but BCE<5/6
        if not bce_valid and narm_score >= 65 and x20_score >= 50:
            return Layer5Decision.RESEARCH

        # WATCHLIST: NARM≥65 but BCE invalid and X20<50
        if not bce_valid and narm_score >= 65:
            return Layer5Decision.WATCHLIST

        # HOLD: Weak signals across the board
        if narm_score < 65 or x20_score < 50 or bce_score < 3.0:
            return Layer5Decision.HOLD

        # REJECT: Strong negative signals
        if not bce_valid and x20_score < 40 and narm_score < 50:
            return Layer5Decision.REJECT

        return Layer5Decision.HOLD

    def _calculate_confidence(
        self,
        decision: Layer5Decision,
        bce_valid: bool,
        x20_score: float,
        narm_score: float,
    ) -> float:
        """Calculate overall confidence 0-100."""
        base_confidence = 50.0

        # BCE contribution (max +25)
        if bce_valid:
            base_confidence += 25.0

        # X20 contribution (max +30)
        if x20_score >= 75:
            base_confidence += 30.0
        elif x20_score >= 65:
            base_confidence += 20.0
        elif x20_score >= 50:
            base_confidence += 10.0

        # NARM contribution (max +20)
        if narm_score >= 75:
            base_confidence += 20.0
        elif narm_score >= 65:
            base_confidence += 15.0
        elif narm_score >= 55:
            base_confidence += 8.0

        # Decision-specific adjustments
        if decision == Layer5Decision.STRONG_BUY:
            base_confidence = min(95.0, base_confidence * 1.1)
        elif decision == Layer5Decision.BUY_ROTATION:
            base_confidence = min(85.0, base_confidence)
        elif decision == Layer5Decision.RESEARCH:
            base_confidence = min(70.0, base_confidence * 0.9)
        elif decision == Layer5Decision.HOLD:
            base_confidence = min(55.0, base_confidence * 0.7)
        elif decision == Layer5Decision.REJECT:
            base_confidence = max(0.0, base_confidence * 0.3)

        return min(100.0, max(0.0, base_confidence))

    def _assess_risk(
        self,
        bce_score: float,
        x20_score: float,
        narm_score: float,
    ) -> str:
        """Assess overall risk level."""
        # Risk is low if all scores are high
        if bce_score >= 5.0 and x20_score >= 75 and narm_score >= 75:
            return "low"

        # Risk is medium if scores are moderate
        if bce_score >= 4.0 and x20_score >= 50 and narm_score >= 50:
            return "medium"

        # Risk is high otherwise
        return "high"

    def _recommend_position_size(
        self,
        decision: Layer5Decision,
        confidence: float,
        risk_level: str,
    ) -> float:
        """Recommend position size as % of portfolio."""
        # Base position by decision
        base_size = {
            Layer5Decision.STRONG_BUY: 5.0,
            Layer5Decision.BUY_ROTATION: 3.0,
            Layer5Decision.RESEARCH: 1.5,
            Layer5Decision.WATCHLIST: 0.5,
            Layer5Decision.HOLD: 0.0,
            Layer5Decision.REJECT: 0.0,
        }

        size = base_size.get(decision, 0.0)

        # Adjust by confidence
        size *= confidence / 100.0

        # Adjust by risk (lower risk = larger position)
        if risk_level == "high":
            size *= 0.5
        elif risk_level == "medium":
            size *= 0.8

        # Cap at 5% max position
        return min(5.0, max(0.0, size))

    def _build_layer5_reasoning(
        self,
        asset: str,
        bce_score: float,
        bce_valid: bool,
        x20_score: float,
        narm_score: float,
        decision: Layer5Decision,
        risk_level: str,
    ) -> List[str]:
        """Build detailed reasoning trail."""
        reasoning = [
            f"=== LAYER 5 INTEGRATED ANALYSIS: {asset.upper()} ===",
            f"",
            f"Component Scores:",
            f"  • BCE Score: {bce_score:.2f}/6 {'✓ VALID' if bce_valid else '✗ INVALID'}",
            f"  • X20 Score: {x20_score:.1f}/100",
            f"  • NARM Score: {narm_score:.1f}/100",
            f"",
            f"Decision: {decision.value.upper()}",
            f"Risk Level: {risk_level.upper()}",
        ]

        # BCE analysis
        if bce_valid:
            reasoning.append(f"✓ BCE valid (≥5/6) - Entry conditions met")
        else:
            reasoning.append(f"✗ BCE invalid (<5/6) - Entry conditions not met")

        # X20 analysis
        if x20_score >= 75:
            reasoning.append(f"✓ Strong opportunity: X20 ≥75")
        elif x20_score >= 65:
            reasoning.append(f"✓ Moderate opportunity: X20 ≥65")
        elif x20_score >= 50:
            reasoning.append(f"◐ Weak opportunity: X20 ≥50")
        else:
            reasoning.append(f"✗ Limited opportunity: X20 <50")

        # NARM analysis
        if narm_score >= 65:
            reasoning.append(
                f"✓ Rotation candidate: NARM ≥65 (narrative-driven)"
            )
        else:
            reasoning.append(f"✗ No rotation signal: NARM <65")

        # Decision explanation
        if decision == Layer5Decision.STRONG_BUY:
            reasoning.append(
                f"→ STRONG_BUY: All conditions met (BCE valid + X20≥75 + NARM≥65)"
            )
        elif decision == Layer5Decision.BUY_ROTATION:
            reasoning.append(
                f"→ BUY_ROTATION: Narrative-driven opportunity (BCE valid + NARM≥65)"
            )
        elif decision == Layer5Decision.RESEARCH:
            reasoning.append(
                f"→ RESEARCH: Monitor for BCE validation (strong opportunity + weak structure)"
            )
        elif decision == Layer5Decision.WATCHLIST:
            reasoning.append(
                f"→ WATCHLIST: Track narrative development (no entry until BCE valid)"
            )
        elif decision == Layer5Decision.HOLD:
            reasoning.append(f"→ HOLD: Insufficient signal strength")
        elif decision == Layer5Decision.REJECT:
            reasoning.append(f"→ REJECT: Multiple negative signals")

        return reasoning

    def get_decision_summary(self, asset: str) -> Optional[Dict]:
        """Get summary of decision for asset."""
        if asset not in self.decision_cache:
            return None

        signal = self.decision_cache[asset]
        return {
            "asset": asset,
            "decision": signal.decision.value,
            "confidence": signal.confidence_level,
            "bce_valid": signal.bce_valid,
            "x20_score": signal.x20_score,
            "narm_score": signal.narm_score,
            "risk": signal.risk_level,
            "position_size": signal.position_size_recommendation,
        }

    def rank_opportunities(
        self,
        limit: int = 10,
    ) -> List[Dict]:
        """Rank recent opportunities by decision signal."""
        # Filter to actionable signals
        actionable = [
            s
            for s in self.decision_history
            if s.decision
            in [
                Layer5Decision.STRONG_BUY,
                Layer5Decision.BUY_ROTATION,
                Layer5Decision.RESEARCH,
            ]
        ]

        # Sort by confidence
        ranked = sorted(
            actionable,
            key=lambda s: (
                s.decision.value,  # Decision tier
                s.confidence_level,
            ),
            reverse=True,
        )[:limit]

        return [
            {
                "asset": s.asset,
                "decision": s.decision.value,
                "confidence": s.confidence_level,
                "narm_score": s.narm_score,
                "x20_score": s.x20_score,
                "position_size": s.position_size_recommendation,
            }
            for s in ranked
        ]

    def audit_layer5_decisions(self) -> Dict:
        """Audit trail for Layer 5 decision quality."""
        if not self.decision_history:
            return {"error": "No decision history"}

        decisions_by_type = {}
        for signal in self.decision_history:
            decision_type = signal.decision.value
            if decision_type not in decisions_by_type:
                decisions_by_type[decision_type] = 0
            decisions_by_type[decision_type] += 1

        return {
            "total_decisions": len(self.decision_history),
            "decisions_by_type": decisions_by_type,
            "avg_confidence": (
                sum(s.confidence_level for s in self.decision_history)
                / len(self.decision_history)
            ),
            "avg_position_size": (
                sum(s.position_size_recommendation for s in self.decision_history)
                / len(self.decision_history)
            ),
            "high_risk_count": sum(
                1 for s in self.decision_history if s.risk_level == "high"
            ),
        }
