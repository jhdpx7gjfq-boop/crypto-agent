import pytest
import pandas as pd
import numpy as np
from src.analysis.rcm_rpm_engine import RCMRPMEngine


@pytest.fixture
def engine():
    return RCMRPMEngine()


@pytest.fixture
def sample_coin_data():
    return {
        "id": "ethereum",
        "price_history": pd.DataFrame({
            "close": [100 * (1.02 ** i) for i in range(50)],
        }),
        "sentiment": {
            "bullish": 0.75,
            "neutral": 0.20,
            "bearish": 0.05,
        },
        "on_chain": {
            "exchange_inflow": [100e6 * i for i in range(20)],
            "active_addresses": [1e6 * (1.05 ** i) for i in range(20)],
            "transaction_volume": [500e6 * (1.03 ** i) for i in range(20)],
        },
        "funding_rates": [0.0003] * 7,
        "open_interest": [10e9 * (1.04 ** i) for i in range(14)],
        "narrative_data": {
            "narrative_mentions": 50000,
            "mention_growth_7d": 0.35,
            "mention_growth_30d": 0.75,
        },
    }


def test_engine_init(engine):
    assert engine is not None
    assert hasattr(engine, "WEIGHTS")
    assert hasattr(engine, "THRESHOLDS")
    weights_sum = sum(engine.WEIGHTS.values())
    assert abs(weights_sum - 1.0) < 0.001


def test_score_rotation_returns_dict(engine, sample_coin_data):
    result = engine.score_rotation(sample_coin_data)

    assert isinstance(result, dict)
    assert "coin_id" in result
    assert "total_score" in result
    assert "components" in result
    assert "rotation_signal" in result
    assert "rotation_strength" in result
    assert "confirmation_level" in result


def test_score_ranges(engine, sample_coin_data):
    result = engine.score_rotation(sample_coin_data)

    # Total score 0-100
    assert 0 <= result["total_score"] <= 100

    # All components 0-100
    for component_name, component_score in result["components"].items():
        assert 0 <= component_score <= 100, f"{component_name} out of range: {component_score}"

    # Confirmation 0-1
    assert 0 <= result["confirmation_level"] <= 1


def test_capital_flow_scoring(engine):
    # Positive net inflow
    coin_inflow = {
        "id": "test_inflow",
        "price_history": pd.DataFrame({"close": [100] * 50}),
        "sentiment": {"bullish": 0.5, "neutral": 0.3, "bearish": 0.2},
        "on_chain": {
            "exchange_inflow": [50e6 * i for i in range(20)],  # Growing inflow
            "active_addresses": [1e6] * 20,
            "transaction_volume": [500e6] * 20,
        },
        "funding_rates": [0.0001] * 7,
        "open_interest": [10e9] * 14,
        "narrative_data": {"narrative_mentions": 10000, "mention_growth_7d": 0.1, "mention_growth_30d": 0.2},
    }
    result = engine.score_rotation(coin_inflow)
    assert result["components"]["capital_flow"] > 30

    # Small net outflow
    coin_small_outflow = {
        "id": "test_small_outflow",
        "price_history": pd.DataFrame({"close": [100] * 50}),
        "sentiment": {"bullish": 0.3, "neutral": 0.4, "bearish": 0.3},
        "on_chain": {
            "exchange_inflow": [-1e6] * 20,  # Small consistent outflow
            "active_addresses": [1e6] * 20,
            "transaction_volume": [500e6] * 20,
        },
        "funding_rates": [-0.0002] * 7,
        "open_interest": [10e9] * 14,
        "narrative_data": {"narrative_mentions": 5000, "mention_growth_7d": 0.05, "mention_growth_30d": 0.1},
    }
    result = engine.score_rotation(coin_small_outflow)
    # Small outflow should score lower than significant inflow
    inflow_score = engine.score_rotation(coin_inflow)["components"]["capital_flow"]
    outflow_score = result["components"]["capital_flow"]
    assert outflow_score < inflow_score


