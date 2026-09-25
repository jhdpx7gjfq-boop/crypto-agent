#!/usr/bin/env python3
"""
Phase 5 Orchestration: Robustness Validation

Tests BCE model across market regimes, volatility levels, and confidence scores.

Timeline: Nov 14-20, 2026
Gate: >75% pass rate in all dimensions (Nov 17)
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase_5_robustness.robustness_tester import RobustnessTester

# Setup logging
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_5"
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
GT_DIR = DATA_DIR / "ground_truth" / "phase_2"


def find_ground_truth_csv() -> Path:
    """Find latest ground truth CSV"""
    frozen_dir = GT_DIR / "frozen_snapshots"
    if frozen_dir.exists():
        frozen_files = list(frozen_dir.glob("ground_truth_frozen_*.csv"))
        if frozen_files:
            return sorted(frozen_files)[-1]

    gt_files = list(GT_DIR.glob("labels_*.csv"))
    if gt_files:
        return sorted(gt_files)[-1]

    raise FileNotFoundError("No ground truth CSV found")


def main():
    """Main entry point"""
    logger.info("="*70)
    logger.info("PHASE 5: ROBUSTNESS VALIDATION ORCHESTRATION")
    logger.info("="*70)

    # Find ground truth
    try:
        gt_csv = find_ground_truth_csv()
        logger.info(f"Using ground truth: {gt_csv}")
    except FileNotFoundError as e:
        logger.error(f"Cannot proceed: {e}")
        sys.exit(1)

    # Run robustness tests
    try:
        tester = RobustnessTester()
        is_valid = tester.run_robustness_tests(gt_csv)
        results_file = tester.save_results()

        # Print summary
        summary = tester.results.get("summary", {})

        print("\n" + "="*70)
        print("ROBUSTNESS TEST RESULTS")
        print("="*70)

        for dim, pass_rate in summary.get("pass_rates_by_dimension", {}).items():
            print(f"{dim:30s}: {pass_rate:.1%}")

        print(f"\nOverall Pass Rate: {summary.get('overall_pass_rate', 0):.1%}")
        print(f"Gate Status: {summary.get('gate_status', 'UNKNOWN')}")
        print(f"\nResults saved to: {results_file}")

        if is_valid:
            print("\nNext: Phase 6 Final Validation Gate")
            sys.exit(0)
        else:
            print("\nReview failures and address robustness issues.")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Robustness testing failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
