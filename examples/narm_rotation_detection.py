#!/usr/bin/env python3
"""
NARM-P+ Rotation Detection Example

Demonstrates narrative adoption rotation scanning:
1. Layer 1: Fetch and validate OHLCV data
2. Layer 5: Run NARM-P+ scanner with narrative/adoption/capital flow signals
3. Output: Rotation candidate detection with timing assessment
"""

import logging
from datetime import datetime

from src.layers.layer1_data.collector import DataCollector
from src.layers.layer1_data.validator import DataValidator
from src.layers.layer5_narm.narm_engine import NARMEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run NARM-P+ rotation scanning."""

    logger.info("=" * 80)
    logger.info("IGWT-PF26 NARM-P+ Rotation Detection")
    logger.info("=" * 80)

    # Step 1: Fetch data
    logger.info("\n[LAYER 1] Collecting market data...")
    collector = DataCollector(use_mock=True)
    ohlcv_data = collector.fetch_coingecko("solana", days=365)

    if not ohlcv_data:
        logger.error("Failed to fetch OHLCV data")
        return

    logger.info(f"✓ Fetched {len(ohlcv_data)} candles for SOL")

    # Step 2: Validate data
    logger.info("\n[LAYER 1] Validating data quality...")
    validator = DataValidator()
    is_valid, summary, warnings = validator.validate_ohlcv_list(ohlcv_data, "SOL")

    logger.info(f"✓ {summary}")
    if warnings:
        for w in warnings[:2]:
            logger.warning(f"  {w}")

    if not is_valid:
        logger.error("Data validation failed")
        return

    # Step 3: Quick scan
    logger.info("\n[LAYER 5] Running quick NARM-P+ scan...")
    engine = NARMEngine()

    # Simulated narrative data
    narrative_data = {
        "narrative_momentum": 78,  # 0-100
        "media_sentiment": 72,  # 0-100
        "community_engagement": 85,  # 0-100
        "narrative_clarity": 68,  # 0-100
    }

    # Simulated adoption data
    adoption_data = {
        "user_growth_rate": 82,  # 0-100
        "developer_activity": 75,  # 0-100
        "transaction_growth": 80,  # 0-100
        "network_effects": 70,  # 0-100
    }

    # Simulated capital flow data
    capital_flow_data = {
        "capital_inflow_rate": 80,  # 0-100
        "sector_rotation_score": 75,  # 0-100
        "whale_accumulation": 68,  # 0-100
        "institutional_interest": 72,  # 0-100
    }

    signal = engine.scan(
        "SOL", ohlcv_data, narrative_data, adoption_data, capital_flow_data
    )

    logger.info(f"✓ NARM Score: {signal.narm_score:.1f}/100")
    logger.info(f"  Narrative Strength:   {signal.narrative_strength:.1f}/100")
    logger.info(f"  Adoption Velocity:    {signal.adoption_velocity:.1f}/100")
    logger.info(f"  Capital Rotation:     {signal.capital_rotation:.1f}/100")
    logger.info(f"  Rotation Valid:       {signal.rotation_valid}")

    # Step 4: Comprehensive analysis
    logger.info("\n[LAYER 5] Running comprehensive analysis...")
    report = engine.analyze(
        "SOL", ohlcv_data, narrative_data, adoption_data, capital_flow_data
    )

    # Print detailed report
    report_text = engine.generate_report_text(report)
    print(report_text)

    # Summary
    logger.info(f"{'='*80}")
    logger.info("ROTATION DETECTION SIGNAL")
    logger.info(f"{'='*80}")

    if report.is_rotation_candidate:
        logger.info("✓✓✓ ROTATION CANDIDATE DETECTED ✓✓✓")
        logger.info(f"Combined Score: {report.combined_score:.1f}/100")
        logger.info(f"Stage: {report.timing_assessment.upper()}")
        logger.info(f"Confidence: {report.rotation_confidence.upper()}")
    else:
        logger.info(f"⚠ Score below rotation threshold: {report.combined_score:.1f}/100")
        logger.info("  Requires ≥65 for rotation candidate classification")

    logger.info(f"{'='*80}\n")

    # Portfolio scan
    logger.info("\n[SCANNING NARRATIVE SECTORS]")
    logger.info("-" * 80)

    test_assets = [
        ("polygon", "MATIC", {"narrative_momentum": 65, "media_sentiment": 60}),
        ("avalanche-2", "AVAX", {"narrative_momentum": 70, "media_sentiment": 68}),
        ("cardano", "ADA", {"narrative_momentum": 55, "media_sentiment": 50}),
    ]

    for gecko_id, symbol, narrative_data_test in test_assets:
        try:
            ohlcv = collector.fetch_coingecko(gecko_id, days=90)
            if ohlcv and len(ohlcv) >= 20:
                signal = engine.scan(
                    symbol,
                    ohlcv,
                    narrative_data=narrative_data_test,
                    adoption_data={"user_growth_rate": 65},
                    capital_flow_data={"capital_inflow_rate": 60},
                )
                status = "✓" if signal.rotation_valid else "✗"
                logger.info(
                    f"{status} {symbol:6s} NARM: {signal.narm_score:6.1f}/100  Valid: {signal.rotation_valid}"
                )
        except Exception as e:
            logger.warning(f"Error scanning {symbol}: {e}")

    logger.info("-" * 80 + "\n")


if __name__ == "__main__":
    main()
