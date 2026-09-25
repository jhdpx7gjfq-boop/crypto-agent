import pytest
import pandas as pd
from src.analysis.wyckoff_bce import WyckoffBCE


@pytest.fixture
def bce():
    return WyckoffBCE()


@pytest.fixture
def sample_df():
    dates = pd.date_range("2026-08-01", periods=100, freq="D")
    df = pd.DataFrame({
        "timestamp": dates,
        "open": 80000 + (pd.Series(range(100)) * 50),
        "high": 81000 + (pd.Series(range(100)) * 50),
        "low": 79000 + (pd.Series(range(100)) * 50),
        "close": 80500 + (pd.Series(range(100)) * 50),
        "volume": [1e9 + i*1e7 for i in range(100)],
    })
    return df


def test_bce_init(bce):
    assert bce.MIN_SCORE == 5


def test_analyze_insufficient_data(bce):
    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-09-01", periods=5, freq="D"),
        "close": [100] * 5,
        "volume": [1e9] * 5,
    })
    result = bce.analyze(df)
    assert result["score"] == 0
    assert result["reason"] == "insufficient_data"


def test_analyze_returns_dict(bce, sample_df):
    result = bce.analyze(sample_df)

    assert "score" in result
    assert "components" in result
    assert "signal" in result
    assert "timestamp" in result

    assert isinstance(result["score"], (int, float))
    assert 0 <= result["score"] <= 6


def test_analyze_components(bce, sample_df):
    result = bce.analyze(sample_df)
    components = result["components"]

    required_keys = [
        "wyckoff_structure",
        "volume_analysis",
        "selling_exhaustion",
        "smart_money",
        "market_structure",
        "momentum",
    ]

    for key in required_keys:
        assert key in components
        assert 0 <= components[key] <= 1


def test_signal_generation(bce, sample_df):
    result = bce.analyze(sample_df)

    if result["score"] >= bce.MIN_SCORE:
        assert result["signal"] == "BUY"
    else:
        assert result["signal"] == "HOLD"


def test_backtest_signals(bce, sample_df):
    backtest_df = bce.backtest_signals(sample_df)

    assert len(backtest_df) > 0
    assert "timestamp" in backtest_df.columns
    assert "price" in backtest_df.columns
    assert "score" in backtest_df.columns
    assert "signal" in backtest_df.columns

    # All scores 0-6
    assert (backtest_df["score"] >= 0).all()
    assert (backtest_df["score"] <= 6).all()


def test_higher_volume_on_downs_scores_well(bce):
    # Accumulation: high volume on downs, low on ups
    dates = pd.date_range("2026-08-01", periods=30, freq="D")

    closes = []
    volumes = []
    opens = []

    for i in range(30):
        if i % 2 == 0:  # Down day
            closes.append(100 - i * 0.5)
            opens.append(101 - i * 0.5)
            volumes.append(2e9)  # High volume
        else:  # Up day
            closes.append(100.5 - i * 0.5)
            opens.append(100 - i * 0.5)
            volumes.append(1e9)  # Low volume

    df = pd.DataFrame({
        "timestamp": dates,
        "open": opens,
        "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes],
        "close": closes,
        "volume": volumes,
    })

    result = bce.analyze(df)
    # Lower volume on downs should score well
    assert result["components"]["volume_analysis"] >= 0.5
