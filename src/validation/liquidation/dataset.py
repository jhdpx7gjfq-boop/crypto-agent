"""Liquidation dataset engineering — feature-label pair creation & splitting.

Dataset Pipeline:
1. Collect features (F001-F006) at observation times
2. Collect labels (RETURN[T→T+1m]) after observation window
3. Create feature-label pairs (X, y)
4. Split: In-Sample (IS) for training, Out-of-Sample (OOS) for testing

PIT Compliance:
- Split based on timestamp ordering (no lookahead)
- OOS data comes strictly after IS data
- No time overlap between IS and OOS
- Validates no data leakage

Walk-Forward Readiness:
- Dataset structure supports expanding train, fixed test
- Can be sliced into 15 windows for WFV
"""

import logging
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class LiquidationDataset:
    """Create and validate feature-label pairs."""

    def __init__(self) -> None:
        """Initialize dataset manager."""
        self.pairs: list[dict[str, Any]] = []
        self.is_data: list[dict[str, Any]] = []
        self.oos_data: list[dict[str, Any]] = []
        self.split_timestamp: datetime | None = None

    def add_pair(
        self,
        timestamp: datetime,
        symbol: str,
        features: dict[str, float],
        label: dict[str, Any],
    ) -> None:
        """Add a feature-label pair to dataset.

        Args:
            timestamp: Observation time (when features were computed)
            symbol: Trading pair
            features: Feature dict from LiquidationFeatureEngine (F001-F006)
            label: Label dict from LiquidationLabelEngine (return, sign, etc.)
        """
        pair = {
            "timestamp": timestamp,
            "symbol": symbol,
            "f001_volume_rolling_sum": features.get("f001_volume_rolling_sum", 0.0),
            "f002_long_short_ratio": features.get("f002_long_short_ratio", 0.0),
            "f003_volume_volatility": features.get("f003_volume_volatility", 0.0),
            "f004_time_of_day": features.get("f004_time_of_day", {}),
            "f005_source_concentration": features.get("f005_source_concentration", 0.0),
            "f006_regime_alignment": features.get("f006_regime_alignment", 0.0),
            # Label
            "return": label.get("return", 0.0),
            "return_sign": label.get("return_sign", 0),
            "log_return": label.get("log_return", 0.0),
        }

        self.pairs.append(pair)
        logger.debug(f"Added pair {len(self.pairs)}: {symbol} @ {timestamp.isoformat()}")

    def split_chronological(self, split_ratio: float = 0.7) -> tuple[list[dict], list[dict]]:
        """Split dataset chronologically (no lookahead).

        Args:
            split_ratio: Proportion for IS (default 0.7 = 70/30 split)

        Returns:
            Tuple of (IS_data, OOS_data) lists, sorted by timestamp
        """
        if not self.pairs:
            logger.warning("No pairs to split")
            return [], []

        # Sort by timestamp (ascending)
        sorted_pairs = sorted(self.pairs, key=lambda p: p["timestamp"])

        # For single pair: IS gets 1, OOS gets 0
        if len(sorted_pairs) == 1:
            self.is_data = sorted_pairs
            self.oos_data = []
            self.split_timestamp = self.is_data[-1]["timestamp"]
            logger.info(f"Split {len(sorted_pairs)} pairs: 1 IS, 0 OOS (single pair)")
            return self.is_data, self.oos_data

        # Calculate split index
        split_idx = int(len(sorted_pairs) * split_ratio)

        # Ensure at least 1 pair in each set (for multi-pair datasets)
        if split_idx == 0:
            split_idx = 1
        if split_idx == len(sorted_pairs):
            split_idx = len(sorted_pairs) - 1

        self.is_data = sorted_pairs[:split_idx]
        self.oos_data = sorted_pairs[split_idx:]
        self.split_timestamp = self.is_data[-1]["timestamp"]

        logger.info(
            f"Split {len(sorted_pairs)} pairs: {len(self.is_data)} IS (up to {self.split_timestamp.isoformat()}), "
            f"{len(self.oos_data)} OOS (from {self.oos_data[0]['timestamp'].isoformat()})"
        )

        return self.is_data, self.oos_data

    def validate_no_leakage(self) -> bool:
        """Validate no data leakage between IS and OOS.

        Checks:
        - IS and OOS don't overlap chronologically
        - OOS strictly after IS
        - No duplicate timestamps across sets

        Returns:
            True if valid, False otherwise
        """
        if not self.is_data or not self.oos_data:
            logger.warning("Cannot validate: missing IS or OOS data")
            return False

        # Get last IS timestamp and first OOS timestamp
        is_max_ts = max(p["timestamp"] for p in self.is_data)
        oos_min_ts = min(p["timestamp"] for p in self.oos_data)

        # OOS must be strictly after IS
        if oos_min_ts <= is_max_ts:
            logger.error(f"Data leakage: OOS starts at {oos_min_ts.isoformat()} ≤ IS ends at {is_max_ts.isoformat()}")
            return False

        # Check for duplicate timestamps
        is_ts = {p["timestamp"] for p in self.is_data}
        oos_ts = {p["timestamp"] for p in self.oos_data}
        overlap = is_ts & oos_ts

        if overlap:
            logger.error(f"Data leakage: {len(overlap)} duplicate timestamps")
            return False

        logger.info("✓ No data leakage detected")
        return True

    def get_dataset_statistics(self) -> dict[str, Any]:
        """Compute statistics on full dataset.

        Returns:
            Dict with comprehensive dataset stats
        """
        if not self.pairs:
            return {
                "total_pairs": 0,
                "symbols": [],
                "date_range": {"start": None, "end": None},
                "label_distribution": {},
            }

        df = pd.DataFrame(self.pairs)

        stats = {
            "total_pairs": len(self.pairs),
            "symbols": sorted(df["symbol"].unique().tolist()),
            "date_range": {
                "start": df["timestamp"].min().isoformat(),
                "end": df["timestamp"].max().isoformat(),
            },
            "label_distribution": {
                "down": int((df["return_sign"] == -1).sum()),
                "flat": int((df["return_sign"] == 0).sum()),
                "up": int((df["return_sign"] == 1).sum()),
            },
            "feature_statistics": {
                "f001_volume_rolling_sum": {
                    "mean": float(df["f001_volume_rolling_sum"].mean()),
                    "std": float(df["f001_volume_rolling_sum"].std()),
                    "min": float(df["f001_volume_rolling_sum"].min()),
                    "max": float(df["f001_volume_rolling_sum"].max()),
                },
                "f002_long_short_ratio": {
                    "mean": float(df["f002_long_short_ratio"].mean()),
                    "std": float(df["f002_long_short_ratio"].std()),
                    "min": float(df["f002_long_short_ratio"].min()),
                    "max": float(df["f002_long_short_ratio"].max()),
                },
                "f003_volume_volatility": {
                    "mean": float(df["f003_volume_volatility"].mean()),
                    "std": float(df["f003_volume_volatility"].std()),
                    "min": float(df["f003_volume_volatility"].min()),
                    "max": float(df["f003_volume_volatility"].max()),
                },
                "f005_source_concentration": {
                    "mean": float(df["f005_source_concentration"].mean()),
                    "std": float(df["f005_source_concentration"].std()),
                    "min": float(df["f005_source_concentration"].min()),
                    "max": float(df["f005_source_concentration"].max()),
                },
                "f006_regime_alignment": {
                    "mean": float(df["f006_regime_alignment"].mean()),
                    "std": float(df["f006_regime_alignment"].std()),
                    "min": float(df["f006_regime_alignment"].min()),
                    "max": float(df["f006_regime_alignment"].max()),
                },
            },
            "return_statistics": {
                "mean": float(df["return"].mean()),
                "std": float(df["return"].std()),
                "min": float(df["return"].min()),
                "max": float(df["return"].max()),
                "positive_pct": float((df["return"] > 0).sum() / len(df) * 100),
            },
        }

        return stats

    def get_is_oos_statistics(self) -> dict[str, Any]:
        """Compute statistics for IS and OOS separately.

        Returns:
            Dict with IS and OOS stats for comparison
        """
        if not self.is_data or not self.oos_data:
            return {"is": {}, "oos": {}}

        def compute_stats(data: list[dict]) -> dict[str, Any]:
            df = pd.DataFrame(data)
            return {
                "count": len(data),
                "symbols": sorted(df["symbol"].unique().tolist()),
                "date_range": {
                    "start": df["timestamp"].min().isoformat(),
                    "end": df["timestamp"].max().isoformat(),
                },
                "label_distribution": {
                    "down": int((df["return_sign"] == -1).sum()),
                    "flat": int((df["return_sign"] == 0).sum()),
                    "up": int((df["return_sign"] == 1).sum()),
                },
                "return_mean": float(df["return"].mean()),
                "return_std": float(df["return"].std()),
                "positive_pct": float((df["return"] > 0).sum() / len(df) * 100),
            }

        return {
            "is": compute_stats(self.is_data),
            "oos": compute_stats(self.oos_data),
        }

    def export_to_dataframe(self) -> pd.DataFrame:
        """Export dataset as pandas DataFrame.

        Returns:
            DataFrame with all features and labels
        """
        if not self.pairs:
            return pd.DataFrame()

        df = pd.DataFrame(self.pairs)

        # Ensure timestamp is datetime
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Flatten time_of_day dict to separate columns
        if "f004_time_of_day" in df.columns:
            tod_expanded = pd.json_normalize(df["f004_time_of_day"])
            df = pd.concat([df.drop("f004_time_of_day", axis=1), tod_expanded.add_prefix("f004_")], axis=1)

        return df

    def pit_compliance_check(self) -> dict[str, bool]:
        """Comprehensive PIT compliance check.

        Returns:
            Dict with compliance status for each check
        """
        checks = {
            "has_timestamps": all("timestamp" in p for p in self.pairs),
            "has_features": all(
                all(f"f{i:03d}" in str(p) for i in range(1, 7))
                or any(f"f00{i}" in p for i in range(1, 7))
                for p in self.pairs
            ),
            "has_labels": all("return_sign" in p for p in self.pairs),
            "no_duplicate_timestamps": len(self.pairs) == len({p["timestamp"] for p in self.pairs}),
            "chronological_order": (
                self.pairs == sorted(self.pairs, key=lambda p: p["timestamp"])
                if self.pairs
                else True
            ),
        }

        if self.is_data and self.oos_data:
            checks["no_leakage"] = self.validate_no_leakage()

        all_pass = all(checks.values())
        logger.info(f"PIT Compliance: {'✓ PASS' if all_pass else '✗ FAIL'} ({sum(checks.values())}/{len(checks)})")

        return checks

    def summary_report(self) -> str:
        """Generate human-readable dataset summary report.

        Returns:
            Markdown-formatted report
        """
        stats = self.get_dataset_statistics()
        is_oos = self.get_is_oos_statistics()
        pit_checks = self.pit_compliance_check()

        report = f"""# Liquidation Dataset Summary

**Generated**: {datetime.now(UTC).isoformat()}

## Dataset Overview

| Metric | Value |
|--------|-------|
| Total Pairs | {stats['total_pairs']} |
| Symbols | {', '.join(stats['symbols']) if stats['symbols'] else 'None'} |
| Date Range | {stats['date_range']['start']} to {stats['date_range']['end']} |

## Label Distribution (Full Dataset)

| Direction | Count | Percentage |
|-----------|-------|-----------|
| Down (-1) | {stats['label_distribution']['down']} | {100*stats['label_distribution']['down']/max(1,stats['total_pairs']):.1f}% |
| Flat (0)  | {stats['label_distribution']['flat']} | {100*stats['label_distribution']['flat']/max(1,stats['total_pairs']):.1f}% |
| Up (+1)   | {stats['label_distribution']['up']} | {100*stats['label_distribution']['up']/max(1,stats['total_pairs']):.1f}% |

## In-Sample / Out-of-Sample Split

| Metric | IS | OOS |
|--------|----|----|
| Count | {is_oos.get('is', {}).get('count', 0)} | {is_oos.get('oos', {}).get('count', 0)} |
| Date Range | {is_oos.get('is', {}).get('date_range', {}).get('start', 'N/A')} to {is_oos.get('is', {}).get('date_range', {}).get('end', 'N/A')} | {is_oos.get('oos', {}).get('date_range', {}).get('start', 'N/A')} to {is_oos.get('oos', {}).get('date_range', {}).get('end', 'N/A')} |
| Down | {is_oos.get('is', {}).get('label_distribution', {}).get('down', 0)} | {is_oos.get('oos', {}).get('label_distribution', {}).get('down', 0)} |
| Flat | {is_oos.get('is', {}).get('label_distribution', {}).get('flat', 0)} | {is_oos.get('oos', {}).get('label_distribution', {}).get('flat', 0)} |
| Up | {is_oos.get('is', {}).get('label_distribution', {}).get('up', 0)} | {is_oos.get('oos', {}).get('label_distribution', {}).get('up', 0)} |
| Return Mean | {is_oos.get('is', {}).get('return_mean', 0):.4f} | {is_oos.get('oos', {}).get('return_mean', 0):.4f} |

## PIT Compliance Audit

{'✓ PASS' if all(pit_checks.values()) else '✗ FAIL'}

| Check | Status |
|-------|--------|
| Has Timestamps | {'✓' if pit_checks.get('has_timestamps', False) else '✗'} |
| Has Features | {'✓' if pit_checks.get('has_features', False) else '✗'} |
| Has Labels | {'✓' if pit_checks.get('has_labels', False) else '✗'} |
| No Duplicate Timestamps | {'✓' if pit_checks.get('no_duplicate_timestamps', False) else '✗'} |
| Chronological Order | {'✓' if pit_checks.get('chronological_order', False) else '✗'} |
| No Data Leakage | {'✓' if pit_checks.get('no_leakage', False) else '✗'} |

## Feature Statistics (Full Dataset)

### F001: Volume Rolling Sum
- Mean: ${stats['feature_statistics']['f001_volume_rolling_sum']['mean']:,.0f}
- Std Dev: ${stats['feature_statistics']['f001_volume_rolling_sum']['std']:,.0f}
- Range: ${stats['feature_statistics']['f001_volume_rolling_sum']['min']:,.0f} to ${stats['feature_statistics']['f001_volume_rolling_sum']['max']:,.0f}

### F006: Regime Alignment
- Mean: {stats['feature_statistics']['f006_regime_alignment']['mean']:.4f}
- Std Dev: {stats['feature_statistics']['f006_regime_alignment']['std']:.4f}
- Range: {stats['feature_statistics']['f006_regime_alignment']['min']:.4f} to {stats['feature_statistics']['f006_regime_alignment']['max']:.4f}

## Return Statistics

- Mean Return: {stats['return_statistics']['mean']:.4f}
- Std Dev: {stats['return_statistics']['std']:.4f}
- Range: {stats['return_statistics']['min']:.4f} to {stats['return_statistics']['max']:.4f}
- Positive Return %: {stats['return_statistics']['positive_pct']:.1f}%

---

**Status**: {'Ready for Walk-Forward Validation' if all(pit_checks.values()) else 'Requires Review'}
"""

        return report
