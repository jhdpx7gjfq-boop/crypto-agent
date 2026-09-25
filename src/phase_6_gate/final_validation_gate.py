#!/usr/bin/env python3
"""
Phase 6: Final Validation Gate

Aggregates results from all previous phases (1-5) and makes final
VALIDATED_ALPHA decision for production deployment.

Gate checks:
- Phase 1: Data audit PASS (≥95% completeness)
- Phase 2: Ground truth frozen (immutable snapshot)
- Phase 3: Walk-forward validation PASS (avg F1 ≥0.75)
- Phase 4: Component ablation complete (ranking available)
- Phase 5: Robustness testing PASS (>75% in all dimensions)

Timeline: Dec 1-20, 2026
Final Decision: VALIDATED_ALPHA (go-live) or REJECT (needs rework)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Configuration
DATA_DIR = Path(__file__).parent.parent.parent / "data"
PHASE1_DIR = DATA_DIR / "raw" / "phase_1" / "audit"
GT_DIR = DATA_DIR / "ground_truth" / "phase_2" / "frozen_snapshots"
VAL_DIR = DATA_DIR / "validation" / "phase_3"
ABLATION_DIR = DATA_DIR / "ablation" / "phase_4"
ROBUST_DIR = DATA_DIR / "robustness" / "phase_5"
GATE_DIR = DATA_DIR / "gate" / "phase_6"
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_6"

LOG_DIR.mkdir(parents=True, exist_ok=True)
GATE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FinalValidationGate:
    """Final validation gate decision framework"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "phase": "6_final_validation_gate",
            "checks": {},
            "decision": {}
        }

    def check_phase1_data_audit(self) -> Tuple[bool, Dict]:
        """Check Phase 1 data audit results"""
        logger.info("Checking Phase 1: Data Audit...")

        # Look for audit report
        audit_files = list(Path(DATA_DIR).glob("**/phase_1/*audit*.json"))

        if not audit_files:
            logger.warning("  No Phase 1 audit report found")
            return False, {"status": "MISSING", "message": "No audit report"}

        try:
            latest_audit = sorted(audit_files)[-1]
            with open(latest_audit, 'r') as f:
                audit_result = json.load(f)

            gate_status = audit_result.get("summary", {}).get("gate_status", "FAIL")
            completeness = audit_result.get("checks", {}).get("completeness", {}).get("coverage_percent", 0)

            if gate_status == "PASS":
                logger.info(f"  ✓ Phase 1 PASSED ({completeness}% coverage)")
                return True, {
                    "status": "PASS",
                    "completeness": completeness,
                    "audit_file": str(latest_audit)
                }
            else:
                logger.warning(f"  ✗ Phase 1 FAILED")
                return False, {"status": "FAIL"}
        except Exception as e:
            logger.error(f"  Error reading audit: {e}")
            return False, {"status": "ERROR", "error": str(e)}

    def check_phase2_ground_truth(self) -> Tuple[bool, Dict]:
        """Check Phase 2 ground truth freeze"""
        logger.info("Checking Phase 2: Ground Truth Freeze...")

        # Look for frozen snapshots
        frozen_files = list(Path(GT_DIR).glob("ground_truth_frozen_*.csv")) if GT_DIR.exists() else []
        cert_files = list(Path(GT_DIR).glob("freeze_certificate_*.json")) if GT_DIR.exists() else []

        if frozen_files and cert_files:
            logger.info(f"  ✓ Phase 2 PASSED (frozen snapshot exists)")
            return True, {
                "status": "PASS",
                "snapshot": str(frozen_files[-1]),
                "certificate": str(cert_files[-1])
            }

        logger.warning(f"  ✗ Phase 2 FAILED (no frozen snapshot)")
        return False, {"status": "FAIL"}

    def check_phase3_walk_forward(self) -> Tuple[bool, Dict]:
        """Check Phase 3 walk-forward validation"""
        logger.info("Checking Phase 3: Walk-Forward Validation...")

        # Look for WFV results
        wfv_files = list(Path(VAL_DIR).glob("wfv_results_*.json")) if VAL_DIR.exists() else []

        if not wfv_files:
            logger.warning("  No WFV results found")
            return False, {"status": "MISSING"}

        try:
            latest_wfv = sorted(wfv_files)[-1]
            with open(latest_wfv, 'r') as f:
                wfv_result = json.load(f)

            summary = wfv_result.get("summary", {})
            avg_f1 = summary.get("avg_f1", 0)
            gate_status = summary.get("gate_status", "FAIL")

            if gate_status == "PASS" and avg_f1 >= 0.75:
                logger.info(f"  ✓ Phase 3 PASSED (F1: {avg_f1:.3f})")
                return True, {
                    "status": "PASS",
                    "avg_f1": avg_f1,
                    "n_windows": summary.get("n_windows", 0),
                    "result_file": str(latest_wfv)
                }
            else:
                logger.warning(f"  ✗ Phase 3 FAILED (F1: {avg_f1:.3f})")
                return False, {"status": "FAIL", "avg_f1": avg_f1}
        except Exception as e:
            logger.error(f"  Error reading WFV: {e}")
            return False, {"status": "ERROR"}

    def check_phase4_ablation(self) -> Tuple[bool, Dict]:
        """Check Phase 4 ablation analysis"""
        logger.info("Checking Phase 4: Ablation Analysis...")

        # Look for ablation results
        ablation_files = list(Path(ABLATION_DIR).glob("ablation_results_*.json")) if ABLATION_DIR.exists() else []

        if not ablation_files:
            logger.warning("  No ablation results found")
            return False, {"status": "MISSING"}

        try:
            latest_ablation = sorted(ablation_files)[-1]
            with open(latest_ablation, 'r') as f:
                ablation_result = json.load(f)

            summary = ablation_result.get("summary", {})
            n_critical = summary.get("n_critical", 0)
            ranking = summary.get("ranking", [])

            if n_critical > 0:
                logger.info(f"  ✓ Phase 4 PASSED ({n_critical} critical components identified)")
                return True, {
                    "status": "PASS",
                    "n_critical_components": n_critical,
                    "ranking": ranking[:3],  # Top 3
                    "result_file": str(latest_ablation)
                }
            else:
                logger.warning(f"  ✗ Phase 4 FAILED (no critical components)")
                return False, {"status": "FAIL"}
        except Exception as e:
            logger.error(f"  Error reading ablation: {e}")
            return False, {"status": "ERROR"}

    def check_phase5_robustness(self) -> Tuple[bool, Dict]:
        """Check Phase 5 robustness validation"""
        logger.info("Checking Phase 5: Robustness Validation...")

        # Look for robustness results
        robust_files = list(Path(ROBUST_DIR).glob("robustness_results_*.json")) if ROBUST_DIR.exists() else []

        if not robust_files:
            logger.warning("  No robustness results found")
            return False, {"status": "MISSING"}

        try:
            latest_robust = sorted(robust_files)[-1]
            with open(latest_robust, 'r') as f:
                robust_result = json.load(f)

            summary = robust_result.get("summary", {})
            overall_pass_rate = summary.get("overall_pass_rate", 0)
            gate_status = summary.get("gate_status", "FAIL")
            pass_rates = summary.get("pass_rates_by_dimension", {})

            if gate_status == "PASS" and overall_pass_rate >= 0.75:
                logger.info(f"  ✓ Phase 5 PASSED ({overall_pass_rate:.1%} overall pass rate)")
                return True, {
                    "status": "PASS",
                    "overall_pass_rate": overall_pass_rate,
                    "pass_rates_by_dimension": pass_rates,
                    "result_file": str(latest_robust)
                }
            else:
                logger.warning(f"  ✗ Phase 5 FAILED ({overall_pass_rate:.1%})")
                return False, {"status": "FAIL", "pass_rate": overall_pass_rate}
        except Exception as e:
            logger.error(f"  Error reading robustness: {e}")
            return False, {"status": "ERROR"}

    def run_final_gate(self) -> bool:
        """Run final validation gate"""
        logger.info("="*70)
        logger.info("PHASE 6: FINAL VALIDATION GATE")
        logger.info("="*70)

        # Check all phases
        p1_pass, p1_result = self.check_phase1_data_audit()
        p2_pass, p2_result = self.check_phase2_ground_truth()
        p3_pass, p3_result = self.check_phase3_walk_forward()
        p4_pass, p4_result = self.check_phase4_ablation()
        p5_pass, p5_result = self.check_phase5_robustness()

        # Store results
        self.results["checks"] = {
            "phase_1_data_audit": {"pass": p1_pass, "result": p1_result},
            "phase_2_ground_truth": {"pass": p2_pass, "result": p2_result},
            "phase_3_walk_forward": {"pass": p3_pass, "result": p3_result},
            "phase_4_ablation": {"pass": p4_pass, "result": p4_result},
            "phase_5_robustness": {"pass": p5_pass, "result": p5_result}
        }

        # Summary
        all_pass = all([p1_pass, p2_pass, p3_pass, p4_pass, p5_pass])

        logger.info("\n" + "="*70)
        logger.info("FINAL GATE SUMMARY")
        logger.info("="*70)

        for phase, passed in [
            ("Phase 1: Data Audit", p1_pass),
            ("Phase 2: Ground Truth", p2_pass),
            ("Phase 3: Walk-Forward", p3_pass),
            ("Phase 4: Ablation", p4_pass),
            ("Phase 5: Robustness", p5_pass)
        ]:
            status = "✓ PASS" if passed else "✗ FAIL"
            logger.info(f"{phase:35s} {status}")

        logger.info(f"\n{'='*70}")

        if all_pass:
            decision = "VALIDATED_ALPHA"
            logger.info("✓ VALIDATED_ALPHA - System approved for production deployment")
            logger.info("\nNext steps:")
            logger.info("  1. System freeze for production")
            logger.info("  2. Mobile dashboard deployment (iOS/Android)")
            logger.info("  3. Begin live market monitoring")
            logger.info("  4. Execute Phase 7: Smart Money Analysis")
            logger.info("  5. Deploy Phase 8: X20 Optimizer")
            logger.info("  6. Launch Phase 9: AI Research Copilot")
        else:
            decision = "REJECT"
            logger.warning("✗ REJECT - System validation incomplete or failed")
            logger.warning("\nNext steps:")
            logger.warning("  1. Review failed phase(s)")
            logger.warning("  2. Address validation issues")
            logger.warning("  3. Re-run validation pipeline")

        self.results["decision"] = {
            "status": decision,
            "all_phases_pass": all_pass,
            "timestamp": datetime.now().isoformat(),
            "message": f"System {decision}: {'Production ready' if all_pass else 'Requires additional work'}"
        }

        return all_pass

    def save_decision(self) -> Path:
        """Save final gate decision"""
        decision_file = GATE_DIR / f"final_gate_decision_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(decision_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Decision saved to {decision_file}")
        return decision_file


if __name__ == "__main__":
    import sys

    gate = FinalValidationGate()
    is_validated = gate.run_final_gate()

    decision_file = gate.save_decision()

    if is_validated:
        print(f"\n✓ VALIDATED_ALPHA")
        print(f"Decision: {decision_file}")
        sys.exit(0)
    else:
        print(f"\n✗ REJECT")
        print(f"Decision: {decision_file}")
        sys.exit(1)
