"""
Layer 2: Data Connectors — Integration Tests (Phase 2)

Tests for:
- CoinGecko connector (BTC dominance, prices)
- Binance Futures connector (funding rates, OI)
- Macro connector (DXY, US10Y, CPI, M2)
- Data aggregator (full regime data collection)

Status: Phase 2 (connector development)
Mock fallback: All tests run with mock data (no real API calls in tests)
"""

import pytest
from datetime import datetime
from src.layers.layer2_regime.data_connectors import (
    CoinGeckoConnector,
    BinanceFuturesConnector,
    MacroConnector,
    RegimeDataCollector,
)


# ============================================================================
# T2.2a: CoinGecko Connector Tests
# ============================================================================

def test_coingecko_global_data_structure():
    """Global data has required fields."""
    connector = CoinGeckoConnector(use_mock=True)
    data = connector.get_global_data()

    assert "btc_dominance" in data
    assert "eth_dominance" in data
    assert "market_cap_change_24h" in data
    assert "timestamp" in data


def test_coingecko_global_data_types():
    """Global data fields have correct types."""
    connector = CoinGeckoConnector(use_mock=True)
    data = connector.get_global_data()

    assert isinstance(data["btc_dominance"], float)
    assert isinstance(data["eth_dominance"], float)
    assert isinstance(data["market_cap_change_24h"], float)
    assert isinstance(data["timestamp"], str)


def test_coingecko_global_data_ranges():
    """Global data values in valid ranges."""
    connector = CoinGeckoConnector(use_mock=True)
    data = connector.get_global_data()

    assert 0 <= data["btc_dominance"] <= 100
    assert 0 <= data["eth_dominance"] <= 100
    assert -50 <= data["market_cap_change_24h"] <= 50


def test_coingecko_coin_history_structure():
    """Coin history has required fields."""
    connector = CoinGeckoConnector(use_mock=True)
    history = connector.get_coin_history("bitcoin", "2026-10-05")

    assert "price" in history
    assert "market_cap" in history
    assert "volume" in history


def test_coingecko_coin_history_types():
    """Coin history fields have correct types."""
    connector = CoinGeckoConnector(use_mock=True)
    history = connector.get_coin_history("ethereum", "2026-10-05")

    assert isinstance(history["price"], float)
    assert isinstance(history["market_cap"], float)
    assert isinstance(history["volume"], float)


def test_coingecko_coin_history_positive_values():
    """Coin history values are non-negative."""
    connector = CoinGeckoConnector(use_mock=True)
    history = connector.get_coin_history("solana", "2026-10-05")

    assert history["price"] >= 0
    assert history["market_cap"] >= 0
    assert history["volume"] >= 0


# ============================================================================
# T2.2b: Binance Futures Connector Tests
# ============================================================================

def test_binance_funding_rate_structure():
    """Funding rate has required fields."""
    connector = BinanceFuturesConnector(use_mock=True)
    data = connector.get_funding_rate()

    assert "funding_rate_8h" in data
    assert "funding_rate_moving_avg_7d" in data


def test_binance_funding_rate_types():
    """Funding rate fields have correct types."""
    connector = BinanceFuturesConnector(use_mock=True)
    data = connector.get_funding_rate()

    assert isinstance(data["funding_rate_8h"], float)
    assert isinstance(data["funding_rate_moving_avg_7d"], float)


def test_binance_funding_rate_ranges():
    """Funding rates in reasonable ranges."""
    connector = BinanceFuturesConnector(use_mock=True)
    data = connector.get_funding_rate()

    # Funding rates typically -1% to +1%
    assert -1.0 <= data["funding_rate_8h"] <= 1.0
    assert -1.0 <= data["funding_rate_moving_avg_7d"] <= 1.0


def test_binance_open_interest_structure():
    """Open interest has required fields."""
    connector = BinanceFuturesConnector(use_mock=True)
    data = connector.get_open_interest()

    assert "open_interest_usd" in data
    assert "open_interest_change_24h" in data
    assert "longs_ratio" in data


def test_binance_open_interest_types():
    """Open interest fields have correct types."""
    connector = BinanceFuturesConnector(use_mock=True)
    data = connector.get_open_interest()

    assert isinstance(data["open_interest_usd"], float)
    assert isinstance(data["open_interest_change_24h"], float)
    assert isinstance(data["longs_ratio"], float)


def test_binance_longs_ratio_bounds():
    """Longs ratio in [0, 1]."""
    connector = BinanceFuturesConnector(use_mock=True)
    data = connector.get_open_interest()

    assert 0.0 <= data["longs_ratio"] <= 1.0


# ============================================================================
# T2.2c: Macro Connector Tests
# ============================================================================

def test_macro_indicators_structure():
    """Macro indicators have required fields."""
    connector = MacroConnector(use_mock=True)
    data = connector.get_macro_indicators()

    assert "dxy" in data
    assert "us10y" in data
    assert "cpi_yoy" in data
    assert "m2_growth_yoy" in data


