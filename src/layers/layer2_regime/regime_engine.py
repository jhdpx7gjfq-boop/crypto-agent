"""Market Regime Detection (Layer 2)."""

import logging
from datetime import datetime
from typing import Optional

from src.core.models import MarketRegime, RegimeType
from src.core.config import Config


logger = logging.getLogger(__name__)


class MarketRegimeDetector:
    """
    Detects current market regime based on:
    - Bitcoin price trend
    - Funding rates (bullish vs bearish sentiment)
    - Open interest (leverage levels)
    - Liquidity indicators
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache = {}

    def detect_regime(
        self,
        btc_price: Optional[float] = None,
        funding_rate: Optional[float] = None,
        open_interest_change: Optional[float] = None,
        btc_dominance: Optional[float] = None,
        dxy: Optional[float] = None,
        us10y: Optional[float] = None,
    ) -> MarketRegime:
        """
        Detect market regime from multiple signals.

        Args:
            btc_price: Current BTC price (USD)
            funding_rate: Perpetual funding rate (% per 8h)
            open_interest_change: % change in open interest
            btc_dominance: BTC dominance % (0-100)
            dxy: Dollar Index
            us10y: US 10Y yield

        Returns:
            MarketRegime object
        """

        timestamp = datetime.utcnow()

        # Fetch data if not provided
        if btc_price is None:
            btc_price = self._fetch_btc_price()
        if funding_rate is None:
            funding_rate = self._fetch_funding_rate()
        if open_interest_change is None:
            open_interest_change = 0.0
        if btc_dominance is None:
            btc_dominance = self._fetch_btc_dominance()

        # Classify regime
        regime = self._classify_regime(
            funding_rate=funding_rate,
            oi_change=open_interest_change,
            btc_dom=btc_dominance,
        )

        macro_score = self._compute_macro_score(
            dxy=dxy,
            us10y=us10y,
        )

        market_regime = MarketRegime(
            timestamp=timestamp,
            regime=regime,
            btc_dominance=btc_dominance or 50.0,
            funding_rate=funding_rate or 0.0,
            open_interest_change=open_interest_change or 0.0,
            dxy=dxy,
            us10y=us10y,
            macro_score=macro_score,
        )

        logger.info(f"Regime: {regime.value} | BTC Dom: {btc_dominance or 50.0:.1f}% | FR: {funding_rate or 0.0:.4f}")

        return market_regime

    @staticmethod
    def _classify_regime(
        funding_rate: Optional[float],
        oi_change: Optional[float],
        btc_dom: Optional[float],
    ) -> RegimeType:
        """Classify regime based on signals."""

        if funding_rate is None:
            return RegimeType.SIDEWAYS

        # Thresholds
        fr_bull_threshold = 0.0005   # 0.05% per 8h = bullish
        fr_bear_threshold = -0.0005  # bearish
        oi_bull_threshold = 20.0     # % increase = bullish
        dom_bull_threshold = 55.0    # BTC dominance spike

        signals = []

        # Signal 1: Funding rate
        if funding_rate > fr_bull_threshold:
            signals.append("bull_fr")
        elif funding_rate < fr_bear_threshold:
            signals.append("bear_fr")
        else:
            signals.append("neutral_fr")

        # Signal 2: Open interest
        if oi_change and oi_change > oi_bull_threshold:
            signals.append("bull_oi")
        elif oi_change and oi_change < -oi_bull_threshold:
            signals.append("bear_oi")

        # Signal 3: BTC dominance
        if btc_dom and btc_dom > dom_bull_threshold:
            signals.append("bull_dom")

        # Decision logic
        bull_count = len([s for s in signals if "bull" in s])
        bear_count = len([s for s in signals if "bear" in s])

        if bull_count >= 2:
            return RegimeType.BULL
        elif bear_count >= 2:
            return RegimeType.BEAR
        elif bull_count >= 1 and bear_count == 0:
            return RegimeType.BULL
        elif bear_count >= 1 and bull_count == 0:
            return RegimeType.BEAR
        else:
            return RegimeType.SIDEWAYS

    @staticmethod
    def _compute_macro_score(
        dxy: Optional[float],
        us10y: Optional[float],
    ) -> float:
        """
        Macro conditions score (0-100).

        Higher = more favorable for crypto (weak USD, low rates).
        """

        score = 50.0

        if dxy:
            # Lower DXY is bullish for crypto
            if dxy < 100:
                score += 10
            elif dxy > 110:
                score -= 10

        if us10y:
            # Lower rates are bullish for crypto
            if us10y < 3.0:
                score += 10
            elif us10y > 5.0:
                score -= 10

        return max(0, min(100, score))

    @staticmethod
    def _fetch_btc_price() -> Optional[float]:
        """Fetch BTC/USDT from Binance."""
        try:
            import requests
            resp = requests.get(
                "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
                timeout=5,
            )
            resp.raise_for_status()
            return float(resp.json()["price"])
        except Exception as e:
            logger.warning(f"Failed to fetch BTC price: {e}")
            return None

    @staticmethod
    def _fetch_funding_rate() -> Optional[float]:
        """Fetch BTC funding rate (8h) from Binance."""
        try:
            import requests
            resp = requests.get(
                "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1",
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            if data:
                return float(data[0]["fundingRate"])
        except Exception as e:
            logger.warning(f"Failed to fetch funding rate: {e}")
        return None

    @staticmethod
    def _fetch_btc_dominance() -> Optional[float]:
        """Fetch BTC dominance % from CoinGecko."""
        try:
            import requests
            resp = requests.get(
                "https://api.coingecko.com/api/v3/global",
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            if "data" in data:
                return data["data"].get("btc_market_cap_percentage", 50.0)
        except Exception as e:
            logger.warning(f"Failed to fetch BTC dominance: {e}")
        return None
