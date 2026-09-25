#!/usr/bin/env python3
"""
Phase 9 Orchestration: AI Research Copilot

Claude-powered decision support for the IGWT-PF26 Cabal Brain.

Timeline: Jan 8-14, 2027
Gate: Copilot operational
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase_9_copilot.research_copilot import ResearchCopilot

# Setup logging
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_9"
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
    logger.info("PHASE 9: AI RESEARCH COPILOT ORCHESTRATION")
    logger.info("="*70)

    try:
        copilot = ResearchCopilot()
        copilot.run_full_copilot()
        results_file = copilot.save_results()

        print("\n" + "="*70)
        print("IGWT-PF26 COMPLETE")
        print("="*70)
        print(f"Results: {results_file}")
        print("\nAll 9 phases implemented and operational")
        print("System ready for live market deployment")

        sys.exit(0)
    except Exception as e:
        logger.error(f"Phase 9 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
