import pytest
import pandas as pd
from src.analysis.narm_p_plus import NARMPPlus


@pytest.fixture
def narm():
    return NARMPPlus()


@pytest.fixture
def sample_coin_data():
    return {
        "id": "ethereum",
        "name": "Ethereum",
        "narratives": ["AI", "RWA", "DeFi"],
        "adoption": {
            "users": 50e6,
            "tvl": 80e9,
            "growth_7d": 0.25,
            "growth_30d": 0.60,
        },
        "sentiment": {
            "bullish": 0.72,
            "neutral": 0.20,
            "bearish": 0.08,
        },
        "fundamentals": {
            "dex_volume": 2.5e9,
            "active_addresses": 8e6,
            "transactions": 50e6,
        },
        "price_data": {
            "momentum": 0.65,
            "rsi": 48,
        },
        "macro": {
            "risk_on": 0.80,
            "crypto_season": "altseason",
        },
    }


def test_narm_init(narm):
    assert narm is not None
    assert hasattr(narm, "WEIGHTS")
    assert hasattr(narm, "NARRATIVES")
    weights_sum = sum(narm.WEIGHTS.values())
    assert abs(weights_sum - 1.0) < 0.001  # Should sum to 1.0


def test_score_narrative_returns_dict(narm, sample_coin_data):
    result = narm.score_narrative(sample_coin_data)

    assert isinstance(result, dict)
    assert "coin_id" in result
    assert "total_score" in result
    assert "components" in result
    assert "primary_narrative" in result
    assert "rotation_opportunity" in result
    assert "confidence" in result


def test_score_ranges(narm, sample_coin_data):
    result = narm.score_narrative(sample_coin_data)

    # Total score 0-100
    assert 0 <= result["total_score"] <= 100

    # All components 0-100
    for component_name, component_score in result["components"].items():
        assert 0 <= component_score <= 100, f"{component_name} out of range: {component_score}"

    # Confidence 0-1
    assert 0 <= result["confidence"] <= 1


def test_narrative_strength_scoring(narm):
    # High narrative heat (AI = 95)
    coin_data = {
        "id": "test1",
        "narratives": ["AI"],
        "adoption": {},
        "sentiment": {},
        "fundamentals": {},
        "price_data": {},
        "macro": {},
    }
    result = narm.score_narrative(coin_data)
    assert result["components"]["narrative_strength"] > 70

    # Low narrative heat (NFT = 30)
    coin_data["narratives"] = ["NFT"]
    result = narm.score_narrative(coin_data)
    assert result["components"]["narrative_strength"] < 50


def test_adoption_growth_scoring(narm):
    # High adoption growth
    coin_data = {
        "id": "test2",
        "narratives": ["AI"],
        "adoption": {
            "users": 100e6,
            "tvl": 5e9,
            "growth_7d": 0.50,  # 50% weekly
            "growth_30d": 0.80,  # 80% monthly
        },
        "sentiment": {"bullish": 0.5, "neutral": 0.3, "bearish": 0.2},
        "fundamentals": {"dex_volume": 100e6, "active_addresses": 1e6, "transactions": 1e6},
        "price_data": {"momentum": 0.5, "rsi": 50},
        "macro": {"risk_on": 0.5, "crypto_season": "neutral"},
    }
    result = narm.score_narrative(coin_data)
    adoption_score = result["components"]["adoption_growth"]
    assert adoption_score > 60


def test_rotation_opportunity_levels(narm):
    # Test HIGH rotation
    high_rotation = {
        "id": "high",
        "narratives": ["AI"],
        "adoption": {"users": 1e6, "tvl": 1e9, "growth_7d": 0.5, "growth_30d": 0.5},
        "sentiment": {"bullish": 0.9, "neutral": 0.08, "bearish": 0.02},
        "fundamentals": {"dex_volume": 1e9, "active_addresses": 2e6, "transactions": 5e6},
        "price_data": {"momentum": 0.8, "rsi": 55},
        "macro": {"risk_on": 0.9, "crypto_season": "altseason"},
    }
    result = narm.score_narrative(high_rotation)
    assert result["rotation_opportunity"] == "HIGH"

    # Test LOW rotation
    low_rotation = {
        "id": "low",
        "narratives": ["NFT"],
        "adoption": {"users": 1e5, "tvl": 100e6, "growth_7d": 0.01, "growth_30d": 0.02},
        "sentiment": {"bullish": 0.3, "neutral": 0.5, "bearish": 0.2},
        "fundamentals": {"dex_volume": 10e6, "active_addresses": 100e3, "transactions": 100e3},
        "price_data": {"momentum": -0.2, "rsi": 35},
        "macro": {"risk_on": 0.3, "crypto_season": "bear"},
    }
    result = narm.score_narrative(low_rotation)
    assert result["rotation_opportunity"] in ["LOW", "MINIMAL"]


