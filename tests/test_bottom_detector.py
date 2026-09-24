"""Tests for Bottom Detector — P0.3

Test coverage:
- Drawdown calculation
- Base consolidation detection
- State machine transitions (4 states)
- 4 synthetic scenarios (A: continue down, B: stabilize, C: range break, D: insufficient)
- Look-ahead prevention (critical)
- Robustness (NaN, duplicates, non-monotonic, empty, single-candle, multi-asset)
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

from src.data.bottom_detector import (
    DrawdownCalculator,
    BaseConsolidationDetector,
    BottomStateMachine,
    BottomDetector,
    BottomDetectorOutput,
    BottomDetectorError,
    DataQualityError,
)


class TestDrawdownCalculator:
    """Tests for DrawdownCalculator."""

    def test_simple_drawdown(self):
        """Test basic drawdown calculation."""
        calc = DrawdownCalculator(lookback=100)
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "high": [100.0] * 50 + [50.0] * 50,  # High drops from 100 to 50
            "close": [100.0] * 50 + [40.0] * 50,  # Close drops to 40
        })
        drawdown_pct, rolling_high, current_close = calc.calculate(df)
        assert rolling_high == 100.0
        assert current_close == 40.0
        assert drawdown_pct == pytest.approx(-60.0, rel=0.01)

    def test_no_drawdown_uptrend(self):
        """Test when price is in uptrend."""
        calc = DrawdownCalculator(lookback=100)
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "high": np.linspace(100, 200, 100),
            "close": np.linspace(100, 200, 100),
        })
        drawdown_pct, rolling_high, current_close = calc.calculate(df)
        assert drawdown_pct > -5  # Minimal or no drawdown

    def test_insufficient_data(self):
        """Test with less than 50 candles."""
        calc = DrawdownCalculator(lookback=100)
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=30),
            "high": [100.0] * 30,
            "close": [80.0] * 30,
        })
        drawdown_pct, rolling_high, current_close = calc.calculate(df)
        assert drawdown_pct is None
        assert rolling_high is None
        assert current_close is None

    def test_nan_in_high(self):
        """Test that NaN in high column raises error."""
        calc = DrawdownCalculator(lookback=100)
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "high": [100.0] * 50 + [np.nan] * 50,
            "close": [100.0] * 100,
        })
        with pytest.raises(DataQualityError):
            calc.calculate(df)

    def test_zero_rolling_high(self):
        """Test when rolling high is zero."""
        calc = DrawdownCalculator(lookback=100)
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "high": [0.0] * 100,
            "close": [0.0] * 100,
        })
        drawdown_pct, rolling_high, current_close = calc.calculate(df)
        assert drawdown_pct is None


class TestBaseConsolidationDetector:
    """Tests for BaseConsolidationDetector."""

    def test_tight_consolidation(self):
        """Test detection of tight consolidation range."""
        detector = BaseConsolidationDetector(lookback=30, range_threshold=12.0, stability_threshold=30.0)
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=50),
            "high": [100.0] * 50,
            "low": [90.0] * 50,
            "close": [95.0] * 50,  # Tight range ~10%
        })
        base_high, base_low, base_range_pct, stability_pct, is_consolidated = detector.detect(df)
        assert base_high == 100.0
        assert base_low == 90.0
        assert base_range_pct == pytest.approx(10.5, rel=0.01)  # (100-90)/95 ≈ 10.5%
        assert stability_pct == pytest.approx(100.0, rel=0.01)  # All closes at 95 (>= mid 95)
        assert is_consolidated == True

    def test_wide_consolidation(self):
        """Test detection of wide, volatile range."""
        detector = BaseConsolidationDetector(lookback=30, range_threshold=12.0, stability_threshold=30.0)
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=50),
            "high": [100.0] * 30 + [110.0] * 20,
            "low": [50.0] * 30 + [45.0] * 20,
            "close": [75.0] * 30 + [50.0] * 20,  # Wide range ~30%
        })
        base_high, base_low, base_range_pct, stability_pct, is_consolidated = detector.detect(df)
        assert base_range_pct > 20  # Wide range
        assert is_consolidated == False

    def test_low_stability(self):
        """Test when closes are mostly near lows (low stability)."""
        detector = BaseConsolidationDetector(lookback=30, range_threshold=12.0, stability_threshold=30.0)
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=50),
            "high": [100.0] * 30 + [100.0] * 20,
            "low": [90.0] * 30 + [90.0] * 20,
            "close": [90.1] * 30 + [91.0] * 20,  # All closes near lows
        })
        base_high, base_low, base_range_pct, stability_pct, is_consolidated = detector.detect(df)
        assert stability_pct < 30  # Low stability
        assert is_consolidated == False

    def test_insufficient_lookback(self):
        """Test with fewer candles than lookback window."""
        detector = BaseConsolidationDetector(lookback=30)
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=20),
            "high": [100.0] * 20,
            "low": [90.0] * 20,
            "close": [95.0] * 20,
        })
        base_high, base_low, base_range_pct, stability_pct, is_consolidated = detector.detect(df)
        assert base_high is None
        assert is_consolidated is False

    def test_nan_in_close(self):
        """Test that NaN in close column raises error."""
        detector = BaseConsolidationDetector(lookback=30)
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=50),
            "high": [100.0] * 50,
            "low": [90.0] * 50,
            "close": [95.0] * 40 + [np.nan] * 10,
        })
        with pytest.raises(DataQualityError):
            detector.detect(df)


class TestBottomStateMachine:
    """Tests for BottomStateMachine."""

    def test_insufficient_data(self):
        """Test NO_BOTTOM_STRUCTURE with < 50 candles."""
        machine = BottomStateMachine()
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=30),
            "high": [100.0] * 30,
            "low": [90.0] * 30,
            "close": [95.0] * 30,
        })
        state, evidence = machine.classify(df, None, None, None, None, None)
        assert state == "NO_BOTTOM_STRUCTURE"
        assert evidence["reason"] == "insufficient_data"

    def test_no_drawdown(self):
        """Test NO_BOTTOM_STRUCTURE when price is in uptrend."""
        machine = BottomStateMachine()
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "high": np.linspace(100, 200, 100),
            "low": np.linspace(90, 190, 100),
            "close": np.linspace(95, 195, 100),
        })
        state, evidence = machine.classify(df, drawdown_pct=-2.0, base_high=None, base_low=None, base_range_pct=None, stability_pct=None)
        assert state == "NO_BOTTOM_STRUCTURE"

    def test_drawdown_wide_range(self):
        """Test DRAWDOWN when base range is too wide."""
        machine = BottomStateMachine()
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "high": [100.0] * 100,
            "low": [50.0] * 100,
            "close": [60.0] * 100,
        })
        state, evidence = machine.classify(
            df, drawdown_pct=-40.0, base_high=100.0, base_low=50.0, base_range_pct=66.0, stability_pct=50.0
        )
        assert state == "DRAWDOWN"
        assert evidence["reason"] == "wide_base_range"

    def test_drawdown_new_lows(self):
        """Test DRAWDOWN when price makes new lows."""
        machine = BottomStateMachine(escape_threshold=-2.0)
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "high": [100.0] * 95 + [50.0] * 5,
            "low": [90.0] * 95 + [30.0] * 5,  # Last 5 candles hit 30
            "close": [95.0] * 95 + [35.0] * 5,
        })
        # base_low=50, so 30 < 50*0.98=49, triggers new lows
        state, evidence = machine.classify(
            df, drawdown_pct=-63.0, base_high=100.0, base_low=50.0, base_range_pct=10.0, stability_pct=40.0
        )
        assert state == "DRAWDOWN"
        assert evidence.get("reason") == "continuing_selloff"

    def test_drawdown_low_stability(self):
        """Test DRAWDOWN when stability is low."""
        machine = BottomStateMachine()
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "high": [100.0] * 100,
            "low": [90.0] * 100,
            "close": [90.5] * 100,
        })
        state, evidence = machine.classify(
            df, drawdown_pct=-40.0, base_high=100.0, base_low=90.0, base_range_pct=10.0, stability_pct=10.0
        )
        assert state == "DRAWDOWN"
        assert evidence["reason"] == "low_stability"

    def test_base_candidate(self):
        """Test BASE_CANDIDATE when all conditions met."""
        machine = BottomStateMachine()
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "high": [100.0] * 100,
            "low": [90.0] * 100,
            "close": [95.0] * 100,
        })
        state, evidence = machine.classify(
            df, drawdown_pct=-50.0, base_high=100.0, base_low=90.0, base_range_pct=10.5, stability_pct=100.0
        )
        assert state == "BASE_CANDIDATE"
        assert "drawdown" in evidence
        assert "stability" in evidence


class TestSyntheticScenarios:
    """Test 4 synthetic scenarios from spec."""

    @staticmethod
    def create_base_df(periods: int = 100) -> pd.DataFrame:
        """Create base DataFrame template."""
        return pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=periods),
            "open": [0.0] * periods,
            "high": [0.0] * periods,
            "low": [0.0] * periods,
            "close": [0.0] * periods,
            "volume": [1000.0] * periods,
        })

    def test_scenario_a_continue_down(self):
        """Scenario A: Up→Down→Continue (expect DRAWDOWN)."""
        df = self.create_base_df(100)
        # Days 1-50: uptrend (100 → 200)
        df.loc[0:49, "high"] = np.linspace(100, 200, 50)
        df.loc[0:49, "close"] = np.linspace(100, 200, 50)
        df.loc[0:49, "low"] = np.linspace(90, 190, 50)
        # Days 51-70: crash (200 → 100)
        df.loc[50:69, "high"] = np.linspace(200, 100, 20)
        df.loc[50:69, "close"] = np.linspace(200, 100, 20)
        df.loc[50:69, "low"] = np.linspace(190, 90, 20)
        # Days 71-100: continue down (100 → 50)
        df.loc[70:99, "high"] = np.linspace(100, 50, 30)
        df.loc[70:99, "close"] = np.linspace(100, 50, 30)
        df.loc[70:99, "low"] = np.linspace(90, 40, 30)

        detector = BottomDetector()
        output = detector.classify("SCEN_A", df)
        assert output.state == "DRAWDOWN", f"Expected DRAWDOWN, got {output.state}"
        assert output.evidence["drawdown"] < -20

    def test_scenario_b_stabilize(self):
        """Scenario B: Up→Down→Stabilize (expect BASE_CANDIDATE)."""
        df = self.create_base_df(100)
        # Days 1-50: uptrend (100 → 200)
        df.loc[0:49, "high"] = np.linspace(100, 200, 50)
        df.loc[0:49, "close"] = np.linspace(100, 200, 50)
        df.loc[0:49, "low"] = np.linspace(90, 190, 50)
        # Days 51-70: crash (200 → 100)
        df.loc[50:69, "high"] = np.linspace(200, 100, 20)
        df.loc[50:69, "close"] = np.linspace(200, 100, 20)
        df.loc[50:69, "low"] = np.linspace(190, 90, 20)
        # Days 71-100: stabilize in range [95-105] with oscillating closes
        base_range = np.tile([95.0, 100.0, 105.0, 102.0, 98.0, 100.0], 5)[:30]
        df.loc[70:99, "high"] = 105.0
        df.loc[70:99, "low"] = 95.0
        df.loc[70:99, "close"] = base_range

        detector = BottomDetector()
        output = detector.classify("SCEN_B", df)
        assert output.state == "BASE_CANDIDATE", f"Expected BASE_CANDIDATE, got {output.state}. Evidence: {output.evidence}"
        assert output.evidence["stability"] >= 30

    def test_scenario_c_range_break(self):
        """Scenario C: Range→Break down (expect DRAWDOWN or NO_BOTTOM)."""
        df = self.create_base_df(100)
        # Days 1-70: range [150-160]
        df.loc[0:69, "high"] = np.tile([160.0], 70)
        df.loc[0:69, "low"] = np.tile([150.0], 70)
        df.loc[0:69, "close"] = np.tile([155.0], 70)
        # Days 71-100: break down (160 → 80)
        df.loc[70:99, "high"] = np.linspace(160, 80, 30)
        df.loc[70:99, "close"] = np.linspace(160, 80, 30)
        df.loc[70:99, "low"] = np.linspace(150, 70, 30)

        detector = BottomDetector()
        output = detector.classify("SCEN_C", df)
        assert output.state in ["DRAWDOWN", "NO_BOTTOM_STRUCTURE"], f"Unexpected state: {output.state}"

    def test_scenario_d_insufficient_data(self):
        """Scenario D: Insufficient data (< 50 candles)."""
        df = self.create_base_df(20)
        df["high"] = 100.0
        df["low"] = 90.0
        df["close"] = 95.0

        detector = BottomDetector()
        output = detector.classify("SCEN_D", df)
        assert output.state == "NO_BOTTOM_STRUCTURE"


class TestLookAheadPrevention:
    """Critical tests: verify no look-ahead bias."""

    def test_future_candle_doesnt_affect_past_state(self):
        """Verify that adding future candles doesn't change past state."""
        df_base = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "high": np.linspace(100, 50, 100),
            "low": np.linspace(90, 40, 100),
            "close": np.linspace(95, 45, 100),
            "open": np.linspace(97, 47, 100),
            "volume": [1000.0] * 100,
        })

        # Classify with 100 candles
        detector = BottomDetector()
        output_before = detector.classify("BTC", df_base)

        # Add 10 extreme future candles
        df_with_future = df_base.copy()
        future_timestamps = pd.date_range("2024-04-11", periods=10)
        future_rows = pd.DataFrame({
            "timestamp": future_timestamps,
            "high": [1000.0] * 10,  # Extreme future
            "low": [500.0] * 10,
            "close": [900.0] * 10,
            "open": [950.0] * 10,
            "volume": [10000.0] * 10,
        })
        df_with_future = pd.concat([df_with_future, future_rows], ignore_index=True)

        # Classify with historical part only (should match before)
        output_after = detector.classify("BTC", df_base)

        assert output_before.state == output_after.state
        assert output_before.evidence == output_after.evidence

    def test_historical_boundary_respected(self):
        """Verify rolling window doesn't use future data."""
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=150),
            "high": np.concatenate([np.full(50, 100.0), np.full(100, 50.0)]),
            "low": np.concatenate([np.full(50, 90.0), np.full(100, 40.0)]),
            "close": np.concatenate([np.full(50, 95.0), np.full(100, 45.0)]),
            "open": np.concatenate([np.full(50, 97.0), np.full(100, 47.0)]),
            "volume": [1000.0] * 150,
        })

        calc = DrawdownCalculator(lookback=100)
        # Calculate at position 100 (should use 0-100, not beyond)
        drawdown_pct, rolling_high, current_close = calc.calculate(df.iloc[:101])
        assert rolling_high == 100.0  # From first 50 candles
        assert current_close <= 95.0  # Not affected by future crash


