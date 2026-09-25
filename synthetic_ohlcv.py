"""
Synthetic OHLCV data generator for RRP validation.

Creates realistic price/volume data patterns for backtesting without live API calls.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any


def generate_dormant_period(
    start_price: float = 100.0,
    days: int = 100,
    start_timestamp: int = 0,
) -> List[Dict[str, Any]]:
    """Generate dormant period: low volume, flat price, minimal volatility."""
    ohlcv = []
    price = start_price

    for i in range(days):
        # Minimal price movement (±0.1% daily)
        daily_move = np.random.normal(0, 0.001) * price
        price += daily_move

        open_price = price
        high_price = price * (1 + np.random.uniform(0, 0.0005))
        low_price = price * (1 - np.random.uniform(0, 0.0005))
        close_price = price

        # Very low volume during dormancy
        volume = np.random.uniform(50, 200)
        quote_volume = volume * price

        ohlcv.append(
            {
                "timestamp": start_timestamp + i * 86400000,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "quote_asset_volume": quote_volume,
            }
        )

    return ohlcv


def generate_revival_period(
    start_price: float = 100.0,
    days: int = 100,
    start_timestamp: int = 0,
    recovery_strength: float = 1.5,  # 1.0 = moderate, 2.0 = strong
) -> List[Dict[str, Any]]:
    """Generate revival period: volume spike, uptrend, momentum."""
    ohlcv = []
    price = start_price

    for i in range(days):
        # Strong uptrend with decreasing volatility (classic recovery)
        trend = 0.005 * recovery_strength * (1 - i / days)
        volatility = 0.02 * (1 - i / (2 * days))

        daily_move = trend * price + np.random.normal(0, volatility) * price
        price += daily_move

        open_price = price - daily_move
        high_price = max(open_price, price) * (1 + np.random.uniform(0, 0.005))
        low_price = min(open_price, price) * (1 - np.random.uniform(0, 0.005))
        close_price = price

        # Volume surge during revival (5-10x dormancy level)
        base_volume = 100
        volume = base_volume * np.random.uniform(5, 10) * (1 + i / days)
        quote_volume = volume * price

        ohlcv.append(
            {
                "timestamp": start_timestamp + i * 86400000,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "quote_asset_volume": quote_volume,
            }
        )

    return ohlcv


def generate_realistic_365day_scenario(
    scenario: str = "dormancy_then_revival",
) -> List[Dict[str, Any]]:
    """Generate 365-day OHLCV scenario for RRP testing.

    Scenarios:
    - dormancy_then_revival: 255 days dormant, 110 days strong revival
    - flat: No clear pattern (baseline)
    - strong_uptrend: Consistent uptrend throughout
    """
    ohlcv = []
    base_timestamp = int(datetime(2025, 1, 1).timestamp()) * 1000

    if scenario == "dormancy_then_revival":
        # Phase 1: 255 days dormant
        phase1 = generate_dormant_period(
            start_price=100.0,
            days=255,
            start_timestamp=base_timestamp,
        )
        ohlcv.extend(phase1)

        # Phase 2: 110 days revival
        final_dormant_price = phase1[-1]["close"]
        phase2 = generate_revival_period(
            start_price=final_dormant_price,
            days=110,
            start_timestamp=base_timestamp + 255 * 86400000,
            recovery_strength=1.5,
        )
        ohlcv.extend(phase2)

    elif scenario == "flat":
        # Flat market with minimal volatility throughout
        price = 100.0
        for i in range(365):
            daily_move = np.random.normal(0, 0.0002) * price
            price += daily_move

            ohlcv.append(
                {
                    "timestamp": base_timestamp + i * 86400000,
                    "open": price,
                    "high": price * 1.001,
                    "low": price * 0.999,
                    "close": price,
                    "volume": 500,
                    "quote_asset_volume": 500 * price,
                }
            )

    elif scenario == "strong_uptrend":
        # Consistent uptrend with high volume
        price = 100.0
        for i in range(365):
            daily_move = 0.002 * price  # 0.2% daily uptrend
            daily_move += np.random.normal(0, 0.01) * price
            price += daily_move

            volume = 1000 + np.random.uniform(0, 500)

            ohlcv.append(
                {
                    "timestamp": base_timestamp + i * 86400000,
                    "open": price - daily_move,
                    "high": price * (1 + np.random.uniform(0, 0.01)),
                    "low": price * (1 - np.random.uniform(0, 0.01)),
                    "close": price,
                    "volume": volume,
                    "quote_asset_volume": volume * price,
                }
            )

    return ohlcv


if __name__ == "__main__":
    # Test synthetic data generation
    scenarios = [
        "dormancy_then_revival",
        "flat",
        "strong_uptrend",
    ]

    for scenario in scenarios:
        data = generate_realistic_365day_scenario(scenario)
        print(f"\n{scenario} (365 days):")
        print(f"  First candle: {data[0]}")
        print(f"  Last candle: {data[-1]}")
        print(f"  Price move: ${data[0]['close']:.2f} → ${data[-1]['close']:.2f}")
        print(f"  Avg volume: {np.mean([c['volume'] for c in data]):.0f}")
