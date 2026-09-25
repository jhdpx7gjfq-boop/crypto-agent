import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import requests

logger = logging.getLogger(__name__)


class MarketRegimeEngine:
    """Detects global market regime: Bitcoin dominance, liquidity, risk-on/off."""

    def __init__(self, binance_api_timeout: int = 10):
        self.binance_api_timeout = binance_api_timeout
        self._cache = {}
        self._cache_ttl_seconds = 300

    def get_btc_price(self) -> Optional[float]:
        """Fetch BTC/USDT price from Binance public API."""
        try:
            resp = requests.get(
                "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
                timeout=self.binance_api_timeout,
            )
            resp.raise_for_status()
            return float(resp.json()["price"])
        except (requests.RequestException, KeyError, ValueError) as exc:
            logger.warning("Failed to fetch BTC price from Binance: %s", exc)
            return None

    def get_btc_funding_rate(self) -> Optional[float]:
        """Fetch perpetual funding rate from Binance (8h rate indicator)."""
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
            logger.warning("Failed to fetch BTC funding rate from Binance: %s", exc)
            return None

    def get_btc_open_interest(self) -> Optional[float]:
        """Fetch BTC open interest in USDT from Binance (proxy for leverage)."""
        try:
            resp = requests.get(
                "https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT",
                timeout=self.binance_api_timeout,
            )
            resp.raise_for_status()
            return float(resp.json()["openInterest"])
        except (requests.RequestException, KeyError, ValueError) as exc:
            logger.warning("Failed to fetch BTC open interest from Binance: %s", exc)
            return None

    def detect_regime(
        self, btc_price: Optional[float] = None, funding_rate: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Detect market regime based on available signals.

        Returns dict with:
        - btc_price: current BTC price (USD)
        - funding_rate: 8h perpetual funding rate (higher = bullish sentiment, greed)
        - oi_sentiment: open interest trend (greedy/cautious)
        - regime: "bullish_greed" | "bullish_caution" | "bearish" | "neutral"
        - score: 0-100 (0=maximum bearish, 100=maximum bullish)
        """
        if btc_price is None:
            btc_price = self.get_btc_price()
        if funding_rate is None:
            funding_rate = self.get_btc_funding_rate()

        regime_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "btc_price": btc_price,
            "funding_rate": funding_rate,
            "regime": "neutral",
            "score": 50,
        }

        if btc_price is None or funding_rate is None:
            logger.warning("Insufficient data to detect regime (price or funding rate missing)")
            return regime_data

        # Regime logic:
        # Funding rate > 0.0005 (0.05%): bullish (traders are long, willing to pay)
        # Funding rate < -0.0005: bearish (shorts dominate)
        # In between: neutral
        #
        # Bitcoin regime (simple: price vs 200-day MA would be ideal, but we use heuristic)
        # For now: use funding rate as primary signal
        funding_threshold_bullish = 0.0005
        funding_threshold_bearish = -0.0005

        if funding_rate > funding_threshold_bullish:
            regime_data["regime"] = "bullish_greed"
            regime_data["score"] = min(100, 50 + int(funding_rate * 100000))
        elif funding_rate < funding_threshold_bearish:
            regime_data["regime"] = "bearish"
            regime_data["score"] = max(0, 50 + int(funding_rate * 100000))
        else:
            regime_data["regime"] = "neutral"
            regime_data["score"] = 50

        return regime_data

    def report(self) -> str:
        """Generate human-readable regime report."""
        regime = self.detect_regime()

        if regime["btc_price"] is None:
            return "Market regime detection unavailable (no price data)."

        price_str = f"${regime['btc_price']:,.0f}"
        rate_pct = regime["funding_rate"] * 100 if regime["funding_rate"] else None
        rate_str = f"{rate_pct:.3f}%" if rate_pct is not None else "N/A"

        return (
            f"Market Regime: {regime['regime'].upper()} (score {regime['score']}/100) | "
            f"BTC {price_str} | Funding {rate_str}"
        )
