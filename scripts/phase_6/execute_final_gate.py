#!/usr/bin/env python3
"""
Phase 6 Execution: Final Validation Gate

Aggregates all validation results and decides on VALIDATED_ALPHA status.

Timeline: Dec 1-20, 2026
Decision: VALIDATED_ALPHA (production ready) or REJECT
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase_6_gate.final_validation_gate import FinalValidationGate

# Setup logging
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_6"
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
    logger.info("IGWT-PF26 PHASE 6: FINAL VALIDATION GATE")
    logger.info("="*70)
    logger.info("\nExecuting comprehensive system validation...")
    logger.info("Checking all phases (1-5) for production readiness...\n")

    gate = FinalValidationGate()
    is_validated = gate.run_final_gate()

    decision_file = gate.save_decision()

    print("\n" + "="*70)
    print("FINAL GATE DECISION")
    print("="*70)

    if is_validated:
        print("\n🟢 VALIDATED_ALPHA")
        print("\nThe IGWT-PF26 system is APPROVED for production deployment.")
        print("\nSystem Status: Ready for live market deployment")
        print("Next: Deploy mobile dashboard and begin live monitoring")
        print("\nDecision file:", decision_file)
        sys.exit(0)
    else:
        print("\n🔴 REJECT")
        print("\nThe IGWT-PF26 system requires additional work.")
        print("\nPlease review the decision file for details on which phases failed.")
        print("Decision file:", decision_file)
        sys.exit(1)


if __name__ == "__main__":
    main()