def test_relative_strength_scoring(engine):
    # Strong uptrend
    coin_strong = {
        "id": "strong",
        "price_history": pd.DataFrame({
            "close": [100 * (1.05 ** i) for i in range(50)],  # 5% daily growth = huge
        }),
        "sentiment": {"bullish": 0.6, "neutral": 0.3, "bearish": 0.1},
        "on_chain": {"exchange_inflow": [1e6] * 20, "active_addresses": [1e6] * 20, "transaction_volume": [500e6] * 20},
        "funding_rates": [0.0001] * 7,
        "open_interest": [10e9] * 14,
        "narrative_data": {"narrative_mentions": 10000, "mention_growth_7d": 0.1, "mention_growth_30d": 0.2},
    }
    result = engine.score_rotation(coin_strong)
    assert result["components"]["relative_strength"] > 60

    # Downtrend
    coin_weak = {
        "id": "weak",
        "price_history": pd.DataFrame({
            "close": [100 * (0.95 ** i) for i in range(50)],  # Declining
        }),
        "sentiment": {"bullish": 0.2, "neutral": 0.5, "bearish": 0.3},
        "on_chain": {"exchange_inflow": [1e6] * 20, "active_addresses": [1e6] * 20, "transaction_volume": [500e6] * 20},
        "funding_rates": [-0.0002] * 7,
        "open_interest": [10e9] * 14,
        "narrative_data": {"narrative_mentions": 5000, "mention_growth_7d": -0.1, "mention_growth_30d": -0.2},
    }
    result = engine.score_rotation(coin_weak)
    assert result["components"]["relative_strength"] < 50


def test_rotation_signal_classification(engine):
    # Strong rotation
    strong_data = {
        "id": "strong_rotation",
        "price_history": pd.DataFrame({"close": [100 * (1.03 ** i) for i in range(50)]}),
        "sentiment": {"bullish": 0.8, "neutral": 0.15, "bearish": 0.05},
        "on_chain": {
            "exchange_inflow": [100e6 * i for i in range(20)],
            "active_addresses": [1e6 * (1.1 ** i) for i in range(20)],
            "transaction_volume": [500e6 * (1.1 ** i) for i in range(20)],
        },
        "funding_rates": [0.0005] * 7,
        "open_interest": [10e9 * (1.1 ** i) for i in range(14)],
        "narrative_data": {
            "narrative_mentions": 100000,
            "mention_growth_7d": 0.5,
            "mention_growth_30d": 1.0,
        },
    }
    result = engine.score_rotation(strong_data)
    assert result["rotation_signal"] in ["STRONG_ROTATION", "MODERATE_ROTATION"]

    # No rotation
    no_rotation_data = {
        "id": "no_rotation",
        "price_history": pd.DataFrame({"close": [100] * 50}),
        "sentiment": {"bullish": 0.3, "neutral": 0.5, "bearish": 0.2},
        "on_chain": {
            "exchange_inflow": [0] * 20,
            "active_addresses": [1e6] * 20,
            "transaction_volume": [500e6] * 20,
        },
        "funding_rates": [-0.0001] * 7,
        "open_interest": [10e9] * 14,
        "narrative_data": {
            "narrative_mentions": 5000,
            "mention_growth_7d": 0.01,
            "mention_growth_30d": 0.02,
        },
    }
    result = engine.score_rotation(no_rotation_data)
    assert result["rotation_signal"] in ["WEAK_ROTATION", "NO_ROTATION"]


