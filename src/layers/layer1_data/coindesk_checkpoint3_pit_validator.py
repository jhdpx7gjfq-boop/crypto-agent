"""Checkpoint 3: Point-in-Time Semantics Audit.

DATA-SRC-COINDESK-001 POC Validation Gate.

Purpose:
- Detect whether volume metrics are revised after initial publication
- Map revision frequency (daily, weekly, or none)
- Document revision magnitude (% change from original)
- Identify systematic bias patterns (consistent over/under-reporting)

Status: RESEARCH MODE (awaiting C2 PASS + API key)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class PitSnapshot:
    """Single point-in-time snapshot of volume metrics."""
    asset: str
    fetch_date: str  # ISO date when this snapshot was taken
    data_date: str  # ISO date the data refers to
    volume_aggregate: float
    volume_top_tier: float
    volume_direct: float
    fetch_timestamp: str  # ISO datetime of the API call


@dataclass
class PitRevision:
    """Document a single revision event."""
    asset: str
    data_date: str
    fetch_t0: str  # First fetch datetime
    fetch_t1: str  # Second fetch datetime (T+7d)
    fetch_t2: str  # Third fetch datetime (T+30d)
    value_t0: float
    value_t1: float
    value_t2: float
    revision_t0_t1: float  # Percent change T0→T1
    revision_t1_t2: float  # Percent change T1→T2
    is_revised: bool  # True if any value differs
    magnitude: float  # Max absolute % change


class Checkpoint3PitValidator:
    """Audit point-in-time semantics for volume metrics."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize PIT validator.

        Args:
            api_key: CoinDesk Pro/Enterprise API key
        """
        self.api_key = api_key
        self.snapshots: Dict[str, List[PitSnapshot]] = {}
        self.revisions: Dict[str, List[PitRevision]] = {}

    def audit_pit_semantics(
        self,
        asset: str = "bitcoin",
        data_date: str = None,
        volume_type: str = "aggregate"
    ) -> Dict[str, Any]:
        """
        Audit PIT semantics by fetching same date range 3 times.

        Args:
            asset: Asset ID (e.g., 'bitcoin', 'ethereum')
            data_date: ISO date to audit (if None, use today - 7 days)
            volume_type: Volume type (aggregate, top_tier, direct)

        Returns:
            Dict with revision audit results
        """
        if not data_date:
            data_date = (datetime.utcnow() - timedelta(days=7)).date().isoformat()

        result = {
            "asset": asset,
            "checkpoint": "C3_PIT_SEMANTICS",
            "data_date": data_date,
            "volume_type": volume_type,
            "status": "NOT_RUN",
            "audit_plan": "Fetch same date 3x: T0, T+7d, T+30d",
            "audit_status": "RESEARCH_MODE",
            "note": "Awaiting C2 PASS + API key for execution",
            "snapshots": [],
            "revisions_detected": False,
            "revision_count": 0,
            "max_magnitude": 0.0,
            "revision_pattern": "UNKNOWN",
            "verdict": "UNVERIFIED",
            "error": None,
        }

        if not self.api_key:
            result["status"] = "SKIPPED"
            result["error"] = "No API key provided (requires Pro/Enterprise tier)"
            result["verdict"] = "UNVERIFIED"
            logger.warning(f"{asset}: C3 SKIPPED — no API key")
            return result

        # Research mode: document what we would do
        logger.info(f"{asset}: C3 Research → PIT audit plan configured")
        result["status"] = "RESEARCH_READY"
        result["verdict"] = "RESEARCH"
        return result

    def fetch_pit_snapshot(
        self,
        asset: str,
        data_date: str,
        volume_type: str = "aggregate"
    ) -> Optional[PitSnapshot]:
        """
        Fetch single PIT snapshot.

        Args:
            asset: Asset ID
            data_date: ISO date to fetch
            volume_type: Volume type

        Returns:
            PitSnapshot or None if fetch fails
        """
        if not self.api_key:
            logger.warning("No API key available for PIT snapshot fetch")
            return None

        try:
            import requests
        except ImportError:
            logger.error("requests library required")
            return None

        # Build request
        endpoint = "https://api.coindesk.com/v1/trade-data/spot/volume"
        params = {
            "asset": asset,
            "start_date": data_date,
            "end_date": data_date,
            "interval": "daily",
            "volume_type": volume_type,
        }
        headers = {"api-key": self.api_key}

        try:
            resp = requests.get(endpoint, params=params, headers=headers, timeout=30)

            if resp.status_code != 200:
                logger.error(f"HTTP {resp.status_code} fetching PIT snapshot")
                return None

            data = resp.json()
            data_points = data.get("data", [])

            if not data_points:
                logger.warning(f"No data for {asset} on {data_date}")
                return None

            point = data_points[0]
            snapshot = PitSnapshot(
                asset=asset,
                fetch_date=datetime.utcnow().date().isoformat(),
                data_date=data_date,
                volume_aggregate=point.get("volume_aggregate", 0.0),
                volume_top_tier=point.get("volume_top_tier", 0.0),
                volume_direct=point.get("volume_direct", 0.0),
                fetch_timestamp=datetime.utcnow().isoformat(),
            )
            return snapshot

        except Exception as e:
            logger.error(f"PIT snapshot fetch failed: {e}")
            return None

    def compare_snapshots(
        self,
        snapshot_t0: PitSnapshot,
        snapshot_t1: PitSnapshot,
        snapshot_t2: PitSnapshot,
    ) -> PitRevision:
        """
        Compare 3 snapshots to detect revisions.

        Args:
            snapshot_t0: First fetch (T)
            snapshot_t1: Second fetch (T+7d)
            snapshot_t2: Third fetch (T+30d)

        Returns:
            PitRevision with revision analysis
        """
        # Calculate percent changes
        if snapshot_t0.volume_aggregate > 0:
            rev_t0_t1 = (
                (snapshot_t1.volume_aggregate - snapshot_t0.volume_aggregate)
                / snapshot_t0.volume_aggregate
                * 100
            )
            rev_t1_t2 = (
                (snapshot_t2.volume_aggregate - snapshot_t1.volume_aggregate)
                / snapshot_t1.volume_aggregate
                * 100
            )
        else:
            rev_t0_t1 = 0.0
            rev_t1_t2 = 0.0

        max_magnitude = max(abs(rev_t0_t1), abs(rev_t1_t2))
        is_revised = max_magnitude > 0.01  # Threshold: 0.01% change

        revision = PitRevision(
            asset=snapshot_t0.asset,
            data_date=snapshot_t0.data_date,
            fetch_t0=snapshot_t0.fetch_timestamp,
            fetch_t1=snapshot_t1.fetch_timestamp,
            fetch_t2=snapshot_t2.fetch_timestamp,
            value_t0=snapshot_t0.volume_aggregate,
            value_t1=snapshot_t1.volume_aggregate,
            value_t2=snapshot_t2.volume_aggregate,
            revision_t0_t1=rev_t0_t1,
            revision_t1_t2=rev_t1_t2,
            is_revised=is_revised,
            magnitude=max_magnitude,
        )
        return revision

    def audit_multiple_dates(
        self,
        asset: str = "bitcoin",
        days: int = 30,
        volume_type: str = "aggregate"
    ) -> Dict[str, Any]:
        """
        Audit PIT semantics across multiple dates.

        Args:
            asset: Asset ID
            days: Number of days to audit
            volume_type: Volume type

        Returns:
            Audit report with revision statistics
        """
        result = {
            "asset": asset,
            "checkpoint": "C3_PIT_SEMANTICS",
            "status": "RESEARCH_READY",
            "days_audited": days,
            "volume_type": volume_type,
            "audit_plan": f"Audit {days} dates, fetch each 3x (T, T+7d, T+30d)",
            "revision_summary": {
                "total_dates": days,
                "dates_revised": 0,
                "dates_stable": days,
                "max_revision_magnitude": 0.0,
                "avg_revision_magnitude": 0.0,
                "revision_pattern": "UNKNOWN",
            },
            "patterns": {
                "no_revisions": "Volume never changes after initial publication",
                "early_revision": "Revisions occur within 7 days, then stabilize",
                "ongoing_revision": "Revisions continue after 30 days",
                "systematic_bias": "Consistent over/under-reporting detected",
            },
            "verdict": "UNVERIFIED",
            "note": "Research framework ready. Awaiting C2 PASS + API key.",
        }
        return result

    def generate_report(self) -> Dict[str, Any]:
        """Generate C3 audit report."""
        return {
            "checkpoint": "C3_PIT_SEMANTICS",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "RESEARCH_MODE",
            "summary": {
                "snapshots_collected": len(self.snapshots),
                "revisions_detected": sum(1 for rev_list in self.revisions.values() for _ in rev_list),
            },
            "findings": [],
            "revision_patterns": {},
            "recommendations": [
                "Audit must wait for C2 to PASS (live API key verification)",
                "Fetch same date range 3x across 30+ dates",
                "Map revision frequency and magnitude",
                "Identify systematic bias (if any)",
            ],
            "next_checkpoint": "C4_REFERENCE_DATASET" if False else None,
            "verdict": "RESEARCH_READY",
        }


# C3 entry point
def checkpoint_3_status():
    """Run Checkpoint 3 research."""
    print("\n" + "=" * 80)
    print("CHECKPOINT 3: Point-in-Time Semantics Audit (RESEARCH MODE)")
    print("=" * 80)

    validator = Checkpoint3PitValidator(api_key=None)
    report = validator.generate_report()

    print(f"\n📋 Status: {report['status']}")
    print(f"🔍 Purpose: Detect volume metric revisions")
    print(f"\n📌 Audit Plan:")
    print("   1. Fetch same date 3 times (T, T+7d, T+30d)")
    print("   2. Compare volumes across fetches")
    print("   3. Detect revisions & magnitude")
    print("   4. Map systematic patterns")

    print(f"\n⚠️  Gate Status:")
    print("   C2 (Historical Access): ⏳ AWAITING LIVE VERIFICATION")
    print("   C3 (PIT Semantics): 🔴 BLOCKED until C2 PASS")

    print(f"\n🔄 Recommendations:")
    for rec in report["recommendations"]:
        print(f"   • {rec}")

    print("\n" + "=" * 80 + "\n")
    return report


if __name__ == "__main__":
    checkpoint_3_status()
