"""Immutable Snapshot Store for RRP history tracking.

Maintains canonical historical snapshots without modification.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import hashlib


@dataclass
class MetricSnapshot:
    """Immutable snapshot of asset metrics at a point in time."""

    asset: str
    timestamp: datetime
    volume_7d: float
    volume_14d_prior: float
    dau: int
    transaction_volume: float
    whale_activity_change: float
    mentions_7d: int
    mentions_14d_prior: int
    sentiment_score: float
    current_price: float
    base_price: float
    months_since_bottom: int
    data_hash: str = ""

    def __post_init__(self):
        """Calculate immutable hash."""
        content = f"{self.asset}{self.timestamp}{self.volume_7d}{self.dau}{self.transaction_volume}"
        self.data_hash = hashlib.sha256(content.encode()).hexdigest()


class SnapshotValidator:
    """Validates snapshot data quality and consistency."""

    def __init__(self, min_volume: float = 0, max_volume: float = 1e12):
        """Initialize validator with constraints."""
        self.min_volume = min_volume
        self.max_volume = max_volume
        self.validation_errors: List[str] = []

    def validate(self, snapshot: MetricSnapshot) -> bool:
        """Validate snapshot integrity."""
        self.validation_errors = []

        if not self._validate_volume(snapshot):
            self.validation_errors.append("Volume out of bounds")

        if not self._validate_dau(snapshot):
            self.validation_errors.append("DAU invalid")

        if not self._validate_sentiment(snapshot):
            self.validation_errors.append("Sentiment out of range")

        if not self._validate_price(snapshot):
            self.validation_errors.append("Price invalid")

        return len(self.validation_errors) == 0

    def _validate_volume(self, snapshot: MetricSnapshot) -> bool:
        """Validate volume metrics."""
        if snapshot.volume_7d < self.min_volume:
            return False
        if snapshot.volume_7d > self.max_volume:
            return False
        if snapshot.volume_14d_prior < self.min_volume:
            return False
        return True

    def _validate_dau(self, snapshot: MetricSnapshot) -> bool:
        """Validate daily active users."""
        if snapshot.dau < 0:
            return False
        if snapshot.dau > 10_000_000:
            return False
        return True

    def _validate_sentiment(self, snapshot: MetricSnapshot) -> bool:
        """Validate sentiment score."""
        return -100 <= snapshot.sentiment_score <= 100

    def _validate_price(self, snapshot: MetricSnapshot) -> bool:
        """Validate price data."""
        if snapshot.current_price <= 0:
            return False
        if snapshot.base_price <= 0:
            return False
        return True


class ImmutableSnapshotStore:
    """Immutable store of metric snapshots."""

    def __init__(self):
        """Initialize store."""
        self.snapshots: Dict[str, List[MetricSnapshot]] = {}
        self.validator = SnapshotValidator()

    def add_snapshot(self, snapshot: MetricSnapshot) -> bool:
        """Add validated snapshot (immutable)."""
        if not self.validator.validate(snapshot):
            return False

        if snapshot.asset not in self.snapshots:
            self.snapshots[snapshot.asset] = []

        self.snapshots[snapshot.asset].append(snapshot)
        return True

    def get_history(self, asset: str, days: int = 90) -> List[MetricSnapshot]:
        """Retrieve historical snapshots."""
        if asset not in self.snapshots:
            return []

        cutoff = datetime.utcnow().timestamp() - (days * 86400)
        return [s for s in self.snapshots[asset] if s.timestamp.timestamp() > cutoff]

    def get_baseline_metrics(self, asset: str) -> Optional[Dict]:
        """Calculate baseline metrics from history."""
        history = self.get_history(asset, days=180)
        if not history or len(history) < 30:
            return None

        volumes = [s.volume_7d for s in history]
        daus = [s.dau for s in history]

        return {
            "avg_volume": sum(volumes) / len(volumes),
            "baseline_dau": sum(daus) / len(daus),
            "dormancy_days": self._estimate_dormancy(history),
        }

    def _estimate_dormancy(self, history: List[MetricSnapshot]) -> int:
        """Estimate dormancy period (low activity)."""
        if not history:
            return 0

        low_activity_threshold = 0.1  # 10% of baseline
        baseline_volume = sum(s.volume_7d for s in history[-30:]) / 30

        dormant_count = 0
        for snapshot in reversed(history):
            if snapshot.volume_7d < (baseline_volume * low_activity_threshold):
                dormant_count += 1
            else:
                break

        return dormant_count

    def audit_store(self, asset: str) -> Dict:
        """Audit snapshot store for asset."""
        if asset not in self.snapshots:
            return {"asset": asset, "snapshots": 0, "date_range": None}

        history = self.snapshots[asset]
        if not history:
            return {"asset": asset, "snapshots": 0, "date_range": None}

        return {
            "asset": asset,
            "snapshots": len(history),
            "earliest": history[0].timestamp,
            "latest": history[-1].timestamp,
            "avg_volume": sum(s.volume_7d for s in history) / len(history),
        }