def test_narrative_acceleration_scoring(engine):
    # High narrative growth
    coin_hot = {
        "id": "hot_narrative",
        "price_history": pd.DataFrame({"close": [100] * 50}),
        "sentiment": {"bullish": 0.6, "neutral": 0.3, "bearish": 0.1},
        "on_chain": {"exchange_inflow": [1e6] * 20, "active_addresses": [1e6] * 20, "transaction_volume": [500e6] * 20},
        "funding_rates": [0.0001] * 7,
        "open_interest": [10e9] * 14,
        "narrative_data": {
            "narrative_mentions": 100000,
            "mention_growth_7d": 0.75,  # 75% weekly
            "mention_growth_30d": 2.0,  # 200% monthly
        },
    }
    result = engine.score_rotation(coin_hot)
    assert result["components"]["narrative_acceleration"] > 60

    # Low narrative growth
    coin_cold = {
        "id": "cold_narrative",
        "price_history": pd.DataFrame({"close": [100] * 50}),
        "sentiment": {"bullish": 0.3, "neutral": 0.5, "bearish": 0.2},
        "on_chain": {"exchange_inflow": [1e6] * 20, "active_addresses": [1e6] * 20, "transaction_volume": [500e6] * 20},
        "funding_rates": [-0.0001] * 7,
        "open_interest": [10e9] * 14,
        "narrative_data": {
            "narrative_mentions": 1000,
            "mention_growth_7d": 0.02,
            "mention_growth_30d": 0.05,
        },
    }
    result = engine.score_rotation(coin_cold)
    assert result["components"]["narrative_acceleration"] < 40


def test_fundamental_confirmation_scoring(engine):
    # Growing on-chain activity
    coin_growing = {
        "id": "growing_fundamentals",
        "price_history": pd.DataFrame({"close": [100] * 50}),
        "sentiment": {"bullish": 0.6, "neutral": 0.3, "bearish": 0.1},
        "on_chain": {
            "exchange_inflow": [1e6] * 20,
            "active_addresses": [1e6 * (1.2 ** i) for i in range(20)],  # Growing
            "transaction_volume": [500e6 * (1.15 ** i) for i in range(20)],  # Growing
        },
        "funding_rates": [0.0001] * 7,
        "open_interest": [10e9] * 14,
        "narrative_data": {"narrative_mentions": 10000, "mention_growth_7d": 0.1, "mention_growth_30d": 0.2},
    }
    result = engine.score_rotation(coin_growing)
    assert result["components"]["fundamental_confirmation"] > 30

    # Stagnant activity
    coin_flat = {
        "id": "flat_fundamentals",
        "price_history": pd.DataFrame({"close": [100] * 50}),
        "sentiment": {"bullish": 0.3, "neutral": 0.5, "bearish": 0.2},
        "on_chain": {
            "exchange_inflow": [1e6] * 20,
            "active_addresses": [1e6] * 20,  # Flat
            "transaction_volume": [500e6] * 20,  # Flat
        },
        "funding_rates": [-0.0001] * 7,
        "open_interest": [10e9] * 14,
        "narrative_data": {"narrative_mentions": 5000, "mention_growth_7d": 0.02, "mention_growth_30d": 0.05},
    }
    result = engine.score_rotation(coin_flat)
    assert result["components"]["fundamental_confirmation"] < 30


def test_derivatives_structure_scoring(engine):
    # Bullish derivatives (positive funding, rising OI)
    coin_bullish_derivatives = {
        "id": "bullish_derivatives",
        "price_history": pd.DataFrame({"close": [100] * 50}),
        "sentiment": {"bullish": 0.7, "neutral": 0.2, "bearish": 0.1},
        "on_chain": {"exchange_inflow": [1e6] * 20, "active_addresses": [1e6] * 20, "transaction_volume": [500e6] * 20},
        "funding_rates": [0.0008] * 7,  # High positive
        "open_interest": [10e9 * (1.1 ** i) for i in range(14)],  # Rising
        "narrative_data": {"narrative_mentions": 10000, "mention_growth_7d": 0.1, "mention_growth_30d": 0.2},
    }
    result = engine.score_rotation(coin_bullish_derivatives)
    assert result["components"]["derivatives_structure"] > 50

    # Bearish derivatives (negative funding, falling OI)
    coin_bearish_derivatives = {
        "id": "bearish_derivatives",
        "price_history": pd.DataFrame({"close": [100] * 50}),
        "sentiment": {"bullish": 0.2, "neutral": 0.5, "bearish": 0.3},
        "on_chain": {"exchange_inflow": [1e6] * 20, "active_addresses": [1e6] * 20, "transaction_volume": [500e6] * 20},
        "funding_rates": [-0.0008] * 7,  # High negative
        "open_interest": [10e9 * (0.9 ** i) for i in range(14)],  # Falling
        "narrative_data": {"narrative_mentions": 5000, "mention_growth_7d": -0.1, "mention_growth_30d": -0.2},
    }
    result = engine.score_rotation(coin_bearish_derivatives)
    assert result["components"]["derivatives_structure"] < 30


