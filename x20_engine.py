import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

import requests

logger = logging.getLogger(__name__)


class X20Engine:
    """X20 opportunity scorer: Identifies tokens with 10-20x asymmetric potential.

    Analyzes:
    - Momentum: Price acceleration, trend strength
    - Volatility: Price swing magnitude (higher = higher potential)
    - Relative Strength: Performance vs market (BTC dominance, altseason)
    - Liquidity: USDT pair volume (higher = lower slippage risk)
    - Risk/Reward: Win rate proxy via technical setup quality

    Score: 0-100 (higher = stronger X20 candidate)
    Threshold: >=70 for strong opportunity
    """

    def __init__(self, symbol: str = "BTCUSDT", binance_api_timeout: int = 10):
        self.symbol = symbol
        self.binance_api_timeout = binance_api_timeout

    def get_ohlcv(
        self, interval: str = "4h", limit: int = 100
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
            logger.warning("Failed to fetch OHLCV for X20 analysis: %s", exc)
            return None

    def _calculate_momentum(self, ohlcv: List[Dict]) -> float:
        """Momentum score 0-20: Rate of price change.

        Higher = faster uptrend = higher momentum.
        Uses ROC (Rate of Change) over 10 and 20 periods.
        """
        if len(ohlcv) < 20:
            return 0.0

        closes = [c["close"] for c in ohlcv]
        roc_10 = ((closes[-1] - closes[-10]) / closes[-10]) * 100 if closes[-10] != 0 else 0
        roc_20 = ((closes[-1] - closes[-20]) / closes[-20]) * 100 if closes[-20] != 0 else 0

        avg_roc = (roc_10 + roc_20) / 2
        momentum_score = min(20, max(0, avg_roc / 5))

        return momentum_score

    def _calculate_volatility(self, ohlcv: List[Dict]) -> float:
        """Volatility score 0-20: Price swing magnitude.

        Higher volatility = larger potential moves = higher score.
        Uses ATR (Average True Range) as percentage of price.
        """
        if len(ohlcv) < 14:
            return 0.0

        recent = ohlcv[-14:]
        true_ranges = []

        for i, candle in enumerate(recent):
            if i == 0:
                tr = candle["high"] - candle["low"]
            else:
                prev_close = recent[i - 1]["close"]
                tr = max(
                    candle["high"] - candle["low"],
                    abs(candle["high"] - prev_close),
                    abs(candle["low"] - prev_close),
                )
            true_ranges.append(tr)

        atr = sum(true_ranges) / len(true_ranges)
        avg_price = sum(c["close"] for c in recent) / len(recent)
        atr_pct = (atr / avg_price) * 100 if avg_price > 0 else 0

        volatility_score = min(20, atr_pct * 2)

        return volatility_score

    def _calculate_relative_strength(self, ohlcv: List[Dict]) -> float:
        """Relative Strength score 0-20: Outperformance vs BTC.

        Analyzes RSI (Relative Strength Index) momentum.
        Higher RSI near overbought = stronger uptrend.
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

        rs_score = (rsi - 50) / 2.5 if rsi > 50 else 0
        rs_score = min(20, max(0, rs_score))

        return rs_score

    def _calculate_liquidity(self, ohlcv: List[Dict]) -> float:
        """Liquidity score 0-20: USDT trading volume depth.

        Higher volume = lower slippage = safer entry.
        Uses 20-period average volume.
        """
        if len(ohlcv) == 0:
            return 0.0

        avg_volume = sum(c["volume"] for c in ohlcv[-20:]) / min(20, len(ohlcv))

        if avg_volume < 100000:
            return 0.0
        elif avg_volume < 1000000:
            return 5.0
        elif avg_volume < 10000000:
            return 10.0
        elif avg_volume < 50000000:
            return 15.0
        else:
            return 20.0

    def _calculate_risk_reward(self, ohlcv: List[Dict]) -> float:
        """Risk/Reward score 0-20: Setup quality & recent performance.

        Combines:
        - Recent win rate (% candles closing above open)
        - Swing ratio (high-low range vs close movement)
        """
        if len(ohlcv) < 10:
            return 0.0

        recent = ohlcv[-10:]

        up_candles = sum(1 for c in recent if c["close"] > c["open"])
        win_rate = (up_candles / len(recent)) * 100

        swing_range = sum((c["high"] - c["low"]) for c in recent) / len(recent)
        close_move = abs(recent[-1]["close"] - recent[0]["close"])
        swing_ratio = (close_move / swing_range) if swing_range > 0 else 0

        rr_score = (win_rate / 10) * 0.7 + (swing_ratio * 10) * 0.3
        rr_score = min(20, max(0, rr_score))

        return rr_score

    def score_x20(self, ohlcv: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Score token for X20 potential (0-100).

        Returns:
        {
            "x20_score": 0-100,
            "momentum": 0-20,
            "volatility": 0-20,
            "relative_strength": 0-20,
            "liquidity": 0-20,
            "risk_reward": 0-20,
            "current_price": float,
            "timestamp": ISO,
            "verdict": "STRONG" (>=70) | "MODERATE" (50-69) | "WEAK" (<50)
        }
        """
        if ohlcv is None:
            ohlcv = self.get_ohlcv()

        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "x20_score": 0,
            "momentum": 0.0,
            "volatility": 0.0,
            "relative_strength": 0.0,
            "liquidity": 0.0,
            "risk_reward": 0.0,
            "current_price": None,
            "verdict": "WEAK",
        }

        if ohlcv is None or len(ohlcv) == 0:
            logger.warning("Insufficient OHLCV data for X20 scoring")
            return result

        result["current_price"] = ohlcv[-1]["close"]

        momentum = self._calculate_momentum(ohlcv)
        volatility = self._calculate_volatility(ohlcv)
        rs = self._calculate_relative_strength(ohlcv)
        liquidity = self._calculate_liquidity(ohlcv)
        rr = self._calculate_risk_reward(ohlcv)

        result["momentum"] = momentum
        result["volatility"] = volatility
        result["relative_strength"] = rs
        result["liquidity"] = liquidity
        result["risk_reward"] = rr

        x20_score = momentum + volatility + rs + liquidity + rr
        result["x20_score"] = int(x20_score)

        if x20_score >= 70:
            result["verdict"] = "STRONG"
        elif x20_score >= 50:
            result["verdict"] = "MODERATE"
        else:
            result["verdict"] = "WEAK"

        return result

    def report(self) -> str:
        """Generate human-readable X20 opportunity report."""
        ohlcv = self.get_ohlcv()
        result = self.score_x20(ohlcv)

        if result["current_price"] is None:
            return "X20 scoring unavailable (no price data)."

        price_str = f"${result['current_price']:,.0f}"
        score = result["x20_score"]
        verdict = result["verdict"]

        return (
            f"X20: {score}/100 ({verdict}) | Price {price_str} | "
            f"Mom={result['momentum']:.1f} Vol={result['volatility']:.1f} "
            f"RS={result['relative_strength']:.1f} Liq={result['liquidity']:.1f} "
            f"RR={result['risk_reward']:.1f}"
        )
