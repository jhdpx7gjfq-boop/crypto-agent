#!/usr/bin/env python3
"""
CoinGecko OHLCV Data Collector for IGWT-PF26 Phase 1

Collects daily OHLCV data from CoinGecko API for 3,421+ coins.
- Handles rate limiting (100 req/min)
- Logs all failures with metadata
- Creates SHA256 manifest
- Stores in Parquet format

Timeline: Oct 9-12, 2026
Target: 3,400/3,421 coins (21 failures acceptable)
"""

import os
import sys
import json
import time
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path
import requests
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

# Configuration
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
RATE_LIMIT = 100  # req/min
RATE_LIMIT_DELAY = 60 / RATE_LIMIT  # 0.6 seconds per request
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "phase_1"
MANIFEST_DIR = DATA_DIR / "manifests"
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_1"

# Setup logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"coingecko_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class CoinGeckoCollector:
    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_dir = self.data_dir / "manifests"
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.failed_coins = []
        self.collected_coins = []
        self.request_count = 0
        self.last_request_time = 0

    def rate_limit(self):
        """Enforce rate limiting (100 req/min)"""
        elapsed = time.time() - self.last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()
        self.request_count += 1

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_coin_list(self) -> List[Dict]:
        """Fetch list of all coins from CoinGecko"""
        logger.info("Fetching coin list from CoinGecko...")
        self.rate_limit()
        response = self.session.get(
            f"{COINGECKO_API_URL}/coins/list",
            params={"order": "market_cap_desc", "per_page": 250, "page": 1}
        )
        response.raise_for_status()
        coins = response.json()
        logger.info(f"Retrieved {len(coins)} coins from first page")

        # Paginate through all coins
        page = 2
        while len(response.json()) == 250:
            self.rate_limit()
            response = self.session.get(
                f"{COINGECKO_API_URL}/coins/list",
                params={"order": "market_cap_desc", "per_page": 250, "page": page}
            )
            response.raise_for_status()
            page_coins = response.json()
            coins.extend(page_coins)
            logger.info(f"Page {page}: Retrieved {len(page_coins)} coins (total: {len(coins)})")
            page += 1

        logger.info(f"Total coins available: {len(coins)}")
        return coins

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_ohlcv(self, coin_id: str, days: int = 2100) -> Tuple[pd.DataFrame, bool]:
        """Fetch OHLCV data for a coin (2020-2026, ~6 years)"""
        try:
            self.rate_limit()
            response = self.session.get(
                f"{COINGECKO_API_URL}/coins/{coin_id}/market_chart",
                params={
                    "vs_currency": "usd",
                    "days": days,
                    "interval": "daily"
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            # Parse OHLCV data
            ohlcv_data = []
            prices = data.get("prices", [])

            for price_point in prices:
                timestamp_ms, price = price_point
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
                # Note: CoinGecko market_chart returns close prices, we'll fill OHLC with close
                ohlcv_data.append({
                    "timestamp": timestamp,
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": 0  # CoinGecko market_chart doesn't include volume in this endpoint
                })

            if not ohlcv_data:
                logger.warning(f"No OHLCV data for {coin_id}")
                return pd.DataFrame(), False

            df = pd.DataFrame(ohlcv_data)
            df.set_index("timestamp", inplace=True)
            logger.debug(f"Collected {len(df)} candles for {coin_id}")
            return df, True

        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {coin_id}: {str(e)}")
            return pd.DataFrame(), False

    def collect_all(self, max_coins: int = 3421, start_page: int = 1):
        """Collect OHLCV data for all coins"""
        logger.info(f"Starting data collection for up to {max_coins} coins...")

        coins = self.fetch_coin_list()
        coins_to_collect = coins[:max_coins]

        collection_start = datetime.now()

        for i, coin in enumerate(coins_to_collect, 1):
            coin_id = coin["id"]
            coin_symbol = coin["symbol"].upper()

            if i % 100 == 0:
                logger.info(f"Progress: {i}/{len(coins_to_collect)} ({100*i/len(coins_to_collect):.1f}%)")

            df, success = self.fetch_ohlcv(coin_id)

            if success and not df.empty:
                # Save to Parquet
                output_file = self.data_dir / f"{coin_symbol}_{coin_id}.parquet"
                df.to_parquet(output_file)
                self.collected_coins.append({
                    "id": coin_id,
                    "symbol": coin_symbol,
                    "records": len(df),
                    "file": str(output_file)
                })
            else:
                self.failed_coins.append({
                    "id": coin_id,
                    "symbol": coin_symbol,
                    "reason": "API error or no data"
                })

        collection_end = datetime.now()
        duration = (collection_end - collection_start).total_seconds()

        logger.info(f"Collection complete!")
        logger.info(f"  Collected: {len(self.collected_coins)} coins")
        logger.info(f"  Failed: {len(self.failed_coins)} coins")
        logger.info(f"  Duration: {duration:.1f} seconds")
        logger.info(f"  Rate: {len(self.collected_coins) / (duration/60):.1f} coins/min")

        return self.create_manifest()

    def create_manifest(self) -> Dict:
        """Create SHA256 manifest of collected data"""
        logger.info("Creating manifest...")

        manifest = {
            "timestamp": datetime.now().isoformat(),
            "phase": "1_data_audit",
            "source": "CoinGecko",
            "rate_limit": RATE_LIMIT,
            "total_requests": self.request_count,
            "collected": {
                "count": len(self.collected_coins),
                "coins": self.collected_coins
            },
            "failed": {
                "count": len(self.failed_coins),
                "coins": self.failed_coins
            },
            "files": {}
        }

        # Calculate SHA256 for each file
        for coin_file in self.data_dir.glob("*.parquet"):
            sha256_hash = hashlib.sha256()
            with open(coin_file, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            manifest["files"][coin_file.name] = {
                "sha256": sha256_hash.hexdigest(),
                "size_bytes": coin_file.stat().st_size
            }

        # Save manifest
        manifest_file = self.manifest_dir / f"coingecko_manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Manifest saved to {manifest_file}")
        return manifest

    def verify_manifest(self, manifest_file: Path) -> bool:
        """Verify all files in manifest match expected SHA256"""
        logger.info(f"Verifying manifest: {manifest_file}")

        with open(manifest_file, "r") as f:
            manifest = json.load(f)

        all_valid = True
        for filename, file_info in manifest["files"].items():
            filepath = self.data_dir / filename
            if not filepath.exists():
                logger.error(f"Missing file: {filename}")
                all_valid = False
                continue

            sha256_hash = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)

            actual_sha256 = sha256_hash.hexdigest()
            expected_sha256 = file_info["sha256"]

            if actual_sha256 != expected_sha256:
                logger.error(f"SHA256 mismatch for {filename}")
                logger.error(f"  Expected: {expected_sha256}")
                logger.error(f"  Actual:   {actual_sha256}")
                all_valid = False
            else:
                logger.debug(f"✓ {filename}")

        if all_valid:
            logger.info("✓ All files verified")
        else:
            logger.error("✗ Verification failed")

        return all_valid


if __name__ == "__main__":
    collector = CoinGeckoCollector()

    # Collect data
    manifest = collector.collect_all(max_coins=3421)

    # Verify
    manifest_file = list(collector.manifest_dir.glob("coingecko_manifest_*.json"))[-1]
    is_valid = collector.verify_manifest(manifest_file)

    sys.exit(0 if is_valid else 1)
