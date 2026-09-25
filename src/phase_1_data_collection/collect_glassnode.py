#!/usr/bin/env python3
"""
Glassnode On-Chain Metrics Collector for IGWT-PF26 Phase 1

Collects on-chain metrics from Glassnode API:
- active_addresses: Daily unique addresses
- total_transfers: Daily transaction count
- exchange_inflow/outflow: Exchange flow data

Timeline: Oct 11-12, 2026
Requires: Glassnode API key (env: GLASSNODE_API_KEY)
"""

import os
import sys
import json
import time
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from pathlib import Path
import requests
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

# Configuration
GLASSNODE_API_URL = "https://api.glassnode.com/v1"
GLASSNODE_API_KEY = os.getenv("GLASSNODE_API_KEY")
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "phase_1"
MANIFEST_DIR = DATA_DIR / "manifests"
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_1"

# Setup logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"glassnode_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Major coins to collect on-chain data for
MAJOR_COINS = [
    ("bitcoin", "btc"),
    ("ethereum", "eth"),
    ("ripple", "xrp"),
    ("cardano", "ada"),
    ("solana", "sol"),
    ("polkadot", "dot"),
    ("litecoin", "ltc"),
    ("dogecoin", "doge"),
    ("avalanche-2", "avax"),
    ("polygon", "matic"),
]


class GlassnodeCollector:
    def __init__(self, api_key: str = GLASSNODE_API_KEY, data_dir=DATA_DIR):
        if not api_key:
            raise ValueError("GLASSNODE_API_KEY environment variable not set")

        self.api_key = api_key
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_dir = self.data_dir / "manifests"
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": self.api_key})
        self.collected_metrics = []
        self.failed_metrics = []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_metric(self, asset: str, metric: str, start_date: datetime, end_date: datetime) -> Tuple[pd.DataFrame, bool]:
        """Fetch on-chain metric from Glassnode"""
        try:
            start_ts = int(start_date.timestamp())
            end_ts = int(end_date.timestamp())

            response = self.session.get(
                f"{GLASSNODE_API_URL}/metrics/blockchain/{metric}",
                params={
                    "a": asset,
                    "s": start_ts,
                    "u": end_ts,
                    "resolution": "1d"
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if not data or "data" not in data:
                logger.warning(f"No data for {asset}/{metric}")
                return pd.DataFrame(), False

            # Parse data into DataFrame
            records = []
            for point in data["data"]:
                timestamp = datetime.fromtimestamp(point[0])
                value = point[1]
                if value is not None:
                    records.append({
                        "timestamp": timestamp,
                        metric: value
                    })

            if not records:
                logger.warning(f"No valid records for {asset}/{metric}")
                return pd.DataFrame(), False

            df = pd.DataFrame(records)
            df.set_index("timestamp", inplace=True)
            logger.info(f"✓ {asset}/{metric}: {len(df)} records")
            return df, True

        except Exception as e:
            logger.error(f"Failed to fetch {asset}/{metric}: {str(e)}")
            return pd.DataFrame(), False

    def collect_all(self):
        """Collect on-chain metrics for major coins"""
        logger.info("Starting Glassnode on-chain metrics collection...")

        start_date = datetime(2020, 1, 1)
        end_date = datetime.now()

        metrics = [
            "active_addresses",
            "transaction_count_all",
            "exchange_inflow",
            "exchange_outflow"
        ]

        for coin_name, coin_symbol in MAJOR_COINS:
            logger.info(f"Collecting metrics for {coin_name.upper()}...")

            coin_data = {}
            for metric in metrics:
                df, success = self.fetch_metric(coin_name, metric, start_date, end_date)
                if success:
                    coin_data[metric] = df
                    time.sleep(0.5)  # Rate limiting

            if coin_data:
                # Merge all metrics
                merged_df = pd.concat(coin_data.values(), axis=1)

                # Save to Parquet
                output_file = self.data_dir / f"{coin_symbol}_onchain.parquet"
                merged_df.to_parquet(output_file)

                self.collected_metrics.append({
                    "symbol": coin_symbol,
                    "name": coin_name,
                    "records": len(merged_df),
                    "metrics": list(coin_data.keys()),
                    "file": str(output_file)
                })
                logger.info(f"✓ Saved {coin_symbol}_onchain.parquet ({len(merged_df)} rows)")
            else:
                self.failed_metrics.append({
                    "symbol": coin_symbol,
                    "name": coin_name,
                    "reason": "All metrics failed"
                })
                logger.error(f"✗ Failed to collect metrics for {coin_name}")

        logger.info(f"Collection complete!")
        logger.info(f"  Collected: {len(self.collected_metrics)} coins")
        logger.info(f"  Failed: {len(self.failed_metrics)} coins")

        return self.create_manifest()

    def create_manifest(self) -> Dict:
        """Create SHA256 manifest of collected data"""
        logger.info("Creating Glassnode manifest...")

        manifest = {
            "timestamp": datetime.now().isoformat(),
            "phase": "1_data_audit",
            "source": "Glassnode",
            "data_type": "on_chain_metrics",
            "collected": {
                "count": len(self.collected_metrics),
                "coins": self.collected_metrics
            },
            "failed": {
                "count": len(self.failed_metrics),
                "coins": self.failed_metrics
            },
            "files": {}
        }

        # Calculate SHA256 for each file
        for coin_file in self.data_dir.glob("*_onchain.parquet"):
            sha256_hash = hashlib.sha256()
            with open(coin_file, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            manifest["files"][coin_file.name] = {
                "sha256": sha256_hash.hexdigest(),
                "size_bytes": coin_file.stat().st_size
            }

        # Save manifest
        manifest_file = self.manifest_dir / f"glassnode_manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Manifest saved to {manifest_file}")
        return manifest


if __name__ == "__main__":
    if not GLASSNODE_API_KEY:
        logger.error("GLASSNODE_API_KEY not set. Set via: export GLASSNODE_API_KEY=<key>")
        sys.exit(1)

    collector = GlassnodeCollector()
    manifest = collector.collect_all()

    sys.exit(0)
