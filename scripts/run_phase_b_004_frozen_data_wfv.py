#!/usr/bin/env python
"""
Phase B-004-DATA-RETRY: WFV with FROZEN REAL Dataset

Uses locally validated CSV (SHA256 frozen before WFV).
- No live data fetch
- Strict PIT compliance
- 19-window expanding WFV per B-004_SPEC v1.0
- Gate evaluation: ΔIC > 0.005 AND HR > 0.50 AND Stability > 0.65 (ALL required)
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
import hashlib
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'research'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'data'))

from phase_b_004_runner import PhaseB004Runner
from rpm_layer import RPMLayer
from rcm_layer import RCMLayer


class B004FrozenDataLoader:
    """Load FROZEN BTC OHLCV from local CSV (pre-validated)."""

    def __init__(self, csv_path: str = None):
        if csv_path is None:
            csv_path = Path(__file__).parent.parent / 'BTC-Daily-2021-2024.csv'
        self.csv_path = Path(csv_path)
        self.expected_hash = "f03f4afd12eab84e483d71adaefa784a3266b50f1f882916966cc9993621b300"

    def load_and_verify(self) -> pd.DataFrame:
        """Load CSV, verify SHA256, return DataFrame."""
        if not self.csv_path.exists():
            print(f"❌ CSV NOT FOUND: {self.csv_path}")
            sys.exit(1)

        print(f"[1] Loading FROZEN BTC OHLCV from {self.csv_path}...")

        # Compute hash
        with open(self.csv_path, 'rb') as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()

        print(f"  SHA256: {actual_hash}")
        print(f"  Expected: {self.expected_hash}")

        if actual_hash != self.expected_hash:
            print(f"❌ HASH MISMATCH - Dataset tampered or wrong file")
            sys.exit(1)

        print(f"  ✅ Hash verified")

        # Load CSV
        df = pd.read_csv(self.csv_path)
        df['date'] = pd.to_datetime(df['date'])

        print(f"  Rows: {len(df)}")
        print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
        print(f"  Columns: {list(df.columns)}")

        return df


def run_wfv():
    """Execute Phase B-004 WFV with frozen real data."""

    print("="*80)
    print("Phase B-004-DATA-RETRY: RPM/RCM Real Data WFV")
    print("GOVERNANCE: FROZEN DATASET (pre-validated SHA256)")
    print("SPEC: SPRING-PHASE-B-004-SPEC.md v1.0")
    print("="*80)
    print()

    # Load frozen data
    loader = B004FrozenDataLoader()
    df = loader.load_and_verify()
    print()

    # Execute WFV
    print("[2] Executing 19-window expanding WFV (PIT-compliant)...")
    runner = PhaseB004Runner()
    results = runner.run_wfv(df)
    print()

    # Report results
    print("[3] WFV Results (19 windows, PIT-compliant):")
    print("-" * 80)
    baseline_ic_a = -0.1208
    print(f"  Baseline Model A (momentum):")
    print(f"    IC: {baseline_ic_a:.6f} (prior from B-003)")
    print()
    print(f"  Model J (RPM alone):")
    print(f"    IC: {results.mean_ic_j:.6f} ± {results.std_ic_j:.6f}")
    print(f"    ΔIC: {results.delta_ic_j:.6f} (target > 0.005)")
    print(f"    HR: {results.mean_hr_j:.4f} (target > 0.50)")
    print(f"    Stability: {results.stability_j:.4f} (target > 0.65)")
    print()
    print(f"  Model K (RCM regime-weighted):")
    print(f"    IC: {results.mean_ic_k:.6f} ± {results.std_ic_k:.6f}")
    print(f"    ΔIC: {results.delta_ic_k:.6f}")
    print(f"    HR: {results.mean_hr_k:.4f}")
    print(f"    Stability: {results.stability_k:.4f}")
    print()
    print(f"  Model L (Full stack):")
    print(f"    IC: {results.mean_ic_l:.6f} ± {results.std_ic_l:.6f}")
    print(f"    ΔIC: {results.delta_ic_l:.6f}")
    print(f"    HR: {results.mean_hr_l:.4f}")
    print(f"    Stability: {results.stability_l:.4f}")
    print()

    # Evaluate gate criteria
    print("[4] Gate Evaluation (Model J vs Baseline A):")
    print("-" * 80)
    gate_1 = results.delta_ic_j > 0.005
    gate_2 = results.mean_hr_j > 0.50
    gate_3 = results.stability_j > 0.65

    print(f"  ✓ ΔIC > 0.005: {gate_1} ({results.delta_ic_j:.6f})")
    print(f"  ✓ HR > 0.50: {gate_2} ({results.mean_hr_j:.4f})")
    print(f"  ✓ Stability > 0.65: {gate_3} ({results.stability_j:.4f})")
    print()

    gate_pass = results.gate_pass_j
    gate_status = "✅ PASS" if gate_pass else "❌ FAIL"
    print(f"  GATE DECISION: {gate_status}")
    print()

    # Save results
    output = {
        "timestamp": datetime.utcnow().isoformat(),
        "dataset_hash": "f03f4afd12eab84e483d71adaefa784a3266b50f1f882916966cc9993621b300",
        "rows": len(df),
        "date_range": {
            "start": df['date'].min().isoformat(),
            "end": df['date'].max().isoformat()
        },
        "baseline_a": {
            "ic": -0.1208,
            "source": "B-003 prior"
        },
        "model_j_rpm": {
            "ic_mean": float(results.mean_ic_j),
            "ic_std": float(results.std_ic_j),
            "delta_ic": float(results.delta_ic_j),
            "hr": float(results.mean_hr_j),
            "stability": float(results.stability_j),
            "gate_pass": bool(gate_pass)
        },
        "gate_criteria": {
            "delta_ic_gt_0005": bool(gate_1),
            "hr_gt_050": bool(gate_2),
            "stability_gt_065": bool(gate_3),
            "all_pass": bool(gate_pass)
        }
    }

    output_path = Path(__file__).parent.parent / 'reports' / 'research' / 'phase_b_004_frozen_wfv.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"  Results saved to: {output_path}")
    print()

    # Interpretation
    print("[5] Interpretation:")
    print("-" * 80)
    if gate_pass:
        print("  ✅ B-004 GATE PASSED")
        print("     RPM/RCM signals validated on real BTC 1D (2021-2024)")
        print("     Layer 8 becomes eligible for governance review (owner decision required)")
    else:
        print("  ❌ B-004 GATE FAILED")
        print("     RPM/RCM signals rejected for tested scope (BTC 1D 2021-2024)")
        print("     Layer 8 remains blocked indefinitely")
        if not gate_1:
            print(f"     - ΔIC too low: {results.delta_ic_j:.6f} < 0.005")
        if not gate_2:
            print(f"     - HR too low: {results.mean_hr_j:.4f} < 0.50")
        if not gate_3:
            print(f"     - Stability too low: {results.stability_j:.4f} < 0.65")

    print()
    print("="*80)

    return gate_pass


if __name__ == "__main__":
    gate_pass = run_wfv()
    sys.exit(0 if gate_pass else 1)
