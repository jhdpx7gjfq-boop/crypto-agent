"""
X20 Engine - Layer 4 Asymmetric Opportunity Scoring
Version: 1.0.0

Identifies 10-20x opportunity tokens using multi-factor analysis.
Score: 0-100 points
"""

import logging
from typing import Optional, Dict

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

VERSION = "1.0.0"


class X20Engine:
    """X20 Engine - asymmetric opportunity scoring."""

    THRESHOLDS = {
        "score_buy": 65,  # Strong buy threshold
        "score_hold": 45,  # Hold/evaluate threshold
    }

    def __init__(self):
        logger.info(f"X20Engine initialized (v{VERSION})")

    def score_opportunity(
        self,
        coin_id: str,
        price_data: Dict,
        fundamentals: Dict,
        narrative: Dict,
    ) -> Dict:
        """
        Score an opportunity across 5 dimensions.

        Args:
            coin_id: Coin identifier
            price_data: {"price", "market_cap", "volume", "momentum"}
            fundamentals: {"team_strength", "tokenomics", "adoption"}
            narrative: {"sector_strength", "narrative_growth", "attention"}

        Returns:
            Dict with total score (0-100) and component breakdown
        """

        components = {
            "momentum_score": self._score_momentum(price_data),           # 20pts
            "volatility_score": self._score_volatility(price_data),      # 15pts
            "liquidity_score": self._score_liquidity(price_data),        # 15pts
            "fundamental_score": self._score_fundamentals(fundamentals), # 25pts
            "narrative_score": self._score_narrative(narrative),         # 25pts
        }

        total = sum(components.values())

        return {
            "coin_id": coin_id,
            "total_score": total,
            "components": components,
            "signal": self._get_signal(total),
            "risk_level": self._assess_risk(components),
        }

    def _score_momentum(self, price_data: Dict) -> float:
        """
        Momentum scoring: relative strength vs market.
        Max: 20 points
        """
        momentum = price_data.get("momentum", 0)  # Range: -1 to 1

        if momentum > 0.5:
            return 20.0
        elif momentum > 0:
            return 10.0
        elif momentum > -0.3:
            return 5.0
        else:
            return 0.0

    def _score_volatility(self, price_data: Dict) -> float:
        """
        Volatility scoring: high volatility = high reward potential.
        Max: 15 points
        """
        volatility = price_data.get("volatility", 0)  # Range: 0 to 1

        if 0.15 < volatility < 0.4:
            return 15.0  # Optimal range
        elif volatility > 0.1:
            return 10.0
        elif volatility > 0.05:
            return 5.0
        else:
            return 0.0

    def _score_liquidity(self, price_data: Dict) -> float:
        """
        Liquidity scoring: sufficient volume but not mega-cap.
        Max: 15 points
        """
        market_cap = price_data.get("market_cap", 0)
        volume = price_data.get("volume", 0)

        if market_cap == 0:
            return 0.0

        volume_ratio = volume / market_cap if market_cap > 0 else 0

        # Sweet spot: $50M-$500M market cap, >10% volume ratio
        if 50e6 < market_cap < 500e6 and volume_ratio > 0.1:
            return 15.0
        elif 10e6 < market_cap < 2e9 and volume_ratio > 0.05:
            return 10.0
        elif market_cap < 10e9:
            return 5.0
        else:
            return 0.0  # Too large

    def _score_fundamentals(self, fundamentals: Dict) -> float:
        """
        Fundamentals scoring: team, tokenomics, adoption.
        Max: 25 points
        """
        score = 0.0

        # Team strength (0-1 scale)
        team = fundamentals.get("team_strength", 0)
        if team > 0.7:
            score += 10.0
        elif team > 0.4:
            score += 5.0

        # Tokenomics (0-1 scale)
        tokenomics = fundamentals.get("tokenomics", 0)
        if tokenomics > 0.7:
            score += 8.0
        elif tokenomics > 0.4:
            score += 4.0

        # Adoption (0-1 scale)
        adoption = fundamentals.get("adoption", 0)
        if adoption > 0.6:
            score += 7.0
        elif adoption > 0.3:
            score += 3.0

        return min(25.0, score)

    def _score_narrative(self, narrative: Dict) -> float:
        """
        Narrative scoring: sector rotation, attention growth.
        Max: 25 points
        """
        score = 0.0

        # Sector strength (0-1 scale)
        sector = narrative.get("sector_strength", 0)
        if sector > 0.7:
            score += 10.0
        elif sector > 0.4:
            score += 5.0

        # Narrative growth (momentum)
        narrative_growth = narrative.get("narrative_growth", 0)
        if narrative_growth > 0.5:
            score += 10.0
        elif narrative_growth > 0:
            score += 5.0

        # Attention (social/news)
        attention = narrative.get("attention_growth", 0)
        if attention > 0.6:
            score += 5.0
        elif attention > 0.2:
            score += 2.5

        return min(25.0, score)

    def _get_signal(self, total_score: float) -> str:
        """Convert score to action signal."""
        if total_score >= self.THRESHOLDS["score_buy"]:
            return "STRONG_BUY"
        elif total_score >= self.THRESHOLDS["score_hold"]:
            return "BUY"
        elif total_score >= 30:
            return "HOLD"
        else:
            return "SKIP"

    def _assess_risk(self, components: Dict) -> str:
        """Assess risk level based on component distribution."""
        momentum = components.get("momentum_score", 0)
        volatility = components.get("volatility_score", 0)
        liquidity = components.get("liquidity_score", 0)

        if liquidity < 5 or volatility > 12:
            return "VERY_HIGH"
        elif liquidity < 10 and momentum < 10:
            return "HIGH"
        elif volatility > 10:
            return "MEDIUM"
        else:
            return "MODERATE"

    def score_batch(self, coins: list) -> pd.DataFrame:
        """Score multiple coins and return ranked DataFrame."""
        results = []

        for coin in coins:
            result = self.score_opportunity(
                coin["id"],
                coin["price_data"],
                coin.get("fundamentals", {}),
                coin.get("narrative", {}),
            )
            results.append({
                "coin_id": result["coin_id"],
                "total_score": result["total_score"],
                "signal": result["signal"],
                "risk": result["risk_level"],
                **result["components"],
            })

        df = pd.DataFrame(results)
        return df.sort_values("total_score", ascending=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    engine = X20Engine()

    # Test coins
    test_coins = [
        {
            "id": "bitcoin",
            "price_data": {
                "price": 84000,
                "market_cap": 1.7e12,
                "volume": 30e9,
                "momentum": 0.3,
                "volatility": 0.08,
            },
            "fundamentals": {
                "team_strength": 0.9,
                "tokenomics": 0.8,
                "adoption": 0.95,
            },
            "narrative": {
                "sector_strength": 0.8,
                "narrative_growth": 0.5,
                "attention_growth": 0.3,
            },
        },
        {
            "id": "altcoin_example",
            "price_data": {
                "price": 0.50,
                "market_cap": 150e6,
                "volume": 20e6,
                "momentum": 0.7,
                "volatility": 0.25,
            },
            "fundamentals": {
                "team_strength": 0.6,
                "tokenomics": 0.5,
                "adoption": 0.4,
            },
            "narrative": {
                "sector_strength": 0.75,
                "narrative_growth": 0.8,
                "attention_growth": 0.7,
            },
        },
    ]

    print("=== X20 Opportunity Scoring ===\n")
    results_df = engine.score_batch(test_coins)
    print(results_df)

    print("\n=== Detailed Analysis ===")
    for _, row in results_df.iterrows():
        print(f"\n{row['coin_id'].upper()}")
        print(f"  Signal: {row['signal']} (Score: {row['total_score']:.0f}/100)")
        print(f"  Risk Level: {row['risk']}")
        print(f"  Momentum: {row['momentum_score']:.0f} | Volatility: {row['volatility_score']:.0f} | Liquidity: {row['liquidity_score']:.0f}")
        print(f"  Fundamentals: {row['fundamental_score']:.0f} | Narrative: {row['narrative_score']:.0f}")

    print("\n✓ X20 Engine test complete")
