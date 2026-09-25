#!/usr/bin/env python3
"""
End-to-End IGWT-PF26 Analysis Example

Demonstrates complete pipeline:
1. Layer 1: Data collection & validation
2. Layer 2: Market regime detection
3. Layer 3: Wyckoff BCE analysis
4. Decision: Multi-confirmation signal
"""

import logging
from datetime import datetime

from src.layers.layer1_data.collector import DataCollector, DataStore
from src.layers.layer1_data.validator import DataValidator
from src.layers.layer2_regime.regime_engine import MarketRegimeDetector
from src.layers.layer3_wyckoff.bce_analyzer import BCEAnalyzer
from src.core.pipeline import DecisionPipeline


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run end-to-end analysis."""

    logger.info("=" * 80)
    logger.info("IGWT-PF26 End-to-End Analysis")
    logger.info("=" * 80)

    # Step 1: Fetch data
    logger.info("\n[LAYER 1] Collecting market data...")
    collector = DataCollector(use_mock=True)  # Use mock data for demo
    ohlcv_data = collector.fetch_coingecko("bitcoin", days=365)

    if not ohlcv_data:
        logger.error("Failed to fetch OHLCV data")
        return

    logger.info(f"✓ Fetched {len(ohlcv_data)} candles for BTC")

    # Step 2: Validate data
    logger.info("\n[LAYER 1] Validating data quality...")
    validator = DataValidator()
    is_valid, summary, warnings = validator.validate_ohlcv_list(ohlcv_data, "BTC")

    logger.info(f"✓ {summary}")
    if warnings:
        for w in warnings[:3]:  # Show first 3 warnings
            logger.warning(f"  {w}")

    if not is_valid:
        logger.error("Data validation failed")
        return

    # Step 3: Market regime detection
    logger.info("\n[LAYER 2] Detecting market regime...")
    regime_detector = MarketRegimeDetector()
    regime = regime_detector.detect_regime()

    logger.info(f"✓ Market regime: {regime.regime.value}")
    logger.info(f"  BTC Dominance: {regime.btc_dominance:.1f}%")
    logger.info(f"  Funding Rate: {regime.funding_rate:.5f}")
    logger.info(f"  Macro Score: {regime.macro_score:.1f}/100")

    # Step 4: Wyckoff BCE analysis
    logger.info("\n[LAYER 3] Running Wyckoff bottom confirmation analysis...")
    analyzer = BCEAnalyzer()
    bce_report = analyzer.analyze("BTC", ohlcv_data)

    # Print report
    report_text = analyzer.generate_report_text(bce_report)
    print(report_text)

    # Step 5: Decision pipeline
    logger.info("\n[PIPELINE] Generating final decision signal...")
    pipeline = DecisionPipeline()

    # Create signal using pipeline
    from src.core.models import WyckoffSignal

    # Create BCE signal from report
    bce_signal = WyckoffSignal(
        timestamp=datetime.utcnow(),
        asset="BTC",
        bce_score=bce_report.bce_score,
        wyckoff_structure=bce_report.components.get("structure", 0),
        volume_analysis=bce_report.components.get("volume", 0),
        selling_exhaustion=bce_report.components.get("exhaustion", 0),
        smart_money_accumulation=bce_report.components.get("smart_money", 0),
        market_structure=bce_report.components.get("market_struct", 0),
        momentum_confirmation=bce_report.components.get("momentum", 0),
    )

    decision_signal = pipeline.process_asset(
        asset="BTC",
        ohlcv_data=ohlcv_data,
        market_regime=regime,
        wyckoff_signal=bce_signal,
    )

    logger.info(f"\n{'='*80}")
    logger.info(f"FINAL DECISION SIGNAL")
    logger.info(f"{'='*80}")
    logger.info(f"Asset: {decision_signal.asset}")
    logger.info(f"Signal: {decision_signal.signal_type.value}")
    logger.info(f"Confidence: {decision_signal.confidence:.1f}%")
    logger.info(f"Reason: {decision_signal.reason}")
    logger.info(f"Risk Level: {decision_signal.risk_level}")
    logger.info(f"{'='*80}\n")

    # Summary
    if decision_signal.signal_type.value == "long":
        logger.info("✓✓✓ ENTRY SIGNAL VALID — Multi-confirmation achieved ✓✓✓")
    else:
        logger.info(f"⚠ No entry signal ({decision_signal.signal_type.value})")

    # Save data for later analysis
    logger.info("\n[I/O] Saving analysis data...")
    store = DataStore()
    store.save_ohlcv_json("BTC", ohlcv_data[-100:])  # Save last 100 candles
    logger.info("✓ Data saved")


if __name__ == "__main__":
    main()
