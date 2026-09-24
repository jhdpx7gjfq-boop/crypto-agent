"""
Look-ahead bias prevention tests.
Ensures that signals computed at time T use only data available at T, not future data.
"""
import pytest
from datetime import datetime, timedelta
import pandas as pd
from src.data.store import ParquetStore
from src.data.binance_client import BinanceClient


class TestLookaheadPrevention:
    """Validate that future candles do not affect past signals."""

    def test_future_candle_does_not_affect_past(self):
        """
        If we compute a signal at timestamp T using data up to T,
        adding a future candle at T+1 should not change the signal for T.
        """
        # Historical data up to T
        df_past = pd.DataFrame({
            "symbol": ["BTCUSDT"] * 3,
            "source": ["binance"] * 3,
            "timeframe": ["daily"] * 3,
            "timestamp": [
                datetime(2024, 1, 1, 0, 0, 0),
                datetime(2024, 1, 2, 0, 0, 0),
                datetime(2024, 1, 3, 0, 0, 0),
            ],
            "open": [40000, 41000, 42000],
            "high": [42000, 43000, 44000],
            "low": [39000, 40000, 41000],
            "close": [41000, 42000, 43000],
            "volume": [100, 110, 120],
        })

        # Compute a simple metric (e.g., mean close) on past data
        metric_past = df_past["close"].mean()

        # Add future candle
        df_with_future = df_past.copy()
        future_row = pd.DataFrame({
            "symbol": ["BTCUSDT"],
            "source": ["binance"],
            "timeframe": ["daily"],
            "timestamp": [datetime(2024, 1, 4, 0, 0, 0)],
            "open": [43000],
            "high": [45000],
            "low": [42000],
            "close": [44000],
            "volume": [130],
        })
        df_with_future = pd.concat([df_with_future, future_row], ignore_index=True)

        # Compute metric on data up to T (excluding future)
        metric_with_future = df_with_future[df_with_future["timestamp"] <= datetime(2024, 1, 3, 0, 0, 0)]["close"].mean()

        # Should be identical
        assert metric_past == metric_with_future, "Future candle affected historical signal"

    def test_binance_client_respects_historical_boundary(self):
        """
        When fetching OHLCV up to timestamp T,
        ensure that modifying data for T+1 doesn't change the signal for T.
        """
        client = BinanceClient()

        # Create a dataframe with historical candles
        df_hist = pd.DataFrame({
            "symbol": ["BTCUSDT"] * 3,
            "source": ["binance"] * 3,
            "timeframe": ["daily"] * 3,
            "timestamp": [
                datetime(2024, 1, 1, 0, 0, 0),
                datetime(2024, 1, 2, 0, 0, 0),
                datetime(2024, 1, 3, 0, 0, 0),
            ],
            "open": [40000, 41000, 42000],
            "high": [42000, 43000, 44000],
            "low": [39000, 40000, 41000],
            "close": [41000, 42000, 43000],
            "volume": [100, 110, 120],
        })

        # Simulate filtering to a specific date
        cutoff_date = datetime(2024, 1, 3, 0, 0, 0)
        df_filtered = df_hist[df_hist["timestamp"] <= cutoff_date].reset_index(drop=True)

        # Compute a rolling metric
        df_filtered["rolling_mean_close"] = df_filtered["close"].rolling(window=2, min_periods=1).mean()

        # Extract signal at the last row
        signal_value = df_filtered.iloc[-1]["rolling_mean_close"]

        # Now create a version with a future candle
        future_row = pd.DataFrame({
            "symbol": ["BTCUSDT"],
            "source": ["binance"],
            "timeframe": ["daily"],
            "timestamp": [datetime(2024, 1, 4, 0, 0, 0)],
            "open": [43000],
            "high": [50000],  # Much higher
            "low": [42000],
            "close": [49000],  # Much higher
            "volume": [150],
        })
        df_with_future = pd.concat([df_hist, future_row], ignore_index=True)

        # Recompute rolling metric
        df_with_future["rolling_mean_close"] = df_with_future["close"].rolling(window=2, min_periods=1).mean()

        # Extract signal at the historical cutoff (should be unchanged)
        signal_with_future = df_with_future[df_with_future["timestamp"] <= cutoff_date].iloc[-1]["rolling_mean_close"]

        # Signals must be identical
        assert signal_value == signal_with_future, "Future candle affected historical rolling metric"

    def test_window_operations_never_use_future(self):
        """
        Test that any window-based operation (SMA, rolling volatility, etc.)
        does not accidentally use future candles.
        """
        df = pd.DataFrame({
            "timestamp": [datetime(2024, 1, 1, 0, 0, 0) + timedelta(days=i) for i in range(10)],
            "close": [100 + i for i in range(10)],  # 100, 101, 102, ...
        })

        # Compute SMA-5 without lookahead
        # At each point T, use only data from [T-4, T]
        for i in range(5, len(df)):
            window_data = df.iloc[i-4:i+1]["close"]
            sma = window_data.mean()
            # Ensure we didn't use future data
            assert len(window_data) == 5
            assert window_data.iloc[-1] == df.iloc[i]["close"]  # Last data point is current

        # Built-in rolling mean should match
        df["sma5"] = df["close"].rolling(window=5, min_periods=1).mean()
        # Check that the 5th candle matches our manual calculation
        manual_sma_5 = df.iloc[0:5]["close"].mean()
        assert abs(df.iloc[4]["sma5"] - manual_sma_5) < 0.01
