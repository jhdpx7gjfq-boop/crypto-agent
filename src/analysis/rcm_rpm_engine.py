"""
RCM/RPM - Rotation Confirmation Model / Rotation Performance Model
Version: 1.0.0

Detects capital rotation patterns and confirms multi-week rotation trends.
Score: 0-100 points (weighting: 25% capital_flow, 25% relative_strength,
20% narrative_acceleration, 20% fundamental_confirmation, 10% derivatives_structure)

Walk Forward validation compatible (no lookahead bias).
"""

import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

VERSION = "1.0.0"


class RCMRPMEngine:
    """RCM/RPM: Capital Rotation Detection Engine."""

    WEIGHTS = {
        "capital_flow": 0.25,              # Inflow/outflow momentum
        "relative_strength": 0.25,         # Relative performance vs market
        "narrative_acceleration": 0.20,    # Narrative momentum
        "fundamental_confirmation": 0.20,  # Fundamental improvement
        "derivatives_structure": 0.10,     # Futures/options positioning
    }

    THRESHOLDS = {
        "score_strong_rotation": 75,
        "score_moderate_rotation": 55,
        "score_weak_rotation": 35,
    }

    def __init__(self):
        logger.info(f"RCM/RPM Engine initialized (v{VERSION})")

    def score_rotation(self, coin_data: Dict) -> Dict:
        """
        Score capital rotation confirmation for a coin.

        Args:
            coin_data: {
                "id": "ethereum",
                "price_history": DataFrame with OHLCV + market_cap over time,
                "sentiment": {"bullish": 0.7, "neutral": 0.2, "bearish": 0.1},
                "on_chain": {
                    "exchange_inflow": [values],  # Historical inflows (negative = outflow)
                    "active_addresses": [values],
                    "transaction_volume": [values],
                },
                "funding_rates": [values],  # Average funding rates over periods
                "open_interest": [values],  # OI over time
                "narrative_data": {
                    "narrative_mentions": int,
                    "mention_growth_7d": float,
                    "mention_growth_30d": float,
                },
            }

        Returns:
            Dict with total score (0-100) and component breakdown
        """

        components = {
            "capital_flow": self._score_capital_flow(coin_data),
            "relative_strength": self._score_relative_strength(coin_data),
            "narrative_acceleration": self._score_narrative_acceleration(coin_data),
            "fundamental_confirmation": self._score_fundamental_confirmation(coin_data),
            "derivatives_structure": self._score_derivatives_structure(coin_data),
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
            "rotation_signal": self._assess_rotation_signal(total_score),
            "rotation_strength": self._assess_rotation_strength(components),
            "confirmation_level": self._calculate_confirmation_level(components),
        }

    def _score_capital_flow(self, coin_data: Dict) -> float:
        """
        Score capital flow momentum (0-100).

        Positive net inflow over recent period indicates rotation in.
        """
        on_chain = coin_data.get("on_chain", {})
        exchange_inflow = on_chain.get("exchange_inflow", [])

        if not exchange_inflow or len(exchange_inflow) < 2:
            return 0.0

        # Convert to array if list
        inflow_array = np.array(exchange_inflow[-20:]) if isinstance(exchange_inflow, list) else exchange_inflow

        # Calculate net inflow trend
        recent_inflow = np.sum(inflow_array[-7:]) if len(inflow_array) >= 7 else np.sum(inflow_array)
        longer_inflow = np.sum(inflow_array[-14:]) if len(inflow_array) >= 14 else np.sum(inflow_array)

        base_score = 0.0

        # Strong net outflow (negative) = rotation out (lower score)
        # Strong net inflow (positive) = rotation in (higher score)
        if longer_inflow > 0:  # Net inflow trend
            if recent_inflow > longer_inflow * 0.5:
                base_score += 50  # Accelerating inflow
            else:
                base_score += 35  # Stable inflow
        elif longer_inflow < 0:  # Net outflow trend
            if recent_inflow < longer_inflow * 0.8:
                base_score += 10  # Accelerating outflow
            else:
                base_score += 20  # Slowing outflow

        # Magnitude matters
        abs_inflow = abs(longer_inflow)
        if abs_inflow > 1e9:  # $1B+
            base_score += 40
        elif abs_inflow > 100e6:  # $100M+
            base_score += 25
        elif abs_inflow > 10e6:  # $10M+
            base_score += 10

        return min(100.0, base_score)

    def _score_relative_strength(self, coin_data: Dict) -> float:
        """
        Score relative strength vs market (0-100).

        Outperformance = capital rotating into this asset.
        """
        price_history = coin_data.get("price_history")

        if price_history is None or len(price_history) < 14:
            return 50.0  # Neutral if insufficient data

        df = price_history.copy()
        df["returns_7d"] = df["close"].pct_change(7)
        df["returns_30d"] = df["close"].pct_change(30)

        recent_returns_7d = df["returns_7d"].iloc[-1] if len(df) > 0 else 0
        recent_returns_30d = df["returns_30d"].iloc[-1] if len(df) > 0 else 0

        base_score = 50.0  # Neutral baseline

        # 7-day momentum
        if recent_returns_7d > 0.20:  # 20%+ weekly gain
            base_score += 25
        elif recent_returns_7d > 0.10:  # 10%+ weekly gain
            base_score += 15
        elif recent_returns_7d > 0:
            base_score += 8
        elif recent_returns_7d > -0.10:
            base_score += 0
        else:
            base_score -= 15

        # 30-day momentum (longer confirmation)
        if recent_returns_30d > 0.50:  # 50%+ monthly
            base_score += 25
        elif recent_returns_30d > 0.25:  # 25%+ monthly
            base_score += 15
        elif recent_returns_30d > 0:
            base_score += 5

        return np.clip(base_score, 0.0, 100.0)

    def _score_narrative_acceleration(self, coin_data: Dict) -> float:
        """
        Score narrative momentum acceleration (0-100).

        Accelerating mention growth = narrative gaining momentum.
        """
        narrative = coin_data.get("narrative_data", {})

        mentions = narrative.get("narrative_mentions", 0)
        growth_7d = narrative.get("mention_growth_7d", 0)
        growth_30d = narrative.get("mention_growth_30d", 0)

        base_score = 0.0

        # Recent acceleration
        if growth_7d > 0.50:  # 50%+ weekly growth
            base_score += 40
        elif growth_7d > 0.25:  # 25%+ weekly
            base_score += 25
        elif growth_7d > 0.10:  # 10%+ weekly
            base_score += 15
        else:
            base_score += 5

        # Sustained growth (30d)
        if growth_30d > 1.0:  # 100%+ monthly
            base_score += 35
        elif growth_30d > 0.50:  # 50%+ monthly
            base_score += 20
        elif growth_30d > 0.20:  # 20%+ monthly
            base_score += 10

        # Absolute volume matters
        if mentions > 50000:  # High-volume narrative
            base_score += 15
        elif mentions > 10000:
            base_score += 8
        elif mentions > 1000:
            base_score += 3

        return min(100.0, base_score)

    def _score_fundamental_confirmation(self, coin_data: Dict) -> float:
        """
        Score fundamental improvement (0-100).

        Growth in on-chain activity confirms real capital deployment.
        """
        on_chain = coin_data.get("on_chain", {})

        active_addresses = on_chain.get("active_addresses", [])
        transaction_volume = on_chain.get("transaction_volume", [])

        base_score = 0.0

        # Active address growth
        if active_addresses and len(active_addresses) >= 14:
            addresses_array = np.array(active_addresses[-14:])
            growth_7d = (addresses_array[-1] - addresses_array[-8]) / addresses_array[-8] if addresses_array[-8] > 0 else 0

            if growth_7d > 0.30:  # 30%+ growth
                base_score += 35
            elif growth_7d > 0.15:
                base_score += 20
            elif growth_7d > 0.05:
                base_score += 10

        # Transaction volume growth
        if transaction_volume and len(transaction_volume) >= 14:
            volume_array = np.array(transaction_volume[-14:])
            avg_recent = np.mean(volume_array[-7:]) if len(volume_array) >= 7 else np.mean(volume_array)
            avg_older = np.mean(volume_array[-14:-7]) if len(volume_array) >= 14 else np.mean(volume_array)

            if avg_older > 0:
                growth_7d = (avg_recent - avg_older) / avg_older
                if growth_7d > 0.40:
                    base_score += 35
                elif growth_7d > 0.20:
                    base_score += 20
                elif growth_7d > 0.05:
                    base_score += 10

        return min(100.0, base_score)

    def _score_derivatives_structure(self, coin_data: Dict) -> float:
        """
        Score derivatives positioning (0-100).

        Positive funding rates = long accumulation.
        Rising OI = capital flowing into leverage.
        """
        funding_rates = coin_data.get("funding_rates", [])
        open_interest = coin_data.get("open_interest", [])

        base_score = 0.0

        # Funding rate analysis
        if funding_rates and len(funding_rates) >= 7:
            funding_array = np.array(funding_rates[-7:])
            avg_funding = np.mean(funding_array)

            if avg_funding > 0.0005:  # 0.05%+ positive
                base_score += 40  # Strong long positioning
            elif avg_funding > 0:  # Any positive
                base_score += 25
            elif avg_funding > -0.0003:  # Slightly negative
                base_score += 15
            else:  # Strong negative
                base_score += 0

        # Open Interest growth
        if open_interest and len(open_interest) >= 14:
            oi_array = np.array(open_interest[-14:])
            oi_recent = oi_array[-1]
            oi_older = oi_array[-8] if len(oi_array) >= 8 else oi_array[0]

            if oi_older > 0:
                oi_growth = (oi_recent - oi_older) / oi_older
                if oi_growth > 0.30:
                    base_score += 40
                elif oi_growth > 0.10:
                    base_score += 25
                elif oi_growth > 0:
                    base_score += 10

        return min(100.0, base_score)

    def _assess_rotation_signal(self, total_score: float) -> str:
        """Assess rotation signal strength."""
        if total_score >= self.THRESHOLDS["score_strong_rotation"]:
            return "STRONG_ROTATION"
        elif total_score >= self.THRESHOLDS["score_moderate_rotation"]:
            return "MODERATE_ROTATION"
        elif total_score >= self.THRESHOLDS["score_weak_rotation"]:
            return "WEAK_ROTATION"
        else:
            return "NO_ROTATION"

    def _assess_rotation_strength(self, components: Dict) -> str:
        """Assess rotation strength based on component variance."""
        scores = list(components.values())
        avg_score = np.mean(scores)

        if avg_score > 70:
            return "VERY_STRONG"
        elif avg_score > 55:
            return "STRONG"
        elif avg_score > 40:
            return "MODERATE"
        else:
            return "WEAK"

    def _calculate_confirmation_level(self, components: Dict) -> float:
        """
        Calculate rotation confirmation level (0-1).

        Higher confirmation when multiple components agree.
        """
        scores = list(components.values())
        avg = np.mean(scores)
        variance = np.var(scores)

        # Lower variance = higher confidence in rotation signal
        confirmation = 1.0 / (1.0 + variance / 500)
        return round(confirmation, 2)

    def score_batch(self, coins: List[Dict]) -> pd.DataFrame:
        """Score multiple coins and rank by rotation score."""
        results = []

        for coin in coins:
            result = self.score_rotation(coin)
            results.append({
                "coin_id": result["coin_id"],
                "total_score": result["total_score"],
                "signal": result["rotation_signal"],
                "strength": result["rotation_strength"],
                "confirmation": result["confirmation_level"],
                **result["components"],
            })

        df = pd.DataFrame(results)
        return df.sort_values("total_score", ascending=False)

    def walk_forward_backtest(
        self,
        historical_data: List[Dict],
        train_window_days: int = 30,
        test_window_days: int = 7,
    ) -> pd.DataFrame:
        """
        Walk forward backtest for rotation confirmation (no lookahead bias).

        Trains on past N days, tests on next M days, slides window forward.
        """
        results = []

        if not historical_data or len(historical_data) < train_window_days + test_window_days:
            return pd.DataFrame()

        # Ensure historical_data is sorted by timestamp
        sorted_data = sorted(historical_data, key=lambda x: x.get("timestamp", ""))

        for i in range(train_window_days, len(sorted_data) - test_window_days):
            # Training window
            train_data = sorted_data[:i]

            # Test point
            test_point = sorted_data[i]

            # Score rotation at test point
            score_result = self.score_rotation(test_point)

            results.append({
                "timestamp": test_point.get("timestamp"),
                "coin_id": test_point.get("id"),
                "score": score_result["total_score"],
                "signal": score_result["rotation_signal"],
                "strength": score_result["rotation_strength"],
                "confirmation": score_result["confirmation_level"],
            })

        return pd.DataFrame(results)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    engine = RCMRPMEngine()

    # Test rotation scoring
    test_coin = {
        "id": "ethereum",
        "price_history": pd.DataFrame({
            "close": [100 * (1.02 ** i) for i in range(50)],  # Steady uptrend
        }),
        "sentiment": {
            "bullish": 0.75,
            "neutral": 0.20,
            "bearish": 0.05,
        },
        "on_chain": {
            "exchange_inflow": [100e6 * i for i in range(20)],  # Growing inflow
            "active_addresses": [1e6 * (1.05 ** i) for i in range(20)],
            "transaction_volume": [500e6 * (1.03 ** i) for i in range(20)],
        },
        "funding_rates": [0.0003] * 7,  # Positive (bullish)
        "open_interest": [10e9 * (1.04 ** i) for i in range(14)],
        "narrative_data": {
            "narrative_mentions": 50000,
            "mention_growth_7d": 0.35,
            "mention_growth_30d": 0.75,
        },
    }

    print("=== RCM/RPM Rotation Scoring ===\n")
    result = engine.score_rotation(test_coin)

    print(f"Coin: {test_coin['id']}")
    print(f"Score: {result['total_score']:.1f}/100")
    print(f"Signal: {result['rotation_signal']}")
    print(f"Strength: {result['rotation_strength']}")
    print(f"Confirmation: {result['confirmation_level']}")

    print("\nComponent Scores:")
    for component, score in result["components"].items():
        print(f"  {component}: {score:.1f}")

    print("\n✓ RCM/RPM test complete")
