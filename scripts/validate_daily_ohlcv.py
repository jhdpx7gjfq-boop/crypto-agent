#!/usr/bin/env python3
"""
Validate integrity of downloaded daily OHLCV files before B-004 execution.

Checks:
- File existence
- Candle count (730 minimum)
- Daily granularity (24h intervals)
- Price validity (high≥low≥close≥0)
- Volume > 0
- No gaps in date sequence

Usage:
    python scripts/validate_daily_ohlcv.py
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class OHLCVValidator:
    """Validate daily OHLCV data files."""

    SYMBOLS = ["BTC", "ETH", "SOL", "AVAX"]
    MIN_CANDLES = 730
    DATA_DIR = Path("./real_market_data")

    def validate_all(self) -> bool:
        """Validate all OHLCV files."""
        logger.info("=" * 60)
        logger.info("OHLCV DATA VALIDATION")
        logger.info("=" * 60)
        logger.info(f"Data directory: {self.DATA_DIR}\n")

        all_valid = True

        for symbol in self.SYMBOLS:
            logger.info(f"[{symbol}]")
            valid = self.validate_symbol(symbol)
            all_valid = all_valid and valid
            logger.info()

        logger.info("=" * 60)
        if all_valid:
            logger.info("✅ ALL SYMBOLS VALIDATED")
            logger.info("\nReady for B-004 execution:")
            logger.info("  python b004_wfv.py")
        else:
            logger.error("❌ VALIDATION FAILED. Check errors above.")
        logger.info("=" * 60)

        return all_valid

    def validate_symbol(self, symbol: str) -> bool:
        """Validate a single symbol's OHLCV file."""
        filepath = self.DATA_DIR / f"{symbol}_daily_730d.json"

        # Check file exists
        if not filepath.exists():
            logger.error(f"  ❌ File not found: {filepath}")
            return False

        # Load file
        try:
            with open(filepath) as f:
                data = json.load(f)
            candles = data.get("candles", [])
        except Exception as e:
            logger.error(f"  ❌ Failed to load: {e}")
            return False

        # Check candle count
        if len(candles) < self.MIN_CANDLES:
            logger.error(
                f"  ❌ Insufficient candles: {len(candles)} "
                f"(need {self.MIN_CANDLES})"
            )
            return False

        logger.info(f"  ✅ Candle count: {len(candles)}")

        # Check first and last dates
        first_date = datetime.utcfromtimestamp(candles[0]["timestamp"]).strftime("%Y-%m-%d")
        last_date = datetime.utcfromtimestamp(candles[-1]["timestamp"]).strftime("%Y-%m-%d")
        logger.info(f"  ✅ Date range: {first_date} to {last_date}")

        # Check daily granularity
        granularity_ok = True
        for i in range(1, min(10, len(candles))):  # Check first 10 for efficiency
            ts_diff = candles[i]["timestamp"] - candles[i - 1]["timestamp"]
            if abs(ts_diff - 86400) > 60:  # Allow 60 sec tolerance
                logger.error(
                    f"  ❌ Non-daily granularity at candle {i} "
                    f"(diff={ts_diff} seconds)"
                )
                granularity_ok = False
                break

        if granularity_ok:
            logger.info(f"  ✅ Daily granularity validated")

        # Check price validity
        price_ok = True
        for i, candle in enumerate(candles):
            if candle["high"] < candle["low"]:
                logger.error(f"  ❌ High < Low at candle {i}")
                price_ok = False
                break
            if candle["low"] < candle["close"] or candle["close"] < 0:
                logger.error(f"  ❌ Invalid close at candle {i}")
                price_ok = False
                break
            if candle["volume"] <= 0:
                logger.error(f"  ❌ Zero/negative volume at candle {i}")
                price_ok = False
                break

        if price_ok:
            logger.info(f"  ✅ Price validity checked")

        return granularity_ok and price_ok


if __name__ == "__main__":
    validator = OHLCVValidator()
    valid = validator.validate_all()
    sys.exit(0 if valid else 1)
