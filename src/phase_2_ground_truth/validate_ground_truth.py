#!/usr/bin/env python3
"""
Phase 2 Ground Truth Validation

Validates labeled data quality and prepares for ground truth freeze.
- Confidence level distribution
- Inter-rater agreement (if multiple labelers)
- Coverage verification
- Label consistency checks

Timeline: Oct 22-23, 2026
Gate: Ground Truth Freeze (Oct 23)
"""

import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import csv
import pandas as pd

# Configuration
DATA_DIR = Path(__file__).parent.parent.parent / "data"
GT_DIR = DATA_DIR / "ground_truth" / "phase_2"
QA_DIR = DATA_DIR / "qa" / "phase_2"
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_2"

# Setup logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    ]
)
logger = logging.getLogger(__name__)


class GroundTruthValidator:
    def __init__(self, ground_truth_dir=GT_DIR, qa_dir=QA_DIR):
        self.gt_dir = Path(ground_truth_dir)
        self.qa_dir = Path(qa_dir)
        self.qa_dir.mkdir(parents=True, exist_ok=True)
        self.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "phase": "2_ground_truth",
            "checks": {},
            "summary": {}
        }

    def load_labels(self, csv_file: Path) -> Dict:
        """Load labeled data from CSV"""
        logger.info(f"Loading labels from {csv_file}")

        labels = {}
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                coin_id = row.get("coin_id")
                if coin_id:
                    labels[coin_id] = {
                        "symbol": row.get("symbol"),
                        "label": row.get("label"),
                        "confidence": int(row.get("confidence", 0)),
                        "labeler": row.get("labeler"),
                        "timestamp": row.get("timestamp")
                    }

        logger.info(f"Loaded {len(labels)} labels")
        return labels

    def validate_completeness(self, labels: Dict, min_coverage: float = 0.95) -> Dict:
        """Check coverage vs Phase 1 data"""
        logger.info("Validating completeness...")

        # Count Phase 1 files
        data_dir = DATA_DIR / "raw" / "phase_1"
        phase1_files = list(data_dir.glob("*.parquet"))
        phase1_coins = len(phase1_files)

        labeled_coins = len(labels)
        coverage = labeled_coins / phase1_coins if phase1_coins > 0 else 0

        result = {
            "phase1_coins": phase1_coins,
            "labeled_coins": labeled_coins,
            "unlabeled_coins": phase1_coins - labeled_coins,
            "coverage_percent": round(100 * coverage, 2),
            "status": "PASS" if coverage >= min_coverage else "FAIL"
        }

        self.validation_results["checks"]["completeness"] = result
        return result

    def validate_confidence_distribution(self, labels: Dict) -> Dict:
        """Check confidence level distribution"""
        logger.info("Validating confidence distribution...")

        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for label in labels.values():
            conf = label.get("confidence", 0)
            if conf in distribution:
                distribution[conf] += 1

        total = sum(distribution.values())
        avg_confidence = sum(k*v for k,v in distribution.items()) / total if total > 0 else 0

        high_confidence = sum(distribution[k] for k in [4, 5])
        high_confidence_percent = 100 * high_confidence / total if total > 0 else 0

        result = {
            "total_labels": total,
            "distribution": distribution,
            "average_confidence": round(avg_confidence, 2),
            "high_confidence_count": high_confidence,
            "high_confidence_percent": round(high_confidence_percent, 1),
            "status": "PASS" if avg_confidence >= 3.0 else "WARN"
        }

        self.validation_results["checks"]["confidence"] = result
        return result

    def validate_label_distribution(self, labels: Dict) -> Dict:
        """Check Q1 vs Q2 distribution"""
        logger.info("Validating label distribution...")

        q1_count = sum(1 for l in labels.values() if l["label"] == "Q1")
        q2_count = sum(1 for l in labels.values() if l["label"] == "Q2")
        skip_count = sum(1 for l in labels.values() if l["label"] not in ["Q1", "Q2"])

        total = len(labels)

        result = {
            "total_labeled": total,
            "q1_count": q1_count,
            "q2_count": q2_count,
            "skipped_count": skip_count,
            "q1_percent": round(100 * q1_count / total, 1) if total > 0 else 0,
            "q2_percent": round(100 * q2_count / total, 1) if total > 0 else 0,
            "balance_ratio": round(max(q1_count, q2_count) / min(q1_count, q2_count), 2) if min(q1_count, q2_count) > 0 else 0,
            "status": "PASS" if q1_count > 0 and q2_count > 0 else "FAIL"
        }

        self.validation_results["checks"]["distribution"] = result
        return result

    def validate_consistency(self, labels: Dict) -> Dict:
        """Check for inconsistencies (missing fields, invalid labels)"""
        logger.info("Validating consistency...")

        errors = []
        warnings = []

        for coin_id, label in labels.items():
            # Check required fields
            if not label.get("symbol"):
                errors.append(f"{coin_id}: Missing symbol")
            if label.get("label") not in ["Q1", "Q2", "SKIP"]:
                errors.append(f"{coin_id}: Invalid label '{label.get('label')}'")
            if not isinstance(label.get("confidence"), int) or label.get("confidence") not in [1,2,3,4,5]:
                errors.append(f"{coin_id}: Invalid confidence '{label.get('confidence')}'")

            # Check timestamps
            if not label.get("timestamp"):
                warnings.append(f"{coin_id}: Missing timestamp")

        result = {
            "total_checked": len(labels),
            "errors": errors,
            "error_count": len(errors),
            "warnings": warnings,
            "warning_count": len(warnings),
            "status": "PASS" if len(errors) == 0 else "FAIL"
        }

        self.validation_results["checks"]["consistency"] = result
        return result

    def validate_all(self, csv_file: Path) -> bool:
        """Run all validation checks"""
        logger.info("="*60)
        logger.info("GROUND TRUTH VALIDATION")
        logger.info("="*60)

        if not csv_file.exists():
            logger.error(f"Labels file not found: {csv_file}")
            return False

        # Load labels
        labels = self.load_labels(csv_file)

        # Run checks
        self.validate_completeness(labels)
        self.validate_confidence_distribution(labels)
        self.validate_label_distribution(labels)
        self.validate_consistency(labels)

        # Summary
        all_pass = all(
            check.get("status") == "PASS"
            for check in self.validation_results["checks"].values()
        )

        self.validation_results["summary"] = {
            "gate_status": "PASS" if all_pass else "FAIL",
            "all_checks_passed": all_pass,
            "review_required": not all_pass
        }

        logger.info(f"\n{'='*60}")
        logger.info("VALIDATION RESULTS")
        logger.info(f"{'='*60}")
        for check_name, result in self.validation_results["checks"].items():
            status = result.get("status", "UNKNOWN")
            logger.info(f"  {check_name}: {status}")

        logger.info(f"\nOverall: {self.validation_results['summary']['gate_status']}")

        return all_pass

    def save_validation_report(self) -> Path:
        """Save validation report"""
        report_file = self.qa_dir / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        logger.info(f"Validation report saved to {report_file}")
        return report_file


