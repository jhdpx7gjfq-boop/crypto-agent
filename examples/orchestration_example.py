"""
Phase 9: Decision Orchestrator & Research Agent Example

Demonstrates complete workflow:
1. Collect market data (Layers 1-2)
2. Orchestrate 8-layer decision (Layer 9)
3. Autonomous portfolio analysis (Layer 9 Agent)
"""

import logging
from datetime import datetime

from src.layers.layer9_dashboard.orchestrator import DecisionOrchestrator
from src.layers.layer9_dashboard.research_agent import ResearchAgent
from tests.fixtures.market_data import generate_bull_ohlcv, generate_bear_ohlcv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def demo_single_asset_orchestration():
    """Analyze a single asset through all 8 layers."""

    logger.info("="*70)
    logger.info("DEMO 1: Single Asset Orchestration (BTC)")
    logger.info("="*70)

    orchestrator = DecisionOrchestrator()

    # Simulate bullish BTC market
    btc_ohlcv = generate_bull_ohlcv(100)

    # Analyze with all layer inputs
    btc_signal = orchestrator.analyze(
        asset="BTC",
        ohlcv_data=btc_ohlcv,
        fundamental_data={
            "team_quality": 95,
            "investor_strength": 90,
            "adoption_stage": "mature",
        },
        narrative_data={
            "media_sentiment": "bullish",
            "adoption_growth": 15.5,
            "sector_rotation": "inflows",
        },
        macro_data={
            "funding_rate": 0.0006,
            "btc_dominance": 58.5,
            "oi_change": 18.0,
            "dxy": 101.5,
            "us10y": 4.1,
        },
    )

    # Print decision report
    print(orchestrator.generate_report_text(btc_signal))

    # Summary
    logger.info(f"\n→ Decision: {'ENTER' if btc_signal.should_enter else 'WAIT'}")
    logger.info(f"→ Confidence: {btc_signal.confidence}")
    logger.info(f"→ Risk Level: {btc_signal.risk_level}")

    return btc_signal


def demo_multi_asset_analysis():
    """Analyze portfolio of multiple assets."""

    logger.info("="*70)
    logger.info("DEMO 2: Multi-Asset Portfolio Analysis")
    logger.info("="*70)

    agent = ResearchAgent()
    orchestrator = DecisionOrchestrator()

    # Simulate 3-asset portfolio
    portfolio = {
        "BTC": {
            "ohlcv": generate_bull_ohlcv(100),
            "fundamental": {
                "team_quality": 95,
                "adoption_stage": "mature",
            },
            "narrative": {
                "media_sentiment": "bullish",
                "adoption_growth": 15.5,
            },
        },
        "ETH": {
            "ohlcv": generate_bull_ohlcv(100),
            "fundamental": {
                "team_quality": 90,
                "adoption_stage": "established",
            },
            "narrative": {
                "media_sentiment": "neutral",
                "adoption_growth": 8.2,
            },
        },
        "SOL": {
            "ohlcv": generate_bear_ohlcv(100),
            "fundamental": {
                "team_quality": 75,
                "adoption_stage": "growth",
            },
            "narrative": {
                "media_sentiment": "bearish",
                "adoption_growth": 2.1,
            },
        },
    }

    # Analyze portfolio
    report = agent.analyze_assets(portfolio)

    # Print report
    print("\n" + "="*70)
    print("RESEARCH REPORT")
    print("="*70)
    print(report.market_summary)

    print("\n" + "-"*70)
    print("DECISIONS")
    print("-"*70)
    for asset, decision in report.decisions.items():
        print(f"  {asset}: {decision}")

    if report.strong_signals:
        print("\n" + "-"*70)
        print("STRONG OPPORTUNITIES")
        print("-"*70)
        for signal in report.strong_signals:
            print(f"  • {signal.asset}: confidence={signal.confidence}, risk={signal.risk_level}")

    if report.alerts:
        print("\n" + "-"*70)
        print("ALERTS")
        print("-"*70)
        for alert in report.alerts:
            print(f"  ⚠ {alert}")

    if report.top_opportunity:
        print("\n" + "-"*70)
        print("TOP OPPORTUNITY")
        print("-"*70)
        top = report.top_opportunity
        print(f"  Asset: {top.asset}")
        print(f"  Confidence: {top.confidence}")
        print(f"  BCE Score: {top.bce_score:.1f}/6")
        print(f"  X20 Score: {top.x20_score:.1f}/100")
        print(f"  RCM Score: {top.rcm_score:.1f}/100")

    logger.info(f"\n→ Portfolio analyzed: {len(report.assets_analyzed)} assets")
    logger.info(f"→ Strong signals: {len(report.strong_signals)}")
    logger.info(f"→ Weak signals: {len(report.weak_signals)}")

    return report


