"""Liquidation QA stage — data quality assurance pipeline.

Tasks:
1. Duplicate detection (exact match removal)
2. Outlier flagging ($10M+ single events)
3. Gap identification (missing time windows)
4. Source reliability scoring
5. Quality report generation
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from src.validation.liquidation.contracts import LiquidationQAReport
from src.validation.liquidation.persistence import LiquidationStore

logger = logging.getLogger(__name__)


class LiquidationQA:
    """Quality assurance pipeline for liquidation events."""

    def __init__(
        self,
        store: LiquidationStore,
        outlier_threshold_usd: float = 10_000_000.0,
        gap_threshold_minutes: int = 60,
    ) -> None:
        """Initialize QA pipeline.

        Args:
            store: LiquidationStore instance
            outlier_threshold_usd: Flag events above this USD value
            gap_threshold_minutes: Flag gaps larger than this
        """
        self.store = store
        self.outlier_threshold_usd = outlier_threshold_usd
        self.gap_threshold_minutes = gap_threshold_minutes
        self.report: LiquidationQAReport | None = None

    def run_full_audit(self) -> LiquidationQAReport:
        """Run complete QA audit on raw events.

        Returns:
            LiquidationQAReport with all findings
        """
        logger.info("Starting full QA audit...")

        stats = self.store.get_stats()
        total_events = stats["total_events"]

        if total_events == 0:
            logger.warning("No events to audit")
            self.report = LiquidationQAReport(
                total_events=0,
                duplicates_found=0,
                outliers_flagged=0,
                gaps_identified=0,
                source_reliability_score=0.0,
                data_quality_score=0.0,
                timestamp=datetime.now(UTC),
            )
            return self.report

        # Get raw events for detailed analysis
        events = self.store.get_raw_events(limit=100_000)
        logger.info(f"Retrieved {len(events)} events for audit")

        # Run checks
        duplicates = self._detect_duplicates(events)
        outliers = self._flag_outliers(events)
        gaps = self._identify_gaps(events)
        reliability_score = self._score_source_reliability(len(events), len(duplicates))

        # Calculate overall quality score
        quality_score = self._calculate_quality_score(
            total_events, len(duplicates), len(outliers), len(gaps)
        )

        # Create report
        self.report = LiquidationQAReport(
            total_events=total_events,
            duplicates_found=len(duplicates),
            outliers_flagged=len(outliers),
            gaps_identified=len(gaps),
            source_reliability_score=reliability_score,
            data_quality_score=quality_score,
            timestamp=datetime.now(UTC),
        )

        logger.info(
            f"QA audit complete: "
            f"duplicates={len(duplicates)}, "
            f"outliers={len(outliers)}, "
            f"gaps={len(gaps)}, "
            f"quality_score={quality_score:.2%}"
        )

        return self.report

    def _detect_duplicates(self, events: list[dict]) -> list[dict]:
        """Detect exact duplicate events (same source_id).

        Args:
            events: List of event dicts from store

        Returns:
            List of duplicate events (should be empty after dedup)
        """
        seen = set()
        duplicates = []

        for event in events:
            source_id = event.get("source_id")
            if source_id in seen:
                duplicates.append(event)
            else:
                seen.add(source_id)

        logger.info(f"Duplicate detection: {len(duplicates)} found")
        return duplicates

    def _flag_outliers(self, events: list[dict]) -> list[dict]:
        """Flag high-value outlier events.

        Args:
            events: List of event dicts

        Returns:
            List of outlier events
        """
        outliers = []

        for event in events:
            usd_value = event.get("usd_value", 0.0)
            if usd_value >= self.outlier_threshold_usd:
                outliers.append({**event, "outlier_reason": f"USD value ${usd_value:,.0f}"})

        logger.info(f"Outlier flagging: {len(outliers)} found (>${self.outlier_threshold_usd/1e6:.1f}M)")
        return outliers

    def _identify_gaps(self, events: list[dict]) -> list[dict]:
        """Identify time gaps in event stream.

        Args:
            events: List of event dicts (assumed sorted by timestamp)

        Returns:
            List of gap descriptions
        """
        if len(events) < 2:
            return []

        gaps = []
        gap_threshold = timedelta(minutes=self.gap_threshold_minutes)

        # Sort by timestamp
        sorted_events = sorted(events, key=lambda e: e.get("timestamp", ""))

        for i in range(len(sorted_events) - 1):
            # Handle both datetime objects and ISO strings from DuckDB
            curr_ts = sorted_events[i]["timestamp"]
            next_ts = sorted_events[i + 1]["timestamp"]

            if isinstance(curr_ts, str):
                current_ts = datetime.fromisoformat(curr_ts.replace("Z", "+00:00"))
            else:
                current_ts = curr_ts

            if isinstance(next_ts, str):
                next_ts = datetime.fromisoformat(next_ts.replace("Z", "+00:00"))
            else:
                next_ts = next_ts

            gap = next_ts - current_ts
            if gap > gap_threshold:
                gaps.append(
                    {
                        "gap_start": current_ts.isoformat(),
                        "gap_end": next_ts.isoformat(),
                        "gap_duration_minutes": gap.total_seconds() / 60,
                    }
                )

        logger.info(f"Gap identification: {len(gaps)} gaps found (>{self.gap_threshold_minutes}min)")
        return gaps

    def _score_source_reliability(
        self, total_events: int, duplicates: int, connection_failures: int = 0
    ) -> float:
        """Score source data reliability [0, 1].

        Args:
            total_events: Total events collected
            duplicates: Number of duplicates (lower is better)
            connection_failures: Number of reconnections (lower is better)

        Returns:
            Reliability score [0, 1]
        """
        if total_events == 0:
            return 0.0

        # Base score: 1.0 (perfect)
        score = 1.0

        # Penalty for duplicates (5 bps per duplicate)
        duplicate_penalty = min(0.05, duplicates * 0.0005)
        score -= duplicate_penalty

        # Penalty for connection failures (10 bps per failure)
        failure_penalty = min(0.10, connection_failures * 0.001)
        score -= failure_penalty

        score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
        logger.info(f"Source reliability score: {score:.4f}")
        return score

    def _calculate_quality_score(
        self, total_events: int, duplicates: int, outliers: int, gaps: int
    ) -> float:
        """Calculate overall data quality score [0, 1].

        Factors:
        - Data completeness (fewer gaps = higher)
        - Data integrity (fewer duplicates = higher)
        - Data reasonableness (fewer outliers = context-dependent)

        Args:
            total_events: Total events
            duplicates: Number of duplicates
            outliers: Number of outliers
            gaps: Number of gaps

        Returns:
            Quality score [0, 1]
        """
        if total_events == 0:
            return 0.0

        # Base score
        score = 1.0

        # Duplicate penalty (critical): -10 bps per duplicate
        duplicate_ratio = duplicates / total_events if total_events > 0 else 0
        score -= min(0.20, duplicate_ratio * 10)

        # Gap penalty (medium): -1 bp per gap
        score -= min(0.10, gaps * 0.001)

        # Outlier consideration: not penalized (legitimate liquidations can be large)
        # Outliers flagged for review, not for quality score

        score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
        logger.info(f"Data quality score: {score:.4f}")
        return score

    def get_report_summary(self) -> str:
        """Generate human-readable QA report summary.

        Returns:
            Markdown-formatted report
        """
        if not self.report:
            return "No QA report generated yet. Run run_full_audit() first."

        report = self.report
        return f"""# Liquidation Data Quality Audit

