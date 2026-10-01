"""RCM/RPM Engine — Rotation Confirmation Model (Phase 6, Layer 6)."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
import statistics

from .capital_flow_tracker import CapitalFlowTracker
from .relative_strength import RelativeStrengthAnalyzer
from .narrative_acceleration import NarrativeAccelerationEngine
from .fundamental_analyzer import FundamentalAnalyzer
from .derivatives_analyzer import DerivativesAnalyzer


class RCMDecision(str, Enum):
    """RCM decision outcomes."""

    CONFIRM = "confirm"
    MONITOR = "monitor"
    NEUTRAL = "neutral"
    REJECT = "reject"


@dataclass
class RCMSignal:
    """Complete RCM analysis signal."""

    asset: str
    timestamp: datetime
    rcm_score: float  # 0-100
    decision: RCMDecision
    confidence: float  # 0-1
    component_scores: Dict[str, float] = field(default_factory=dict)
    bullish_components: int = 0
    bearish_components: int = 0
    validation_status: str = "pending"
    layer5_narm_score: Optional[float] = None
    integration_with_layer5: str = ""


class RCMEngine:
    """Rotation Confirmation Model (RCM) / Rotation Prediction Model (RPM)."""

    def __init__(self):
        """Initialize RCM engine with component analyzers."""
        self.capital_flow = CapitalFlowTracker()
        self.relative_strength = RelativeStrengthAnalyzer()
        self.narrative_accel = NarrativeAccelerationEngine()
        self.fundamentals = FundamentalAnalyzer()
        self.derivatives = DerivativesAnalyzer()

        self.analysis_history: Dict[str, List[RCMSignal]] = {}
        self.decision_cache: Dict[str, RCMSignal] = {}

    def scan(
        self,
        asset: str,
        cf_score: float,
        rs_score: float,
        na_score: float,
        fund_score: float,
        deriv_score: float,
        layer5_narm: Optional[float] = None,
    ) -> RCMSignal:
        """Quick RCM scan with pre-calculated component scores."""
        rcm_score = (
            cf_score * 0.30
            + rs_score * 0.25
            + na_score * 0.20
            + fund_score * 0.20
            + deriv_score * 0.05
        )
        rcm_score = min(100, max(0, rcm_score))

        scores = [cf_score, rs_score, na_score, fund_score, deriv_score]
        bullish = sum(1 for s in scores if s > 65)
        bearish = sum(1 for s in scores if s < 40)

        # Decision
        if rcm_score >= 75:
            decision = RCMDecision.CONFIRM
            confidence = 0.85
        elif rcm_score >= 60:
            decision = RCMDecision.MONITOR
            confidence = 0.70
        elif rcm_score >= 45:
            decision = RCMDecision.NEUTRAL
            confidence = 0.55
        else:
            decision = RCMDecision.REJECT
            confidence = 0.65

        # Validation
        validation = "pending"
        alignment = "No Layer 5 signal"
        if layer5_narm is not None:
            is_rotation = layer5_narm >= 65
            if rcm_score >= 75 and is_rotation:
                validation = "confirmed"
                alignment = f"RCM {rcm_score:.0f} confirms L5 {layer5_narm:.0f}"
            elif rcm_score < 45 and is_rotation:
                validation = "rejected"
                alignment = f"RCM {rcm_score:.0f} rejects L5 {layer5_narm:.0f}"
            else:
                validation = "pending"
                alignment = f"RCM {rcm_score:.0f} vs L5 {layer5_narm:.0f}"

        signal = RCMSignal(
            asset=asset,
            timestamp=datetime.utcnow(),
            rcm_score=rcm_score,
            decision=decision,
            confidence=confidence,
            component_scores={
                "capital_flow": cf_score,
                "relative_strength": rs_score,
                "narrative_acceleration": na_score,
                "fundamentals": fund_score,
                "derivatives": deriv_score,
            },
            bullish_components=bullish,
            bearish_components=bearish,
            validation_status=validation,
            layer5_narm_score=layer5_narm,
            integration_with_layer5=alignment,
        )

        self.decision_cache[asset] = signal
        if asset not in self.analysis_history:
            self.analysis_history[asset] = []
        self.analysis_history[asset].append(signal)

        return signal

    def rank_opportunities(
        self, assets: List[str], limit: int = 10
    ) -> List[Dict]:
        """Rank assets by RCM score."""
        signals = [
            self.decision_cache[a]
            for a in assets
            if a in self.decision_cache
        ]

        ranked = sorted(
            signals,
            key=lambda x: (x.rcm_score, x.confidence),
            reverse=True,
        )

        return [
            {
                "asset": s.asset,
                "rcm_score": round(s.rcm_score, 1),
                "decision": s.decision.value,
                "confidence": round(s.confidence, 2),
                "components": s.component_scores,
            }
            for s in ranked[:limit]
        ]

    def get_decision_summary(self, asset: str) -> Optional[Dict]:
        """Get latest RCM decision."""
        if asset not in self.decision_cache:
            return None

        s = self.decision_cache[asset]
        return {
            "asset": asset,
            "rcm_score": round(s.rcm_score, 1),
            "decision": s.decision.value,
            "confidence": round(s.confidence, 2),
            "validation": s.validation_status,
            "bullish": s.bullish_components,
            "bearish": s.bearish_components,
        }

    def audit_rcm_decisions(self) -> Dict:
        """Audit RCM decision history."""
        total = sum(
            len(self.analysis_history.get(a, []))
            for a in self.analysis_history
        )

        decision_counts = {}
        all_scores = []

        for asset in self.analysis_history:
            for sig in self.analysis_history[asset]:
                dec = sig.decision.value
                decision_counts[dec] = decision_counts.get(dec, 0) + 1
                all_scores.append(sig.rcm_score)

        return {
            "total_decisions": total,
            "assets_analyzed": len(self.analysis_history),
            "decisions_by_type": decision_counts,
            "avg_rcm_score": (
                statistics.mean(all_scores) if all_scores else 0.0
            ),
        }
