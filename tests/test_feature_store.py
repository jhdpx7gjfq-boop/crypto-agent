import pytest
import pandas as pd
from pathlib import Path
from src.data.feature_store import FeatureStore


@pytest.fixture
def store():
    db_path = "test_features.duckdb"
    store = FeatureStore(db_path)
    yield store
    store.close()
    if Path(db_path).exists():
        Path(db_path).unlink()


@pytest.fixture
def sample_ohlcv():
    dates = pd.date_range("2026-09-01", periods=100, freq="D")
    return pd.DataFrame({
        "timestamp": dates,
        "open": 80000 + (pd.Series(range(100)) * 100),
        "high": 81000 + (pd.Series(range(100)) * 100),
        "low": 79000 + (pd.Series(range(100)) * 100),
        "close": 80500 + (pd.Series(range(100)) * 100),
        "volume": [1e9] * 100,
        "market_cap": [1.6e12] * 100,
    })


def test_init(store):
    assert store.db_path == "test_features.duckdb"
    assert store.conn is not None


def test_ingest_ohlcv(store, sample_ohlcv):
    store.ingest_ohlcv("bitcoin", sample_ohlcv)
    result = store.get_latest("bitcoin", limit=5)
    assert len(result) == 5
    assert "bitcoin" in result["coin_id"].values


def test_calculate_indicators(store, sample_ohlcv):
    store.ingest_ohlcv("bitcoin", sample_ohlcv)
    indicators = store.calculate_indicators("bitcoin")

    assert "rsi14" in indicators.columns
    assert "sma20" in indicators.columns
    assert "sma50" in indicators.columns
    assert "bb_upper" in indicators.columns
    assert "bb_lower" in indicators.columns
    assert "atr14" in indicators.columns

    # Check RSI range
    valid_rsi = indicators["rsi14"].dropna()
    assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()


def test_save_indicators(store, sample_ohlcv):
    store.ingest_ohlcv("bitcoin", sample_ohlcv)
    indicators = store.calculate_indicators("bitcoin")
    store.save_indicators("bitcoin", indicators)

    latest = store.get_latest("bitcoin", limit=1)
    assert "rsi14" in latest.columns
    assert latest["rsi14"].notna().any()


def test_export_parquet(store, sample_ohlcv, tmp_path):
    store.ingest_ohlcv("bitcoin", sample_ohlcv)
    indicators = store.calculate_indicators("bitcoin")
    store.save_indicators("bitcoin", indicators)

    output_path = str(tmp_path / "test.parquet")
    store.export_parquet("bitcoin", output_path, days=100)

    assert Path(output_path).exists()

    # Verify parquet content
    df = pd.read_parquet(output_path)
    assert len(df) > 0
    assert "rsi14" in df.columns
