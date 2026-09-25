"""Test fixtures for market data."""

from datetime import datetime, timedelta
from typing import List
import random

from src.core.models import OHLCV, MarketRegime, RegimeType


def generate_mock_ohlcv(
    count: int = 100,
    start_price: float = 50000.0,
    volatility: float = 0.02,
) -> List[OHLCV]:
    """Generate synthetic OHLCV for testing."""

    ohlcv_list = []
    now = datetime.utcnow()
    current_price = start_price

    for i in range(count):
        timestamp = now - timedelta(days=count - i)

        # Random walk
        change = random.uniform(-volatility, volatility * 1.5)
        current_price *= (1 + change)

        vol = volatility / 2
        open_price = current_price * (1 - vol)
        high_price = current_price * (1 + vol)
        low_price = current_price * (1 - vol)
        close_price = current_price
        volume = random.uniform(1e8, 5e9)

        try:
            ohlcv = OHLCV(
                timestamp=timestamp,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
            )
            ohlcv_list.append(ohlcv)
        except ValueError:
            continue

    return ohlcv_list


def generate_bull_ohlcv(count: int = 100) -> List[OHLCV]:
    """Generate uptrend OHLCV."""
    ohlcv = generate_mock_ohlcv(count, start_price=50000.0, volatility=0.01)

    # Add uptrend bias
    for i, candle in enumerate(ohlcv):
        bias = i / count * 0.15  # 15% total increase
        ohlcv[i] = OHLCV(
            timestamp=candle.timestamp,
            open=candle.open * (1 + bias),
            high=candle.high * (1 + bias),
            low=candle.low * (1 + bias),
            close=candle.close * (1 + bias),
            volume=candle.volume,
        )

    return ohlcv


def generate_bear_ohlcv(count: int = 100) -> List[OHLCV]:
    """Generate downtrend OHLCV."""
    ohlcv = generate_mock_ohlcv(count, start_price=50000.0, volatility=0.015)

    # Add downtrend bias
    for i, candle in enumerate(ohlcv):
        bias = -i / count * 0.20  # 20% total decrease
        ohlcv[i] = OHLCV(
            timestamp=candle.timestamp,
            open=candle.open * (1 + bias),
            high=candle.high * (1 + bias),
            low=candle.low * (1 + bias),
            close=candle.close * (1 + bias),
            volume=candle.volume,
        )

    return ohlcv


def generate_sideways_ohlcv(count: int = 100) -> List[OHLCV]:
    """Generate range-bound OHLCV."""
    ohlcv = generate_mock_ohlcv(count, start_price=50000.0, volatility=0.005)
    return ohlcv


def generate_accumulation_ohlcv(count: int = 100) -> List[OHLCV]:
    """Generate OHLCV with accumulation pattern (tight range)."""
    ohlcv = []
    now = datetime.utcnow()
    base_price = 50000.0
    range_width = 500.0  # Tight range

    for i in range(count):
        timestamp = now - timedelta(days=count - i)

        # Price stays in tight range
        price_offset = random.uniform(-range_width / 2, range_width / 2)
        open_price = base_price + price_offset
        close_price = base_price + random.uniform(-range_width / 2, range_width / 2)
        high_price = max(open_price, close_price) + 100
        low_price = min(open_price, close_price) - 100

        # Volume increases on bounces
        if i % 10 == 0:
            volume = 3e9
        else:
            volume = 1e9

        try:
            ohlcv.append(
                OHLCV(
                    timestamp=timestamp,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                )
            )
        except ValueError:
            continue

    return ohlcv


def generate_market_regime(
    regime: RegimeType = RegimeType.BULL,
    btc_dominance: float = 55.0,
    funding_rate: float = 0.0005,
) -> MarketRegime:
    """Generate market regime snapshot."""

    return MarketRegime(
        timestamp=datetime.utcnow(),
        regime=regime,
        btc_dominance=btc_dominance,
        funding_rate=funding_rate,
        open_interest_change=0.0,
        dxy=None,
        us10y=None,
        macro_score=50.0,
    )


# Preset fixtures
SAMPLE_BULL_OHLCV = generate_bull_ohlcv(100)
SAMPLE_BEAR_OHLCV = generate_bear_ohlcv(100)
SAMPLE_SIDEWAYS_OHLCV = generate_sideways_ohlcv(100)
SAMPLE_ACCUMULATION_OHLCV = generate_accumulation_ohlcv(100)

SAMPLE_BULL_REGIME = generate_market_regime(RegimeType.BULL)
SAMPLE_BEAR_REGIME = generate_market_regime(RegimeType.BEAR)
SAMPLE_SIDEWAYS_REGIME = generate_market_regime(RegimeType.SIDEWAYS)
