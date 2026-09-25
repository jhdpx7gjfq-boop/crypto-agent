import pytest
import pandas as pd
from src.analysis.x20_engine import X20Engine


@pytest.fixture
def engine():
    return X20Engine()


def test_engine_init(engine):
    assert engine.THRESHOLDS["score_buy"] == 65
    assert engine.THRESHOLDS["score_hold"] == 45


def test_score_opportunity_btc(engine):
    result = engine.score_opportunity(
        "bitcoin",
        {
            "price": 84000,
            "market_cap": 1.7e12,
            "volume": 30e9,
            "momentum": 0.3,
            "volatility": 0.08,
        },
        {
            "team_strength": 0.9,
            "tokenomics": 0.8,
            "adoption": 0.95,
        },
        {
            "sector_strength": 0.8,
            "narrative_growth": 0.5,
            "attention_growth": 0.3,
        },
    )

    assert result["coin_id"] == "bitcoin"
    assert 0 <= result["total_score"] <= 100
    assert "components" in result
    assert "signal" in result
    assert "risk_level" in result


def test_score_structure(engine):
    # Large cap = SKIP signal
    result = engine.score_opportunity(
        "megacap",
        {
            "price": 1,
            "market_cap": 2e12,  # Too large
            "volume": 10e9,
            "momentum": 0.5,
            "volatility": 0.05,
        },
        {"team_strength": 0.9, "tokenomics": 0.9, "adoption": 0.9},
        {"sector_strength": 0.9, "narrative_growth": 0.9, "attention_growth": 0.9},
    )

    # Large cap scores poorly on liquidity
    assert result["components"]["liquidity_score"] == 0
    # Strong fundamentals still give decent score despite poor liquidity
    assert result["total_score"] < 70  # Below STRONG_BUY threshold


def test_score_high_volatility_opportunity(engine):
    # Small cap, high volatility, strong fundamentals
    result = engine.score_opportunity(
        "altcoin",
        {
            "price": 0.50,
            "market_cap": 150e6,  # Sweet spot
            "volume": 20e6,
            "momentum": 0.7,
            "volatility": 0.25,  # High
        },
        {
            "team_strength": 0.7,
            "tokenomics": 0.6,
            "adoption": 0.5,
        },
        {
            "sector_strength": 0.8,
            "narrative_growth": 0.7,
            "attention_growth": 0.6,
        },
    )

    assert result["total_score"] >= 50  # Should score reasonably well
    assert result["risk_level"] in ["MODERATE", "MEDIUM", "HIGH", "VERY_HIGH"]


def test_score_ranges(engine):
    result = engine.score_opportunity(
        "test",
        {
            "price": 1,
            "market_cap": 100e6,
            "volume": 10e6,
            "momentum": 0,
            "volatility": 0.1,
        },
        {
            "team_strength": 0.5,
            "tokenomics": 0.5,
            "adoption": 0.5,
        },
        {
            "sector_strength": 0.5,
            "narrative_growth": 0.5,
            "attention_growth": 0.5,
        },
    )

    components = result["components"]
    assert all(0 <= v <= 20 for v in [components["momentum_score"]])
    assert all(0 <= v <= 15 for v in [components["volatility_score"], components["liquidity_score"]])
    assert all(0 <= v <= 25 for v in [components["fundamental_score"], components["narrative_score"]])


def test_signal_mapping(engine):
    # Test BUY signal
    result_buy = engine.score_opportunity(
        "strong",
        {
            "price": 0.1,
            "market_cap": 200e6,
            "volume": 25e6,
            "momentum": 0.8,
            "volatility": 0.2,
        },
        {
            "team_strength": 0.9,
            "tokenomics": 0.8,
            "adoption": 0.7,
        },
        {
            "sector_strength": 0.9,
            "narrative_growth": 0.9,
            "attention_growth": 0.9,
        },
    )

    assert result_buy["signal"] in ["STRONG_BUY", "BUY", "HOLD", "SKIP"]
    assert result_buy["total_score"] >= 65  # Should be strong buy


def test_batch_scoring(engine):
    coins = [
        {
            "id": "coin1",
            "price_data": {
                "price": 1,
                "market_cap": 100e6,
                "volume": 10e6,
                "momentum": 0.5,
                "volatility": 0.15,
            },
            "fundamentals": {"team_strength": 0.6, "tokenomics": 0.5, "adoption": 0.4},
            "narrative": {"sector_strength": 0.6, "narrative_growth": 0.5, "attention_growth": 0.4},
        },
        {
            "id": "coin2",
            "price_data": {
                "price": 1,
                "market_cap": 150e6,
                "volume": 20e6,
                "momentum": 0.7,
                "volatility": 0.2,
            },
            "fundamentals": {"team_strength": 0.8, "tokenomics": 0.7, "adoption": 0.6},
            "narrative": {"sector_strength": 0.8, "narrative_growth": 0.7, "attention_growth": 0.6},
        },
    ]

    result_df = engine.score_batch(coins)

    assert len(result_df) == 2
    assert "total_score" in result_df.columns
    assert "signal" in result_df.columns
    assert "risk" in result_df.columns

    # Should be sorted by score descending
    assert result_df["total_score"].iloc[0] >= result_df["total_score"].iloc[1]
