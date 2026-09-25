"""
Layer 8 - Decision Support Engine (Research Infrastructure)

NOT alpha production. NOT automated trading.

Purpose: Aggregate all 7 research signals into unified decision support dashboard
for HUMAN qualitative analysis.

Approach:
- Combine Spring + Regime + Flow + NARM-P+ + RPM + RRP
- Weight by reliability (not alpha, but research signal strength)
- Generate decision alerts with supporting evidence
- Enable human override at all levels
"""

import pandas as pd
import numpy as np
from typing import Dict, List, NamedTuple
from dataclasses import dataclass


@dataclass
class DecisionSignal:
    """Single research signal contributing to decision."""
    layer_name: str
    signal_type: str  # 'bullish', 'bearish', 'neutral'
    confidence: float  # [0, 1] - research strength, NOT trading confidence
    evidence: str  # Human-readable explanation
    timestamp: str


@dataclass
class DecisionAlert:
    """Unified decision recommendation from all layers."""
    asset: str
    decision: str  # 'INVESTIGATE_LONG', 'INVESTIGATE_SHORT', 'MONITOR', 'SKIP'
    confidence_score: float  # [0, 100] - aggregate research signal strength
    signals: List[DecisionSignal]  # Contributing evidence
    rationale: str  # Why this decision
    human_required: bool  # Always true - no auto execution
    warnings: List[str]  # Risk flags


