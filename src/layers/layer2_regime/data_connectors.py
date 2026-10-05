"""
Layer 2: Data Connectors — Phase 2

Fetches real market data from external sources:
- CoinGecko: BTC dominance, prices (ETH, BTC)
- Binance Futures: Funding rates, open interest
- FRED/TradingView: Macro indicators (DXY, US10Y, CPI, M2)
- ETF flows: Morningstar (fallback: proxy from price/volume)

Status: Phase 2 (connector development)
PIT_STATUS: "UNVERIFIED" (sources are real, availability unvalidated)
Offline mode: Mock fallback for development
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ============================================================================
# CoinGecko Connector (BTC Dominance, Prices)
# ============================================================================

class CoinGeckoConnector:
    """
    Fetch BTC dominance, ETH/BTC prices from CoinGecko API.

    Proof Level: C (API historical with timestamp)
    Update Frequency: Daily
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self, use_mock: bool = False):
        """
        Initialize CoinGecko connector.

        Args:
            use_mock: If True, return mock data (for offline development)
        """
        self.use_mock = use_mock
        self.session = None

    def get_global_data(self) -> Dict[str, Any]:
        """
        Fetch global market data (BTC dominance).

        Returns:
            {
                "btc_dominance": float (%)
                "eth_dominance": float (%)
                "market_cap_change_24h": float (%)
                "timestamp": str (ISO 8601)
            }
        """
        if self.use_mock:
            return self._mock_global_data()

        try:
            import requests
            url = f"{self.BASE_URL}/global"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            return {
                "btc_dominance": data.get("data", {}).get("btc_market_cap_percentage", 50.0),
                "eth_dominance": data.get("data", {}).get("eth_market_cap_percentage", 15.0),
                "market_cap_change_24h": data.get("data", {}).get("market_cap_change_percentage_24h_usd", 0.0),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        except Exception as e:
            logger.error(f"CoinGecko global data fetch failed: {e}")
            return self._mock_global_data()

    def get_coin_history(self, coin_id: str, date: str) -> Optional[Dict[str, float]]:
        """
        Fetch historical price for a coin on a specific date.

        Args:
            coin_id: CoinGecko coin ID (e.g., "bitcoin", "ethereum")
            date: Date in YYYY-MM-DD format

        Returns:
            {
                "price": float (USD),
                "market_cap": float (USD),
                "volume": float (USD),
            }
        """
        if self.use_mock:
            return self._mock_coin_history(coin_id, date)

        try:
            import requests
            url = f"{self.BASE_URL}/coins/{coin_id}/history"
            params = {"date": date, "localization": "false"}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            market_data = data.get("market_data", {})

            return {
                "price": market_data.get("current_price", {}).get("usd", 0.0),
                "market_cap": market_data.get("market_cap", {}).get("usd", 0.0),
                "volume": market_data.get("total_volume", {}).get("usd", 0.0),
            }
        except Exception as e:
            logger.error(f"CoinGecko history fetch failed for {coin_id} on {date}: {e}")
            return self._mock_coin_history(coin_id, date)

    @staticmethod
    def _mock_global_data() -> Dict[str, Any]:
        """Mock global market data for offline development."""
        return {
            "btc_dominance": 50.5,
            "eth_dominance": 16.2,
            "market_cap_change_24h": 2.3,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    @staticmethod
    def _mock_coin_history(coin_id: str, date: str) -> Dict[str, float]:
        """Mock coin history for offline development."""
        mock_prices = {
            "bitcoin": 42000.0,
            "ethereum": 2500.0,
            "solana": 150.0,
        }
        return {
            "price": mock_prices.get(coin_id, 1000.0),
            "market_cap": mock_prices.get(coin_id, 1000.0) * 1_000_000,
            "volume": mock_prices.get(coin_id, 1000.0) * 100_000,
        }


# ============================================================================
# Binance Futures Connector (Funding Rates, Open Interest)
# ============================================================================

class BinanceFuturesConnector:
    """
    Fetch funding rates and open interest from Binance Futures API.

    Proof Level: C (futures data real-time, some revision possible)
    Update Frequency: 8-hourly, aggregated daily
    Note: Historical funding rates difficult to obtain; backtest uses proxy (volatility)
    """

    BASE_URL = "https://fapi.binance.com/fapi/v1"

    def __init__(self, use_mock: bool = False):
        """
        Initialize Binance Futures connector.

        Args:
            use_mock: If True, return mock data (for offline development)
        """
        self.use_mock = use_mock

    def get_funding_rate(self, symbol: str = "BTCUSDT") -> Optional[Dict[str, float]]:
        """
        Fetch current and average funding rate.

        Args:
            symbol: Binance futures symbol (e.g., "BTCUSDT")

        Returns:
            {
                "funding_rate_8h": float (%),
                "funding_rate_moving_avg_7d": float (%),
            }
        """
        if self.use_mock:
            return self._mock_funding_rate()

        try:
            import requests
            url = f"{self.BASE_URL}/fundingRate"
            params = {"symbol": symbol, "limit": 56}  # 7 days * 8h intervals
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            rates = response.json()
            if not rates:
                return self._mock_funding_rate()

            current = float(rates[0].get("fundingRate", 0.0)) * 100
            avg = sum(float(r.get("fundingRate", 0.0)) for r in rates) / len(rates) * 100

            return {
                "funding_rate_8h": current,
                "funding_rate_moving_avg_7d": avg,
            }
        except Exception as e:
            logger.error(f"Binance funding rate fetch failed: {e}")
            return self._mock_funding_rate()

    def get_open_interest(self, symbol: str = "BTCUSDT") -> Optional[Dict[str, float]]:
        """
        Fetch open interest and positioning.

        Args:
            symbol: Binance futures symbol

        Returns:
            {
                "open_interest_usd": float,
                "open_interest_change_24h": float (%),
                "longs_ratio": float (0-1),
            }
        """
        if self.use_mock:
            return self._mock_open_interest()

        try:
            import requests
            url = f"{self.BASE_URL}/openInterest"
            params = {"symbol": symbol}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            oi = response.json()
            return {
                "open_interest_usd": float(oi.get("openInterest", 0.0)),
                "open_interest_change_24h": 0.0,  # Would require historical comparison
                "longs_ratio": 0.5,  # Would require long/short ratio endpoint
            }
        except Exception as e:
            logger.error(f"Binance open interest fetch failed: {e}")
            return self._mock_open_interest()

    @staticmethod
    def _mock_funding_rate() -> Dict[str, float]:
        """Mock funding rate data for offline development."""
        return {
            "funding_rate_8h": 0.03,
            "funding_rate_moving_avg_7d": 0.02,
        }

    @staticmethod
    def _mock_open_interest() -> Dict[str, float]:
        """Mock open interest data for offline development."""
        return {
            "open_interest_usd": 10_000_000_000.0,
            "open_interest_change_24h": 5.0,
            "longs_ratio": 0.55,
        }


# ============================================================================
# Macro Indicators Connector (DXY, US10Y, CPI, M2)
# ============================================================================

class MacroConnector:
    """
    Fetch macro indicators from FRED (Federal Reserve Economic Data).

    Proof Level: A (published by central banks, versioned releases)
    Update Frequency: Monthly (CPI, M2), Daily (DXY, US10Y)
    Latency: CPI lag ~10 days; M2 data typically 1 week old

    Note: This is a mock implementation. Real connector would use FRED API or TradingView.
    """

    def __init__(self, use_mock: bool = True):
        """
        Initialize Macro connector.

        Args:
            use_mock: If True, return mock data (FRED API not integrated yet)
        """
        self.use_mock = use_mock

    def get_macro_indicators(self) -> Dict[str, float]:
        """
        Fetch current macro indicators.

        Returns:
            {
                "dxy": float (US Dollar Index),
                "us10y": float (% yield),
                "cpi_yoy": float (% change),
                "m2_growth_yoy": float (% change),
            }
        """
        if self.use_mock:
            return self._mock_macro_indicators()

        # Placeholder: Real implementation would call FRED API
        logger.warning("Macro connector using mock data (FRED API not integrated)")
        return self._mock_macro_indicators()

    @staticmethod
    def _mock_macro_indicators() -> Dict[str, float]:
        """Mock macro data for offline development."""
        return {
            "dxy": 103.5,
            "us10y": 4.0,
            "cpi_yoy": 2.8,
            "m2_growth_yoy": 3.5,
        }


# ============================================================================
# Data Aggregator (All Connectors)
# ============================================================================

class RegimeDataCollector:
    """
    Aggregates data from all connectors for regime calculation.

    Automatically falls back to mock data if real sources fail.
    """

    def __init__(self, use_mock: bool = False):
        """
        Initialize data collector.

        Args:
            use_mock: Force mock data for all connectors
        """
        self.cg = CoinGeckoConnector(use_mock=use_mock)
        self.binance = BinanceFuturesConnector(use_mock=use_mock)
        self.macro = MacroConnector(use_mock=use_mock)

    def collect_regime_data(self) -> Dict[str, Any]:
        """
        Collect all data needed for regime calculation.

        Returns:
            Dict with keys: timestamp, btc_dom, sma20_dom, sma60_dom,
            funding_rate, funding_avg, oi_change, btc_spy_corr, vtix,
            eth_btc, dxy, us10y, cpi, m2, spy_flow, gld_flow, oi_shorts
        """
        global_data = self.cg.get_global_data()
        binance_data = self.binance.get_funding_rate()
        macro_data = self.macro.get_macro_indicators()

        # Note: Some indicators (SMA, SPY correlation, VIX, ETF flows) require
        # time-series data or external APIs not yet integrated.
        # For Phase 2, using placeholder values.

        return {
            "timestamp": global_data.get("timestamp"),
            "btc_dom": global_data.get("btc_dominance", 50.0),
            "sma20_dom": 49.5,  # TODO: Compute from historical data
            "sma60_dom": 49.0,  # TODO: Compute from historical data
            "funding_rate": binance_data.get("funding_rate_8h", 0.0) / 100,
            "funding_avg": binance_data.get("funding_rate_moving_avg_7d", 0.0) / 100,
            "oi_change": 0.0,  # TODO: Fetch from Binance historical
            "btc_spy_corr": 0.5,  # TODO: Compute from price correlation
            "vtix": 20.0,  # TODO: Fetch from TradingView/TipRanks
            "eth_btc": 0.045,  # TODO: Compute from prices
            "dxy": macro_data.get("dxy", 103.0),
            "us10y": macro_data.get("us10y", 4.0),
            "cpi": macro_data.get("cpi_yoy", 2.5),
            "m2": macro_data.get("m2_growth_yoy", 3.0),
            "spy_flow": 0.0,  # TODO: Fetch from Morningstar/ETF.com
            "gld_flow": 0.0,  # TODO: Fetch from Morningstar/ETF.com
            "oi_shorts": 0.5,  # TODO: Fetch from Binance long/short ratio
        }