class GroundTruthFreezer:
    """Freeze ground truth after validation"""

    def __init__(self, ground_truth_dir=GT_DIR):
        self.gt_dir = Path(ground_truth_dir)

    def create_immutable_snapshot(self, csv_file: Path) -> Tuple[Path, str]:
        """Create immutable ground truth snapshot"""
        logger.info("Creating immutable ground truth snapshot...")

        # Read CSV
        with open(csv_file, 'rb') as f:
            sha256_hash = hashlib.sha256(f.read()).hexdigest()

        # Create snapshot
        snapshot_dir = self.gt_dir / "frozen_snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        snapshot_file = snapshot_dir / f"ground_truth_frozen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # Copy file (read-only)
        import shutil
        shutil.copy2(csv_file, snapshot_file)

        # Make read-only
        import os
        os.chmod(snapshot_file, 0o444)

        logger.info(f"Immutable snapshot created: {snapshot_file}")
        logger.info(f"SHA256: {sha256_hash}")

        return snapshot_file, sha256_hash

    def create_freeze_certificate(self, snapshot_file: Path, sha256: str) -> Path:
        """Create ground truth freeze certificate"""
        certificate = {
            "phase": "2_ground_truth",
            "timestamp": datetime.now().isoformat(),
            "snapshot_file": str(snapshot_file),
            "sha256": sha256,
            "immutable": True,
            "locked_until": "Phase 6 gate closes (Dec 20, 2026)",
            "cannot_modify": True,
            "cannot_relabel": True,
            "next_phase": "Phase 3: Walk-Forward Validation"
        }

        cert_file = snapshot_file.parent / f"freeze_certificate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(cert_file, 'w') as f:
            json.dump(certificate, f, indent=2)

        logger.info(f"Freeze certificate created: {cert_file}")
        return cert_file


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 validate_ground_truth.py <csv_file>")
        sys.exit(1)

    csv_file = Path(sys.argv[1])

    # Validate
    validator = GroundTruthValidator()
    is_valid = validator.validate_all(csv_file)

    # Save report
    report = validator.save_validation_report()

    if is_valid:
        # Freeze
        freezer = GroundTruthFreezer()
        snapshot, sha256 = freezer.create_immutable_snapshot(csv_file)
        cert = freezer.create_freeze_certificate(snapshot, sha256)
        print(f"\n✓ GROUND TRUTH FROZEN")
        print(f"  Snapshot: {snapshot}")
        print(f"  Certificate: {cert}")
    else:
        print(f"\n✗ VALIDATION FAILED - Review report: {report}")
        sys.exit(1)
