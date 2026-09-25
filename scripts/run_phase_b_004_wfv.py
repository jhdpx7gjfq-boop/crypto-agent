#!/usr/bin/env python
"""
Phase B-004: WFV Execution Script (Dry-Run with Synthetic Data)

Runs 19-window expanding WFV per B-004_SPEC.md Section 4.
- No pre-filtering to Bull/Bear
- Freezes results before post-hoc regime analysis
- Measures gate criteria: ΔIC > 0.005, HR > 0.50, Stability > 0.65
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'research'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'data'))

from phase_b_004_runner import PhaseB004Runner
from b004_data_loader import B004DataLoader


def load_data(source: str = 'synthetic', start_date: str = '2021-01-01',
              end_date: str = '2024-09-25') -> pd.DataFrame:
    """Load OHLCV + RPM features (synthetic with realistic crypto patterns)."""
    loader = B004DataLoader(data_source=source)
    return loader.load(start_date, end_date)


def main():
    """Execute B-004 WFV dry-run."""
    print("=" * 80)
    print("Phase B-004: RPM/RCM Walk-Forward Validation")
    print("=" * 80)
    print()

    # Load data
    print("[1] Loading OHLCV + RPM features (2021-01-01 to 2024-09-25)...")
    df = load_data(source='synthetic')
    print(f"    Data shape: {df.shape}")
    print(f"    Date range: {df.index[0].date()} to {df.index[-1].date()}")
    print()

    # Initialize runner
    print("[2] Initializing Phase B-004 runner...")
    runner = PhaseB004Runner()
    windows = runner.create_wfv_windows()
    print(f"    Windows created: {len(windows)}")
    print()

    # Execute WFV
    print("[3] Executing 19-window expanding WFV (no pre-filtering)...")
    result = runner.run_wfv(df)
    print("    WFV complete.")
    print()

    # Report results
    print("[4] Aggregated Results (FROZEN):")
    print("-" * 80)
    print(f"Model J (RPM alone):")
    print(f"  Mean IC:     {result.mean_ic_j:+.6f}")
    print(f"  Std IC:      {result.std_ic_j:.6f}")
    print(f"  Stability:   {result.stability_j:.4f}")
    print(f"  Hit Rate:    {result.mean_hr_j:.4f} ({int(result.mean_hr_j*100)}%)")
    print(f"  ΔIC vs A:    {result.delta_ic_j:+.6f}")
    print(f"  Gate Pass:   {'✅ PASS' if result.gate_pass_j else '❌ FAIL'}")
    print()

    print(f"Model K (RCM regime-weighted):")
    print(f"  Mean IC:     {result.mean_ic_k:+.6f}")
    print(f"  Std IC:      {result.std_ic_k:.6f}")
    print(f"  Stability:   {result.stability_k:.4f}")
    print(f"  Hit Rate:    {result.mean_hr_k:.4f} ({int(result.mean_hr_k*100)}%)")
    print(f"  ΔIC vs A:    {result.delta_ic_k:+.6f}")
    print(f"  Gate Pass:   {'✅ PASS' if result.gate_pass_k else '❌ FAIL'}")
    print()

    print(f"Model L (Full stack: baseline + RPM):")
    print(f"  Mean IC:     {result.mean_ic_l:+.6f}")
    print(f"  Std IC:      {result.std_ic_l:.6f}")
    print(f"  Stability:   {result.stability_l:.4f}")
    print(f"  Hit Rate:    {result.mean_hr_l:.4f} ({int(result.mean_hr_l*100)}%)")
    print(f"  ΔIC vs A:    {result.delta_ic_l:+.6f}")
    print(f"  Gate Pass:   {'✅ PASS' if result.gate_pass_l else '❌ FAIL'}")
    print()

    # Gate decision
    print("[5] Gate Criteria Evaluation (B-004_SPEC.md Section 6):")
    print("-" * 80)
    print(f"Criterion 1: ΔIC_J > 0.005 points")
    print(f"  Result: {result.delta_ic_j:+.6f} ... {'✅ PASS' if result.delta_ic_j > 0.005 else '❌ FAIL'}")
    print()
    print(f"Criterion 2: HR_J > 0.50 (50%)")
    print(f"  Result: {result.mean_hr_j:.4f} ... {'✅ PASS' if result.mean_hr_j > 0.50 else '❌ FAIL'}")
    print()
    print(f"Criterion 3: Stability_J > 0.65")
    print(f"  Result: {result.stability_j:.4f} ... {'✅ PASS' if result.stability_j > 0.65 else '❌ FAIL'}")
    print()

    # Final decision
    all_pass = result.gate_pass_j
    print("[6] Final Gate Decision:")
    print("=" * 80)
    if all_pass:
        print("✅ GATE PASS — RPM layer validated as incremental alpha source")
        print("   Action: Proceed to Phase 3 (combined macro layer)")
    else:
        print("❌ GATE FAIL — RPM layer does not meet gate criteria")
        print("   Action: Document findings, consider alternative hypotheses")
    print()

    # Save results
    results_dict = {
        'model_j': {
            'mean_ic': float(result.mean_ic_j),
            'std_ic': float(result.std_ic_j),
            'delta_ic': float(result.delta_ic_j),
            'hit_rate': float(result.mean_hr_j),
            'stability': float(result.stability_j),
            'gate_pass': result.gate_pass_j,
        },
        'model_k': {
            'mean_ic': float(result.mean_ic_k),
            'std_ic': float(result.std_ic_k),
            'delta_ic': float(result.delta_ic_k),
            'hit_rate': float(result.mean_hr_k),
            'stability': float(result.stability_k),
            'gate_pass': result.gate_pass_k,
        },
        'model_l': {
            'mean_ic': float(result.mean_ic_l),
            'std_ic': float(result.std_ic_l),
            'delta_ic': float(result.delta_ic_l),
            'hit_rate': float(result.mean_hr_l),
            'stability': float(result.stability_l),
            'gate_pass': result.gate_pass_l,
        },
        'gate_decision': 'PASS' if all_pass else 'FAIL',
        'frozen': True,
    }

    # Save to file
    output_path = Path(__file__).parent.parent / 'reports' / 'research' / 'phase_b_004_results.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results_dict, f, indent=2)

    print(f"Results saved to: {output_path}")
    print()


if __name__ == '__main__':
    main()
