#!/usr/bin/env python3
"""
Phase 8 Orchestration: X20 Optimizer Engine

Multi-objective optimization for entry, position sizing, exits, rebalancing.

Timeline: Jan 1-7, 2027
Gate: Optimal parameters locked
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase_8_optimizer.x20_optimizer import X20Optimizer

# Setup logging
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_8"
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


def main():
    """Main entry point"""
    logger.info("="*70)
    logger.info("PHASE 8: X20 OPTIMIZER ENGINE ORCHESTRATION")
    logger.info("="*70)

    try:
        optimizer = X20Optimizer()
        optimizer.run_optimization()
        results_file = optimizer.save_results()

        print("\n" + "="*70)
        print("PHASE 8 COMPLETE")
        print("="*70)
        print(f"Results: {results_file}")
        print("\nNext: Phase 9 AI Research Copilot")

        sys.exit(0)
    except Exception as e:
        logger.error(f"Phase 8 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
