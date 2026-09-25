#!/usr/bin/env python3
"""
Fetch 730 daily OHLCV candles for B-004 validation.

Run locally (non-cloud environment) with unrestricted internet access.
Uses Binance public API (free, no authentication required).

Usage:
    python scripts/fetch_daily_ohlcv_local.py

Output:
    ./real_market_data/{SYMBOL}_daily_730d.json (one file per symbol)

Requirements:
    - requests library: pip install requests
    - Network access to api.binance.com (not blocked by proxy)
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DailyOHLCVFetcher:
    """Fetch daily OHLCV candles from Binance."""

    BINANCE_API = "https://api.binance.com/api/v3/klines"
    TIMEOUT = 10
    SYMBOLS = ["BTC", "ETH", "SOL", "AVAX"]
    CANDLES_PER_SYMBOL = 730

    def __init__(self, output_dir: str = "./real_market_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        logger.info(f"Output directory: {self.output_dir}")

    def fetch_binance_daily(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch 730 daily candles from Binance for a symbol.

        Args:
            symbol: Trading pair (e.g., "BTC")

        Returns:
            List of OHLCV candles or None if fetch failed
        """
        pair = f"{symbol}USDT"
        logger.info(f"Fetching {self.CANDLES_PER_SYMBOL} daily candles for {pair}...")

        try:
            response = requests.get(
                self.BINANCE_API,
                params={
                    "symbol": pair,
                    "interval": "1d",
                    "limit": self.CANDLES_PER_SYMBOL,
                },
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            if not data:
                logger.warning(f"  No data returned for {pair}")
                return None

            candles = []
            for candle in data:
                # Binance format: [timestamp, open, high, low, close, volume, ...]
                candles.append({
                    "timestamp": int(candle[0]) // 1000,  # Convert to seconds
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[7]),  # Quote asset volume (USDT)
                })

            logger.info(f"  ✅ Fetched {len(candles)} candles for {pair}")
            return candles

        except requests.exceptions.RequestException as e:
            logger.error(f"  ❌ Failed to fetch {pair}: {e}")
            return None

    def validate_candles(self, candles: List[Dict], symbol: str) -> bool:
        """Validate fetched candles for data quality."""
        if not candles:
            logger.warning(f"{symbol}: Empty candle list")
            return False

        if len(candles) < 730:
            logger.warning(f"{symbol}: Only {len(candles)} candles (need 730)")
            return False

        # Check daily granularity (86400 seconds = 1 day)
        for i in range(1, len(candles)):
            ts_diff = candles[i]["timestamp"] - candles[i - 1]["timestamp"]
            if abs(ts_diff - 86400) > 60:  # Allow 60 sec tolerance
                logger.warning(
                    f"{symbol}: Non-daily granularity at index {i} "
                    f"(diff={ts_diff} seconds)"
                )
                return False

        # Check price sanity
        for i, candle in enumerate(candles):
            if candle["high"] < candle["low"]:
                logger.warning(f"{symbol}: High < Low at candle {i}")
                return False
            if candle["close"] < 0 or candle["volume"] <= 0:
                logger.warning(f"{symbol}: Invalid close/volume at candle {i}")
                return False

        logger.info(f"{symbol}: ✅ Validation passed ({len(candles)} candles)")
        return True

    def save_candles(self, candles: List[Dict], symbol: str) -> Path:
        """Save candles to JSON file."""
        output_file = self.output_dir / f"{symbol}_daily_730d.json"

        # Create metadata
        data = {
            "symbol": symbol,
            "source": "Binance Public API (api.binance.com)",
            "interval": "1d",
            "candles_count": len(candles),
            "date_range": f"{self._format_timestamp(candles[0]['timestamp'])} to {self._format_timestamp(candles[-1]['timestamp'])}",
            "fetch_timestamp": self._format_timestamp(int(__import__('time').time())),
            "candles": candles,
        }

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {output_file}")
        return output_file

    def _format_timestamp(self, ts: int) -> str:
        """Format Unix timestamp as ISO date."""
        from datetime import datetime
        return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")

    def run(self) -> bool:
        """Fetch and save daily OHLCV for all symbols."""
        logger.info("=" * 60)
        logger.info("DAILY OHLCV FETCHER FOR B-004 VALIDATION")
        logger.info("=" * 60)

        all_success = True

        for symbol in self.SYMBOLS:
            logger.info(f"\n[{symbol}]")

            # Fetch
            candles = self.fetch_binance_daily(symbol)
            if candles is None:
                all_success = False
                continue

            # Validate
            if not self.validate_candles(candles, symbol):
                all_success = False
                continue

            # Save
            try:
                self.save_candles(candles, symbol)
            except Exception as e:
                logger.error(f"Failed to save {symbol}: {e}")
                all_success = False

        logger.info("\n" + "=" * 60)
        if all_success:
            logger.info("✅ ALL SYMBOLS FETCHED SUCCESSFULLY")
            logger.info("\nNext step: Run B-004 validation")
            logger.info("  cd /home/user/crypto-agent")
            logger.info("  python b004_wfv.py")
        else:
            logger.error("❌ Some symbols failed. Check errors above.")

        logger.info("=" * 60)
        return all_success


if __name__ == "__main__":
    fetcher = DailyOHLCVFetcher()
    success = fetcher.run()
    sys.exit(0 if success else 1)