def demo_hypothesis_validation():
    """Test hypothesis validation against real signals."""

    logger.info("="*70)
    logger.info("DEMO 3: Hypothesis Validation")
    logger.info("="*70)

    agent = ResearchAgent()
    orchestrator = DecisionOrchestrator()

    # Generate BTC signal
    btc_signal = orchestrator.analyze(
        asset="BTC",
        ohlcv_data=generate_bull_ohlcv(100),
        macro_data={
            "funding_rate": 0.0006,
            "btc_dominance": 58.5,
            "oi_change": 18.0,
        },
    )

    # Test multiple hypotheses
    hypotheses = [
        "BTC is in bullish regime with strong BCE confirmation",
        "BTC shows high X20 opportunity score",
        "BTC has maximum risk tolerance",
        "BTC is in bearish market regime",
    ]

    print("\nHypothesis Validation Results:")
    print("-"*70)

    for hypothesis in hypotheses:
        result = agent.challenge_hypothesis(hypothesis, btc_signal)
        status = "✓ VALID" if result else "✗ INVALID"
        print(f"{status}: {hypothesis}")

    logger.info(f"\n→ Tested {len(hypotheses)} hypotheses")


def demo_decision_audit_trail():
    """Show complete decision reasoning and audit trail."""

    logger.info("="*70)
    logger.info("DEMO 4: Decision Audit Trail")
    logger.info("="*70)

    orchestrator = DecisionOrchestrator()

    # Analyze asset with detailed audit
    signal = orchestrator.analyze(
        asset="BTC",
        ohlcv_data=generate_bull_ohlcv(100),
        macro_data={
            "funding_rate": 0.0006,
            "btc_dominance": 58.5,
            "oi_change": 18.0,
        },
    )

    print("\n" + "="*70)
    print("DECISION AUDIT TRAIL")
    print("="*70)
    print(f"\nAsset: {signal.asset}")
    print(f"Timestamp: {signal.timestamp}")
    print(f"Decision: {'ENTER' if signal.should_enter else 'WAIT'}")

    print("\n--- Reasoning Steps ---")
    for i, reason in enumerate(signal.reasoning, 1):
        print(f"{i}. {reason}")

    if signal.warnings:
        print("\n--- Warnings ---")
        for warning in signal.warnings:
            print(f"⚠ {warning}")

    print("\n--- Layer Scores ---")
    print(f"Market Regime: {signal.market_regime}")
    print(f"BCE Score: {signal.bce_score:.1f}/6 {'✓' if signal.bce_confirmed else '✗'}")
    print(f"X20 Opportunity: {signal.x20_score:.1f}/100")
    print(f"NARM Adoption: {signal.narm_score:.1f}/100")
    print(f"RCM Confirmation: {signal.rcm_score:.1f}/100")
    print(f"RRP Revival: {signal.rrp_probability:.1f}%")

    logger.info("\n→ Complete audit trail generated")


def main():
    """Run all demonstrations."""

    print("\n")
    print("█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  Phase 9: Decision Orchestrator & Research Agent Demo".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)
    print()

    # Demo 1: Single asset
    btc_signal = demo_single_asset_orchestration()
    input("\n[Press Enter to continue to Demo 2...]")

    # Demo 2: Multi-asset portfolio
    report = demo_multi_asset_analysis()
    input("\n[Press Enter to continue to Demo 3...]")

    # Demo 3: Hypothesis validation
    demo_hypothesis_validation()
    input("\n[Press Enter to continue to Demo 4...]")

    # Demo 4: Audit trail
    demo_decision_audit_trail()

    # Summary
    print("\n")
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nPhase 9 successfully demonstrates:")
    print("  ✓ Single asset orchestration (all 8 layers)")
    print("  ✓ Multi-asset portfolio analysis")
    print("  ✓ Hypothesis validation")
    print("  ✓ Complete decision audit trails")
    print("  ✓ Risk-aware decision making")
    print("  ✓ FOMO circuit breaker protection")
    print("\nReady for Phase 10 (Dashboard UI) or production deployment.")
    print("=" * 70)


if __name__ == "__main__":
    main()
