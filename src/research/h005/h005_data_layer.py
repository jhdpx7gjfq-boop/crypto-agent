"""H-005 Data Layer: Glassnode Exchange Flows + Binance Baseline

PIT-safe snapshot versioning for all data sources.
API key injected via environment variable (GLASSNODE_API_KEY).
"""

import os
import json
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple


class GlassnodeSnapshotManager:
    """Archive and retrieve Glassnode data with immutable snapshots.

    Each snapshot is timestamped and versioned to enforce PIT compliance.
    No backfills; data is frozen at snapshot time.
    """

    def __init__(self, snapshot_dir: str = "data/snapshots/glassnode"):
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = os.getenv("GLASSNODE_API_KEY")

    def snapshot_exists(self, timestamp: datetime) -> bool:
        """Check if snapshot already archived for this timestamp."""
        snapshot_path = self._snapshot_path(timestamp)
        return snapshot_path.exists()

    def _snapshot_path(self, timestamp: datetime) -> Path:
        """Immutable path: YYYY-MM-DD_HHmm_<metric>.json"""
        ts_str = timestamp.strftime("%Y-%m-%d_%H%M")
        return self.snapshot_dir / f"{ts_str}_exchange_flows.json"

    def fetch_and_archive(self, pit_timestamp: datetime, asset: str = "BTC") -> Dict[str, Any]:
        """Fetch exchange flows from Glassnode and archive snapshot.

        Args:
            pit_timestamp: Point-in-time reference (data must be <= this time)
            asset: BTC, ETH, etc.

        Returns:
            Snapshot dict with flows data and metadata (frozen)
        """
        if not self.api_key:
            raise ValueError("GLASSNODE_API_KEY not set. Preflight 2B incomplete.")

        # Placeholder: actual Glassnode REST call would go here
        # For now, return skeleton
        snapshot = {
            "pit_timestamp": pit_timestamp.isoformat(),
            "asset": asset,
            "archived_at": datetime.utcnow().isoformat(),
            "data": {
                # Glassnode metrics (6 features max for H-005)
                "exchange_inflow": [],
                "exchange_outflow": [],
                "exchange_netflow": [],
                # Additional supplementary metrics if needed
            },
            "metadata": {
                "source": "Glassnode",
                "version": "H-005-v0.1",
                "embargo_hours": 24,
                "immutable": True,
            }
        }

        # Archive snapshot
        snapshot_path = self._snapshot_path(pit_timestamp)
        with open(snapshot_path, 'w') as f:
            json.dump(snapshot, f, indent=2)

        return snapshot

    def load_snapshot(self, pit_timestamp: datetime) -> Dict[str, Any]:
        """Load frozen snapshot (immutable)."""
        snapshot_path = self._snapshot_path(pit_timestamp)
        if not snapshot_path.exists():
            raise FileNotFoundError(f"No snapshot for {pit_timestamp}")

        with open(snapshot_path, 'r') as f:
            return json.load(f)


class H005DataLayer:
    """Unified data source: Binance prices + Glassnode flows.

    Enforces PIT compliance: data[:idx+1] only.
    Frozen development period: 2021-01-01 to 2024-09-25
    Locked hold-out: 2024-09-26 to 2025-09-28
    """

    def __init__(self, binance_csv: str = "BTC-Daily-2021-2024.csv"):
        self.binance_csv = Path(binance_csv)
        self.glassnode = GlassnodeSnapshotManager()
        self._binance_df = None
        self._load_binance()

    def _load_binance(self):
        """Load validated Binance baseline (frozen 2021-2024)."""
        if not self.binance_csv.exists():
            raise FileNotFoundError(f"Binance data not found: {self.binance_csv}")

        self._binance_df = pd.read_csv(self.binance_csv, parse_dates=['Date'])
        self._binance_df.set_index('Date', inplace=True)

        # Validate frozen period
        dev_end = pd.Timestamp("2024-09-25")
        if self._binance_df.index.max() < dev_end:
            raise ValueError(f"Binance data ends before {dev_end}")

    def get_ohlcv(self, pit_idx: int) -> pd.DataFrame:
        """Get OHLCV data up to pit_idx (PIT-safe).

        Args:
            pit_idx: Row index (0-based)

        Returns:
            DataFrame with OHLCV columns, data[:pit_idx+1] only
        """
        if pit_idx >= len(self._binance_df):
            raise IndexError(f"pit_idx {pit_idx} >= len {len(self._binance_df)}")

        return self._binance_df.iloc[:pit_idx+1].copy()

    def get_flows(self, pit_idx: int, pit_timestamp: datetime) -> Dict[str, Any]:
        """Get Glassnode exchange flows up to pit_idx.

        Args:
            pit_idx: Row index
            pit_timestamp: Point-in-time reference for snapshot

        Returns:
            Flows dict (immutable snapshot)
        """
        try:
            snapshot = self.glassnode.load_snapshot(pit_timestamp)
            return snapshot["data"]
        except FileNotFoundError:
            # Try to fetch and archive
            return self.glassnode.fetch_and_archive(pit_timestamp, "BTC")["data"]

    def get_dev_period(self) -> Tuple[int, int]:
        """Dev period indices: 2021-01-01 to 2024-09-25."""
        dev_end = pd.Timestamp("2024-09-25")
        dev_idx = (self._binance_df.index <= dev_end).sum() - 1
        return 0, dev_idx

    def get_holdout_period(self) -> Tuple[int, int]:
        """Hold-out period indices: 2024-09-26 to 2025-09-28 (LOCKED)."""
        holdout_start = pd.Timestamp("2024-09-26")
        holdout_end = pd.Timestamp("2025-09-28")
        start_idx = (self._binance_df.index >= holdout_start).argmax()
        end_idx = (self._binance_df.index <= holdout_end).sum() - 1
        return start_idx, end_idx
