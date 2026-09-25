#!/usr/bin/env python3
"""
Phase 1 Data Quality Audit

Validates collected OHLCV data:
- Completeness check: ≥95% data points
- Gap analysis: <14 day maximum gaps
- Outlier detection: Invalid values
- Immutable snapshot creation

Timeline: Oct 13-14, 2026
Decision: PASS/FAIL gate for Phase 1 completion
"""

import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple, List
import pandas as pd
import numpy as np
import hashlib

# Configuration
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "phase_1"
QA_DIR = Path(__file__).parent.parent.parent / "data" / "qa" / "phase_1"
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_1"

# Quality thresholds
MIN_COMPLETENESS = 0.95  # ≥95%
MAX_GAP_DAYS = 14
EXPECTED_START = datetime(2020, 1, 1)
EXPECTED_END = datetime.now()
EXPECTED_DAYS = (EXPECTED_END - EXPECTED_START).days

# Setup logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"audit_completeness_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DataQualityAuditor:
    def __init__(self, data_dir=DATA_DIR, qa_dir=QA_DIR):
        self.data_dir = Path(data_dir)
        self.qa_dir = Path(qa_dir)
        self.qa_dir.mkdir(parents=True, exist_ok=True)
        self.audit_results = {
            "timestamp": datetime.now().isoformat(),
            "phase": "1_data_audit",
            "coins": {},
            "summary": {}
        }
        self.gate_pass = True

    def validate_ohlcv(self, df: pd.DataFrame, coin_symbol: str) -> Dict:
        """Validate single coin OHLCV data"""
        result = {
            "symbol": coin_symbol,
            "status": "PASS",
            "checks": {}
        }

        try:
            # 1. Check for negative values
            invalid_prices = (
                (df["open"] < 0) | (df["high"] < 0) |
                (df["low"] < 0) | (df["close"] < 0)
            ).sum()
            result["checks"]["negative_values"] = {
                "count": int(invalid_prices),
                "status": "PASS" if invalid_prices == 0 else "FAIL"
            }

            # 2. Check OHLC consistency (low <= close <= high)
            invalid_structure = (
                (df["low"] > df["high"]) |
                (df["close"] < df["low"]) |
                (df["close"] > df["high"])
            ).sum()
            result["checks"]["ohlc_structure"] = {
                "count": int(invalid_structure),
                "status": "PASS" if invalid_structure == 0 else "FAIL"
            }

            # 3. Completeness check
            data_points = len(df)
            expected_points = EXPECTED_DAYS
            completeness = data_points / expected_points if expected_points > 0 else 0
            result["checks"]["completeness"] = {
                "data_points": data_points,
                "expected_points": expected_points,
                "percentage": round(completeness * 100, 2),
                "status": "PASS" if completeness >= MIN_COMPLETENESS else "FAIL"
            }

            # 4. Gap analysis
            gaps = self._detect_gaps(df)
            max_gap = max(gaps) if gaps else 0
            result["checks"]["gaps"] = {
                "count": len(gaps),
                "max_days": max_gap,
                "gaps": gaps[:10],  # First 10 gaps
                "status": "PASS" if max_gap <= MAX_GAP_DAYS else "FAIL"
            }

            # 5. Price volatility check (reasonable bounds)
            price_range = df["close"].max() / df["close"].min() if df["close"].min() > 0 else 0
            extreme_volatility = price_range > 100000  # >10000x range is suspicious
            result["checks"]["volatility"] = {
                "price_range": round(price_range, 2),
                "status": "PASS" if not extreme_volatility else "WARN"
            }

            # Overall status
            failures = [v["status"] for v in result["checks"].values() if v.get("status") == "FAIL"]
            result["status"] = "FAIL" if failures else "PASS"

        except Exception as e:
            logger.error(f"Validation error for {coin_symbol}: {str(e)}")
            result["status"] = "ERROR"
            result["error"] = str(e)

        return result

    def _detect_gaps(self, df: pd.DataFrame, max_report: int = 20) -> List[int]:
        """Detect gaps in date sequence"""
        if df.empty:
            return []

        dates = pd.to_datetime(df.index)
        date_diffs = dates.diff().dt.days
        gaps = (date_diffs[date_diffs > 1] - 1).astype(int).values.tolist()
        return sorted(gaps, reverse=True)[:max_report]

    def audit_all(self) -> Tuple[bool, Dict]:
        """Audit all collected coin data"""
        logger.info("Starting comprehensive data quality audit...")

        parquet_files = list(self.data_dir.glob("*.parquet"))
        if not parquet_files:
            logger.error("No Parquet files found in data directory")
            return False, self.audit_results

        logger.info(f"Found {len(parquet_files)} Parquet files to audit")

        passed = 0
        failed = 0

        for parquet_file in parquet_files:
            try:
                # Extract symbol from filename
                coin_symbol = parquet_file.stem.split("_")[0].upper()

                # Load data
                df = pd.read_parquet(parquet_file)

                # Validate
                result = self.validate_ohlcv(df, coin_symbol)
                self.audit_results["coins"][coin_symbol] = result

                if result["status"] == "PASS":
                    passed += 1
                    logger.info(f"✓ {coin_symbol}: PASS")
                else:
                    failed += 1
                    self.gate_pass = False
                    logger.warning(f"✗ {coin_symbol}: {result['status']}")

                    # Log details
                    for check, details in result["checks"].items():
                        if details.get("status") == "FAIL":
                            logger.warning(f"  - {check}: {details}")

            except Exception as e:
                logger.error(f"Failed to audit {parquet_file}: {str(e)}")
                failed += 1
                self.gate_pass = False

        # Summary statistics
        self.audit_results["summary"] = {
            "total_coins": len(parquet_files),
            "passed": passed,
            "failed": failed,
            "pass_rate": round(100 * passed / len(parquet_files), 2) if parquet_files else 0,
            "gate_status": "PASS" if self.gate_pass else "FAIL"
        }

        logger.info(f"\nAudit Complete:")
        logger.info(f"  Passed: {passed}/{len(parquet_files)}")
        logger.info(f"  Failed: {failed}/{len(parquet_files)}")
        logger.info(f"  Pass Rate: {self.audit_results['summary']['pass_rate']}%")
        logger.info(f"  Gate Status: {self.audit_results['summary']['gate_status']}")

        return self.gate_pass, self.audit_results

    def save_audit_report(self) -> Path:
        """Save audit report as JSON"""
        report_file = self.qa_dir / f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(self.audit_results, f, indent=2)
        logger.info(f"Audit report saved to {report_file}")
        return report_file

    def create_gate_decision_document(self, report_file: Path) -> Path:
        """Create formal gate decision document"""
        decision_doc = {
            "phase": "1_data_audit",
            "timestamp": datetime.now().isoformat(),
            "decision": "PASS" if self.gate_pass else "FAIL",
            "criteria": {
                "completeness_threshold": f">={MIN_COMPLETENESS*100}%",
                "max_gap_days": MAX_GAP_DAYS,
                "no_negative_values": True,
                "valid_ohlc_structure": True
            },
            "results": self.audit_results["summary"],
            "audit_report": str(report_file),
            "reviewer_required": True,
            "reviewer_name": "QA Lead",
            "approval_timestamp": None,
            "approval_signature": None
        }

        decision_file = self.qa_dir / f"gate_decision_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(decision_file, "w") as f:
            json.dump(decision_doc, f, indent=2)

        logger.info(f"Gate decision document saved to {decision_file}")
        return decision_file


if __name__ == "__main__":
    auditor = DataQualityAuditor()
    gate_pass, audit_results = auditor.audit_all()

    report_file = auditor.save_audit_report()
    decision_file = auditor.create_gate_decision_document(report_file)

    logger.info(f"\n{'='*60}")
    logger.info(f"GATE DECISION: {'✓ PASS' if gate_pass else '✗ FAIL'}")
    logger.info(f"{'='*60}")

    sys.exit(0 if gate_pass else 1)
