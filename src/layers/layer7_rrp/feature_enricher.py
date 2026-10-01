"""Feature Enricher — Derives revival signals from raw metrics.

Transforms raw snapshots into interpretable features.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from .snapshot_store import MetricSnapshot


@dataclass
class RevivalFeatures:
    """Enriched features for revival prediction."""

    asset: str
    timestamp: datetime
    volume_acceleration_7d: float
    volume_acceleration_14d: float
    on_chain_acceleration: float
    social_acceleration: float
    price_recovery_pct: float
    dormancy_breakout_ratio: float
    composite_signal: float  # 0-100
    signal_components: Dict[str, float] = None

    def __post_init__(self):
        """Initialize signal components."""
        if self.signal_components is None:
            self.signal_components = {}


class FeatureEnricher:
    """Enriches snapshots into revival features."""

    def __init__(self):
        """Initialize enricher."""
        self.feature_history: Dict[str, List[RevivalFeatures]] = {}

    def enrich(self, snapshot: MetricSnapshot, historical: List[MetricSnapshot]) -> RevivalFeatures:
        """
        Enrich snapshot with revival features.

        Args:
            snapshot: Current metric snapshot
            historical: Prior snapshots for comparison

        Returns:
            RevivalFeatures with derived signals
        """
        vol_accel_7d = self._calc_volume_acceleration(snapshot, historical, 7)
        vol_accel_14d = self._calc_volume_acceleration(snapshot, historical, 14)
        on_chain_accel = self._calc_on_chain_acceleration(snapshot, historical)
        social_accel = self._calc_social_acceleration(snapshot, historical)
        price_recovery = self._calc_price_recovery(snapshot)
        dormancy_ratio = self._calc_dormancy_breakout_ratio(snapshot, historical)

        composite = self._calc_composite_signal(
            vol_accel_7d, vol_accel_14d, on_chain_accel, social_accel, price_recovery
        )

        features = RevivalFeatures(
            asset=snapshot.asset,
            timestamp=snapshot.timestamp,
            volume_acceleration_7d=vol_accel_7d,
            volume_acceleration_14d=vol_accel_14d,
            on_chain_acceleration=on_chain_accel,
            social_acceleration=social_accel,
            price_recovery_pct=price_recovery,
            dormancy_breakout_ratio=dormancy_ratio,
            composite_signal=composite,
            signal_components={
                "volume_7d": vol_accel_7d,
                "volume_14d": vol_accel_14d,
                "on_chain": on_chain_accel,
                "social": social_accel,
                "price": price_recovery,
                "breakout_ratio": dormancy_ratio,
            },
        )

        # Track history
        if snapshot.asset not in self.feature_history:
            self.feature_history[snapshot.asset] = []
        self.feature_history[snapshot.asset].append(features)

        return features

    def _calc_volume_acceleration(
        self, snapshot: MetricSnapshot, historical: List[MetricSnapshot], days: int
    ) -> float:
        """Calculate volume acceleration over N days."""
        if not historical or len(historical) < 2:
            return 0.0

        # Current 7d volume
        current_vol = snapshot.volume_7d

        # Find average from N days ago
        if days == 7:
            prior_vol = snapshot.volume_14d_prior
        else:
            # Estimate from historical
            prior_snapshots = [s for s in historical if (snapshot.timestamp - s.timestamp).days <= days]
            if not prior_snapshots:
                return 0.0
            prior_vol = sum(s.volume_7d for s in prior_snapshots) / len(prior_snapshots)

        if prior_vol == 0:
            return 0.0
        return ((current_vol - prior_vol) / prior_vol) * 100

    def _calc_on_chain_acceleration(
        self, snapshot: MetricSnapshot, historical: List[MetricSnapshot]
    ) -> float:
        """Calculate on-chain activity acceleration."""
        if not historical or len(historical) < 2:
            return 0.0

        current_dau = snapshot.dau
        prior_daus = [s.dau for s in historical[-7:]]
        if not prior_daus:
            return 0.0

        avg_prior_dau = sum(prior_daus) / len(prior_daus)
        if avg_prior_dau == 0:
            return 0.0
        return ((current_dau - avg_prior_dau) / avg_prior_dau) * 100

    def _calc_social_acceleration(
        self, snapshot: MetricSnapshot, historical: List[MetricSnapshot]
    ) -> float:
        """Calculate social attention acceleration."""
        current_mentions = snapshot.mentions_7d
        prior_mentions = snapshot.mentions_14d_prior

        if prior_mentions == 0:
            return 0.0 if current_mentions == 0 else 100.0
        return ((current_mentions - prior_mentions) / prior_mentions) * 100

    def _calc_price_recovery(self, snapshot: MetricSnapshot) -> float:
        """Calculate price recovery from base."""
        if snapshot.base_price == 0:
            return 0.0
        return ((snapshot.current_price - snapshot.base_price) / snapshot.base_price) * 100

    def _calc_dormancy_breakout_ratio(
        self, snapshot: MetricSnapshot, historical: List[MetricSnapshot]
    ) -> float:
        """Ratio of current volume to dormancy baseline."""
        if not historical or len(historical) < 30:
            return 1.0

        # Calculate baseline from dormant period
        dormant_snapshots = [s for s in historical[-90:] if s.volume_7d < snapshot.volume_7d * 0.3]
        if not dormant_snapshots:
            return 1.0

        dormancy_baseline = sum(s.volume_7d for s in dormant_snapshots) / len(dormant_snapshots)
        if dormancy_baseline == 0:
            return 1.0
        return snapshot.volume_7d / dormancy_baseline

    def _calc_composite_signal(
        self,
        vol_7d: float,
        vol_14d: float,
        on_chain: float,
        social: float,
        price_recovery: float,
    ) -> float:
        """Calculate composite revival signal 0-100."""
        # Normalize components to 0-1
        vol_score = min(1.0, max(0.0, vol_7d / 200))
        on_chain_score = min(1.0, max(0.0, on_chain / 150))
        social_score = min(1.0, max(0.0, social / 300))
        price_score = min(1.0, max(0.0, price_recovery / 100))

        # Weighted composite
        composite = (
            vol_score * 0.25 + on_chain_score * 0.30 + social_score * 0.20 + price_score * 0.25
        )

        # Bonus for synchronized signals
        signals_present = sum([vol_7d > 0, on_chain > 0, social > 0, price_recovery > 0])
        if signals_present >= 3:
            composite = min(1.0, composite * 1.15)

        return composite * 100

    def get_feature_series(self, asset: str, days: int = 90) -> List[RevivalFeatures]:
        """Get feature time series for asset."""
        if asset not in self.feature_history:
            return []

        cutoff = datetime.utcnow().timestamp() - (days * 86400)
        return [f for f in self.feature_history[asset] if f.timestamp.timestamp() > cutoff]

    def audit_enrichment(self, asset: str) -> Dict:
        """Audit enrichment results."""
        if asset not in self.feature_history:
            return {"asset": asset, "features_extracted": 0}

        features = self.feature_history[asset]
        if not features:
            return {"asset": asset, "features_extracted": 0}

        return {
            "asset": asset,
            "features_extracted": len(features),
            "latest_composite": features[-1].composite_signal,
            "latest_acceleration": features[-1].on_chain_acceleration,
            "avg_composite": sum(f.composite_signal for f in features) / len(features),
        }
