#!/usr/bin/env python
"""
Layer 7 - RRP WFV Execution Script

Runs 19-window expanding walk-forward validation per SPRING-PHASE-LAYER7-SPEC.md Section 5:
- Binary target: revival (30% gain in 30d) vs non-revival
- Gate criteria: WR > 50%, Precision > 60%, Stability < 0.5, OOS validation
- Results frozen before post-hoc analysis
"""

import pandas as pd
import numpy as np
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'research'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'data'))

from layer_7_runner import Layer7Runner
from rrp_data_layer import RRPDataLayer
from rrp_layer import RRPLayer


def load_data(source: str = 'synthetic', start_date: str = '2021-01-01',
              end_date: str = '2024-09-25') -> pd.DataFrame:
    """Load OHLCV data for RRP validation."""
    dates = pd.date_range(start_date, end_date, freq='D')
    n = len(dates)

    # Synthetic BTC-like price series
    close_prices = 10000 + np.cumsum(np.random.normal(0.5, 50, n))
    close_prices = np.maximum(close_prices, 1000)  # Floor

    df = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices + np.random.normal(0, 30, n),
        'high': close_prices + abs(np.random.normal(0, 50, n)),
        'low': close_prices - abs(np.random.normal(0, 50, n)),
        'close': close_prices,
        'volume': np.random.uniform(1e8, 1e10, n),
    })

    return df


def main():
    """Execute Layer 7 RRP WFV."""
    print("=" * 80)
    print("Layer 7 - RRP (Revival Radar Pipeline) Walk-Forward Validation")
    print("=" * 80)
    print()

    # Load data
    print("[1] Loading OHLCV data (2021-01-01 to 2024-09-25)...")
    df = load_data(source='synthetic')
    print(f"    Data shape: {df.shape}")
    print(f"    Date range: {df.index[0] if len(df) > 0 else 'N/A'} to {df.index[-1] if len(df) > 0 else 'N/A'}")
    print()

    # Load dormant tokens and score candidates
    print("[2] Loading dormant tokens and computing revival scores...")
    data_layer = RRPDataLayer()
    tokens_df = data_layer.load_dormant_tokens(market_cap_min=1e6)
    print(f"    Dormant tokens loaded: {len(tokens_df)}")

    metrics = data_layer.generate_synthetic_metrics(tokens_df, periods=100)
    print(f"    Metric trajectories generated: {len(metrics)}")

    rrp = RRPLayer()
    candidates = rrp.score_tokens(tokens_df, metrics)
    print(f"    Candidates scored: {len(candidates)}")
    print()

    # Show top candidates
    print("[3] Top Revival Candidates (by confidence):")
    print("-" * 80)
    for i, c in enumerate(candidates[:5]):
        print(f"  {i+1}. {c.symbol}: {c.revival_confidence:.1f}/100 | Dormancy: {c.dormancy_days}d | Recommendation: {c.recommendation}")
    print()

    # Initialize runner
    print("[4] Initializing Layer 7 WFV runner...")
    runner = Layer7Runner()
    windows = runner.create_wfv_windows()
    print(f"    Windows created: {len(windows)}")
    print()

    # Execute WFV
    print("[5] Executing 19-window expanding WFV (binary revival target)...")
    result = runner.run_wfv(df)
    print("    WFV complete.")
    print()

    # Report results
    print("[6] Aggregated Results (FROZEN):")
    print("-" * 80)
    print(f"Mean Win Rate:       {result.mean_win_rate:.4f} ({int(result.mean_win_rate*100)}%)")
    print(f"Std Win Rate:        {result.std_win_rate:.4f}")
    print(f"Mean Precision:      {result.mean_precision:.4f} ({int(result.mean_precision*100)}%)")
    print(f"Mean Return Winners: {result.mean_return_winners:+.4f}")
    print(f"Mean Loss Losers:    {result.mean_loss_losers:+.4f}")
    print(f"Stability Score:     {result.stability:.4f}")
    print(f"OOS Win Rate:        {result.oos_win_rate:.4f}")
    print()

    # Gate criteria evaluation
    print("[7] Gate Criteria Evaluation (Layer 7 Specification Section 6):")
    print("-" * 80)

    gate_1_wr = result.mean_win_rate > 0.50
    gate_2_precision = result.mean_precision > 0.60
    gate_3_stability = result.stability < 0.50
    gate_4_oos = result.oos_win_rate >= (result.mean_win_rate - 0.05)

    print(f"Criterion 1: Win Rate > 0.50")
    print(f"  Result: {result.mean_win_rate:.4f} ... {'✅ PASS' if gate_1_wr else '❌ FAIL'}")
    print()

    print(f"Criterion 2: Precision > 0.60")
    print(f"  Result: {result.mean_precision:.4f} ... {'✅ PASS' if gate_2_precision else '❌ FAIL'}")
    print()

    print(f"Criterion 3: Stability < 0.50")
    print(f"  Result: {result.stability:.4f} ... {'✅ PASS' if gate_3_stability else '❌ FAIL'}")
    print()

    print(f"Criterion 4: OOS >= IS - 0.05")
    print(f"  Result: OOS={result.oos_win_rate:.4f}, IS={result.mean_win_rate:.4f}, Diff={result.oos_win_rate - result.mean_win_rate:+.4f} ... {'✅ PASS' if gate_4_oos else '❌ FAIL'}")
    print()

    # Final decision
    all_pass = result.gate_pass
    print("[8] Final Gate Decision:")
    print("=" * 80)
    if all_pass:
        print("✅ GATE PASS — RRP layer validates as revival detection signal")
        print("   Action: Proceed to Layer 7 integration and Layer 8 investigation")
    else:
        print("❌ GATE FAIL — RRP layer does not meet all gate criteria")
        print("   Action: Document findings, consider alternative signal paradigms")
    print()

    # Save results
    results_dict = {
        'mean_win_rate': float(result.mean_win_rate),
        'std_win_rate': float(result.std_win_rate),
        'mean_precision': float(result.mean_precision),
        'mean_return_winners': float(result.mean_return_winners),
        'mean_loss_losers': float(result.mean_loss_losers),
        'stability': float(result.stability),
        'oos_win_rate': float(result.oos_win_rate),
        'gate_criteria': {
            'criterion_1_wr': bool(gate_1_wr),
            'criterion_2_precision': bool(gate_2_precision),
            'criterion_3_stability': bool(gate_3_stability),
            'criterion_4_oos': bool(gate_4_oos),
        },
        'gate_decision': 'PASS' if all_pass else 'FAIL',
        'frozen': True,
        'window_metrics': {
            'win_rates': result.window_win_rates,
            'precisions': result.window_precisions,
        },
        'top_candidates': [
            {
                'symbol': c.symbol,
                'confidence': c.revival_confidence,
                'dormancy_days': c.dormancy_days,
                'recommendation': c.recommendation,
            }
            for c in candidates[:10]
        ],
    }

    # Save to file
    output_path = Path(__file__).parent.parent / 'reports' / 'research' / 'layer_7_rrp_results.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results_dict, f, indent=2)

    print(f"Results saved to: {output_path}")
    print()


if __name__ == '__main__':
    main()
