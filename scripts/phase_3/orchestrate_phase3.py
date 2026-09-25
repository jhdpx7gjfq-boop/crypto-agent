#!/usr/bin/env python3
"""
Phase 3 Orchestration: Walk-Forward Validation Pipeline

Runs PIT → OOS → WFV to validate BCE and scoring models.

Timeline: Oct 24-Nov 6, 2026
Gate: All three validations PASS (Oct 31 checkpoint)
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase_3_validation.pit_backtest import PITBacktest
from phase_3_validation.oos_validator import OOSValidator
from phase_3_validation.walk_forward_validator import WalkForwardValidator

# Setup logging
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_3"
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
VAL_DIR = DATA_DIR / "validation" / "phase_3"

VAL_DIR.mkdir(parents=True, exist_ok=True)


def find_ground_truth_csv() -> Path:
    """Find latest ground truth CSV from Phase 2"""
    frozen_dir = GT_DIR / "frozen_snapshots"
    if frozen_dir.exists():
        frozen_files = list(frozen_dir.glob("ground_truth_frozen_*.csv"))
        if frozen_files:
            return sorted(frozen_files)[-1]

    # Fallback to unfrozen
    gt_files = list(GT_DIR.glob("labels_*.csv"))
    if gt_files:
        return sorted(gt_files)[-1]

    raise FileNotFoundError("No ground truth CSV found")


def orchestrate_validation():
    """Run complete validation pipeline"""
    logger.info("="*70)
    logger.info("PHASE 3: WALK-FORWARD VALIDATION PIPELINE")
    logger.info("="*70)

    # Find ground truth
    try:
        gt_csv = find_ground_truth_csv()
        logger.info(f"Using ground truth: {gt_csv}")
    except FileNotFoundError as e:
        logger.error(f"Cannot proceed: {e}")
        return False

    results = {
        "timestamp": datetime.now().isoformat(),
        "phase": "3_validation_pipeline",
        "ground_truth": str(gt_csv),
        "validations": {}
    }

    # Step 1: PIT Backtest
    logger.info("\n" + "="*70)
    logger.info("STEP 1: PIT (PERIOD IN TIME) BACKTEST")
    logger.info("="*70)

    try:
        pit = PITBacktest()
        pit_pass = pit.validate_all(gt_csv)
        pit_results_file = pit.save_results()

        results["validations"]["pit"] = {
            "status": "PASS" if pit_pass else "FAIL",
            "results_file": str(pit_results_file),
            "summary": pit.results.get("summary", {})
        }

        logger.info(f"PIT Result: {'✓ PASS' if pit_pass else '✗ FAIL'}")
    except Exception as e:
        logger.error(f"PIT failed with error: {e}", exc_info=True)
        results["validations"]["pit"] = {"status": "ERROR", "error": str(e)}
        pit_pass = False

    # Step 2: OOS Validation
    logger.info("\n" + "="*70)
    logger.info("STEP 2: OOS (OUT-OF-SAMPLE) VALIDATION")
    logger.info("="*70)

    try:
        oos = OOSValidator()
        oos_pass = oos.validate_all(gt_csv)
        oos_results_file = oos.save_results()

        results["validations"]["oos"] = {
            "status": "PASS" if oos_pass else "FAIL",
            "results_file": str(oos_results_file),
            "summary": oos.results.get("summary", {})
        }

        logger.info(f"OOS Result: {'✓ PASS' if oos_pass else '✗ FAIL'}")
    except Exception as e:
        logger.error(f"OOS failed with error: {e}", exc_info=True)
        results["validations"]["oos"] = {"status": "ERROR", "error": str(e)}
        oos_pass = False

    # Step 3: WFV (Walk-Forward Validation)
    logger.info("\n" + "="*70)
    logger.info("STEP 3: WFV (WALK-FORWARD VALIDATION)")
    logger.info("="*70)

    try:
        wfv = WalkForwardValidator()
        wfv_pass = wfv.validate_all_windows(gt_csv)
        wfv_results_file = wfv.save_results()

        results["validations"]["wfv"] = {
            "status": "PASS" if wfv_pass else "FAIL",
            "results_file": str(wfv_results_file),
            "summary": wfv.results.get("summary", {})
        }

        logger.info(f"WFV Result: {'✓ PASS' if wfv_pass else '✗ FAIL'}")
    except Exception as e:
        logger.error(f"WFV failed with error: {e}", exc_info=True)
        results["validations"]["wfv"] = {"status": "ERROR", "error": str(e)}
        wfv_pass = False

    # Summary
    logger.info("\n" + "="*70)
    logger.info("VALIDATION PIPELINE SUMMARY")
    logger.info("="*70)

    all_pass = pit_pass and oos_pass and wfv_pass

    results["summary"] = {
        "pit_status": "PASS" if pit_pass else "FAIL",
        "oos_status": "PASS" if oos_pass else "FAIL",
        "wfv_status": "PASS" if wfv_pass else "FAIL",
        "overall_status": "PASS" if all_pass else "FAIL",
        "gate_decision": "PROCEED_TO_PHASE_4" if all_pass else "REVIEW_REQUIRED"
    }

    for key, value in results["validations"].items():
        logger.info(f"{key.upper()}: {value['status']}")

    logger.info(f"\nOverall: {results['summary']['overall_status']}")
    logger.info(f"Gate Decision: {results['summary']['gate_decision']}")

    # Save orchestration results
    orch_results_file = VAL_DIR / f"phase3_orchestration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(orch_results_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"\nOrchestration results: {orch_results_file}")

    return all_pass


def main():
    """Main entry point"""
    success = orchestrate_validation()

    if success:
        print("\n" + "="*70)
        print("✓ PHASE 3 VALIDATION COMPLETE")
        print("="*70)
        print("All validations PASSED. Ready for Phase 4: Ablation Analysis")
        sys.exit(0)
    else:
        print("\n" + "="*70)
        print("✗ PHASE 3 VALIDATION FAILED")
        print("="*70)
        print("Review validation results and address issues before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()
