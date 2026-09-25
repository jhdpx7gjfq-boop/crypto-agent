#!/usr/bin/env python3
"""
Phase 4 Orchestration: Ablation Analysis

Analyzes which BCE components are critical vs non-critical.

Timeline: Nov 7-13, 2026
Gate: Component ranking finalized (Nov 10)
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase_4_ablation.ablation_analyzer import AblationAnalyzer

# Setup logging
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_4"
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
    logger.info("PHASE 4: ABLATION ANALYSIS ORCHESTRATION")
    logger.info("="*70)

    # Find ground truth
    try:
        gt_csv = find_ground_truth_csv()
        logger.info(f"Using ground truth: {gt_csv}")
    except FileNotFoundError as e:
        logger.error(f"Cannot proceed: {e}")
        sys.exit(1)

    # Run ablation study
    try:
        analyzer = AblationAnalyzer()
        analyzer.run_ablation_study(gt_csv)
        results_file = analyzer.save_results()

        # Print summary
        summary = analyzer.results.get("summary", {})

        print("\n" + "="*70)
        print("ABLATION ANALYSIS RESULTS")
        print("="*70)
        print(f"Baseline F1: {summary.get('baseline_f1', 0):.3f}")
        print(f"Critical Components ({len(summary.get('critical_components', []))}):")

        for item in summary.get("ranking", []):
            print(f"  {item['rank']}. {item['component']:30s} Impact: {item['impact']:+.3f}")

        print(f"\nResults saved to: {results_file}")
        print("\nNext: Phase 5 Robustness Validation")

        sys.exit(0)

    except Exception as e:
        logger.error(f"Ablation analysis failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
