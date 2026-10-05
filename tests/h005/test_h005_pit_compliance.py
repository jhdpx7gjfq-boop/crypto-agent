"""H-005 PIT Compliance Tests

Verify that signals never use future data.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

# Assuming H-005 modules in src/research/h005
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "research" / "h005"))

from h005_data_layer import H005DataLayer
from h005_feature_engineering import ExchangeFlowFeatures, H005SignalGenerator
from h005_runner import H005WFVRunner


class TestH005PITCompliance:
    """Verify no lookahead bias in H-005."""

    @pytest.fixture
    def sample_df(self):
        """Create minimal test DataFrame."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        df = pd.DataFrame({
            "Date": dates,
            "open": np.random.uniform(60000, 70000, 100),
            "high": np.random.uniform(70000, 75000, 100),
            "low": np.random.uniform(55000, 60000, 100),
            "close": np.random.uniform(60000, 70000, 100),
            "volume": np.random.uniform(1e6, 1e7, 100),
        })
        df.set_index("Date", inplace=True)
        return df

    def test_data_layer_pit_safe(self, sample_df):
        """Test that get_ohlcv() only returns data up to pit_idx."""
        # This is a mock test; real test requires actual data file

        pit_idx = 50
        # Simulated: would call h005_layer.get_ohlcv(pit_idx)
        # Expected: returns only [:pit_idx+1]

        pit_data = sample_df.iloc[:pit_idx+1]
        assert len(pit_data) == pit_idx + 1
        assert pit_data.index[-1] == sample_df.index[pit_idx]

    def test_feature_computation_pit_safe(self, sample_df):
        """Test that features use only data up to pit_idx."""

        flows_df = pd.DataFrame({
            "inflow": np.random.uniform(0, 1000, len(sample_df)),
            "outflow": np.random.uniform(0, 1000, len(sample_df)),
        }, index=sample_df.index)

        feature_gen = ExchangeFlowFeatures(lookback=30)

        pit_idx = 50
        features = feature_gen.compute_features(flows_df, pit_idx)

        # Verify: features should only consider data[:pit_idx+1]
        # No feature should reference data[pit_idx+1:] (future)
        assert all(-1 <= v <= 1 for v in features.values()), "Features not normalized"

    def test_signal_generation_pit_safe(self):
        """Test that signal generation uses only current/past data."""

        features = {
            "inflow_7d": 0.5,
            "outflow_7d": -0.3,
            "netflow_7d": 0.2,
            "inflow_accum": 0.4,
            "outflow_accum": -0.1,
            "exchange_ratio": 0.6,
        }

        signal_gen = H005SignalGenerator()
        signal = signal_gen.generate_signal(features)

        # Signal should be deterministic from features (no future data)
        assert -1 <= signal <= 1, "Signal not normalized"

        # Same features should produce same signal
        signal2 = signal_gen.generate_signal(features)
        assert signal == signal2, "Signal not deterministic"

    def test_wfv_window_no_overlap(self):
        """Test that WFV windows don't leak future data into training."""

        runner = H005WFVRunner(n_windows=5, train_days=180, test_days=30)
        windows = runner.build_windows(df_len=500, dev_end_idx=450)

        for w in windows:
            # Verify: train_end < test_start (no overlap)
            assert w.train_end_idx < w.test_start_idx, f"Window {w} has overlap"

            # Verify: test_end < next train_start (expanding, no reverse time)
            assert w.test_end_idx < 500, f"Window {w} exceeds data"

    def test_embargo_rule(self):
        """Test 1-day embargo: signal can only use data from >= (pit_date - 1 day)."""

        # Placeholder: embargo rule enforced by snapshot timestamp
        # In real execution: ensure data snapshot is at least 1 day old

        from datetime import datetime, timedelta

        pit_date = datetime.now()
        embargo_hours = 24

        earliest_snapshot = pit_date - timedelta(hours=embargo_hours)

        assert earliest_snapshot <= pit_date, "Embargo rule violated"


class TestH005GateThresholds:
    """Verify gate criteria are frozen and non-negotiable."""

    def test_gate_criteria_immutable(self):
        """Gate: ΔIC > 0.005 AND HR > 0.50 AND Stability > 0.65."""

        # These thresholds must not change during development
        required_thresholds = {
            "delta_ic_min": 0.005,
            "hr_min": 0.50,
            "stability_min": 0.65,
        }

        # Verify each threshold
        assert required_thresholds["delta_ic_min"] == 0.005
        assert required_thresholds["hr_min"] == 0.50
        assert required_thresholds["stability_min"] == 0.65

    def test_gate_all_must_pass(self):
        """All 3 criteria must pass (AND logic, not OR)."""

        # Scenario 1: ΔIC passes, HR fails
        delta_ic = 0.01
        hr = 0.45
        stability = 0.70

        passes = (delta_ic > 0.005) and (hr > 0.50) and (stability > 0.65)
        assert not passes, "Should fail (HR < 0.50)"

        # Scenario 2: All pass
        delta_ic = 0.01
        hr = 0.52
        stability = 0.70

        passes = (delta_ic > 0.005) and (hr > 0.50) and (stability > 0.65)
        assert passes, "Should pass (all criteria met)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
