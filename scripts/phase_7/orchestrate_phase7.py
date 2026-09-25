#!/usr/bin/env python3
"""
Phase 7 Orchestration: Smart Money Analysis

Collects and analyzes whale/institutional activity patterns.

Timeline: Dec 21-31, 2026 (post-VALIDATED_ALPHA)
Gate: Correlation with price established
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase_7_smart_money.smart_money_collector import SmartMoneyCollector

# Setup logging
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_7"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"orchestration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
DATA_DIR = Path(__file__).parent.parent.parent / "data"
PHASE1_DIR = DATA_DIR / "raw" / "phase_1"


def get_test_coins() -> list:
    """Get top coins from Phase 1 data"""
    if PHASE1_DIR.exists():
        coin_files = list(PHASE1_DIR.glob("*.parquet"))
        coins = [f.stem.rsplit("_", 1)[1] for f in coin_files[:20]]  # Top 20
        return coins
    return ["bitcoin", "ethereum", "solana", "cardano", "polkadot"]


def main():
    """Main entry point"""
    logger.info("="*70)
    logger.info("PHASE 7: SMART MONEY ANALYSIS ORCHESTRATION")
    logger.info("="*70)

    # Get coins to analyze
    coins = get_test_coins()
    logger.info(f"Analyzing {len(coins)} coins for smart money patterns")

    # Run analysis
    try:
        collector = SmartMoneyCollector()
        collector.run_full_analysis(coins)
        results_file = collector.save_results()

        print("\n" + "="*70)
        print("PHASE 7 COMPLETE")
        print("="*70)
        print(f"Results: {results_file}")
        print("\nNext: Phase 8 X20 Optimizer Engine")

        sys.exit(0)
    except Exception as e:
        logger.error(f"Phase 7 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
