import pytest
import pandas as pd
from datetime import datetime
from src.data.universe_filter import (
    MarketCapFilter, VolumeFilter, DataAvailabilityFilter,
    DataQualityFilter, UniverseFilter, FilterResult
)


class TestMarketCapFilter:
    def test_market_cap_pass(self):
        f = MarketCapFilter(min_market_cap=1e9, max_market_cap=1e12)
        result = f.apply(1e11, "BTC")
        assert result.status == "PASS"

    def test_market_cap_below_min(self):
        f = MarketCapFilter(min_market_cap=1e9)
        result = f.apply(1e8, "TOKEN")
        assert result.status == "FAIL"
        assert "min" in result.reason

    def test_market_cap_above_max(self):
        f = MarketCapFilter(max_market_cap=1e12)
        result = f.apply(1e13, "TOKEN")
        assert result.status == "FAIL"
        assert "max" in result.reason

    def test_market_cap_none(self):
        f = MarketCapFilter()
        result = f.apply(None, "TOKEN")
        assert result.status == "UNKNOWN"

    def test_market_cap_zero(self):
        f = MarketCapFilter(min_market_cap=1e9)
        result = f.apply(0, "TOKEN")
        assert result.status == "FAIL"


class TestVolumeFilter:
    def test_volume_pass(self):
        f = VolumeFilter(min_volume_24h=1e6)
        result = f.apply(1e7, "BTC")
        assert result.status == "PASS"

    def test_volume_below_min(self):
        f = VolumeFilter(min_volume_24h=1e6)
        result = f.apply(1e5, "TOKEN")
        assert result.status == "FAIL"
        assert "min" in result.reason

    def test_volume_none(self):
        f = VolumeFilter(min_volume_24h=1e6)
        result = f.apply(None, "TOKEN")
        assert result.status == "UNKNOWN"

    def test_volume_zero(self):
        f = VolumeFilter(min_volume_24h=1e6)
        result = f.apply(0, "TOKEN")
        assert result.status == "UNKNOWN"

    def test_volume_no_minimum(self):
        f = VolumeFilter()
        result = f.apply(100, "TOKEN")
        assert result.status == "PASS"


class TestDataAvailabilityFilter:
    def test_sufficient_daily_and_4h(self):
        f = DataAvailabilityFilter(min_candles=50)
        result = f.apply("BTC", daily_count=100, fourbh_count=100)
        assert result.status == "PASS"

    def test_insufficient_daily(self):
        f = DataAvailabilityFilter(require_daily=True, min_candles=50)
        result = f.apply("BTC", daily_count=30, fourbh_count=100)
        assert result.status == "FAIL"
        assert "daily" in result.reason

    def test_insufficient_4h(self):
        f = DataAvailabilityFilter(require_4h=True, min_candles=50)
        result = f.apply("BTC", daily_count=100, fourbh_count=30)
        assert result.status == "FAIL"
        assert "4h" in result.reason

    def test_daily_not_required(self):
        f = DataAvailabilityFilter(require_daily=False, require_4h=True, min_candles=50)
        result = f.apply("BTC", daily_count=0, fourbh_count=100)
        assert result.status == "PASS"

    def test_4h_not_required(self):
        f = DataAvailabilityFilter(require_daily=True, require_4h=False, min_candles=50)
        result = f.apply("BTC", daily_count=100, fourbh_count=0)
        assert result.status == "PASS"


