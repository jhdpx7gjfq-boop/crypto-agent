#!/usr/bin/env python3
"""Fetch 730 days of daily OHLCV from Binance for RRP validation."""

import logging
from real_data_collector import RealDataCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Symbol mapping: Crypto symbol → Binance trading pair
BINANCE_PAIRS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "AVAX": "AVAXUSDT",
}

def main():
    collector = RealDataCollector(output_dir="./real_market_data")

    logger.info("="*60)
    logger.info("Fetching 730 days of daily OHLCV from Binance")
    logger.info("="*60)

    for symbol, binance_pair in BINANCE_PAIRS.items():
        logger.info(f"\nFetching {symbol} ({binance_pair})...")

        # Fetch 730 daily candles
        ohlcv = collector.fetch_binance_daily_ohlcv(
            symbol=binance_pair,
            days=730,
        )

        if ohlcv:
            # Save with provenance
            collector.save_dataset(
                ohlcv,
                symbol,
                "binance",
                {
                    "days": 730,
                    "source": "Binance public API (klines endpoint)",
                    "interval": "1d (daily)",
                    "pair": binance_pair,
                },
            )
            logger.info(f"✅ {symbol}: Saved {len(ohlcv)} daily candles")
        else:
            logger.error(f"❌ {symbol}: Failed to fetch data")

    logger.info("\n" + "="*60)
    logger.info("Data fetch complete. Ready for validation.")
    logger.info("="*60)

if __name__ == "__main__":
    main()
