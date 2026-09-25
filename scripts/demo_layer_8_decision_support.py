#!/usr/bin/env python
"""
Demo: Layer 8 Decision Support Engine

Shows how all 7 research layers aggregate into unified decision recommendation.

⚠️  IMPORTANT: This is RESEARCH SUPPORT, NOT trading signal.
Layers 1-7 failed production gate criteria. Use qualitatively only.
Human judgment required for all decisions.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'research'))

from layer_8_decision_support import Layer8DecisionSupport


def demo_bullish_case():
    """Demo: Multiple bullish signals."""
    print("=" * 80)
    print("SCENARIO 1: Bullish Confluence (Multiple Research Signals)")
    print("=" * 80)
    print()

    engine = Layer8DecisionSupport()

    # Asset: Bitcoin in bull market with revival signals
    signals = [
        engine.ingest_spring_signal('BTC', spring_detected=True, confidence=0.85),
        engine.ingest_regime_signal('BTC', regime='Bull', bullish_probability=0.8),
        engine.ingest_flow_signal('BTC', flow_direction='inflow', magnitude=0.7),
        engine.ingest_narm_signal('BTC', narrative_score=75, adoption_trend='accelerating'),
        engine.ingest_rpm_signal('BTC', rotation_detected=True, rotation_strength=0.7),
        engine.ingest_rrp_signal('BTC', revival_confidence=78),
    ]

    alert = engine.aggregate_decision('BTC', signals)
    report = engine.generate_report(alert)
    print(report)

    return alert


def demo_bearish_case():
    """Demo: Multiple bearish signals."""
    print()
    print("=" * 80)
    print("SCENARIO 2: Bearish Confluence (Risk Signals)")
    print("=" * 80)
    print()

    engine = Layer8DecisionSupport()

    # Asset: Altcoin in bear market
    signals = [
        engine.ingest_spring_signal('ALT', spring_detected=False, confidence=0.9),
        engine.ingest_regime_signal('ALT', regime='Bear', bullish_probability=0.2),
        engine.ingest_flow_signal('ALT', flow_direction='outflow', magnitude=-0.8),
        engine.ingest_narm_signal('ALT', narrative_score=25, adoption_trend='declining'),
        engine.ingest_rpm_signal('ALT', rotation_detected=False, rotation_strength=0.1),
        engine.ingest_rrp_signal('ALT', revival_confidence=20),
    ]

    alert = engine.aggregate_decision('ALT', signals)
    report = engine.generate_report(alert)
    print(report)

    return alert


def demo_mixed_case():
    """Demo: Conflicting signals (requires human judgment)."""
    print()
    print("=" * 80)
    print("SCENARIO 3: Mixed Signals (Ambiguous - Requires Human Analysis)")
    print("=" * 80)
    print()

    engine = Layer8DecisionSupport()

    # Asset: Token with conflicting signals
    signals = [
        engine.ingest_spring_signal('MIX', spring_detected=True, confidence=0.6),
        engine.ingest_regime_signal('MIX', regime='Accumulation', bullish_probability=0.5),
        engine.ingest_flow_signal('MIX', flow_direction='inflow', magnitude=0.3),
        engine.ingest_narm_signal('MIX', narrative_score=50, adoption_trend='stable'),
        engine.ingest_rpm_signal('MIX', rotation_detected=False, rotation_strength=0.2),
        engine.ingest_rrp_signal('MIX', revival_confidence=55),
    ]

    alert = engine.aggregate_decision('MIX', signals)
    report = engine.generate_report(alert)
    print(report)

    return alert


def main():
    """Run all demos."""
    print()
    print("╔═══════════════════════════════════════════════════════════════════════════════╗")
    print("║ IGWT-PF26: RESEARCH DECISION SUPPORT ENGINE DEMO                             ║")
    print("║ Layer 8: Signal Aggregation & Research Infrastructure                        ║")
    print("╚═══════════════════════════════════════════════════════════════════════════════╝")
    print()

    print("⚠️  CRITICAL DISCLAIMER:")
    print("   • This is RESEARCH SUPPORT infrastructure, NOT trading signals")
    print("   • Layers 1-7 FAILED production gate criteria")
    print("   • Use qualitatively for human analysis ONLY")
    print("   • NO automated execution. Human judgment required.")
    print()

    # Run scenarios
    alert1 = demo_bullish_case()
    alert2 = demo_bearish_case()
    alert3 = demo_mixed_case()

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Scenario 1 (Bullish):    {alert1.decision} (Score: {alert1.confidence_score:.0f}/100)")
    print(f"Scenario 2 (Bearish):    {alert2.decision} (Score: {alert2.confidence_score:.0f}/100)")
    print(f"Scenario 3 (Mixed):      {alert3.decision} (Score: {alert3.confidence_score:.0f}/100)")
    print()

    print("USE CASES:")
    print("  ✓ Identify research opportunities for deeper investigation")
    print("  ✓ Aggregate multiple research perspectives")
    print("  ✓ Flag ambiguous situations requiring human expertise")
    print("  ✓ Support human-driven decision making")
    print()

    print("NOT FOR:")
    print("  ✗ Automated trading execution")
    print("  ✗ Production alpha generation")
    print("  ✗ Systematic strategy implementation")
    print("  ✗ Backtesting performance claims")
    print()

    print("=" * 80)
    print("Demo Complete")
    print("=" * 80)


if __name__ == '__main__':
    main()
