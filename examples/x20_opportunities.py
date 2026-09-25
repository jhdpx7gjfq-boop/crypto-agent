#!/usr/bin/env python3
"""
X20 Opportunity Scanner Example

Demonstrates asymmetric opportunity detection:
1. Layer 1: Fetch and validate OHLCV data
2. Layer 4: Run X20 scanner with fundamental/narrative/quantitative signals
3. Output: Opportunity detection with multi-factor analysis
"""

import logging
from datetime import datetime

from src.layers.layer1_data.collector import DataCollector
from src.layers.layer1_data.validator import DataValidator
from src.layers.layer4_x20.x20_engine import X20Scanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run X20 opportunity scanning."""

    logger.info("=" * 80)
    logger.info("IGWT-PF26 X20 Opportunity Detection")
    logger.info("=" * 80)

    # Step 1: Fetch data
    logger.info("\n[LAYER 1] Collecting market data...")
    collector = DataCollector(use_mock=True)
    ohlcv_data = collector.fetch_coingecko("ethereum", days=365)

    if not ohlcv_data:
        logger.error("Failed to fetch OHLCV data")
        return

    logger.info(f"✓ Fetched {len(ohlcv_data)} candles for ETH")

    # Step 2: Validate data
    logger.info("\n[LAYER 1] Validating data quality...")
    validator = DataValidator()
    is_valid, summary, warnings = validator.validate_ohlcv_list(ohlcv_data, "ETH")

    logger.info(f"✓ {summary}")
    if warnings:
        for w in warnings[:2]:
            logger.warning(f"  {w}")

    if not is_valid:
        logger.error("Data validation failed")
        return

    # Step 3: Quick scan
    logger.info("\n[LAYER 4] Running quick X20 scan...")
    scanner = X20Scanner()

    # Simulated fundamental data
    fundamental_data = {
        "team_quality": "elite",  # elite/strong/adequate/unknown
        "investors": ["Paradigm", "Sequoia", "Binance Labs"],
        "tokenomics_score": 78,  # 0-100
        "adoption_score": 82,  # 0-100
    }

    # Simulated narrative data
    narrative_data = {
        "sector": "L2/Scaling",
        "sector_growth": 85,  # 0-100
        "media_attention": 72,  # 0-100
        "capital_inflow_score": 80,  # 0-100
        "competitive_advantage": 75,  # 0-100
    }

    opportunity = scanner.scan(
        "ETH", ohlcv_data, fundamental_data, narrative_data
    )

    logger.info(f"✓ Combined Score: {opportunity.combined_score:.1f}/100")
    logger.info(
        f"  Fundamental:    {opportunity.fundamental_score:.1f}/100"
    )
    logger.info(f"  Narrative:      {opportunity.narrative_score:.1f}/100")
    logger.info(
        f"  Quantitative:   {opportunity.quantitative_score:.1f}/100"
    )

    # Step 4: Comprehensive analysis
    logger.info("\n[LAYER 4] Running comprehensive analysis...")
    report = scanner.analyze(
        "ETH", ohlcv_data, fundamental_data, narrative_data
    )

    # Print detailed report
    report_text = scanner.generate_report_text(report)
    print(report_text)

    # Summary
    logger.info(f"{'='*80}")
    logger.info("DECISION SIGNAL")
    logger.info(f"{'='*80}")

    if report.is_opportunity:
        logger.info("✓✓✓ X20 OPPORTUNITY DETECTED ✓✓✓")
        logger.info(f"Combined Score: {report.combined_score:.1f}/100")
        logger.info(f"Asymmetric Ratio: {report.asymmetric_ratio:.2f}x potential return")
        logger.info(f"Risk Level: {report.risk_assessment.upper()}")
    else:
        logger.info(f"⚠ Score below threshold: {report.combined_score:.1f}/100")
        logger.info("  Requires ≥70 for X20 opportunity classification")

    logger.info(f"{'='*80}\n")

    # Test with additional assets
    logger.info("\n[SCANNING PORTFOLIO]")
    logger.info("-" * 80)

    test_assets = [
        ("solana", "SOL", {"team_quality": "strong", "adoption_score": 85}),
        ("polygon", "MATIC", {"team_quality": "strong", "adoption_score": 70}),
        ("avalanche-2", "AVAX", {"team_quality": "adequate", "adoption_score": 65}),
    ]

    for gecko_id, symbol, fund_data in test_assets:
        try:
            ohlcv = collector.fetch_coingecko(gecko_id, days=90)
            if ohlcv and len(ohlcv) >= 20:
                opp = scanner.scan(
                    symbol,
                    ohlcv,
                    fundamental_data=fund_data,
                    narrative_data={"sector_growth": 75},
                )
                status = "✓" if opp.combined_score >= 70 else "✗"
                logger.info(
                    f"{status} {symbol:6s} Score: {opp.combined_score:6.1f}/100"
                )
        except Exception as e:
            logger.warning(f"Error scanning {symbol}: {e}")

    logger.info("-" * 80 + "\n")


if __name__ == "__main__":
    main()
