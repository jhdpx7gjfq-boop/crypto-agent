"""Phase 1: Real Data Loader (CoinGecko fallback).

Replaces mock data in Phase1DataCollector with real OHLCV from CoinGecko API.
Uses free, public API endpoint (no authentication required).
Alternative to Binance when proxy blocks access.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
import time

logger = logging.getLogger(__name__)


class Phase1RealDataLoader:
    """Load real OHLCV data from CoinGecko API (fallback when Binance blocked)."""

    COINGECKO_BASE = "https://api.coingecko.com/api/v3"

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.session = requests.Session()
        self.data_loaded: Dict[str, Dict[str, Any]] = {}

    def load_btc_real(
        self,
        days: int = 180,
        vs_currency: str = "usd",
    ) -> Dict[str, Any]:
        """
        Load real BTC OHLCV data from CoinGecko.

        Args:
            days: Historical days to fetch (max ~365 from free API)
            vs_currency: Target currency (usd, eur, gbp, etc.)

        Returns:
            Dict with OHLCV arrays and metadata
        """
        return self.load_real(
            coin_id="bitcoin",
            asset="BTC",
            days=days,
            vs_currency=vs_currency,
        )

    def load_eth_real(
        self,
        days: int = 180,
        vs_currency: str = "usd",
    ) -> Dict[str, Any]:
        """Load real ETH OHLCV data from CoinGecko."""
        return self.load_real(
            coin_id="ethereum",
            asset="ETH",
            days=days,
            vs_currency=vs_currency,
        )

    def load_real(
        self,
        coin_id: str = "bitcoin",
        asset: str = "BTC",
        days: int = 180,
        vs_currency: str = "usd",
    ) -> Dict[str, Any]:
        """
        Load real OHLCV from CoinGecko market_chart endpoint.

        Endpoint: /coins/{id}/market_chart
        Returns: [timestamp, open, high, low, close, volume]
        """
        logger.info(f"Loading {asset} real data from CoinGecko (free API)")
        logger.info(f"  Coin ID: {coin_id}, Days: {days}")

        try:
            # Fetch market chart with OHLC data
            url = f"{self.COINGECKO_BASE}/coins/{coin_id}/market_chart"
            params = {
                "vs_currency": vs_currency,
                "days": min(days, 365),  # Free API limited to ~365 days
                "interval": "daily",  # Get daily candles
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            time.sleep(1)  # Rate limit to avoid 429

            data = response.json()

            # Extract OHLC data
            candles = []
            prices = data.get("prices", [])
            market_caps = data.get("market_caps", [])
            volumes = data.get("volumes", [])

            logger.info(f"  ✓ Fetched {len(prices)} daily candles from CoinGecko")

            # Build OHLCV records
            # Note: CoinGecko prices endpoint gives [timestamp, price] but NOT open/high/low/close
            # So we'll use price as close proxy and mark as real source
            for i, (ts, close_price) in enumerate(prices):
                timestamp_ms = int(ts)

                # Estimate OHLC (not ideal, but honest about the limitation)
                # In real usage: use binance_real_collector.py instead
                candle = {
                    "timestamp_ms": timestamp_ms,
                    "open": close_price,      # Close price as proxy
                    "high": close_price,
                    "low": close_price,
                    "close": close_price,
                    "volume": volumes[i][1] if i < len(volumes) else 0,
                    "quote_asset_volume": 0,
                    "number_of_trades": 0,
                    "source": "coingecko",    # Mark real source
                    "is_real_data": True,     # Explicit real flag
                    "note": "Price proxied as OHLC (use Binance for real OHLCV)",
                }
                candles.append(candle)

            # Validate
            self._validate_real_data(asset, candles)

            # Store
            self.data_loaded[asset] = {
                "asset": asset,
                "source": "coingecko",
                "is_real_data": True,
                "candles": candles,
                "count": len(candles),
                "date_range": {
                    "first": datetime.utcfromtimestamp(candles[0]["timestamp_ms"] / 1000).isoformat(),
                    "last": datetime.utcfromtimestamp(candles[-1]["timestamp_ms"] / 1000).isoformat(),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(f"  ✓ Loaded {len(candles)} real {asset} candles")
            logger.info(f"    Date range: {self.data_loaded[asset]['date_range']['first']} → {self.data_loaded[asset]['date_range']['last']}")

            return self.data_loaded[asset]

        except requests.RequestException as e:
            logger.error(f"Failed to load real data: {e}")
            raise

    @staticmethod
    def _validate_real_data(asset: str, candles: List[Dict]) -> None:
        """Validate real OHLCV integrity."""
        if not candles:
            logger.warning(f"  ⚠ No candles loaded for {asset}")
            return

        issues = []

        for i, candle in enumerate(candles):
            # Check timestamps are monotonic
            if i > 0:
                prev_ts = candles[i - 1]["timestamp_ms"]
                curr_ts = candle["timestamp_ms"]
                if curr_ts <= prev_ts:
                    issues.append(f"  Row {i}: timestamp not monotonic ({curr_ts} ≤ {prev_ts})")

            # Check OHLC fields exist
            for field in ["open", "high", "low", "close"]:
                if field not in candle:
                    issues.append(f"  Row {i}: missing field '{field}'")

            # Check price >= 0
            if candle.get("close", 0) <= 0:
                issues.append(f"  Row {i}: invalid price {candle.get('close')}")

        if issues:
            logger.warning(f"Data quality issues ({len(issues)}):")
            for issue in issues[:5]:
                logger.warning(issue)
            if len(issues) > 5:
                logger.warning(f"  ... and {len(issues) - 5} more")
        else:
            logger.info(f"  ✓ Data validation passed ({len(candles)} candles, all real)")

    def export_json(self, asset: str, filepath: str) -> None:
        """Export real data to JSON."""
        if asset not in self.data_loaded:
            logger.error(f"No data for {asset}")
            return

        with open(filepath, "w") as f:
            json.dump(self.data_loaded[asset], f, indent=2)
        logger.info(f"  ✓ Exported {asset} to {filepath}")

    def summary(self) -> Dict[str, Any]:
        """Return loaded data summary."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "source": "coingecko",
            "is_real_data": True,
            "assets_loaded": list(self.data_loaded.keys()),
            "total_candles": sum(d["count"] for d in self.data_loaded.values()),
            "candles_by_asset": {
                asset: data["count"] for asset, data in self.data_loaded.items()
            },
        }


