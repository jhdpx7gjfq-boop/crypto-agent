"""
Quick test adapter to run existing tests against P0.5 temporal.
"""
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from src.data.spring_detector_p05_temporal import (
    SpringDetectorOutput,
    SpringDetector,
)

# Test A: Scenario A (genuine candidate)
def test_scenario_a():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=100),
        "open": [0.0] * 100,
        "high": [0.0] * 100,
        "low": [0.0] * 100,
        "close": [0.0] * 100,
        "volume": [1000.0] * 100,
    })
    # Days 1-50: Range [95-105]
    df.loc[0:49, "high"] = 105.0
    df.loc[0:49, "low"] = 95.0
    df.loc[0:49, "close"] = np.linspace(100, 100, 50)
    # Days 51-52: Sweep below 95
    df.loc[50:51, "high"] = 100.0
    df.loc[50:51, "low"] = [90.0, 88.0]
    df.loc[50:51, "close"] = [92.0, 89.0]
    # Days 53-55: Recovery and reclaim
    df.loc[52:54, "high"] = [95.0, 100.0, 105.0]
    df.loc[52:54, "low"] = [88.0, 92.0, 100.0]
    df.loc[52:54, "close"] = [93.0, 98.0, 103.0]
    # Days 56+: Hold above range
    df.loc[55:99, "high"] = 105.0
    df.loc[55:99, "low"] = 100.0
    df.loc[55:99, "close"] = 102.0

    detector = SpringDetector()
    output = detector.classify("SCEN_A", df)
    print(f"Scenario A: {output.state} (expected SPRING_CANDIDATE)")
    return output.state == "SPRING_CANDIDATE"

# Test C: Sweep not confirmed early
def test_look_ahead_c():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=100),
        # Positions 0-30: old sweep [88-102]
        "open": [99.0] * 31 + [100.5] * 22 + [100.5, 100.5, 101.0] + [100.5] * 44,
        "high": [102.0] * 31 + [102.0] * 22 + [102.0, 102.0, 103.0] + [102.0] * 44,
        # Positions 0-30 low 88, Positions 31-52 low 95 (range)
        # Positions 53: sweep to 93 (no reclaim yet)
        # Positions 54: reclaim above 95
        "low": [88.0] * 31 + [95.0] * 22 + [93.5, 93.0, 94.5] + [95.0] * 44,
        "close": [90.0] * 31 + [99.0] * 22 + [93.5, 93.0, 99.0] + [99.0] * 44,
        "volume": [1000.0] * 100,
    })

    detector = SpringDetector()

    # At position 52 (sweep detected, but no reclaim yet)
    output_at_sweep = detector.classify("BTC", df.iloc[:53])
    print(f"test_look_ahead_c at sweep (pos 52): {output_at_sweep.state} (expected SWEEP)")
    sweep_ok = output_at_sweep.state == "SWEEP"

    # At position 53 (reclaim confirmed: close 99 > 95)
    output_at_reclaim = detector.classify("BTC", df.iloc[:54])
    print(f"test_look_ahead_c at reclaim (pos 53): {output_at_reclaim.state} (expected SPRING_CANDIDATE)")
    reclaim_ok = output_at_reclaim.state == "SPRING_CANDIDATE"

    return sweep_ok and reclaim_ok

# Test E: P0.3 base to spring
def test_scenario_e():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=100),
        "open": [0.0] * 100,
        "high": [0.0] * 100,
        "low": [0.0] * 100,
        "close": [0.0] * 100,
        "volume": [1000.0] * 100,
    })
    # Days 1-50: Uptrend
    df.loc[0:49, "high"] = np.linspace(100, 150, 50)
    df.loc[0:49, "low"] = np.linspace(90, 140, 50)
    df.loc[0:49, "close"] = np.linspace(95, 145, 50)
    # Days 51-70: Consolidation/base
    df.loc[50:69, "high"] = np.tile([145.0], 20)
    df.loc[50:69, "low"] = np.tile([140.0], 20)
    df.loc[50:69, "close"] = np.tile([142.0], 20)
    # Days 71-75: Sweep below base low
    df.loc[70:72, "high"] = [142.0, 141.0, 139.0]
    df.loc[70:72, "low"] = [140.0, 138.0, 135.0]
    df.loc[70:72, "close"] = [139.0, 137.0, 136.0]
    # Days 76+: Recovery and reclaim above 140
    df.loc[73:99, "high"] = 145.0
    df.loc[73:99, "low"] = 138.0
    df.loc[73:99, "close"] = 142.0

    detector = SpringDetector()
    output = detector.classify("SCEN_E", df)
    print(f"Scenario E: {output.state} (expected SPRING_CANDIDATE)")
    return output.state == "SPRING_CANDIDATE"

if __name__ == "__main__":
    print("Testing P0.5 (Temporal)...\n")

    results = {
        "Scenario A (genuine candidate)": test_scenario_a(),
        "Scenario E (base to spring)": test_scenario_e(),
        "Look-ahead C (sweep timing)": test_look_ahead_c(),
    }

    print("\n" + "=" * 50)
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    total = len(results)
    passed = sum(results.values())
    print(f"\nResult: {passed}/{total} critical tests passed")
    sys.exit(0 if passed == total else 1)
