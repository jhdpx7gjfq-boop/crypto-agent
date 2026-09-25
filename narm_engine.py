import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

import requests

logger = logging.getLogger(__name__)


class NARMEngine:
    """NARM-P+ scorer: Narrative Adoption Rotation Model Plus.

    Identifies tokens with strong narrative + adoption momentum.
    100-point model combining:
    - Narrative Strength (0-20): Trend positioning (AI, RWA, DeFi, Layer2, etc.)
    - Adoption (0-20): User/holder growth trajectory
    - Capital Rotation (0-20): Money flowing into this sector
    - Fundamentals (0-20): Team credibility, investor backing
    - Market Timing (0-20): Cycle positioning, relative strength

    Score: 0-100 (higher = better entry opportunity)
    Threshold: >=70 for high-confidence narrative trade
    """

    def __init__(self, symbol: str = "BTCUSDT", binance_api_timeout: int = 10):
        self.symbol = symbol
        self.binance_api_timeout = binance_api_timeout

    def get_ohlcv(
        self, interval: str = "1d", limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch daily OHLCV candles from Binance."""
        try:
            resp = requests.get(
                "https://api.binance.com/api/v3/klines",
                params={"symbol": self.symbol, "interval": interval, "limit": limit},
                timeout=self.binance_api_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {
                    "timestamp": int(candle[0]),
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[7]),
                    "quote_asset_volume": float(candle[8]),
                }
                for candle in data
            ]
        except (requests.RequestException, KeyError, ValueError, IndexError) as exc:
            logger.warning("Failed to fetch OHLCV for NARM analysis: %s", exc)
            return None

    def _calculate_narrative_strength(self, ohlcv: List[Dict]) -> float:
        """Narrative Strength 0-20: Trend positioning.

        Proxy: Recent volume acceleration + price momentum.
        Higher volume + uptrend = stronger narrative engagement.
        """
        if len(ohlcv) < 20:
            return 0.0

        recent = ohlcv[-20:]
        closes = [c["close"] for c in recent]
        volumes = [c["volume"] for c in recent]

        avg_recent_vol = sum(volumes[-5:]) / 5
        avg_prior_vol = sum(volumes[:-5]) / 15 if len(volumes) > 5 else sum(volumes) / len(volumes)

        vol_accel = (avg_recent_vol / avg_prior_vol - 1) * 100 if avg_prior_vol > 0 else 0
        vol_score = min(10, max(0, vol_accel / 10))

        price_change = ((closes[-1] - closes[0]) / closes[0]) * 100 if closes[0] != 0 else 0
        price_score = min(10, max(0, max(price_change, 0) / 10))

        narrative_score = vol_score + price_score
        return narrative_score

    def _calculate_adoption(self, ohlcv: List[Dict]) -> float:
        """Adoption 0-20: User/holder growth trajectory.

        Proxy: Volume growth consistency + candle count above MA.
        Consistent volume = sustained adoption, not just pump.
        """
        if len(ohlcv) < 30:
            return 0.0

        volumes = [c["volume"] for c in ohlcv[-30:]]
        ma_20 = sum(volumes[-20:]) / 20

        volumes_above_ma = sum(1 for v in volumes[-20:] if v > ma_20)
        consistency_score = (volumes_above_ma / 20) * 20

        vol_trend_30 = volumes[-1] / (sum(volumes[:15]) / 15) if sum(volumes[:15]) > 0 else 1
        trend_score = min(10, (vol_trend_30 - 1) * 5)

        adoption_score = (consistency_score * 0.6) + (trend_score * 0.4)
        return min(20, adoption_score)

    def _calculate_capital_rotation(self, ohlcv: List[Dict]) -> float:
        """Capital Rotation 0-20: Money flowing into sector.

        Proxy: Quote asset volume (USDT volume) growth.
        Higher USDT volume = larger capital inflows.
        """
        if len(ohlcv) < 20:
            return 0.0

        quote_volumes = [c["quote_asset_volume"] for c in ohlcv[-20:]]
        avg_recent = sum(quote_volumes[-5:]) / 5
        avg_prior = sum(quote_volumes[:-5]) / 15 if len(quote_volumes) > 5 else sum(quote_volumes) / len(quote_volumes)

        capital_growth = (avg_recent / avg_prior - 1) * 100 if avg_prior > 0 else 0
        capital_score = min(20, max(0, capital_growth / 10))

        return capital_score

    def _calculate_fundamentals(self, ohlcv: List[Dict]) -> float:
        """Fundamentals 0-20: Team, investors, tokenomics quality.

        Proxy: Price stability, no extreme swings.
        Established projects = lower volatility.
        Well-funded = consistent support levels.
        """
        if len(ohlcv) < 30:
            return 0.0

        recent = ohlcv[-30:]
        highs = [c["high"] for c in recent]
        lows = [c["low"] for c in recent]

        price_range = [(h - l) / l * 100 if l > 0 else 0 for h, l in zip(highs, lows)]
        avg_range = sum(price_range) / len(price_range) if price_range else 0

        range_consistency = 20 - min(20, avg_range / 2)

        closes = [c["close"] for c in recent]
        support_test_count = sum(
            1 for i in range(1, len(closes))
            if closes[i - 1] < closes[0] and closes[i] > closes[0]
        )
        support_score = min(10, support_test_count * 2)

        fundamentals_score = (range_consistency * 0.6) + (support_score * 0.4)
        return min(20, fundamentals_score)

    def _calculate_market_timing(self, ohlcv: List[Dict]) -> float:
        """Market Timing 0-20: Cycle positioning & relative strength.

        Proxy: RSI positioning + multi-timeframe trend alignment.
        """
        if len(ohlcv) < 14:
            return 0.0

        closes = [c["close"] for c in ohlcv[-14:]]
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

        gains = sum(d for d in deltas if d > 0)
        losses = sum(-d for d in deltas if d < 0)

        avg_gain = gains / len(deltas) if len(deltas) > 0 else 0
        avg_loss = losses / len(deltas) if len(deltas) > 0 else 0

        if avg_loss == 0:
            rsi = 100 if avg_gain > 0 else 50
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        if rsi > 70:
            timing_score = 20
        elif rsi > 60:
            timing_score = 15
        elif rsi > 50:
            timing_score = 10
        elif rsi > 40:
            timing_score = 5
        else:
            timing_score = 0

        return timing_score

    def score_narm(self, ohlcv: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Score token on NARM-P+ 0-100.

        Returns:
        {
            "narm_score": 0-100,
            "narrative": 0-20,
            "adoption": 0-20,
            "capital_rotation": 0-20,
            "fundamentals": 0-20,
            "market_timing": 0-20,
            "current_price": float,
            "timestamp": ISO,
            "verdict": "HOT" (>=80) | "STRONG" (70-79) | "MODERATE" (50-69) | "WEAK" (<50)
        }
        """
        if ohlcv is None:
            ohlcv = self.get_ohlcv()

        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "narm_score": 0,
            "narrative": 0.0,
            "adoption": 0.0,
            "capital_rotation": 0.0,
            "fundamentals": 0.0,
            "market_timing": 0.0,
            "current_price": None,
            "verdict": "WEAK",
        }

        if ohlcv is None or len(ohlcv) == 0:
            logger.warning("Insufficient OHLCV data for NARM scoring")
            return result

        result["current_price"] = ohlcv[-1]["close"]

        narrative = self._calculate_narrative_strength(ohlcv)
        adoption = self._calculate_adoption(ohlcv)
        capital = self._calculate_capital_rotation(ohlcv)
        fundamentals = self._calculate_fundamentals(ohlcv)
        timing = self._calculate_market_timing(ohlcv)

        result["narrative"] = narrative
        result["adoption"] = adoption
        result["capital_rotation"] = capital
        result["fundamentals"] = fundamentals
        result["market_timing"] = timing

        narm_score = narrative + adoption + capital + fundamentals + timing
        result["narm_score"] = int(narm_score)

        if narm_score >= 80:
            result["verdict"] = "HOT"
        elif narm_score >= 70:
            result["verdict"] = "STRONG"
        elif narm_score >= 50:
            result["verdict"] = "MODERATE"
        else:
            result["verdict"] = "WEAK"

        return result

    def report(self) -> str:
        """Generate human-readable NARM opportunity report."""
        ohlcv = self.get_ohlcv()
        result = self.score_narm(ohlcv)

        if result["current_price"] is None:
            return "NARM scoring unavailable (no price data)."

        price_str = f"${result['current_price']:,.0f}"
        score = result["narm_score"]
        verdict = result["verdict"]

        return (
            f"NARM: {score}/100 ({verdict}) | Price {price_str} | "
            f"Narr={result['narrative']:.1f} Adopt={result['adoption']:.1f} "
            f"Cap={result['capital_rotation']:.1f} Fund={result['fundamentals']:.1f} "
            f"Time={result['market_timing']:.1f}"
        )
