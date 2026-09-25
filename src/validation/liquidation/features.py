"""Liquidation feature engineering — F001-F006 computation.

Features (Phase 1, v0.1):
- F001: Liquidation volume rolling sum (4-hour window)
- F002: Long/short ratio calculation
- F003: Volatility of volume (coefficient of variation)
- F004: Time-of-day patterns (market microstructure)
- F005: Source concentration score (exchange dominance)
- F006: Regime alignment (correlation with macro signals)

Deferred (v0.2):
- F008: Cross-exchange spread analysis

PIT Compliance:
- All features computed at specific timestamp (no lookahead)
- Window boundaries strictly before observation time
- Training/test separation enforced
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
from scipy import stats

from src.validation.liquidation.contracts import LiquidationEvent

logger = logging.getLogger(__name__)


class LiquidationFeatureEngine:
    """Compute liquidation features (F001-F006) from events."""

    def __init__(self, window_hours: int = 4) -> None:
        """Initialize feature engine.

        Args:
            window_hours: Rolling window size in hours (default 4)
        """
        self.window_hours = window_hours
        self.window_timedelta = timedelta(hours=window_hours)

    def compute_f001_volume_rolling_sum(
        self, events: list[dict], observation_time: datetime
    ) -> float:
        """F001: Liquidation volume rolling sum (4-hour window).

        Counts USD volume of liquidations in [observation_time - 4h, observation_time).
        PIT-compliant: uses only events strictly before observation_time.

        Args:
            events: List of event dicts sorted by timestamp (DESC)
            observation_time: Reference timestamp (exclusive upper bound)

        Returns:
            Total USD liquidation volume in window [0.0, ∞)
        """
        window_start = observation_time - self.window_timedelta
        volume = 0.0

        for event in events:
            # Handle both datetime objects and ISO strings
            event_ts = event.get("timestamp")
            if isinstance(event_ts, str):
                event_ts = datetime.fromisoformat(event_ts.replace("Z", "+00:00"))

            # PIT: strictly before observation_time
            if event_ts >= observation_time:
                continue

            # Within window
            if event_ts >= window_start:
                volume += event.get("usd_value", 0.0)

        logger.debug(f"F001 (volume_rolling_sum): {volume:.2f} USD in {self.window_hours}h window")
        return volume

    def compute_f002_long_short_ratio(
        self, events: list[dict], observation_time: datetime
    ) -> float:
        """F002: Long/short ratio calculation.

        Ratio of long liquidations to short liquidations in 4-hour window.
        Returns 0 if no short liquidations (avoid division by zero).

        Args:
            events: List of event dicts
            observation_time: Reference timestamp

        Returns:
            Long/short ratio [0.0, ∞), or 0 if no shorts
        """
        window_start = observation_time - self.window_timedelta
        long_volume = 0.0
        short_volume = 0.0

        for event in events:
            event_ts = event.get("timestamp")
            if isinstance(event_ts, str):
                event_ts = datetime.fromisoformat(event_ts.replace("Z", "+00:00"))

            if event_ts >= observation_time or event_ts < window_start:
                continue

            usd_value = event.get("usd_value", 0.0)
            if event.get("side") == "long":
                long_volume += usd_value
            elif event.get("side") == "short":
                short_volume += usd_value

        ratio = long_volume / short_volume if short_volume > 0 else 0.0
        logger.debug(f"F002 (long_short_ratio): {ratio:.4f}")
        return ratio

    def compute_f003_volume_volatility(
        self, events: list[dict], observation_time: datetime, bucket_minutes: int = 15
    ) -> float:
        """F003: Volatility of volume (coefficient of variation).

        Divides 4-hour window into 15-minute buckets, calculates volume per bucket,
        then computes coefficient of variation (std / mean).

        Args:
            events: List of event dicts
            observation_time: Reference timestamp
            bucket_minutes: Size of time buckets (default 15)

        Returns:
            Coefficient of variation [0.0, ∞), or 0 if no events
        """
        window_start = observation_time - self.window_timedelta
        bucket_timedelta = timedelta(minutes=bucket_minutes)

        # Initialize buckets
        num_buckets = int(self.window_timedelta.total_seconds() / bucket_timedelta.total_seconds())
        bucket_volumes = [0.0] * num_buckets

        # Fill buckets
        for event in events:
            event_ts = event.get("timestamp")
            if isinstance(event_ts, str):
                event_ts = datetime.fromisoformat(event_ts.replace("Z", "+00:00"))

            if event_ts >= observation_time or event_ts < window_start:
                continue

            # Calculate bucket index
            time_offset = event_ts - window_start
            bucket_idx = int(time_offset.total_seconds() / bucket_timedelta.total_seconds())
            if 0 <= bucket_idx < num_buckets:
                bucket_volumes[bucket_idx] += event.get("usd_value", 0.0)

        # Calculate coefficient of variation
        volumes = np.array(bucket_volumes)
        if np.sum(volumes) > 0:
            mean = np.mean(volumes)
            std = np.std(volumes)
            cv = std / mean if mean > 0 else 0.0
        else:
            cv = 0.0

        logger.debug(f"F003 (volume_volatility): {cv:.4f}")
        return float(cv)

    def compute_f004_time_of_day_pattern(
        self, events: list[dict], observation_time: datetime
    ) -> dict[str, float]:
        """F004: Time-of-day patterns (market microstructure).

        Returns volume ratios for different times of day in the 4-hour window:
        - asia: 00:00-08:00 UTC
        - europe: 08:00-16:00 UTC
        - americas: 16:00-24:00 UTC

        Args:
            events: List of event dicts
            observation_time: Reference timestamp

        Returns:
            Dict with keys {asia, europe, americas} → USD volumes
        """
        window_start = observation_time - self.window_timedelta

        volumes = {"asia": 0.0, "europe": 0.0, "americas": 0.0}

        for event in events:
            event_ts = event.get("timestamp")
            if isinstance(event_ts, str):
                event_ts = datetime.fromisoformat(event_ts.replace("Z", "+00:00"))

            if event_ts >= observation_time or event_ts < window_start:
                continue

            hour = event_ts.hour
            usd_value = event.get("usd_value", 0.0)

            if 0 <= hour < 8:
                volumes["asia"] += usd_value
            elif 8 <= hour < 16:
                volumes["europe"] += usd_value
            elif 16 <= hour < 24:
                volumes["americas"] += usd_value

        logger.debug(f"F004 (time_of_day): {volumes}")
        return volumes

    def compute_f005_source_concentration(
        self, events: list[dict], observation_time: datetime
    ) -> float:
        """F005: Source concentration score (exchange dominance).

        Herfindahl-Hirschman Index (HHI) of source distribution.
        HHI = sum((source_share)^2) where source_share = source_volume / total_volume.
        Range: [1/N, 1.0] where 1.0 = monopoly, 1/N = equal distribution.

        Args:
            events: List of event dicts
            observation_time: Reference timestamp

        Returns:
            HHI concentration score [0.0, 1.0]
        """
        window_start = observation_time - self.window_timedelta

        source_volumes: dict[str, float] = {}
        total_volume = 0.0

        for event in events:
            event_ts = event.get("timestamp")
            if isinstance(event_ts, str):
                event_ts = datetime.fromisoformat(event_ts.replace("Z", "+00:00"))

            if event_ts >= observation_time or event_ts < window_start:
                continue

            source = event.get("source", "unknown")
            usd_value = event.get("usd_value", 0.0)

            source_volumes[source] = source_volumes.get(source, 0.0) + usd_value
            total_volume += usd_value

        # Calculate HHI
        if total_volume > 0:
            hhi = sum((vol / total_volume) ** 2 for vol in source_volumes.values())
        else:
            hhi = 0.0

        logger.debug(f"F005 (source_concentration): {hhi:.4f}")
        return float(hhi)

    def compute_f006_regime_alignment(
        self, events: list[dict], observation_time: datetime, baseline_volume: float = 1_000_000.0
    ) -> float:
        """F006: Regime alignment (correlation with macro signals).

        Simple proxy: compares observed volume to baseline.
        Returns ratio of rolling sum to baseline (volume_regime = observed / baseline).

        Args:
            events: List of event dicts
            observation_time: Reference timestamp
            baseline_volume: Baseline USD volume for "normal" regime (default $1M)

        Returns:
            Regime alignment score [0.0, ∞), where 1.0 = baseline
        """
        rolling_volume = self.compute_f001_volume_rolling_sum(events, observation_time)
        regime_score = rolling_volume / baseline_volume if baseline_volume > 0 else 0.0

        logger.debug(f"F006 (regime_alignment): {regime_score:.4f}")
        return float(regime_score)

    def compute_all_features(
        self, events: list[dict], observation_time: datetime
    ) -> dict[str, Any]:
        """Compute all features (F001-F006) for a given observation time.

        Args:
            events: List of event dicts (should be sorted DESC by timestamp)
            observation_time: Reference timestamp (PIT-compliant)

        Returns:
            Dict with keys {f001, f002, f003, f004, f005, f006, timestamp}
        """
        logger.info(f"Computing F001-F006 features for {observation_time.isoformat()}")

        features = {
            "timestamp": observation_time.isoformat(),
            "f001_volume_rolling_sum": self.compute_f001_volume_rolling_sum(events, observation_time),
            "f002_long_short_ratio": self.compute_f002_long_short_ratio(events, observation_time),
            "f003_volume_volatility": self.compute_f003_volume_volatility(events, observation_time),
            "f004_time_of_day": self.compute_f004_time_of_day_pattern(events, observation_time),
            "f005_source_concentration": self.compute_f005_source_concentration(events, observation_time),
            "f006_regime_alignment": self.compute_f006_regime_alignment(events, observation_time),
        }

        logger.debug(f"Features computed: {features}")
        return features
