import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

import requests

logger = logging.getLogger(__name__)


class BottomConfirmationEngine:
    """Wyckoff-based bottom confirmation scorer (BCE).

    Detects accumulation phases via:
    - Wyckoff structure (support/resistance, swings)
    - Volume analysis (relative volume, VPT)
    - Exhaustion signals (selling pressure taper)
    - Smart money patterns (price/volume accumulation)

    Outputs: 0-6 score, >=5 required for valid long signal.
    """

    def __init__(self, symbol: str = "BTCUSDT", binance_api_timeout: int = 10):
        self.symbol = symbol
        self.binance_api_timeout = binance_api_timeout

    def get_ohlcv(
        self, interval: str = "1h", limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch OHLCV candles from Binance."""
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
                }
                for candle in data
            ]
        except (requests.RequestException, KeyError, ValueError, IndexError) as exc:
            logger.warning("Failed to fetch OHLCV from Binance: %s", exc)
            return None

    def _calculate_support_resistance(self, ohlcv: List[Dict]) -> Dict[str, float]:
        """Detect support (low pivot) and resistance (high pivot) levels."""
        if len(ohlcv) < 3:
            return {"support": None, "resistance": None}

        lows = [c["low"] for c in ohlcv[-20:]]
        highs = [c["high"] for c in ohlcv[-20:]]

        support = min(lows) if lows else None
        resistance = max(highs) if highs else None

        return {"support": support, "resistance": resistance}

    def _calculate_relative_volume(self, ohlcv: List[Dict]) -> float:
        """Relative volume: current volume / 20-period average."""
        if len(ohlcv) < 2:
            return 1.0

        current_volume = ohlcv[-1]["volume"]
        avg_volume = sum(c["volume"] for c in ohlcv[-20:]) / min(20, len(ohlcv))

        return current_volume / avg_volume if avg_volume > 0 else 1.0

    def _detect_exhaustion(self, ohlcv: List[Dict]) -> int:
        """Exhaustion score 0-2: selling pressure signals.

        0 = High selling pressure
        1 = Moderate
        2 = Exhausted (low volume, bouncing)
        """
        if len(ohlcv) < 5:
            return 1

        recent_closes = [c["close"] for c in ohlcv[-5:]]
        recent_volumes = [c["volume"] for c in ohlcv[-10:]]

        avg_recent_vol = sum(recent_volumes[-5:]) / 5
        avg_prior_vol = sum(recent_volumes[:5]) / 5

        is_bouncing = recent_closes[-1] > recent_closes[-2]
        vol_declining = avg_recent_vol < avg_prior_vol

        if vol_declining and is_bouncing:
            return 2
        elif vol_declining or is_bouncing:
            return 1
        else:
            return 0

    def _detect_accumulation(self, ohlcv: List[Dict]) -> int:
        """Accumulation score 0-2: smart money buy signals.

        0 = No accumulation
        1 = Weak signs
        2 = Strong accumulation (high volume on bounces, tight range)
        """
        if len(ohlcv) < 10:
            return 0

        recent = ohlcv[-10:]
        price_range = max(c["high"] for c in recent) - min(c["low"] for c in recent)
        avg_price = sum(c["close"] for c in recent) / len(recent)
        range_pct = (price_range / avg_price) * 100 if avg_price > 0 else 100

        up_candles = sum(1 for c in recent if c["close"] > c["open"])
        high_vol_candles = sum(
            1 for c in recent if c["volume"] > sum(x["volume"] for x in recent) / len(recent)
        )

        tight_range = range_pct < 5
        balanced_closes = 3 <= up_candles <= 7
        vol_on_structure = high_vol_candles >= 3

        if tight_range and balanced_closes and vol_on_structure:
            return 2
        elif tight_range or balanced_closes:
            return 1
        else:
            return 0

    def _analyze_price_structure(self, ohlcv: List[Dict]) -> int:
        """Structure score 0-2: Wyckoff patterns.

        0 = Downtrend, lower lows/highs
        1 = Sideways/weak
        2 = Accumulation (higher lows, stable resistance)
        """
        if len(ohlcv) < 10:
            return 1

        recent = ohlcv[-10:]
        lows = [c["low"] for c in recent]
        highs = [c["high"] for c in recent]

        low_trend = [lows[i] for i in range(0, len(lows), 2)]
        high_trend = [highs[i] for i in range(0, len(highs), 2)]

        lower_lows = low_trend[-1] < low_trend[0]
        lower_highs = high_trend[-1] < high_trend[0]

        if lower_lows and lower_highs:
            return 0
        elif any(lows[i] < lows[i - 1] for i in range(1, len(lows))):
            return 1
        else:
            return 2

    def score_bce(self, ohlcv: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Score bottom confirmation 0-6.

        Returns:
        {
            "bce_score": 0-6,
            "timestamp": ISO timestamp,
            "exhaustion": 0-2,
            "accumulation": 0-2,
            "structure": 0-2,
            "relative_volume": float,
            "support": float or None,
            "resistance": float or None,
            "current_price": float or None,
        }
        """
        if ohlcv is None:
            ohlcv = self.get_ohlcv()

        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "bce_score": 0,
            "exhaustion": 0,
            "accumulation": 0,
            "structure": 0,
            "relative_volume": 1.0,
            "support": None,
            "resistance": None,
            "current_price": None,
        }

        if ohlcv is None or len(ohlcv) == 0:
            logger.warning("Insufficient OHLCV data for BCE scoring")
            return result

        current_price = ohlcv[-1]["close"]
        result["current_price"] = current_price

        exhaustion = self._detect_exhaustion(ohlcv)
        accumulation = self._detect_accumulation(ohlcv)
        structure = self._analyze_price_structure(ohlcv)
        rel_volume = self._calculate_relative_volume(ohlcv)
        sr = self._calculate_support_resistance(ohlcv)

        result["exhaustion"] = exhaustion
        result["accumulation"] = accumulation
        result["structure"] = structure
        result["relative_volume"] = rel_volume
        result["support"] = sr["support"]
        result["resistance"] = sr["resistance"]

        bce_score = exhaustion + accumulation + structure
        result["bce_score"] = bce_score

        return result

    def report(self) -> str:
        """Generate human-readable BCE report."""
        ohlcv = self.get_ohlcv()
        result = self.score_bce(ohlcv)

        if result["current_price"] is None:
            return "BCE scoring unavailable (no price data)."

        price_str = f"${result['current_price']:,.0f}"
        score = result["bce_score"]
        verdict = "VALID" if score >= 5 else "INVALID"
        vol_str = f"{result['relative_volume']:.2f}x"

        return (
            f"BCE: {score}/6 ({verdict}) | BTC {price_str} | Vol {vol_str} | "
            f"Exhaust={result['exhaustion']} Accum={result['accumulation']} "
            f"Struct={result['structure']}"
        )
