"""
Unit tests for RPM Engine (capital_flow, relative_strength metrics)
"""

import pytest
import numpy as np
from rpm_engine import RPMEngine, CapitalFlowMetric, RelativeStrengthMetric


@pytest.fixture
def sample_ohlcv():
    """Generate synthetic OHLCV data (150 candles for testing)."""
    np.random.seed(42)
    closes = 100 + np.cumsum(np.random.normal(0, 2, 150))
    volumes = 1000000 + np.random.normal(0, 200000, 150)

    return [
        {
            "timestamp": i * 86400,
            "open": closes[i] - 1,
            "high": closes[i] + 2,
            "low": closes[i] - 2,
            "close": closes[i],
            "volume": max(100000, volumes[i]),
        }
        for i in range(150)
    ]


@pytest.fixture
def engine():
    return RPMEngine()


def test_capital_flow_calculation(engine, sample_ohlcv):
    """Test capital_flow metric calculation."""
    metric = engine.calculate_capital_flow(sample_ohlcv, "BTC")

    assert isinstance(metric, CapitalFlowMetric)
    assert -1.0 <= metric.value <= 1.0
    assert 0.0 <= metric.confidence <= 1.0
    assert metric.timestamp == sample_ohlcv[-1]["timestamp"]
    assert metric.lookback_days == 7


def test_capital_flow_insufficient_data(engine):
    """Test capital_flow with insufficient data."""
    short_ohlcv = [
        {"timestamp": 0, "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000000}
    ]

    metric = engine.calculate_capital_flow(short_ohlcv, "BTC")
    assert metric.value == 0.0
    assert metric.confidence == 0.0


def test_relative_strength_calculation(engine, sample_ohlcv):
    """Test relative_strength metric calculation."""
    ohlcv_dict = {
        "BTC": sample_ohlcv,
        "ETH": sample_ohlcv[:],
        "SOL": sample_ohlcv[:],
        "AVAX": sample_ohlcv[:],
    }

    metric = engine.calculate_relative_strength(ohlcv_dict, "BTC")

    assert isinstance(metric, RelativeStrengthMetric)
    assert -1.0 <= metric.value <= 1.0
    assert metric.timestamp == sample_ohlcv[-1]["timestamp"]
    assert metric.lookback_days == 14


def test_relative_strength_missing_symbol(engine, sample_ohlcv):
    """Test relative_strength with missing target symbol."""
    ohlcv_dict = {"ETH": sample_ohlcv}

    metric = engine.calculate_relative_strength(ohlcv_dict, "BTC")
    assert metric.value == 0.0
    assert metric.symbol_momentum == 0.0
    assert metric.market_baseline == 0.0


def test_score_rpm_partial_single_component(engine, sample_ohlcv):
    """Test partial RPM score calculation for single component."""
    ohlcv_dict = {"BTC": sample_ohlcv}

    scores = engine.score_rpm_partial(ohlcv_dict, "BTC", components=["capital_flow"])

    assert "capital_flow" in scores
    assert "relative_strength" not in scores
    assert -1.0 <= scores["capital_flow"] <= 1.0


def test_score_rpm_partial_all_components(engine, sample_ohlcv):
    """Test partial RPM score calculation for all components."""
    ohlcv_dict = {
        "BTC": sample_ohlcv,
        "ETH": sample_ohlcv[:],
        "SOL": sample_ohlcv[:],
        "AVAX": sample_ohlcv[:],
    }

    scores = engine.score_rpm_partial(ohlcv_dict, "BTC")

    assert "capital_flow" in scores
    assert "relative_strength" in scores
    assert -1.0 <= scores["capital_flow"] <= 1.0
    assert -1.0 <= scores["relative_strength"] <= 1.0


def test_capital_flow_confidence(engine, sample_ohlcv):
    """Test that high confidence correlates with absolute value."""
    metric = engine.calculate_capital_flow(sample_ohlcv, "BTC")

    # Confidence should equal absolute value of normalized score
    assert abs(metric.confidence - abs(metric.value)) < 0.01
