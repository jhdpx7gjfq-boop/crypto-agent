"""CoinDesk historical volume metrics collector.

POC for DATA-SRC-COINDESK-001 research candidate.
Fetch historical volume metrics (Top-Tier, Direct, Aggregate) from CoinDesk Data API.

Status: RESEARCH CANDIDATE — not yet WFV-admissible
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json

import pandas as pd

logger = logging.getLogger(__name__)


class CoinDeskHistoricalCollector:
    """
    Fetch historical volume metrics from CoinDesk REST API.

    Metrics:
    - volume_aggregate: Total volume across all venues
    - volume_top_tier: Volume from CoinDesk-classified top-tier exchanges
    - volume_direct: Non-aggregated volume
    """

    BASE_URL = "https://api.coindesk.com/v1"

    ASSET_IDS = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize collector.

        Args:
            api_key: CoinDesk Data API key (optional, some endpoints are public)
        """
        self.api_key = api_key
        self.session = None

    def fetch_volume_metrics(
        self,
        asset: str = "bitcoin",
        days: int = 365,
        vs_currency: str = "usd"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical volume metrics from CoinDesk.

        Args:
            asset: CoinGecko asset ID (e.g., 'bitcoin', 'ethereum')
            days: Number of historical days to fetch
            vs_currency: Quote currency (default USD)

        Returns:
            DataFrame with columns:
            - timestamp (datetime)
            - volume_aggregate (float)
            - volume_top_tier (float, if available)
            - volume_direct (float, if available)
            - ttcr (float): top_tier / aggregate ratio
            - bcr (float, placeholder): binance / aggregate ratio (fetch separately)

        Returns None if fetch fails.
        """

        try:
            import requests
        except ImportError:
            logger.error("requests library required")
            return None

        url = f"{self.BASE_URL}/coins/{asset}/market_chart"
        params = {
            "vs_currency": vs_currency,
            "days": days,
            "interval": "daily",
        }

        # Optional: add API key to header if available
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            # Parse response
            prices = data.get("prices", [])
            volumes = data.get("volumes", [])
            market_caps = data.get("market_caps", [])

            if not volumes or not prices:
                logger.warning(f"Incomplete data for {asset}")
                return None

            # Build DataFrame
            records = []
            for i, (timestamp_ms, volume) in enumerate(volumes):
                ts = datetime.fromtimestamp(timestamp_ms / 1000)

                record = {
                    "timestamp": ts,
                    "volume_aggregate": float(volume),
                }

                # Placeholder columns for top-tier and direct
                # (require DATA API key, not free tier)
                record["volume_top_tier"] = None
                record["volume_direct"] = None

                records.append(record)

            df = pd.DataFrame(records)

            # Calculate TTCR where available
            if df["volume_top_tier"].notna().any():
                df["ttcr"] = df["volume_top_tier"] / df["volume_aggregate"]
            else:
                df["ttcr"] = None

            logger.info(
                f"Fetched {len(df)} daily volume records for {asset}"
            )
            return df

        except requests.exceptions.RequestException as e:
            logger.error(f"CoinDesk fetch failed: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Data parsing failed: {e}")
            return None

    def fetch_binance_volume(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1d",
        days: int = 365
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical Binance spot volume (for BCR calculation).

        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Candle interval (default '1d')
            days: Number of historical days

        Returns:
            DataFrame with columns:
            - timestamp (datetime)
            - volume (float)
        """

        try:
            import requests
        except ImportError:
            logger.error("requests library required")
            return None

        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(days, 1000),
        }

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            klines = resp.json()

            records = []
            for kline in klines:
                ts = datetime.fromtimestamp(kline[0] / 1000)
                volume = float(kline[7])

                records.append({
                    "timestamp": ts,
                    "volume_binance": volume,
                })

            df = pd.DataFrame(records)
            logger.info(f"Fetched {len(df)} Binance candles for {symbol}")
            return df

        except requests.exceptions.RequestException as e:
            logger.error(f"Binance fetch failed: {e}")
            return None

    def calculate_bcr(
        self,
        coindesk_df: pd.DataFrame,
        binance_df: pd.DataFrame
    ) -> Optional[pd.DataFrame]:
        """
        Calculate Binance-CoinDesk Ratio (BCR).

        Args:
            coindesk_df: CoinDesk volume metrics
            binance_df: Binance volume metrics

        Returns:
            DataFrame with BCR column: binance_volume / coindesk_aggregate_volume
        """

        if coindesk_df is None or binance_df is None:
            return None

        # Merge on timestamp
        merged = pd.merge_asof(
            coindesk_df.sort_values("timestamp"),
            binance_df.sort_values("timestamp"),
            on="timestamp",
            direction="nearest"
        )

        merged["bcr"] = (
            merged["volume_binance"] / merged["volume_aggregate"]
        )

        logger.info(f"Calculated BCR for {len(merged)} days")
        return merged

    def save_to_parquet(
        self,
        df: pd.DataFrame,
        filepath: str
    ) -> bool:
        """Save DataFrame to Parquet (for data lineage)."""

        try:
            df.to_parquet(filepath, index=False)
            logger.info(f"Saved {len(df)} rows to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False


# POC gates check
class CoinDeskResearchGates:
    """Track POC validation gates."""

    @staticmethod
    def checkpoint_1_api_mapping() -> bool:
        """Gate 1: Verify API endpoint mapping."""
        try:
            from src.layers.layer1_data.coindesk_api_discovery import (
                CoinDeskAPIDiscovery
            )
            endpoints = CoinDeskAPIDiscovery.list_endpoints()
            volume_eps = CoinDeskAPIDiscovery.list_volume_endpoints()

            logger.info(f"Gate 1: API mapping — PASS ({len(endpoints)} endpoints, {len(volume_eps)} volume-related)")
            return len(volume_eps) > 0
        except Exception as e:
            logger.error(f"Gate 1: API mapping — FAIL ({e})")
            return False

    @staticmethod
    def checkpoint_2_historical_access() -> bool:
        """Gate 2: Verify historical data access & timestamps."""
        # TODO: Fetch 365 days for BTC, ETH, SOL
        logger.info("Gate 2: Historical access — NOT YET IMPLEMENTED")
        return False

    @staticmethod
    def checkpoint_3_pit_validation() -> bool:
        """Gate 3: Validate point-in-time semantics (revision detection)."""
        # TODO: Fetch same date 3x at intervals, compare
        logger.info("Gate 3: PIT validation — NOT YET IMPLEMENTED")
        return False

    @staticmethod
    def checkpoint_4_reference_dataset() -> bool:
        """Gate 4: Build reference dataset (12m, 3 assets)."""
        # TODO: Download and store BTC/ETH/SOL metrics
        logger.info("Gate 4: Reference dataset — NOT YET IMPLEMENTED")
        return False

    @staticmethod
    def checkpoint_5_cross_venue_validation() -> bool:
        """Gate 5: Cross-venue comparison (Binance vs CoinDesk)."""
        # TODO: Compare volumes, correlation, survivorship
        logger.info("Gate 5: Cross-venue validation — NOT YET IMPLEMENTED")
        return False

    @staticmethod
    def checkpoint_6_signal_quality() -> bool:
        """Gate 6: Signal quality assessment (TTCR, BCR alpha testing)."""
        # TODO: WFV-lite correlation analysis
        logger.info("Gate 6: Signal quality — NOT YET IMPLEMENTED")
        return False

    @staticmethod
    def all_gates_passed() -> bool:
        """Check if all validation gates are passed."""
        gates = [
            CoinDeskResearchGates.checkpoint_1_api_mapping(),
            CoinDeskResearchGates.checkpoint_2_historical_access(),
            CoinDeskResearchGates.checkpoint_3_pit_validation(),
            CoinDeskResearchGates.checkpoint_4_reference_dataset(),
            CoinDeskResearchGates.checkpoint_5_cross_venue_validation(),
            CoinDeskResearchGates.checkpoint_6_signal_quality(),
        ]
        return all(gates)

    @staticmethod
    def status_report() -> Dict[str, Any]:
        """Generate status report for POC progress."""
        passed = sum([
            CoinDeskResearchGates.checkpoint_1_api_mapping(),
            CoinDeskResearchGates.checkpoint_2_historical_access(),
            CoinDeskResearchGates.checkpoint_3_pit_validation(),
            CoinDeskResearchGates.checkpoint_4_reference_dataset(),
            CoinDeskResearchGates.checkpoint_5_cross_venue_validation(),
            CoinDeskResearchGates.checkpoint_6_signal_quality(),
        ])

        next_checkpoint = (
            "Checkpoint 2: Historical access validation"
            if passed >= 1
            else "Checkpoint 1: API endpoint mapping"
        )

        return {
            "data_source": "DATA-SRC-COINDESK-001",
            "status": "RESEARCH CANDIDATE",
            "gates_passed": passed,
            "gates_total": 6,
            "wfv_admissible": False,
            "next_milestone": next_checkpoint,
            "estimated_completion": "2026-10-15",
        }
