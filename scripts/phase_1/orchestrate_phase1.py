#!/usr/bin/env python3
"""
Phase 1 Complete Orchestration Script

Orchestrates the entire Phase 1 data collection workflow:
1. CoinGecko OHLCV collection (Days 1-3)
2. Glassnode on-chain metrics (Days 4-5)
3. Data consolidation (Days 8-9)
4. Quality assurance audit (Days 10-12)
5. Immutable snapshot creation (Days 13-14)
6. Gate decision & approval

Timeline: Oct 9-23, 2026 (14 days)
Gate Decision: Phase 1 PASS/FAIL
"""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Setup logging
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_1"
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

PHASE1_DIR = Path(__file__).parent.parent.parent
SRC_DIR = PHASE1_DIR / "src"


class Phase1Orchestrator:
    def __init__(self):
        self.start_time = datetime.now()
        self.results = {
            "phase": "1_data_audit",
            "start_time": self.start_time.isoformat(),
            "steps": {}
        }

    def run_step(self, step_name: str, script_path: Path) -> bool:
        """Execute a step in the Phase 1 workflow"""
        logger.info(f"\n{'='*60}")
        logger.info(f"STEP: {step_name}")
        logger.info(f"{'='*60}")

        if not script_path.exists():
            logger.error(f"Script not found: {script_path}")
            self.results["steps"][step_name] = {
                "status": "FAILED",
                "error": "Script not found"
            }
            return False

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=PHASE1_DIR,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            if result.returncode == 0:
                logger.info(f"✓ {step_name} completed successfully")
                self.results["steps"][step_name] = {
                    "status": "PASSED",
                    "timestamp": datetime.now().isoformat()
                }
                return True
            else:
                logger.error(f"✗ {step_name} failed")
                logger.error(f"STDOUT:\n{result.stdout}")
                logger.error(f"STDERR:\n{result.stderr}")
                self.results["steps"][step_name] = {
                    "status": "FAILED",
                    "error": result.stderr
                }
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"✗ {step_name} timed out (>1 hour)")
            self.results["steps"][step_name] = {
                "status": "TIMEOUT"
            }
            return False
        except Exception as e:
            logger.error(f"✗ {step_name} error: {str(e)}")
            self.results["steps"][step_name] = {
                "status": "ERROR",
                "error": str(e)
            }
            return False

    def orchestrate(self) -> bool:
        """Execute complete Phase 1 workflow"""
        logger.info(f"{'='*60}")
        logger.info(f"PHASE 1 DATA AUDIT ORCHESTRATION")
        logger.info(f"Start Time: {self.start_time}")
        logger.info(f"{'='*60}")

        steps = [
            ("CoinGecko OHLCV Collection", SRC_DIR / "phase_1_data_collection" / "collect_coingecko.py"),
            ("Glassnode On-Chain Metrics", SRC_DIR / "phase_1_data_collection" / "collect_glassnode.py"),
            ("Data Quality Audit", SRC_DIR / "phase_1_qa" / "audit_completeness.py"),
            ("Immutable Snapshot Creation", SRC_DIR / "phase_1_qa" / "create_immutable_snapshot.py"),
        ]

        passed_steps = 0
        failed_steps = 0

        for step_name, script_path in steps:
            if self.run_step(step_name, script_path):
                passed_steps += 1
            else:
                failed_steps += 1
                logger.warning(f"Continuing despite failure (non-blocking step)")

        # Final summary
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        self.results["end_time"] = end_time.isoformat()
        self.results["duration_seconds"] = duration
        self.results["summary"] = {
            "total_steps": len(steps),
            "passed": passed_steps,
            "failed": failed_steps,
            "overall_status": "PASS" if failed_steps == 0 else "FAIL"
        }

        logger.info(f"\n{'='*60}")
        logger.info(f"PHASE 1 ORCHESTRATION COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Passed Steps: {passed_steps}/{len(steps)}")
        logger.info(f"Failed Steps: {failed_steps}/{len(steps)}")
        logger.info(f"Duration: {duration/60:.1f} minutes")
        logger.info(f"Overall Status: {self.results['summary']['overall_status']}")

        # Save orchestration results
        self.save_results()

        return failed_steps == 0

    def save_results(self):
        """Save orchestration results to JSON"""
        results_file = LOG_DIR / f"orchestration_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {results_file}")


if __name__ == "__main__":
    # Verify environment
    api_key = os.getenv("GLASSNODE_API_KEY")
    if not api_key:
        logger.warning("GLASSNODE_API_KEY not set - Glassnode collection may fail")

    # Run orchestration
    orchestrator = Phase1Orchestrator()
    success = orchestrator.orchestrate()

    sys.exit(0 if success else 1)
