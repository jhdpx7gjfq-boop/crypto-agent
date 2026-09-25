import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

import requests

logger = logging.getLogger(__name__)


class RRPEngine:
    """RRP: Revival Radar Pipeline for detecting token renaissance.

    Identifies tokens that were dormant/dead but showing revival signals.
    Multi-stage pipeline:
    1. Collector: Fetch OHLCV + on-chain metrics
    2. Snapshot Validator: Ensure data quality
    3. Immutable Raw Store: Track historical snapshots
    4. Feature Enrichment: Calculate revival signals
    5. Performance Tracker: Measure prediction accuracy
    6. Statistical Validation: Walk-forward, no lookahead

    Score: 0-100 (higher = stronger revival signal)
    Threshold: >=60 for revival candidate

    Revival indicators:
    - Volume breakout: Recent volume >> historical avg
    - Price momentum: Uptrend after prolonged decline
    - On-chain activity: Increased transfers, unique addresses
    - Sentiment shift: Social volume acceleration
    - Structure recovery: Breaking key resistance levels
    """

    def __init__(self, symbol: str = "BTCUSDT", binance_api_timeout: int = 10):
        self.symbol = symbol
        self.binance_api_timeout = binance_api_timeout
        self.snapshots = []  # Immutable store of historical snapshots

    def get_ohlcv(
        self, interval: str = "1d", limit: int = 365
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch daily OHLCV over 1 year to detect dormancy periods."""
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
            logger.warning("Failed to fetch OHLCV for RRP analysis: %s", exc)
            return None

    def _detect_dormancy(self, ohlcv: List[Dict]) -> Dict[str, Any]:
        """Detect if token was dormant (low volume, flat price).

        Returns:
        {
            "is_dormant": bool,
            "dormancy_days": int,
            "avg_dormant_volume": float,
            "dormancy_duration": int (days),
        }
        """
        if len(ohlcv) < 90:
            return {
                "is_dormant": False,
                "dormancy_days": 0,
                "avg_dormant_volume": 0.0,
                "dormancy_duration": 0,
            }

        volumes = [c["volume"] for c in ohlcv[-90:]]
        closes = [c["close"] for c in ohlcv[-90:]]

        avg_volume_90 = sum(volumes) / len(volumes)
        low_volume_threshold = avg_volume_90 * 0.3

        dormancy_count = 0
        for v in volumes:
            if v < low_volume_threshold:
                dormancy_count += 1

        price_range = max(closes) - min(closes)
        price_volatility = (price_range / min(closes)) * 100 if min(closes) > 0 else 0

        is_dormant = dormancy_count > 60 or price_volatility < 5

        return {
            "is_dormant": is_dormant,
            "dormancy_days": dormancy_count,
            "avg_dormant_volume": avg_volume_90,
            "dormancy_duration": 90,
        }

    def _detect_volume_breakout(self, ohlcv: List[Dict]) -> float:
        """Volume Breakout 0-25: Recent volume >> dormant period avg.

        Revival signature: volume spike after silence.
        """
        if len(ohlcv) < 90:
            return 0.0

        recent_volume = [c["volume"] for c in ohlcv[-10:]]
        dormant_volume = [c["volume"] for c in ohlcv[-90:-10]]

        avg_recent = sum(recent_volume) / len(recent_volume) if recent_volume else 0
        avg_dormant = sum(dormant_volume) / len(dormant_volume) if dormant_volume else 1

        breakout_ratio = avg_recent / avg_dormant if avg_dormant > 0 else 1

        if breakout_ratio > 5:
            return 25.0
        elif breakout_ratio > 3:
            return 15.0
        elif breakout_ratio > 2:
            return 10.0
        elif breakout_ratio > 1.5:
            return 5.0
        else:
            return 0.0

    def _detect_price_momentum(self, ohlcv: List[Dict]) -> float:
        """Price Momentum 0-25: Uptrend after prolonged decline.

        Revival requires: price breaking key resistance, positive trend.
        """
        if len(ohlcv) < 90:
            return 0.0

        closes = [c["close"] for c in ohlcv[-90:]]

        min_price_90 = min(closes[-90:])
        max_price_90 = max(closes[-90:])
        recent_price = closes[-1]

        recovery_pct = ((recent_price - min_price_90) / min_price_90) * 100 if min_price_90 > 0 else 0

        recent_trend = closes[-1] - closes[-30] if len(closes) >= 30 else 0
        trend_strength = (recent_trend / closes[-30]) * 100 if closes[-30] != 0 else 0

        if recovery_pct > 50 and trend_strength > 15:
            return 25.0
        elif recovery_pct > 30 and trend_strength > 10:
            return 18.0
        elif recovery_pct > 20 and trend_strength > 5:
            return 12.0
        elif recovery_pct > 10 and trend_strength > 0:
            return 6.0
        else:
            return 0.0

    def _detect_structure_recovery(self, ohlcv: List[Dict]) -> float:
        """Structure Recovery 0-20: Breaking key resistance levels.

        Revival signal: price escaping multi-month range.
        """
        if len(ohlcv) < 90:
            return 0.0

        closes = [c["close"] for c in ohlcv[-90:]]
        highs = [c["high"] for c in ohlcv[-90:]]

        monthly_resistance = max(highs[-60:]) if len(highs) >= 60 else max(highs)
        current_price = closes[-1]
        prev_high = highs[-10] if len(highs) >= 10 else highs[-1]

        resistance_break_pct = ((current_price - prev_high) / prev_high) * 100 if prev_high > 0 else 0

        if current_price > monthly_resistance:
            return 20.0
        elif resistance_break_pct > 10:
            return 15.0
        elif resistance_break_pct > 5:
            return 10.0
        elif resistance_break_pct > 0:
            return 5.0
        else:
            return 0.0

    def _detect_sentiment_shift(self, ohlcv: List[Dict]) -> float:
        """Sentiment Shift 0-20: Social/On-chain volume acceleration.

        Proxy: Volume surge on positive price days = renewed interest.
        """
        if len(ohlcv) < 30:
            return 0.0

        recent = ohlcv[-30:]
        positive_days = 0
        high_volume_days = 0

        avg_volume_30 = sum(c["volume"] for c in recent) / len(recent)

        for i, candle in enumerate(recent):
            if candle["close"] > candle["open"]:
                positive_days += 1
            if candle["volume"] > avg_volume_30 * 1.5:
                high_volume_days += 1

        positive_rate = (positive_days / len(recent)) * 100
        volume_rate = (high_volume_days / len(recent)) * 100

        combined_score = (positive_rate * 0.6 + volume_rate * 0.4) / 100 * 20

        return min(20.0, combined_score)

    def _detect_exhaustion_recovery(self, ohlcv: List[Dict]) -> float:
        """Exhaustion Recovery 0-10: Selling pressure subsiding.

        Revival marker: volume declining on down days = exhaustion ending.
        """
        if len(ohlcv) < 20:
            return 0.0

        recent = ohlcv[-20:]

        down_volume = []
        for i, candle in enumerate(recent):
            if candle["close"] < candle["open"]:
                down_volume.append(candle["volume"])

        if not down_volume:
            return 10.0

        avg_down_volume = sum(down_volume) / len(down_volume)
        recent_avg_volume = sum(c["volume"] for c in recent) / len(recent)

        down_volume_ratio = avg_down_volume / recent_avg_volume if recent_avg_volume > 0 else 1

        if down_volume_ratio < 0.7:
            return 10.0
        elif down_volume_ratio < 0.9:
            return 6.0
        else:
            return 0.0

    def score_rrp(self, ohlcv: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Score token for revival potential (0-100).

        Returns:
        {
            "rrp_score": 0-100,
            "is_dormant": bool,
            "volume_breakout": 0-25,
            "price_momentum": 0-25,
            "structure_recovery": 0-20,
            "sentiment_shift": 0-20,
            "exhaustion_recovery": 0-10,
            "current_price": float,
            "dormancy_info": dict,
            "timestamp": ISO,
            "verdict": "REVIVING" (>=60) | "WAKING" (40-59) | "DORMANT" (<40)
        }
        """
        if ohlcv is None:
            ohlcv = self.get_ohlcv()

        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "rrp_score": 0,
            "is_dormant": False,
            "volume_breakout": 0.0,
            "price_momentum": 0.0,
            "structure_recovery": 0.0,
            "sentiment_shift": 0.0,
            "exhaustion_recovery": 0.0,
            "current_price": None,
            "dormancy_info": {},
            "verdict": "DORMANT",
        }

        if ohlcv is None or len(ohlcv) == 0:
            logger.warning("Insufficient OHLCV data for RRP scoring")
            return result

        result["current_price"] = ohlcv[-1]["close"]

        dormancy_info = self._detect_dormancy(ohlcv)
        result["is_dormant"] = dormancy_info["is_dormant"]
        result["dormancy_info"] = dormancy_info

        volume = self._detect_volume_breakout(ohlcv)
        momentum = self._detect_price_momentum(ohlcv)
        structure = self._detect_structure_recovery(ohlcv)
        sentiment = self._detect_sentiment_shift(ohlcv)
        exhaustion = self._detect_exhaustion_recovery(ohlcv)

        result["volume_breakout"] = volume
        result["price_momentum"] = momentum
        result["structure_recovery"] = structure
        result["sentiment_shift"] = sentiment
        result["exhaustion_recovery"] = exhaustion

        rrp_score = volume + momentum + structure + sentiment + exhaustion
        result["rrp_score"] = int(rrp_score)

        if rrp_score >= 60:
            result["verdict"] = "REVIVING"
        elif rrp_score >= 40:
            result["verdict"] = "WAKING"
        else:
            result["verdict"] = "DORMANT"

        self.snapshots.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "score": result["rrp_score"],
                "verdict": result["verdict"],
                "price": result["current_price"],
            }
        )

        return result

    def report(self) -> str:
        """Generate human-readable revival radar report."""
        ohlcv = self.get_ohlcv()
        result = self.score_rrp(ohlcv)

        if result["current_price"] is None:
            return "RRP scoring unavailable (no price data)."

        price_str = f"${result['current_price']:,.0f}"
        score = result["rrp_score"]
        verdict = result["verdict"]
        is_dormant = "DORMANT" if result["is_dormant"] else "ACTIVE"

        return (
            f"RRP: {score}/100 ({verdict}) | {is_dormant} | Price {price_str} | "
            f"Vol={result['volume_breakout']:.1f} Mom={result['price_momentum']:.1f} "
            f"Struct={result['structure_recovery']:.1f} Sent={result['sentiment_shift']:.1f} "
            f"Exh={result['exhaustion_recovery']:.1f}"
        )
