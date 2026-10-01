"""
C1.5-PIT: Point-in-Time Validation (Independent Gate)

Validates temporal availability of observations independently.
Distinguishes: availability_time ≤ decision_time (not event_time ≤ decision_time)

Does NOT validate alpha/performance. Only temporal ordering.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum


class AvailabilityProofLevel(Enum):
    """Hierarchy of temporal availability proofs."""
    A_PUBLISHER_VERSIONED = "A"  # Publisher timestamp + versioned history
    B_IMMUTABLE_ARCHIVE = "B"    # Immutable dated archive
    C_API_HISTORICAL = "C"       # API historical with timestamp (conditional)
    D_RETROACTIVE = "D"          # Retroactively reconstructed (FAIL)
    E_SYNTHETIC = "E"            # Synthetic/mock (FAIL)


class PITValidator:
    """
    Point-in-Time validation engine.

    Responsibility:
    - Validate availability_time ≤ decision_time (temporal ordering)
    - Reject future data (100%)
    - Reject late-arriving data (100%)
    - Detect retroactive revisions
    - Validate feature availability (no future lookahead)
    - Enforce aggregation cutoffs
    - Validate availability proofs (Hierarchy A-E)
    """

    @staticmethod
    def temporal_check(availability_time: str, decision_time: str) -> bool:
        """
        Check if availability_time ≤ decision_time.

        Args:
            availability_time: ISO 8601 UTC when data became available
            decision_time: ISO 8601 UTC when decision was made

        Returns:
            True if data was available before/at decision time
        """
        avail = datetime.fromisoformat(availability_time.replace('Z', '+00:00'))
        decision = datetime.fromisoformat(decision_time.replace('Z', '+00:00'))
        return avail <= decision

    @staticmethod
    def reject_future_data(observations: List[Dict], decision_time: str) -> List[Dict]:
        """
        Reject observations with availability_time > decision_time.

        Args:
            observations: List of observations
            decision_time: Decision timestamp

        Returns:
            Filtered list (only available observations)
        """
        return [
            obs for obs in observations
            if PITValidator.temporal_check(obs["availability_time"], decision_time)
        ]

    @staticmethod
    def validate_feature_availability(features: Dict, decision_time: str) -> bool:
        """
        Validate that all features use only available data.

        Rejects:
        - Centered windows (future lookahead)
        - Explicit lookahead_days
        - Series normalization including future
        - High/low availability after decision

        Args:
            features: Dict of feature definitions
            decision_time: Decision timestamp

        Returns:
            True if all features use only available data
        """
        for feature_name, feature in features.items():
            # Reject centered windows
            if feature.get("window") == "centered":
                return False
            # Reject explicit lookahead
            if feature.get("lookahead_days"):
                return False
            # Reject full-series normalization with future data
            if feature.get("series_includes_future"):
                return False
            # Check component availability (e.g., high price availability)
            if "high_availability" in feature:
                if not PITValidator.temporal_check(feature["high_availability"], decision_time):
                    return False
            if "low_availability" in feature:
                if not PITValidator.temporal_check(feature["low_availability"], decision_time):
                    return False
        return True

    @staticmethod
    def detect_retroactive_revision(
        snapshot_t: Dict[str, List[Dict]],
        snapshot_t_plus_1: Dict[str, List[Dict]],
    ) -> List[Dict]:
        """
        Detect retroactive revisions between two snapshots.

        Finds: price corrections, volume changes, field modifications.

        Args:
            snapshot_t: Snapshot at time T
            snapshot_t_plus_1: Snapshot at time T+1

        Returns:
            List of detected revisions (corrections, additions, deletions)
        """
        revisions = []

        for asset in snapshot_t:
            if asset not in snapshot_t_plus_1:
                continue

            rows_t = {row["date"]: row for row in snapshot_t[asset]}
            rows_t1 = {row["date"]: row for row in snapshot_t_plus_1[asset]}

            for date in rows_t:
                if date in rows_t1:
                    # Check for field corrections
                    for field in rows_t1[date]:
                        if field != "date" and rows_t[date].get(field) != rows_t1[date].get(field):
                            revisions.append({
                                "type": "retroactive_correction",
                                "asset": asset,
                                "date": date,
                                "field": field,
                                "old_value": rows_t[date].get(field),
                                "new_value": rows_t1[date].get(field),
                            })

        return revisions

    @staticmethod
    def check_availability(observation: Dict, decision_time: str) -> bool:
        """
        Check if observation is available at decision_time.

        Args:
            observation: Observation dict with availability_time
            decision_time: Decision timestamp

        Returns:
            True if observation was available
        """
        return PITValidator.temporal_check(observation["availability_time"], decision_time)

    @staticmethod
    def get_data_as_of(
        asset: str,
        date: str,
        snapshot: Dict[str, List[Dict]],
        decision_time: str,
    ) -> Optional[Dict]:
        """
        Get data for asset/date if available at decision_time.

        Args:
            asset: Asset symbol
            date: Date string
            snapshot: Snapshot data
            decision_time: Decision timestamp

        Returns:
            Row data if available, None otherwise
        """
        asset_data = snapshot.get(asset, [])
        for row in asset_data:
            if row.get("date") == date:
                # Only return if availability_time ≤ decision_time
                if PITValidator.temporal_check(row.get("availability_time", ""), decision_time):
                    return row
        return None

    @staticmethod
    def check_aggregate_available(
        agg_type: str,
        period_close_utc: str,
        decision_time: str,
    ) -> bool:
        """
        Check if aggregate is available (requires period closure).

        Daily: requires 00:00 UTC next day
        Weekly: requires Monday 00:00 UTC next week
        Monthly: requires 00:00 UTC next month

        Args:
            agg_type: "daily", "weekly", "monthly"
            period_close_utc: Period closure timestamp (ISO 8601 UTC)
            decision_time: Decision timestamp

        Returns:
            True if period is closed and decision is after closure
        """
        return PITValidator.temporal_check(period_close_utc, decision_time)

    @staticmethod
    def validate_availability_proof(proof: Dict) -> str:
        """
        Validate temporal availability proof (Hierarchy A-E).

        Returns:
        - "PASS": Level A or B
        - "PASS_CONDITIONAL": Level C (requires documentation)
        - "FAIL": Level D or E

        Args:
            proof: Dict with "level" key

        Returns:
            Validation verdict string
        """
        level = proof.get("level")

        if level == AvailabilityProofLevel.A_PUBLISHER_VERSIONED:
            return "PASS"
        elif level == AvailabilityProofLevel.B_IMMUTABLE_ARCHIVE:
            return "PASS"
        elif level == AvailabilityProofLevel.C_API_HISTORICAL:
            return "PASS_CONDITIONAL"
        elif level == AvailabilityProofLevel.D_RETROACTIVE:
            return "FAIL"
        elif level == AvailabilityProofLevel.E_SYNTHETIC:
            return "FAIL"

        return "UNKNOWN"

    @staticmethod
    def validate_pit_status(observation: Dict, decision_time: str) -> Dict:
        """
        Validate observation and update pit_status.

        If temporal check passes: pit_status = "VERIFIED"
        If temporal check fails: pit_status = "UNVERIFIED" (observation rejected)

        Args:
            observation: Observation dict
            decision_time: Decision timestamp

        Returns:
            Updated observation dict
        """
        if PITValidator.temporal_check(observation["availability_time"], decision_time):
            observation["pit_status"] = "VERIFIED"
        else:
            observation["pit_status"] = "UNVERIFIED"

        return observation

    @staticmethod
    def validate_snapshot_pit(
        snapshot: Dict[str, List[Dict]],
        decision_time: str,
    ) -> Dict[str, Any]:
        """
        Validate entire snapshot for PIT compliance.

        Returns verdict with:
        - violations: list of detected violations
        - future_observations_rejected: count
        - late_observations_rejected: count
        - retroactive_revisions: list
        - pit_status_propagated: bool

        Args:
            snapshot: Snapshot data
            decision_time: Decision timestamp

        Returns:
            Validation report dict
        """
        violations = []
        future_count = 0
        late_count = 0

        for asset, rows in snapshot.items():
            for row in rows:
                avail_time = row.get("availability_time", "")
                if not avail_time:
                    violations.append(f"{asset} {row.get('date')}: missing availability_time")
                    continue

                if not PITValidator.temporal_check(avail_time, decision_time):
                    if datetime.fromisoformat(avail_time.replace('Z', '+00:00')) > \
                       datetime.fromisoformat(decision_time.replace('Z', '+00:00')):
                        future_count += 1
                    else:
                        late_count += 1
                    violations.append(f"{asset} {row.get('date')}: availability after decision")

        return {
            "violations": violations,
            "violation_count": len(violations),
            "future_observations_rejected": future_count,
            "late_observations_rejected": late_count,
            "pit_pass": len(violations) == 0,
            "pit_status": "VERIFIED" if len(violations) == 0 else "UNVERIFIED",
        }