def test_batch_scoring(narm):
    coins = [
        {
            "id": "coin1",
            "narratives": ["AI"],
            "adoption": {"users": 10e6, "tvl": 5e9, "growth_7d": 0.2, "growth_30d": 0.5},
            "sentiment": {"bullish": 0.6, "neutral": 0.3, "bearish": 0.1},
            "fundamentals": {"dex_volume": 500e6, "active_addresses": 2e6, "transactions": 10e6},
            "price_data": {"momentum": 0.5, "rsi": 50},
            "macro": {"risk_on": 0.7, "crypto_season": "altseason"},
        },
        {
            "id": "coin2",
            "narratives": ["RWA", "DeFi"],
            "adoption": {"users": 5e6, "tvl": 2e9, "growth_7d": 0.1, "growth_30d": 0.3},
            "sentiment": {"bullish": 0.5, "neutral": 0.4, "bearish": 0.1},
            "fundamentals": {"dex_volume": 200e6, "active_addresses": 1e6, "transactions": 5e6},
            "price_data": {"momentum": 0.3, "rsi": 45},
            "macro": {"risk_on": 0.6, "crypto_season": "bull"},
        },
    ]

    result_df = narm.score_batch(coins)

    assert len(result_df) == 2
    assert "coin_id" in result_df.columns
    assert "total_score" in result_df.columns
    assert "narrative" in result_df.columns
    assert "rotation" in result_df.columns
    assert "confidence" in result_df.columns

    # Should be sorted by score descending
    assert result_df["total_score"].iloc[0] >= result_df["total_score"].iloc[1]


def test_detect_narrative_rotation(narm):
    # Previous data
    previous_coins = [
        {
            "id": "test_coin",
            "narratives": ["NFT"],
            "adoption": {"users": 1e6, "tvl": 100e6, "growth_7d": 0.05, "growth_30d": 0.1},
            "sentiment": {"bullish": 0.3, "neutral": 0.5, "bearish": 0.2},
            "fundamentals": {"dex_volume": 10e6, "active_addresses": 100e3, "transactions": 500e3},
            "price_data": {"momentum": 0.1, "rsi": 40},
            "macro": {"risk_on": 0.4, "crypto_season": "neutral"},
        }
    ]

    # Current data - much stronger
    current_coins = [
        {
            "id": "test_coin",
            "narratives": ["AI", "Infrastructure"],
            "adoption": {"users": 50e6, "tvl": 5e9, "growth_7d": 0.35, "growth_30d": 0.70},
            "sentiment": {"bullish": 0.75, "neutral": 0.20, "bearish": 0.05},
            "fundamentals": {"dex_volume": 1e9, "active_addresses": 5e6, "transactions": 30e6},
            "price_data": {"momentum": 0.7, "rsi": 55},
            "macro": {"risk_on": 0.85, "crypto_season": "altseason"},
        }
    ]

    previous_df = narm.score_batch(previous_coins)
    current_df = narm.score_batch(current_coins)

    rotation_df = narm.detect_narrative_rotation(current_df, previous_df, lookback_days=30)

    assert len(rotation_df) > 0
    assert "coin_id" in rotation_df.columns
    assert "score_change" in rotation_df.columns
    assert "direction" in rotation_df.columns
    assert rotation_df["direction"].iloc[0] == "UP"


def test_confidence_calculation(narm):
    # Consistent scores (low variance) should have high confidence
    consistent_coin = {
        "id": "consistent",
        "narratives": ["AI"],
        "adoption": {"users": 50e6, "tvl": 5e9, "growth_7d": 0.25, "growth_30d": 0.5},
        "sentiment": {"bullish": 0.65, "neutral": 0.25, "bearish": 0.1},
        "fundamentals": {"dex_volume": 1e9, "active_addresses": 3e6, "transactions": 15e6},
        "price_data": {"momentum": 0.6, "rsi": 50},
        "macro": {"risk_on": 0.7, "crypto_season": "altseason"},
    }
    result = narm.score_narrative(consistent_coin)
    high_confidence = result["confidence"]

    # Inconsistent scores (high variance) should have lower confidence
    inconsistent_coin = {
        "id": "inconsistent",
        "narratives": ["AI"],
        "adoption": {"users": 1e6, "tvl": 100e6, "growth_7d": 0.01, "growth_30d": 0.8},
        "sentiment": {"bullish": 0.9, "neutral": 0.05, "bearish": 0.05},
        "fundamentals": {"dex_volume": 10e6, "active_addresses": 500e3, "transactions": 2e6},
        "price_data": {"momentum": 0.1, "rsi": 65},
        "macro": {"risk_on": 0.2, "crypto_season": "bear"},
    }
    result = narm.score_narrative(inconsistent_coin)
    low_confidence = result["confidence"]

    # High confidence should be higher than low confidence
    assert high_confidence > low_confidence
