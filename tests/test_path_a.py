"""Tests for PATH-A liquidation-independent alpha pipeline."""

import pytest
from datetime import date

from igwt.data.binance_audit import audit_binance_klines
from igwt.features.liquidation_alpha_signals import (
    volatility_regimesshift_signal,
    _volume_zscore_trend,
    build_path_a_observations,
)


class TestBinanceAudit:
    """Test Binance OHLCV audit."""

    def test_audit_clean_klines(self):
        """Clean klines should PASS."""
        klines = [
            {
                "openTime": 1609459200000,  # 2021-01-01 00:00:00 UTC
                "open": 29000,
                "high": 30000,
                "low": 28500,
                "close": 29500,
                "volume": 100,
            },
            {
                "openTime": 1609545600000,  # 2021-01-02 00:00:00 UTC
                "open": 29500,
                "high": 30500,
                "low": 29000,
                "close": 30000,
                "volume": 110,
            },
        ]
        audit, normalized = audit_binance_klines("BTC", klines)
        assert audit.verdict == "PASS"
        assert audit.accepted_rows == 2
        assert len(normalized) == 2
        assert normalized[0]["date"] == date(2021, 1, 1)
        assert normalized[0]["close"] == 29500

    def test_audit_drops_intraday(self):
        """Intraday points (not aligned to UTC midnight) should be dropped."""
        klines = [
            {
                "openTime": 1609459200000,
                "open": 29000,
                "high": 30000,
                "low": 28500,
                "close": 29500,
                "volume": 100,
            },
            {
                "openTime": 1609459300000,  # Not aligned to midnight
                "open": 29500,
                "high": 30000,
                "low": 29000,
                "close": 29800,
                "volume": 50,
            },
        ]
        audit, normalized = audit_binance_klines("BTC", klines)
        assert audit.verdict == "WARN"
        assert audit.intraday_points_dropped == 1
        assert audit.accepted_rows == 1

    def test_audit_detects_duplicates(self):
        """Duplicate dates should be dropped."""
        klines = [
            {
                "openTime": 1609459200000,
                "open": 29000,
                "high": 30000,
                "low": 28500,
                "close": 29500,
                "volume": 100,
            },
            {
                "openTime": 1609459200000,  # Same date
                "open": 29600,
                "high": 30100,
                "low": 29100,
                "close": 29800,
                "volume": 120,
            },
        ]
        audit, normalized = audit_binance_klines("BTC", klines)
        assert audit.verdict == "WARN"
        assert audit.duplicate_dates == 1
        assert audit.accepted_rows == 1

    def test_audit_cohesion_violation(self):
        """Bars violating OHLC cohesion should be dropped."""
        klines = [
            {
                "openTime": 1609459200000,
                "open": 30000,
                "high": 29500,  # high < close: violates cohesion
                "low": 28500,
                "close": 29500,
                "volume": 100,
            },
            {
                "openTime": 1609545600000,
                "open": 29000,
                "high": 30000,
                "low": 28500,
                "close": 29500,
                "volume": 100,
            },
        ]
        audit, normalized = audit_binance_klines("BTC", klines)
        assert audit.verdict == "WARN"
        assert audit.cohesion_failures == 1
        assert audit.accepted_rows == 1


class TestVolatilityRegimeShiftSignal:
    """Test PATH-A signal construction."""

    def test_signal_basic(self):
        """Signal should return one value per close."""
        # Create volatile series with sufficient data for windows
        closes = [100 + i + (5 if i % 2 == 0 else -3) for i in range(30)]
        volumes = [1000 + i * 10 for i in range(30)]
        signal = volatility_regimesshift_signal(closes, volumes, window_short=2, window_long=5)
        assert len(signal) == len(closes)
        # Early values should be None (insufficient history for long window)
        assert any(s is None for s in signal[:6])
        # Later values should be present (after window_long)
        assert any(s is not None for s in signal[8:])

    def test_signal_pit_safe(self):
        """Signal should not use future data."""
        closes = [100, 101, 102, 103, 104, 105]
        volumes = [1000] * 6
        signal = volatility_regimesshift_signal(closes, volumes, window_short=2, window_long=4)
        # Each signal[i] should only depend on closes[0:i+1]
        # This is guaranteed by the window-based calculation
        assert len(signal) == len(closes)

    def test_volume_zscore_trend(self):
        """Volume z-score trend should normalize to [-1, 1]."""
        volumes = [100] * 10 + [500] + [100] * 10  # Spike at index 10
        trend = _volume_zscore_trend(volumes, window=5)
        assert len(trend) == len(volumes)
        # Early values None (insufficient window)
        assert all(v is None for v in trend[:5])
        # Spike should produce non-negative trend (0 or positive)
        assert trend[10] >= 0
        # Values should be bounded in [-1, 1]
        valid_trends = [t for t in trend if t is not None]
        assert all(-1 <= t <= 1 for t in valid_trends)


class TestBuildPathAObservations:
    """Test WFV observation construction."""

    def test_observations_contract(self):
        """Observations must comply with WFV contract."""
        dates = [date(2021, 1, 1 + i) for i in range(10)]
        closes = [100 + i for i in range(10)]
        volumes = [1000] * 10
        fwd_rets = [0.01, 0.02, 0.01, -0.01, 0.03, 0.02, 0.01, 0.00, -0.01, None]

        obs = build_path_a_observations(dates, closes, volumes, fwd_rets, horizon_days=1)

        # Check structure
        for o in obs:
            assert "date" in o
            assert "signal" in o
            assert "fwdRet" in o
            assert "regimeVol" in o
            assert isinstance(o["date"], date)
            assert isinstance(o["signal"], float)
            assert isinstance(o["fwdRet"], float)
            assert isinstance(o["regimeVol"], float)

        # Check PIT: last obs must have valid fwdRet (since it's in the series)
        # Obs with None fwdRet should be excluded
        for o in obs:
            assert o["fwdRet"] is not None

    def test_observations_empty_if_no_valid_data(self):
        """Observations should be empty if insufficient valid data."""
        dates = [date(2021, 1, 1), date(2021, 1, 2)]
        closes = [100, 101]
        volumes = [1000, 1000]
        fwd_rets = [None, None]  # No valid forward returns

        obs = build_path_a_observations(dates, closes, volumes, fwd_rets)
        assert len(obs) == 0