class TestDataQualityFilter:
    def test_clean_data(self):
        f = DataQualityFilter()
        daily_df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "open": [100.0] * 100,
            "high": [102.0] * 100,
            "low": [98.0] * 100,
            "close": [101.0] * 100,
            "volume": [1000.0] * 100,
        })
        fourbh_df = daily_df.copy()
        result = f.apply("BTC", daily_df, fourbh_df)
        assert result.status == "PASS"

    def test_nan_in_daily(self):
        f = DataQualityFilter()
        daily_df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "open": [100.0] * 50 + [None] * 50,
            "high": [102.0] * 100,
            "low": [98.0] * 100,
            "close": [101.0] * 100,
            "volume": [1000.0] * 100,
        })
        fourbh_df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "open": [100.0] * 100,
            "high": [102.0] * 100,
            "low": [98.0] * 100,
            "close": [101.0] * 100,
            "volume": [1000.0] * 100,
        })
        result = f.apply("BTC", daily_df, fourbh_df)
        assert result.status == "FAIL"
        assert "NaN" in result.reason

    def test_duplicate_timestamps(self):
        f = DataQualityFilter()
        daily_df = pd.DataFrame({
            "timestamp": [datetime(2024, 1, 1, 0, 0, 0)] * 100,
            "open": [100.0] * 100,
            "high": [102.0] * 100,
            "low": [98.0] * 100,
            "close": [101.0] * 100,
            "volume": [1000.0] * 100,
        })
        fourbh_df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "open": [100.0] * 100,
            "high": [102.0] * 100,
            "low": [98.0] * 100,
            "close": [101.0] * 100,
            "volume": [1000.0] * 100,
        })
        result = f.apply("BTC", daily_df, fourbh_df)
        assert result.status == "FAIL"
        assert "duplicate" in result.reason

    def test_non_monotonic_timestamps(self):
        f = DataQualityFilter()
        daily_df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=50).tolist() +
                         pd.date_range("2024-01-01", periods=50).tolist()[::-1],
            "open": [100.0] * 100,
            "high": [102.0] * 100,
            "low": [98.0] * 100,
            "close": [101.0] * 100,
            "volume": [1000.0] * 100,
        })
        fourbh_df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "open": [100.0] * 100,
            "high": [102.0] * 100,
            "low": [98.0] * 100,
            "close": [101.0] * 100,
            "volume": [1000.0] * 100,
        })
        result = f.apply("BTC", daily_df, fourbh_df)
        assert result.status == "FAIL"
        assert "monotonic" in result.reason

    def test_empty_dataframe(self):
        f = DataQualityFilter()
        daily_df = pd.DataFrame()
        fourbh_df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "open": [100.0] * 100,
            "high": [102.0] * 100,
            "low": [98.0] * 100,
            "close": [101.0] * 100,
            "volume": [1000.0] * 100,
        })
        result = f.apply("BTC", daily_df, fourbh_df)
        assert result.status == "FAIL"
        assert "empty" in result.reason


class TestUniverseFilterComposition:
    def test_all_pass(self):
        metadata = pd.DataFrame({
            "symbol": ["BTC", "ETH"],
            "name": ["Bitcoin", "Ethereum"],
            "market_cap": [1e12, 5e11],
            "volume_24h": [1e10, 5e9],
        })

        ohlcv_counts = {
            ("BTC", "daily"): 100,
            ("BTC", "4h"): 400,
            ("ETH", "daily"): 100,
            ("ETH", "4h"): 400,
        }

        ohlcv_data = {}
        for symbol in ["BTC", "ETH"]:
            for tf in ["daily", "4h"]:
                ohlcv_data[(symbol, tf)] = pd.DataFrame({
                    "timestamp": pd.date_range("2024-01-01", periods=100),
                    "open": [100.0] * 100,
                    "high": [102.0] * 100,
                    "low": [98.0] * 100,
                    "close": [101.0] * 100,
                    "volume": [1000.0] * 100,
                })

        f = UniverseFilter(
            MarketCapFilter(min_market_cap=1e10),
            VolumeFilter(min_volume_24h=1e8),
            DataAvailabilityFilter(min_candles=50),
            DataQualityFilter(),
        )

        universe, rejections = f.apply_all(metadata, ohlcv_counts, ohlcv_data)

        assert len(universe) == 2
        assert len(rejections) == 0

    def test_some_fail(self):
        metadata = pd.DataFrame({
            "symbol": ["BTC", "MICRO"],
            "name": ["Bitcoin", "Micro Cap"],
            "market_cap": [1e12, 1e6],
            "volume_24h": [1e10, 1e3],
        })

        ohlcv_counts = {
            ("BTC", "daily"): 100,
            ("BTC", "4h"): 400,
            ("MICRO", "daily"): 10,
            ("MICRO", "4h"): 40,
        }

        ohlcv_data = {
            ("BTC", "daily"): pd.DataFrame({
                "timestamp": pd.date_range("2024-01-01", periods=100),
                "open": [100.0] * 100,
                "high": [102.0] * 100,
                "low": [98.0] * 100,
                "close": [101.0] * 100,
                "volume": [1000.0] * 100,
            }),
            ("BTC", "4h"): pd.DataFrame({
                "timestamp": pd.date_range("2024-01-01", periods=100),
                "open": [100.0] * 100,
                "high": [102.0] * 100,
                "low": [98.0] * 100,
                "close": [101.0] * 100,
                "volume": [1000.0] * 100,
            }),
        }

        f = UniverseFilter(
            MarketCapFilter(min_market_cap=1e10),
            VolumeFilter(min_volume_24h=1e6),
            DataAvailabilityFilter(min_candles=50),
            DataQualityFilter(),
        )

        universe, rejections = f.apply_all(metadata, ohlcv_counts, ohlcv_data)

        assert len(universe) == 1
        assert "BTC" in universe["symbol"].values
        assert "MICRO" not in universe["symbol"].values
        assert len(rejections) >= 1  # MICRO fails on multiple filters
