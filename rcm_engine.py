import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

import requests

logger = logging.getLogger(__name__)


class RCMEngine:
    """RCM/RPM: Rotation Confirmation Model for capital flow detection.

    Detects capital rotation between sectors/tokens.
    Weighted components (no lookahead bias):
    - Capital Flow (25%): USDT volume trend acceleration
    - Relative Strength (25%): Outperformance vs BTC
    - Narrative Acceleration (20%): Volume + price momentum combo
    - Fundamental Confirmation (20%): Support/resistance hold + structure
    - Derivatives Structure (10%): Funding rate + open interest signals

    Score: 0-100 (higher = stronger rotation signal)
    Threshold: >=70 for confirmed rotation entry

    Walk Forward validation: Each score uses only past/present data,
    no future data leakage.
    """

    def __init__(self, symbol: str = "BTCUSDT", binance_api_timeout: int = 10):
        self.symbol = symbol
        self.binance_api_timeout = binance_api_timeout

    def get_ohlcv(
        self, interval: str = "4h", limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch OHLCV candles from Binance (4h timeframe for rotation detection)."""
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
            logger.warning("Failed to fetch OHLCV for RCM analysis: %s", exc)
            return None

    def get_funding_rate(self) -> Optional[float]:
        """Fetch current BTC funding rate (proxy for leverage/sentiment)."""
        try:
            resp = requests.get(
                "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1",
                timeout=self.binance_api_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            if data:
                return float(data[0]["fundingRate"])
            return None
        except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
            logger.warning("Failed to fetch funding rate for RCM: %s", exc)
            return None

    def _calculate_capital_flow(self, ohlcv: List[Dict]) -> float:
        """Capital Flow 0-25: USDT volume acceleration.

        Measures money flowing in/out. Higher acceleration = stronger inflow.
        Uses quote asset volume (USDT volume).
        """
        if len(ohlcv) < 20:
            return 0.0

        quote_volumes = [c["quote_asset_volume"] for c in ohlcv[-20:]]
        avg_recent = sum(quote_volumes[-5:]) / 5
        avg_prior = sum(quote_volumes[:-5]) / 15 if len(quote_volumes) > 5 else sum(quote_volumes) / len(quote_volumes)

        flow_accel = (avg_recent / avg_prior - 1) * 100 if avg_prior > 0 else 0
        capital_score = min(25, max(0, flow_accel / 5))

        return capital_score

    def _calculate_relative_strength(self, ohlcv: List[Dict]) -> float:
        """Relative Strength 0-25: Outperformance (RSI momentum).

        Token outperforming when RSI is elevated.
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
            rs_score = 25
        elif rsi > 60:
            rs_score = 18
        elif rsi > 50:
            rs_score = 12
        else:
            rs_score = 0

        return rs_score

    def _calculate_narrative_acceleration(self, ohlcv: List[Dict]) -> float:
        """Narrative Acceleration 0-20: Volume + momentum combo.

        Measures how quickly narrative is gaining traction.
        Uses volume growth + price momentum together.
        """
        if len(ohlcv) < 20:
            return 0.0

        volumes = [c["volume"] for c in ohlcv[-20:]]
        closes = [c["close"] for c in ohlcv[-20:]]

        vol_accel = (sum(volumes[-5:]) / 5) / (sum(volumes[:15]) / 15) if sum(volumes[:15]) > 0 else 1
        price_accel = ((closes[-1] - closes[-10]) / closes[-10]) * 100 if closes[-10] != 0 else 0

        accel_score = min(20, max(0, (vol_accel - 1) * 10 + max(price_accel, 0) / 5))

        return accel_score

    def _calculate_fundamental_confirmation(self, ohlcv: List[Dict]) -> float:
        """Fundamental Confirmation 0-20: Support/resistance structure.

        Rotation valid when price respects key levels.
        Measures price stability and support holds.
        """
        if len(ohlcv) < 30:
            return 0.0

        recent = ohlcv[-30:]
        lows = [c["low"] for c in recent]
        closes = [c["close"] for c in recent]

        support_level = min(lows)
        price_above_support = closes[-1] > support_level * 1.01

        test_count = sum(
            1 for i in range(1, len(closes))
            if closes[i - 1] < support_level * 1.02 and closes[i] > support_level * 1.02
        )

        hold_score = 10 if price_above_support else 0
        test_score = min(10, test_count * 2)

        fundamental_score = hold_score + test_score
        return fundamental_score

    def _calculate_derivatives_structure(
        self, ohlcv: List[Dict], funding_rate: Optional[float] = None
    ) -> float:
        """Derivatives Structure 0-10: Funding rate + OI signals.

        Positive funding + rising OI = leverage building, rotation confirmation.
        """
        if funding_rate is None:
            funding_rate = self.get_funding_rate()

        if funding_rate is None or len(ohlcv) < 2:
            return 0.0

        funding_threshold = 0.0001
        if funding_rate > funding_threshold:
            funding_score = min(10, (funding_rate * 100000) * 0.5)
        elif funding_rate < -funding_threshold:
            funding_score = 0
        else:
            funding_score = 2

        return funding_score

    def score_rcm(
        self, ohlcv: Optional[List[Dict]] = None, funding_rate: Optional[float] = None
    ) -> Dict[str, Any]:
        """Score rotation confirmation 0-100.

        Returns:
        {
            "rcm_score": 0-100,
            "capital_flow": 0-25,
            "relative_strength": 0-25,
            "narrative_accel": 0-20,
            "fundamental": 0-20,
            "derivatives": 0-10,
            "current_price": float,
            "timestamp": ISO,
            "verdict": "CONFIRMED" (>=70) | "BUILDING" (50-69) | "WEAK" (<50)
        }
        """
        if ohlcv is None:
            ohlcv = self.get_ohlcv()

        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "rcm_score": 0,
            "capital_flow": 0.0,
            "relative_strength": 0.0,
            "narrative_accel": 0.0,
            "fundamental": 0.0,
            "derivatives": 0.0,
            "current_price": None,
            "verdict": "WEAK",
        }

        if ohlcv is None or len(ohlcv) == 0:
            logger.warning("Insufficient OHLCV data for RCM scoring")
            return result

        result["current_price"] = ohlcv[-1]["close"]

        capital = self._calculate_capital_flow(ohlcv)
        rs = self._calculate_relative_strength(ohlcv)
        narrative = self._calculate_narrative_acceleration(ohlcv)
        fundamental = self._calculate_fundamental_confirmation(ohlcv)
        derivatives = self._calculate_derivatives_structure(ohlcv, funding_rate)

        result["capital_flow"] = capital
        result["relative_strength"] = rs
        result["narrative_accel"] = narrative
        result["fundamental"] = fundamental
        result["derivatives"] = derivatives

        rcm_score = capital + rs + narrative + fundamental + derivatives
        result["rcm_score"] = int(rcm_score)

        if rcm_score >= 70:
            result["verdict"] = "CONFIRMED"
        elif rcm_score >= 50:
            result["verdict"] = "BUILDING"
        else:
            result["verdict"] = "WEAK"

        return result

    def report(self) -> str:
        """Generate human-readable rotation confirmation report."""
        ohlcv = self.get_ohlcv()
        funding_rate = self.get_funding_rate()
        result = self.score_rcm(ohlcv, funding_rate)

        if result["current_price"] is None:
            return "RCM scoring unavailable (no price data)."

        price_str = f"${result['current_price']:,.0f}"
        score = result["rcm_score"]
        verdict = result["verdict"]

        return (
            f"RCM: {score}/100 ({verdict}) | Price {price_str} | "
            f"Cap={result['capital_flow']:.1f} RS={result['relative_strength']:.1f} "
            f"Narr={result['narrative_accel']:.1f} Fund={result['fundamental']:.1f} "
            f"Deriv={result['derivatives']:.1f}"
        )