class Layer8DecisionSupport:
    """Aggregate research signals into human decision support."""

    def __init__(self):
        """Initialize decision engine."""
        self.signals = []
        self.alerts = []

    def ingest_spring_signal(self, symbol: str, spring_detected: bool,
                            confidence: float) -> DecisionSignal:
        """Ingest Spring Detector (Wyckoff) signal."""
        signal_type = 'bullish' if spring_detected else 'neutral'

        signal = DecisionSignal(
            layer_name='Spring Detector (Layer 3)',
            signal_type=signal_type,
            confidence=confidence,
            evidence=f"Wyckoff spring pattern {'detected' if spring_detected else 'not detected'}",
            timestamp=pd.Timestamp.now().isoformat()
        )

        self.signals.append(signal)
        return signal

    def ingest_regime_signal(self, symbol: str, regime: str,
                            bullish_probability: float) -> DecisionSignal:
        """Ingest Market Regime signal."""
        regime_map = {
            'Bull': ('bullish', bullish_probability),
            'Bear': ('bearish', 1 - bullish_probability),
            'Accumulation': ('neutral', bullish_probability * 0.5),
        }

        signal_type, confidence = regime_map.get(regime, ('neutral', 0.5))

        signal = DecisionSignal(
            layer_name='Regime Engine (Layer 2)',
            signal_type=signal_type,
            confidence=confidence,
            evidence=f"Regime: {regime} (bullish prob: {bullish_probability:.1%})",
            timestamp=pd.Timestamp.now().isoformat()
        )

        self.signals.append(signal)
        return signal

    def ingest_flow_signal(self, symbol: str, flow_direction: str,
                          magnitude: float) -> DecisionSignal:
        """Ingest Capital Flow signal."""
        signal_type = 'bullish' if flow_direction == 'inflow' else 'bearish'
        confidence = min(abs(magnitude), 1.0)

        signal = DecisionSignal(
            layer_name='Capital Flow (Layer 2)',
            signal_type=signal_type,
            confidence=confidence,
            evidence=f"Flow {flow_direction}: {magnitude:+.3f}",
            timestamp=pd.Timestamp.now().isoformat()
        )

        self.signals.append(signal)
        return signal

    def ingest_narm_signal(self, symbol: str, narrative_score: float,
                          adoption_trend: str) -> DecisionSignal:
        """Ingest NARM-P+ Narrative signal."""
        signal_type = 'bullish' if narrative_score > 50 else 'bearish'
        confidence = abs(narrative_score - 50) / 50  # Distance from neutral

        signal = DecisionSignal(
            layer_name='NARM-P+ (Layer 5)',
            signal_type=signal_type,
            confidence=confidence,
            evidence=f"Narrative: {narrative_score:.0f}/100 | Adoption: {adoption_trend}",
            timestamp=pd.Timestamp.now().isoformat()
        )

        self.signals.append(signal)
        return signal

    def ingest_rpm_signal(self, symbol: str, rotation_detected: bool,
                         rotation_strength: float) -> DecisionSignal:
        """Ingest RPM Capital Rotation signal."""
        signal_type = 'bullish' if rotation_detected else 'neutral'
        confidence = rotation_strength if rotation_detected else 0.0

        signal = DecisionSignal(
            layer_name='RPM/RCM (Layer 6)',
            signal_type=signal_type,
            confidence=confidence,
            evidence=f"Capital rotation {'detected' if rotation_detected else 'not detected'}: {rotation_strength:.2f}",
            timestamp=pd.Timestamp.now().isoformat()
        )

        self.signals.append(signal)
        return signal

    def ingest_rrp_signal(self, symbol: str, revival_confidence: float) -> DecisionSignal:
        """Ingest RRP Revival signal."""
        signal_type = 'bullish' if revival_confidence > 50 else 'neutral'
        confidence = revival_confidence / 100.0  # Normalize to [0, 1]

        signal = DecisionSignal(
            layer_name='RRP Revival (Layer 7)',
            signal_type=signal_type,
            confidence=confidence,
            evidence=f"Revival confidence: {revival_confidence:.0f}/100",
            timestamp=pd.Timestamp.now().isoformat()
        )

        self.signals.append(signal)
        return signal

    def aggregate_decision(self, asset: str, all_signals: List[DecisionSignal]) -> DecisionAlert:
        """
        Aggregate all signals into human decision recommendation.

        NOTE: NOT a trading signal. NOT investment advice.
        This is RESEARCH SUPPORT for human analysis.
        """
        if not all_signals:
            return DecisionAlert(
                asset=asset,
                decision='SKIP',
                confidence_score=0,
                signals=[],
                rationale='No signals available',
                human_required=True,
                warnings=['Insufficient data']
            )

        # Weight signals by research strength
        bullish_weight = sum(s.confidence for s in all_signals if s.signal_type == 'bullish')
        bearish_weight = sum(s.confidence for s in all_signals if s.signal_type == 'bearish')
        neutral_weight = sum(s.confidence for s in all_signals if s.signal_type == 'neutral')

        total_weight = bullish_weight + bearish_weight + neutral_weight

        if total_weight == 0:
            net_score = 50
        else:
            net_score = (bullish_weight / total_weight) * 100

        # Decision logic (NOT for trading, for RESEARCH)
        if net_score > 70:
            decision = 'INVESTIGATE_LONG'
            rationale = f"Multiple bullish research signals ({len([s for s in all_signals if s.signal_type == 'bullish'])} layers)"
        elif net_score < 30:
            decision = 'INVESTIGATE_SHORT'
            rationale = f"Multiple bearish research signals ({len([s for s in all_signals if s.signal_type == 'bearish'])} layers)"
        elif 50 <= net_score <= 60:
            decision = 'MONITOR'
            rationale = "Mixed signals. Requires human analysis."
        else:
            decision = 'SKIP'
            rationale = "Insufficient or conflicting research signals."

        # Always generate warnings (research infrastructure, not trading)
        warnings = [
            '⚠️  RESEARCH SIGNAL ONLY - Not a trading recommendation',
            '⚠️  Layers 1-7 failed production gate criteria - use qualitatively only',
            '⚠️  Human judgment required for all decisions',
            '⚠️  No automated execution. Manual review mandatory.',
        ]

        return DecisionAlert(
            asset=asset,
            decision=decision,
            confidence_score=float(net_score),
            signals=all_signals,
            rationale=rationale,
            human_required=True,
            warnings=warnings
        )

    def generate_report(self, alert: DecisionAlert) -> str:
        """Generate human-readable decision report."""
        report = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║ IGWT-PF26: RESEARCH DECISION SUPPORT REPORT
║ Asset: {alert.asset} | Decision: {alert.decision} | Score: {alert.confidence_score:.0f}/100
╚═══════════════════════════════════════════════════════════════════════════════╝

⚠️  DISCLAIMERS:
{chr(10).join('  ' + w for w in alert.warnings)}

RESEARCH RATIONALE:
  {alert.rationale}

CONTRIBUTING SIGNALS:
"""
        for i, signal in enumerate(alert.signals, 1):
            report += f"""
  {i}. {signal.layer_name}
     Signal: {signal.signal_type.upper()}
     Evidence: {signal.evidence}
     Strength: {signal.confidence:.1%}
"""

        report += f"""
DECISION:
  {alert.decision}

NEXT STEP:
  ➜ Human analysis required
  ➜ Review all contributing signals above
  ➜ Consider external factors not captured by quantitative models
  ➜ Make human-driven decision
  ➜ NO automatic execution

═══════════════════════════════════════════════════════════════════════════════
Generated: {pd.Timestamp.now().isoformat()}
System: IGWT-PF26 Research Infrastructure v1.0
"""
        return report

    def get_all_alerts(self) -> List[DecisionAlert]:
        """Return all generated alerts."""
        return self.alerts