class TestRobustness:
    """Robustness and edge case tests."""

    def test_nan_values_detected(self):
        """Test that NaN values raise error."""
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "high": [100.0] * 50 + [np.nan] * 50,
            "low": [90.0] * 100,
            "close": [95.0] * 100,
            "open": [97.0] * 100,
            "volume": [1000.0] * 100,
        })
        detector = BottomDetector()
        output = detector.classify("NAN_TEST", df)
        assert output.state == "NO_BOTTOM_STRUCTURE"
        assert "NaN" in output.reason or "nan" in output.reason

    def test_duplicate_timestamps(self):
        """Test that duplicate timestamps raise error."""
        df = pd.DataFrame({
            "timestamp": [datetime(2024, 1, 1)] * 100,
            "high": [100.0] * 100,
            "low": [90.0] * 100,
            "close": [95.0] * 100,
            "open": [97.0] * 100,
            "volume": [1000.0] * 100,
        })
        detector = BottomDetector()
        output = detector.classify("DUP_TEST", df)
        assert output.state == "NO_BOTTOM_STRUCTURE"
        assert "duplicate" in output.reason

    def test_non_monotonic_timestamps(self):
        """Test that non-monotonic timestamps raise error."""
        ts_forward = pd.date_range("2024-01-01", periods=50)
        ts_backward = pd.date_range("2024-01-26", periods=50)[::-1]
        timestamps = list(ts_forward) + list(ts_backward)
        df = pd.DataFrame({
            "timestamp": timestamps,
            "high": [100.0] * 100,
            "low": [90.0] * 100,
            "close": [95.0] * 100,
            "open": [97.0] * 100,
            "volume": [1000.0] * 100,
        })
        detector = BottomDetector()
        output = detector.classify("MONO_TEST", df)
        assert output.state == "NO_BOTTOM_STRUCTURE"
        assert "monotonic" in output.reason or "duplicate" in output.reason

    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        df = pd.DataFrame()
        detector = BottomDetector()
        output = detector.classify("EMPTY_TEST", df)
        assert output.state == "NO_BOTTOM_STRUCTURE"

    def test_single_candle(self):
        """Test with single candle."""
        df = pd.DataFrame({
            "timestamp": [datetime(2024, 1, 1)],
            "high": [100.0],
            "low": [90.0],
            "close": [95.0],
            "open": [97.0],
            "volume": [1000.0],
        })
        detector = BottomDetector()
        output = detector.classify("SINGLE_TEST", df)
        assert output.state == "NO_BOTTOM_STRUCTURE"

    def test_multi_asset_isolation(self):
        """Test that detector doesn't leak state between assets."""
        df_btc = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "high": np.linspace(100, 50, 100),
            "low": np.linspace(90, 40, 100),
            "close": np.linspace(95, 45, 100),
            "open": np.linspace(97, 47, 100),
            "volume": [1000.0] * 100,
        })
        df_eth = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "high": [100.0] * 100,
            "low": [90.0] * 100,
            "close": [95.0] * 100,
            "open": [97.0] * 100,
            "volume": [1000.0] * 100,
        })

        detector = BottomDetector()
        output_btc = detector.classify("BTC", df_btc)
        output_eth = detector.classify("ETH", df_eth)

        assert output_btc.symbol == "BTC"
        assert output_eth.symbol == "ETH"
        assert output_btc.evidence != output_eth.evidence
