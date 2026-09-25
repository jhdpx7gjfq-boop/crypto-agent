#!/usr/bin/env python3
"""
Phase 2 Orchestration: Ground Truth Labeling & Freeze

Coordinates:
1. Interactive labeling session
2. CSV import/export
3. Validation checkpoint
4. Immutable freeze

Timeline: Oct 16-23, 2026
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase_2_ground_truth.labeling_interface import LabelingInterface
from phase_2_ground_truth.validate_ground_truth import GroundTruthValidator, GroundTruthFreezer

# Setup logging
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_2"
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


def get_coin_list() -> list:
    """Load coin list from Phase 1 data"""
    logger.info("Loading coin list from Phase 1...")
    phase1_dir = DATA_DIR / "raw" / "phase_1"

    coin_files = list(phase1_dir.glob("*.parquet"))
    coin_list = []

    for f in coin_files:
        # Filename format: SYMBOL_coin_id.parquet
        parts = f.stem.rsplit("_", 1)
        if len(parts) == 2:
            symbol, coin_id = parts
            coin_list.append((coin_id, symbol))

    logger.info(f"Loaded {len(coin_list)} coins from Phase 1")
    return sorted(coin_list)


def step_1_labeling_interactive() -> Tuple[int, int]:
    """Step 1: Interactive labeling session"""
    logger.info("="*60)
    logger.info("STEP 1: INTERACTIVE LABELING SESSION")
    logger.info("="*60)

    coin_list = get_coin_list()
    interface = LabelingInterface()

    labeled_count, skipped_count = interface.label_coins_interactive(coin_list)

    # Export to CSV
    labels_csv = GT_DIR / f"labels_interactive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    interface.export_to_csv(labels_csv)

    # Export summary
    summary = interface.get_summary()
    summary_file = GT_DIR / f"labeling_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Labeled: {labeled_count}, Skipped: {skipped_count}")
    logger.info(f"Labels saved to: {labels_csv}")
    logger.info(f"Summary saved to: {summary_file}")

    return labeled_count, skipped_count


def step_2_csv_import(csv_file: Path) -> int:
    """Step 2: Import pre-labeled CSV"""
    logger.info("="*60)
    logger.info("STEP 2: CSV IMPORT")
    logger.info("="*60)

    interface = LabelingInterface()
    count = interface.import_from_csv(csv_file)

    # Export to standard location
    labels_csv = GT_DIR / f"labels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    interface.export_to_csv(labels_csv)

    logger.info(f"Imported {count} labels from {csv_file}")
    logger.info(f"Exported to: {labels_csv}")

    return count


def step_3_validation(labels_csv: Path) -> bool:
    """Step 3: Validate ground truth"""
    logger.info("="*60)
    logger.info("STEP 3: GROUND TRUTH VALIDATION")
    logger.info("="*60)

    validator = GroundTruthValidator()
    is_valid = validator.validate_all(labels_csv)

    # Save report
    report = validator.save_validation_report()
    logger.info(f"Validation report: {report}")

    return is_valid


def step_4_freeze(labels_csv: Path) -> Tuple[Path, Path]:
    """Step 4: Freeze ground truth (immutable snapshot)"""
    logger.info("="*60)
    logger.info("STEP 4: IMMUTABLE FREEZE")
    logger.info("="*60)

    freezer = GroundTruthFreezer()
    snapshot, sha256 = freezer.create_immutable_snapshot(labels_csv)
    cert = freezer.create_freeze_certificate(snapshot, sha256)

    logger.info(f"Snapshot: {snapshot}")
    logger.info(f"Certificate: {cert}")
    logger.info(f"SHA256: {sha256}")

    return snapshot, cert


def orchestrate_full_pipeline(mode: str = "interactive"):
    """Execute full Phase 2 pipeline"""
    logger.info("="*60)
    logger.info("PHASE 2 ORCHESTRATION: GROUND TRUTH LABELING & FREEZE")
    logger.info("="*60)

    try:
        # Step 1: Labeling
        if mode == "interactive":
            labeled, skipped = step_1_labeling_interactive()
            labels_csv = GT_DIR / f"labels_interactive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        elif mode == "import":
            print("Usage: python3 orchestrate_phase2.py import <csv_file>")
            sys.exit(1)
        else:
            logger.error(f"Unknown mode: {mode}")
            return False

        # Step 2: Validation
        is_valid = step_3_validation(labels_csv)

        if not is_valid:
            logger.error("Validation FAILED - Review report and correct labels")
            return False

        # Step 3: Freeze
        snapshot, cert = step_4_freeze(labels_csv)

        logger.info("="*60)
        logger.info("PHASE 2 COMPLETE - GROUND TRUTH FROZEN")
        logger.info("="*60)
        logger.info(f"✓ Snapshot: {snapshot}")
        logger.info(f"✓ Certificate: {cert}")
        logger.info("✓ Proceeding to Phase 3: Walk-Forward Validation")

        return True

    except Exception as e:
        logger.error(f"Orchestration failed: {e}", exc_info=True)
        return False


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 orchestrate_phase2.py interactive")
        print("  python3 orchestrate_phase2.py import <csv_file>")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "interactive":
        success = orchestrate_full_pipeline(mode="interactive")
    elif mode == "import" and len(sys.argv) > 2:
        csv_file = Path(sys.argv[2])
        step_2_csv_import(csv_file)
        # Still need to validate and freeze
        labels_csv = GT_DIR / f"labels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        is_valid = step_3_validation(labels_csv)
        if is_valid:
            step_4_freeze(labels_csv)
            success = True
        else:
            success = False
    else:
        print("Invalid arguments")
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