def test_batch_scoring(engine):
    coins = [
        {
            "id": "coin1",
            "price_history": pd.DataFrame({"close": [100 * (1.02 ** i) for i in range(50)]}),
            "sentiment": {"bullish": 0.6, "neutral": 0.3, "bearish": 0.1},
            "on_chain": {
                "exchange_inflow": [100e6 * i for i in range(20)],
                "active_addresses": [1e6 * (1.05 ** i) for i in range(20)],
                "transaction_volume": [500e6 * (1.03 ** i) for i in range(20)],
            },
            "funding_rates": [0.0003] * 7,
            "open_interest": [10e9 * (1.04 ** i) for i in range(14)],
            "narrative_data": {
                "narrative_mentions": 50000,
                "mention_growth_7d": 0.35,
                "mention_growth_30d": 0.75,
            },
        },
        {
            "id": "coin2",
            "price_history": pd.DataFrame({"close": [100 * (1.01 ** i) for i in range(50)]}),
            "sentiment": {"bullish": 0.5, "neutral": 0.4, "bearish": 0.1},
            "on_chain": {
                "exchange_inflow": [50e6 * i for i in range(20)],
                "active_addresses": [1e6 * (1.02 ** i) for i in range(20)],
                "transaction_volume": [500e6 * (1.01 ** i) for i in range(20)],
            },
            "funding_rates": [0.0001] * 7,
            "open_interest": [10e9 * (1.02 ** i) for i in range(14)],
            "narrative_data": {
                "narrative_mentions": 20000,
                "mention_growth_7d": 0.15,
                "mention_growth_30d": 0.35,
            },
        },
    ]

    result_df = engine.score_batch(coins)

    assert len(result_df) == 2
    assert "coin_id" in result_df.columns
    assert "total_score" in result_df.columns
    assert "signal" in result_df.columns

    # Should be sorted by score descending
    assert result_df["total_score"].iloc[0] >= result_df["total_score"].iloc[1]


def test_walk_forward_backtest(engine):
    # Create simple historical data
    historical_data = []
    for i in range(50):
        historical_data.append({
            "id": "test_coin",
            "timestamp": f"2026-08-{(i % 30) + 1:02d}",
            "price_history": pd.DataFrame({"close": [100 * (1.01 ** j) for j in range(i + 1)]}),
            "sentiment": {"bullish": 0.6, "neutral": 0.3, "bearish": 0.1},
            "on_chain": {
                "exchange_inflow": [1e6 * j for j in range(20)],
                "active_addresses": [1e6 * (1.02 ** j) for j in range(20)],
                "transaction_volume": [500e6 * (1.01 ** j) for j in range(20)],
            },
            "funding_rates": [0.0001] * 7,
            "open_interest": [10e9 * (1.02 ** j) for j in range(14)],
            "narrative_data": {
                "narrative_mentions": 10000,
                "mention_growth_7d": 0.1,
                "mention_growth_30d": 0.2,
            },
        })

    backtest_df = engine.walk_forward_backtest(historical_data, train_window_days=10, test_window_days=5)

    assert len(backtest_df) > 0
    assert "timestamp" in backtest_df.columns
    assert "score" in backtest_df.columns
    assert "signal" in backtest_df.columns
    assert "confirmation" in backtest_df.columns

    # All scores 0-100
    assert (backtest_df["score"] >= 0).all()
    assert (backtest_df["score"] <= 100).all()


def test_confirmation_level(engine, sample_coin_data):
    result = engine.score_rotation(sample_coin_data)

    # Confirmation should be between 0 and 1
    assert 0 <= result["confirmation_level"] <= 1

    # Confirmation should be high when components have low variance
    assert isinstance(result["confirmation_level"], float)
