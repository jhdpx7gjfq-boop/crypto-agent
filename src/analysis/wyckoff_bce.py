"""
Bottom Confirmation Engine (BCE) - Layer 3 Wyckoff Analysis
Version: 1.0.0

Detects accumulation zones using Wyckoff methodology.
Score: 0-6 (>=5 = BUY signal)
"""

import logging
from typing import Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

VERSION = "1.0.0"


class WyckoffBCE:
    """Bottom Confirmation Engine - Wyckoff accumulation detection."""

    MIN_SCORE = 5  # Minimum score for signal

    def __init__(self):
        logger.info(f"WyckoffBCE initialized (v{VERSION})")

    def analyze(self, df: pd.DataFrame) -> dict:
        """
        Analyze price action for accumulation patterns.

        Args:
            df: DataFrame with OHLCV + indicators (close, volume, low, high)

        Returns:
            Dict with score (0-6) and component scores
        """
        if len(df) < 20:
            return {"score": 0, "reason": "insufficient_data"}

        df = df.sort_values("timestamp").reset_index(drop=True)

        components = {
            "wyckoff_structure": self._score_structure(df),
            "volume_analysis": self._score_volume(df),
            "selling_exhaustion": self._score_exhaustion(df),
            "smart_money": self._score_smart_money(df),
            "market_structure": self._score_structure_confirmation(df),
            "momentum": self._score_momentum(df),
        }

        total_score = sum(components.values())

        return {
            "score": total_score,
            "components": components,
            "signal": "BUY" if total_score >= self.MIN_SCORE else "HOLD",
            "timestamp": df.iloc[-1]["timestamp"],
        }

    def _score_structure(self, df: pd.DataFrame) -> float:
        """
        Wyckoff structure: Spring + stopping volume.
        Score: 0-1
        """
        recent = df.tail(20)
        lows = recent["low"].min()
        highs = recent["high"].max()
        close = recent["close"].iloc[-1]

        # Spring: price breaks low then recovers
        spring_detected = (
            (recent["low"].min() < lows * 0.98) and
            (close > lows * 1.02)
        )

        return 1.0 if spring_detected else 0.5

    def _score_volume(self, df: pd.DataFrame) -> float:
        """
        Volume analysis: declining vol on down days = accumulation.
        Score: 0-1
        """
        recent = df.tail(30)

        # Down days (close < open)
        down_days = recent["close"] < recent["open"]
        down_volume = recent.loc[down_days, "volume"].mean()

        # Up days
        up_days = recent["close"] > recent["open"]
        up_volume = recent.loc[up_days, "volume"].mean()

        # Volume contraction = accumulation
        volume_ratio = down_volume / up_volume if up_volume > 0 else 0

        return min(1.0, volume_ratio)  # Lower ratio = better (lower vol on down)

    def _score_exhaustion(self, df: pd.DataFrame) -> float:
        """
        Selling exhaustion: high volume dump followed by lower volume.
        Score: 0-1
        """
        recent = df.tail(20)

        # Find highest volume day
        max_vol_idx = recent["volume"].idxmax()
        max_vol_day = recent.loc[max_vol_idx]

        if max_vol_idx >= len(recent) - 3:
            # Recent high volume
            # Check if followed by lower volume
            following_volume = recent.iloc[max_vol_idx + 1:]["volume"].mean()
            max_volume = max_vol_day["volume"]

            exhaustion = following_volume < max_volume * 0.8
            return 1.0 if exhaustion else 0.5

        return 0.3

    def _score_smart_money(self, df: pd.DataFrame) -> float:
        """
        Smart money: accumulation on dips without follow-through selling.
        Score: 0-1
        """
        recent = df.tail(30)

        # Identify dips (low volume reversal)
        recent["daily_return"] = recent["close"].pct_change()

        # Negative days
        negative_days = recent["daily_return"] < -0.01
        negative_volume = recent.loc[negative_days, "volume"].mean()

        # Positive days
        positive_days = recent["daily_return"] > 0.01
        positive_volume = recent.loc[positive_days, "volume"].mean()

        # Smart money = buying dips with lower volume
        smart_accumulation = negative_volume < positive_volume * 1.2

        return 1.0 if smart_accumulation else 0.5

    def _score_structure_confirmation(self, df: pd.DataFrame) -> float:
        """
        Market structure: higher lows, consolidation range.
        Score: 0-1
        """
        recent = df.tail(60)

        # Divide into 3 periods
        period_len = len(recent) // 3
        p1_low = recent.iloc[:period_len]["low"].min()
        p2_low = recent.iloc[period_len:2*period_len]["low"].min()
        p3_low = recent.iloc[2*period_len:]["low"].min()

        # Higher lows = uptrend support
        higher_lows = (p2_low > p1_low) and (p3_low > p2_low)

        # Consolidation range width
        range_pct = (recent["high"].max() - recent["low"].min()) / recent["low"].min()
        tight_range = range_pct < 0.15

        score = 0.0
        if higher_lows:
            score += 0.5
        if tight_range:
            score += 0.5

        return score

    def _score_momentum(self, df: pd.DataFrame) -> float:
        """
        Momentum: RSI not deeply oversold on recent lows.
        Score: 0-1
        """
        if "rsi14" not in df.columns:
            return 0.5

        recent = df.tail(20)
        rsi = recent["rsi14"].iloc[-1]

        # RSI between 30-50 = accumulation (not oversold, not overbought)
        if 30 < rsi < 50:
            return 1.0
        elif rsi < 30:
            return 0.8  # Oversold = potential
        else:
            return 0.2

    def backtest_signals(self, df: pd.DataFrame, min_score: int = 5) -> pd.DataFrame:
        """Generate backtest signals for historical data."""
        signals = []

        for i in range(50, len(df)):
            window = df.iloc[:i+1]
            result = self.analyze(window)

            signals.append({
                "timestamp": df.iloc[i]["timestamp"],
                "price": df.iloc[i]["close"],
                "score": result["score"],
                "signal": result["signal"],
                "wyckoff": result["components"]["wyckoff_structure"],
                "volume": result["components"]["volume_analysis"],
                "exhaustion": result["components"]["selling_exhaustion"],
            })

        return pd.DataFrame(signals)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from src.data.coingecko_collector import CoinGeckoCollector
    from src.data.feature_store import FeatureStore

    # Setup
    collector = CoinGeckoCollector()
    store = FeatureStore()
    bce = WyckoffBCE()

    # Get data
    print("=== Fetching BTC data ===")
    btc_df = collector.get_market_chart("bitcoin", days=90)
    btc_df["coin_id"] = "bitcoin"

    store.ingest_ohlcv("bitcoin", btc_df)
    btc_with_ind = store.calculate_indicators("bitcoin")

    # Analyze
    print("=== Running BCE ===")
    result = bce.analyze(btc_with_ind)
    print(f"\nSignal: {result['signal']} (Score: {result['score']}/6)")
    print("\nComponent scores:")
    for component, score in result["components"].items():
        print(f"  {component}: {score:.2f}")

    # Backtest
    print("\n=== Backtest (last 5 signals) ===")
    backtest_df = bce.backtest_signals(btc_with_ind)
    print(backtest_df.tail()[["timestamp", "price", "score", "signal"]])

    store.close()
    print("\n✓ BCE test complete")