**Generated**: {report.timestamp.isoformat()}

## Summary

| Metric | Value |
|--------|-------|
| Total Events | {report.total_events:,} |
| Duplicates Found | {report.duplicates_found} |
| Outliers Flagged | {report.outliers_flagged} |
| Gaps Identified | {report.gaps_identified} |
| Source Reliability | {report.source_reliability_score:.1%} |
| Data Quality Score | {report.data_quality_score:.1%} |

## Assessment

- **Duplication Rate**: {100 * report.duplicates_found / max(1, report.total_events):.2f}%
- **Outlier Rate**: {100 * report.outliers_flagged / max(1, report.total_events):.2f}%
- **Coverage Gaps**: {report.gaps_identified}

## Verdict

{"✅ PASS" if report.data_quality_score >= 0.90 else "⚠️  WARN" if report.data_quality_score >= 0.70 else "❌ FAIL"} — Quality score {report.data_quality_score:.1%}

**Status**: {"Production-ready" if report.data_quality_score >= 0.90 else "Requires review" if report.data_quality_score >= 0.70 else "Not ready"}
"""

    def export_csv(self, filepath: str) -> None:
        """Export QA findings to CSV.

        Args:
            filepath: Path to write CSV
        """
        if not self.report:
            logger.warning("No report to export. Run run_full_audit() first.")
            return

        import csv

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "metric",
                    "value",
                    "timestamp",
                ]
            )
            writer.writerow(
                [
                    "total_events",
                    self.report.total_events,
                    self.report.timestamp.isoformat(),
                ]
            )
            writer.writerow(
                [
                    "duplicates_found",
                    self.report.duplicates_found,
                    self.report.timestamp.isoformat(),
                ]
            )
            writer.writerow(
                [
                    "outliers_flagged",
                    self.report.outliers_flagged,
                    self.report.timestamp.isoformat(),
                ]
            )
            writer.writerow(
                [
                    "gaps_identified",
                    self.report.gaps_identified,
                    self.report.timestamp.isoformat(),
                ]
            )
            writer.writerow(
                [
                    "source_reliability_score",
                    self.report.source_reliability_score,
                    self.report.timestamp.isoformat(),
                ]
            )
            writer.writerow(
                [
                    "data_quality_score",
                    self.report.data_quality_score,
                    self.report.timestamp.isoformat(),
                ]
            )

        logger.info(f"QA report exported to {filepath}")