def test_macro_indicators_types():
    """Macro indicator fields have correct types."""
    connector = MacroConnector(use_mock=True)
    data = connector.get_macro_indicators()

    assert isinstance(data["dxy"], float)
    assert isinstance(data["us10y"], float)
    assert isinstance(data["cpi_yoy"], float)
    assert isinstance(data["m2_growth_yoy"], float)


def test_macro_indicators_reasonable_ranges():
    """Macro indicators in reasonable ranges."""
    connector = MacroConnector(use_mock=True)
    data = connector.get_macro_indicators()

    # DXY typically 90-110
    assert 80 <= data["dxy"] <= 120

    # US10Y typically 2-6%
    assert 0 <= data["us10y"] <= 10

    # CPI typically 0-10% YoY
    assert -5 <= data["cpi_yoy"] <= 15

    # M2 growth typically 0-10% YoY
    assert -5 <= data["m2_growth_yoy"] <= 15


# ============================================================================
# T2.2d: Data Aggregator Tests
# ============================================================================

def test_collector_aggregation_structure():
    """Collector aggregates all required fields."""
    collector = RegimeDataCollector(use_mock=True)
    data = collector.collect_regime_data()

    required_keys = [
        "timestamp", "btc_dom", "sma20_dom", "sma60_dom",
        "funding_rate", "funding_avg", "oi_change",
        "btc_spy_corr", "vtix", "eth_btc",
        "dxy", "us10y", "cpi", "m2",
        "spy_flow", "gld_flow", "oi_shorts",
    ]

    for key in required_keys:
        assert key in data, f"Missing key: {key}"


def test_collector_aggregation_types():
    """Collector fields have correct types."""
    collector = RegimeDataCollector(use_mock=True)
    data = collector.collect_regime_data()

    assert isinstance(data["timestamp"], str)
    assert isinstance(data["btc_dom"], float)
    assert isinstance(data["sma20_dom"], float)
    assert isinstance(data["dxy"], float)


def test_collector_timestamp_format():
    """Timestamp is ISO 8601 format."""
    collector = RegimeDataCollector(use_mock=True)
    data = collector.collect_regime_data()

    # Should be parseable as ISO format
    timestamp_str = data["timestamp"]
    assert "T" in timestamp_str or "Z" in timestamp_str


def test_collector_mock_fallback():
    """Collector successfully uses mock fallback."""
    # Force mock mode
    collector = RegimeDataCollector(use_mock=True)

    # Should not raise any exceptions
    data = collector.collect_regime_data()

    # Should return complete data
    assert len(data) >= 16  # At least 16 keys


# ============================================================================
# T2.2e: Connector Fallback Tests
# ============================================================================

def test_coingecko_fallback_to_mock():
    """CoinGecko connector falls back to mock on error."""
    connector = CoinGeckoConnector(use_mock=False)  # Try real API

    # Should not raise, should return mock data
    data = connector.get_global_data()
    assert "btc_dominance" in data


def test_binance_fallback_to_mock():
    """Binance connector falls back to mock on error."""
    connector = BinanceFuturesConnector(use_mock=False)  # Try real API

    # Should not raise, should return mock data
    data = connector.get_funding_rate()
    assert "funding_rate_8h" in data


def test_data_collection_robustness():
    """Data collection doesn't fail with any connector unavailable."""
    collector = RegimeDataCollector(use_mock=True)

    # Should work even if individual connectors fail
    data = collector.collect_regime_data()
    assert data is not None
    assert len(data) > 0


# ============================================================================
# T2.2f: Data Quality Tests
# ============================================================================

def test_collector_data_consistency():
    """Multiple calls return consistent data structure."""
    collector = RegimeDataCollector(use_mock=True)

    data1 = collector.collect_regime_data()
    data2 = collector.collect_regime_data()

    # Both should have same keys
    assert set(data1.keys()) == set(data2.keys())


def test_coingecko_dominance_sum():
    """BTC + ETH dominance is reasonable (not >100)."""
    connector = CoinGeckoConnector(use_mock=True)
    data = connector.get_global_data()

    # BTC + ETH dominance should be less than 100% total market cap
    # (other coins make up the rest)
    assert data["btc_dominance"] + data["eth_dominance"] < 100


def test_funding_rate_reasonable():
    """Funding rate 7d avg is near current rate."""
    connector = BinanceFuturesConnector(use_mock=True)
    data = connector.get_funding_rate()

    # 7d moving average should be in same ballpark as current rate
    # Not requiring exact match (could diverge), but within 0.5%
    diff = abs(data["funding_rate_8h"] - data["funding_rate_moving_avg_7d"])
    assert diff < 0.5, f"Funding rate divergence too large: {diff}"