def main():
    """Test real data loading."""
    logging.basicConfig(level=logging.INFO)

    loader = Phase1RealDataLoader()

    print("\n" + "="*70)
    print("PHASE 1: REAL DATA LOADER TEST (CoinGecko Fallback)")
    print("="*70 + "\n")

    try:
        print("Loading BTC real data (180 days)...\n")
        btc_data = loader.load_btc_real(days=180)

        print(f"✓ Loaded {btc_data['count']} BTC candles")
        print(f"  Date range: {btc_data['date_range']['first']} → {btc_data['date_range']['last']}")
        print(f"  Source: {btc_data['source']}")
        print(f"  Is Real Data: {btc_data['is_real_data']}\n")

        print("Loading ETH real data (180 days)...\n")
        eth_data = loader.load_eth_real(days=180)

        print(f"✓ Loaded {eth_data['count']} ETH candles")
        print(f"  Date range: {eth_data['date_range']['first']} → {eth_data['date_range']['last']}")
        print(f"  Source: {eth_data['source']}")
        print(f"  Is Real Data: {eth_data['is_real_data']}\n")

        # Export
        loader.export_json("BTC", "/tmp/btc_real_coingecko.json")
        loader.export_json("ETH", "/tmp/eth_real_coingecko.json")

        # Summary
        print("-"*70)
        print("Real Data Loading Summary")
        print("-"*70)
        summary = loader.summary()
        print(f"  Source: {summary['source']}")
        print(f"  Is Real Data: {summary['is_real_data']}")
        print(f"  Total Candles: {summary['total_candles']}")
        print(f"  Assets: {summary['assets_loaded']}")
        print("="*70 + "\n")

    except Exception as e:
        logger.error(f"Real data loading failed: {e}")
        raise


if __name__ == "__main__":
    main()
