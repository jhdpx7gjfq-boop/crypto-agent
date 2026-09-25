"""
NARM-P+ - Narrative Adoption Rotation Model
Version: 1.0.0

Detects narrative shifts and sector rotations for opportunity discovery.
Score: 0-100 points (weighting: 20% narrative, 20% adoption, 20% rotation, 20% fundamentals, 20% timing)
"""

import logging
from typing import Dict, List
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

VERSION = "1.0.0"


class NARMPPlus:
    """NARM-P+ Narrative Adoption Rotation Model."""

    WEIGHTS = {
        "narrative_strength": 0.20,      # Sector/theme strength
        "adoption_growth": 0.20,          # User/TVL adoption rate
        "capital_rotation": 0.20,         # Inflow vs outflow momentum
        "fundamental_score": 0.20,        # Chain metrics + usage
        "market_timing": 0.20,            # Macro + cycle timing
    }

    NARRATIVES = {
        "AI": ["artificial intelligence", "llm", "agents", "inference"],
        "RWA": ["real world assets", "tokenized", "securities", "staking"],
        "DeFi": ["lending", "yield", "swap", "protocol"],
        "L2": ["layer 2", "scaling", "rollup", "optimistic"],
        "NFT": ["nft", "gaming", "collectible", "metaverse"],
        "Infrastructure": ["network", "validator", "node", "blockchain"],
        "Privacy": ["privacy", "encrypted", "zkp", "anon"],
        "Memes": ["meme", "community", "social"],
    }

    def __init__(self):
        logger.info(f"NARM-P+ initialized (v{VERSION})")

    def score_narrative(self, coin_data: Dict) -> Dict:
        """
        Score a coin's narrative positioning and rotation opportunity.

        Args:
            coin_data: {
                "id": "bitcoin",
                "name": "Bitcoin",
                "narratives": ["AI", "Infrastructure"],
                "adoption": {"users": 100M, "tvl": 50B, "growth_7d": 0.15},
                "sentiment": {"bullish": 0.65, "neutral": 0.25, "bearish": 0.10},
                "fundamentals": {"dex_volume": 1B, "active_addresses": 5M},
                "price_data": {"momentum": 0.5, "rsi": 45},
                "macro": {"risk_on": 0.7, "crypto_season": "bull"},
            }

        Returns:
            Dict with total score (0-100) and component breakdown
        """

        components = {
            "narrative_strength": self._score_narrative_strength(coin_data),
            "adoption_growth": self._score_adoption(coin_data),
            "capital_rotation": self._score_rotation(coin_data),
            "fundamental_score": self._score_fundamentals(coin_data),
            "market_timing": self._score_timing(coin_data),
        }

        # Weighted score
        total_score = sum(
            components[key] * self.WEIGHTS[key]
            for key in components.keys()
        )

        return {
            "coin_id": coin_data.get("id"),
            "total_score": total_score,
            "components": components,
            "primary_narrative": self._detect_primary_narrative(coin_data),
            "rotation_opportunity": self._assess_rotation_opportunity(components),
            "confidence": self._calculate_confidence(components),
        }

    def _score_narrative_strength(self, coin_data: Dict) -> float:
        """
        Score narrative strength (0-100).

        Hot narratives score higher.
        """
        narratives = coin_data.get("narratives", [])

        if not narratives:
            return 20.0  # Base score

        narrative_heat = {
            "AI": 95,
            "RWA": 85,
            "L2": 70,
            "DeFi": 60,
            "Infrastructure": 55,
            "Privacy": 50,
            "NFT": 30,
            "Memes": 40,
        }

        # Average narrative strength
        scores = [narrative_heat.get(n, 50) for n in narratives]
        avg_narrative = np.mean(scores)

        # Boost for multiple narratives
        narrative_count_bonus = min(20, len(narratives) * 10)

        return min(100.0, avg_narrative + narrative_count_bonus)

    def _score_adoption(self, coin_data: Dict) -> float:
        """
        Score adoption growth (0-100).

        Fast-growing adoption = high score.
        """
        adoption = coin_data.get("adoption", {})

        users = adoption.get("users", 0)
        tvl = adoption.get("tvl", 0)
        growth_7d = adoption.get("growth_7d", 0)
        growth_30d = adoption.get("growth_30d", 0)

        base_score = 0.0

        # User growth
        if growth_7d > 0.30:  # 30% weekly growth
            base_score += 35
        elif growth_7d > 0.15:
            base_score += 25
        elif growth_7d > 0.05:
            base_score += 15
        else:
            base_score += 5

        # TVL growth
        if growth_30d > 0.50:  # 50% monthly growth
            base_score += 35
        elif growth_30d > 0.25:
            base_score += 20
        elif growth_30d > 0.10:
            base_score += 10
        else:
            base_score += 2

        # Absolute size matters
        if tvl > 1e9:  # $1B+
            base_score += 30
        elif tvl > 100e6:  # $100M+
            base_score += 20
        elif tvl > 10e6:  # $10M+
            base_score += 10

        return min(100.0, base_score)

    def _score_rotation(self, coin_data: Dict) -> float:
        """
        Score capital rotation potential (0-100).

        Inflow momentum vs outflow = rotation opportunity.
        """
        sentiment = coin_data.get("sentiment", {})
        price_data = coin_data.get("price_data", {})

        bullish = sentiment.get("bullish", 0)
        momentum = price_data.get("momentum", 0)  # -1 to 1

        base_score = 0.0

        # Bullish sentiment
        if bullish > 0.70:
            base_score += 40
        elif bullish > 0.55:
            base_score += 25
        elif bullish > 0.40:
            base_score += 15
        else:
            base_score += 5

        # Momentum confirmation
        if momentum > 0.5:
            base_score += 35
        elif momentum > 0:
            base_score += 20
        elif momentum > -0.3:
            base_score += 10
        else:
            base_score += 0

        # Combined rotation potential
        rotation_potential = bullish * (1 + momentum)
        base_score += rotation_potential * 25

        return min(100.0, base_score)

    def _score_fundamentals(self, coin_data: Dict) -> float:
        """
        Score on-chain fundamentals (0-100).
        """
        fundamentals = coin_data.get("fundamentals", {})
        adoption = coin_data.get("adoption", {})

        dex_volume = fundamentals.get("dex_volume", 0)
        active_addresses = fundamentals.get("active_addresses", 0)
        transactions = fundamentals.get("transactions", 0)

        base_score = 0.0

        # Volume activity
        if dex_volume > 1e9:  # $1B+ daily
            base_score += 30
        elif dex_volume > 100e6:
            base_score += 20
        elif dex_volume > 10e6:
            base_score += 10

        # Active addresses
        if active_addresses > 5e6:
            base_score += 30
        elif active_addresses > 1e6:
            base_score += 20
        elif active_addresses > 100e3:
            base_score += 10

        # Transaction throughput
        if transactions > 10e6:
            base_score += 25
        elif transactions > 1e6:
            base_score += 15
        elif transactions > 100e3:
            base_score += 8

        # Growth trajectory
        growth_30d = adoption.get("growth_30d", 0)
        if growth_30d > 0.30:
            base_score += 15

        return min(100.0, base_score)

    def _score_timing(self, coin_data: Dict) -> float:
        """
        Score market timing (0-100).

        Macro conditions + cycle timing.
        """
        macro = coin_data.get("macro", {})
        price_data = coin_data.get("price_data", {})

        risk_on = macro.get("risk_on", 0.5)
        season = macro.get("crypto_season", "neutral")
        rsi = price_data.get("rsi", 50)

        base_score = 0.0

        # Risk-on environment
        if risk_on > 0.70:
            base_score += 30
        elif risk_on > 0.50:
            base_score += 20
        elif risk_on > 0.30:
            base_score += 10

        # Crypto season
        season_scores = {
            "altseason": 40,
            "bull": 35,
            "recovery": 25,
            "neutral": 15,
            "bear": 5,
        }
        base_score += season_scores.get(season, 15)

        # RSI (momentum confirmation)
        if 40 < rsi < 60:
            base_score += 15  # Accumulation zone
        elif rsi < 40:
            base_score += 20  # Oversold
        elif rsi > 60:
            base_score += 5   # Overbought

        return min(100.0, base_score)

    def _detect_primary_narrative(self, coin_data: Dict) -> str:
        """Identify primary narrative."""
        narratives = coin_data.get("narratives", [])
        return narratives[0] if narratives else "Other"

    def _assess_rotation_opportunity(self, components: Dict) -> str:
        """Assess rotation opportunity level."""
        rotation_score = components.get("capital_rotation", 0)
        narrative_score = components.get("narrative_strength", 0)

        combined = (rotation_score + narrative_score) / 2

        if combined > 75:
            return "HIGH"
        elif combined > 55:
            return "MODERATE"
        elif combined > 35:
            return "LOW"
        else:
            return "MINIMAL"

    def _calculate_confidence(self, components: Dict) -> float:
        """Calculate scoring confidence (0-1)."""
        scores = list(components.values())
        # Higher variance = lower confidence
        variance = np.var(scores)
        confidence = 1.0 / (1.0 + variance / 100)
        return round(confidence, 2)

    def score_batch(self, coins: List[Dict]) -> pd.DataFrame:
        """Score multiple coins and rank by opportunity."""
        results = []

        for coin in coins:
            result = self.score_narrative(coin)
            results.append({
                "coin_id": result["coin_id"],
                "total_score": result["total_score"],
                "narrative": result["primary_narrative"],
                "rotation": result["rotation_opportunity"],
                "confidence": result["confidence"],
                **result["components"],
            })

        df = pd.DataFrame(results)
        return df.sort_values("total_score", ascending=False)

    def detect_narrative_rotation(
        self,
        current_data: pd.DataFrame,
        previous_data: pd.DataFrame,
        lookback_days: int = 30,
    ) -> pd.DataFrame:
        """
        Detect narrative rotations over time.

        Returns coins with significant score changes.
        """
        changes = []

        for coin_id in current_data["coin_id"].unique():
            current_row = current_data[current_data["coin_id"] == coin_id]
            previous_row = previous_data[previous_data["coin_id"] == coin_id]

            if len(current_row) == 0 or len(previous_row) == 0:
                continue

            current_score = current_row["total_score"].iloc[0]
            previous_score = previous_row["total_score"].iloc[0]
            score_change = current_score - previous_score
            change_pct = (score_change / previous_score * 100) if previous_score > 0 else 0

            if abs(score_change) > 10:  # Significant change threshold
                changes.append({
                    "coin_id": coin_id,
                    "previous_score": previous_score,
                    "current_score": current_score,
                    "score_change": score_change,
                    "change_pct": change_pct,
                    "direction": "UP" if score_change > 0 else "DOWN",
                })

        return pd.DataFrame(changes).sort_values("score_change", key=abs, ascending=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    narm = NARMPPlus()

    # Test scoring
    test_coin = {
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

    print("=== NARM-P+ Narrative Scoring ===\n")
    result = narm.score_narrative(test_coin)

    print(f"Coin: {test_coin['name']}")
    print(f"Score: {result['total_score']:.1f}/100")
    print(f"Narrative: {result['primary_narrative']}")
    print(f"Rotation Opportunity: {result['rotation_opportunity']}")
    print(f"Confidence: {result['confidence']}")

    print("\nComponent Scores:")
    for component, score in result["components"].items():
        print(f"  {component}: {score:.1f}")

    # Batch test
    test_coins = [test_coin] + [
        {
            "id": "solana",
            "name": "Solana",
            "narratives": ["AI"],
            "adoption": {
                "users": 30e6,
                "tvl": 20e9,
                "growth_7d": 0.35,
                "growth_30d": 0.80,
            },
            "sentiment": {"bullish": 0.68, "neutral": 0.25, "bearish": 0.07},
            "fundamentals": {
                "dex_volume": 1.5e9,
                "active_addresses": 6e6,
                "transactions": 100e6,
            },
            "price_data": {"momentum": 0.70, "rsi": 52},
            "macro": {"risk_on": 0.75, "crypto_season": "altseason"},
        }
    ]

    print("\n=== Batch Scoring (Top 2) ===")
    batch_results = narm.score_batch(test_coins)
    print(batch_results[["coin_id", "total_score", "narrative", "rotation"]].head())

    print("\n✓ NARM-P+ test complete")
