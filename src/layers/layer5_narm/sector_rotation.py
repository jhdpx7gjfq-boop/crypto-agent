"""
Phase 5: Sector Rotation Tracker for NARM-P+

Detects capital rotation between narrative sectors by tracking:
- Top narratives by NARM score
- Sector weighting changes
- Inflow acceleration by sector
- Narrative lifecycle stage
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


@dataclass
class SectorMetrics:
    """Metrics for a single sector/narrative."""

    sector_name: str
    assets: List[str]
    avg_narm_score: float
    median_narm_score: float
    top_scorer: str
    top_score: float
    total_adoption_velocity: float
    total_capital_rotation: float
    sector_momentum: float
    candidate_count: int  # Assets with NARM >= 65
    inflow_acceleration: float  # Rate of change in inflows


@dataclass
class SectorWeighting:
    """Sector allocation as % of total attention."""

    sector_name: str
    weight_pct: float
    weight_change_pct: float  # vs previous period
    momentum_direction: str  # up/down/stable


@dataclass
class SectorRotationSignal:
    """Rotation detection between sectors."""

    timestamp: datetime
    from_sector: str
    to_sector: str
    rotation_strength: float  # 0-100
    confidence: str  # high/medium/low
    top_candidates: List[Tuple[str, float]]  # [(asset, narm_score), ...]
    rotation_stage: str  # early/mid/late
    reasoning: List[str]


class SectorRotationTracker:
    """Track capital flows between narrative sectors."""

    # Rotation detection thresholds
    ROTATION_THRESHOLD = 65.0  # NARM score
    WEIGHT_CHANGE_MIN = 0.05  # 5% weight change to trigger
    CONFIDENCE_HIGH_THRESHOLD = 0.75
    CONFIDENCE_MEDIUM_THRESHOLD = 0.50

    def __init__(self):
        """Initialize tracker."""
        self.sector_history: Dict[str, List[SectorMetrics]] = {}
        self.rotation_history: List[SectorRotationSignal] = []

    def track_sector_metrics(
        self,
        narm_signals: Dict[str, float],
        asset_sectors: Dict[str, str],
        adoption_velocities: Optional[Dict[str, float]] = None,
        capital_rotations: Optional[Dict[str, float]] = None,
    ) -> Dict[str, SectorMetrics]:
        """
        Track metrics for each sector based on assets.

        Args:
            narm_signals: {asset: narm_score}
            asset_sectors: {asset: sector_name}
            adoption_velocities: {asset: adoption_score}
            capital_rotations: {asset: capital_flow_score}

        Returns:
            {sector_name: SectorMetrics}
        """
        sectors: Dict[str, List[Tuple[str, float]]] = {}

        # Group assets by sector
        for asset, sector in asset_sectors.items():
            if sector not in sectors:
                sectors[sector] = []
            narm_score = narm_signals.get(asset, 0.0)
            sectors[sector].append((asset, narm_score))

        # Calculate sector metrics
        metrics = {}
        for sector, assets_scores in sectors.items():
            if not assets_scores:
                continue

            scores = [score for _, score in assets_scores]
            assets = [asset for asset, _ in assets_scores]

            # Basic metrics
            avg_score = sum(scores) / len(scores)
            median_score = sorted(scores)[len(scores) // 2]
            top_scorer_idx = scores.index(max(scores))
            top_scorer = assets[top_scorer_idx]
            top_score = max(scores)

            # Count candidates (NARM >= 65)
            candidates = [s for s in scores if s >= self.ROTATION_THRESHOLD]
            candidate_count = len(candidates)

            # Adoption and capital flow metrics
            adoption_total = sum(
                adoption_velocities.get(asset, 50.0) for asset in assets
            )
            adoption_avg = adoption_total / len(assets) if assets else 0.0

            rotation_total = sum(
                capital_rotations.get(asset, 50.0) for asset in assets
            )
            rotation_avg = rotation_total / len(assets) if assets else 0.0

            # Sector momentum (avg of adoption + capital rotation)
            sector_momentum = (adoption_avg * 0.5 + rotation_avg * 0.5) / 100.0 * 50

            # Inflow acceleration (rate of change)
            inflow_accel = rotation_avg - 50.0  # Baseline 50

            sector_metrics = SectorMetrics(
                sector_name=sector,
                assets=assets,
                avg_narm_score=avg_score,
                median_narm_score=median_score,
                top_scorer=top_scorer,
                top_score=top_score,
                total_adoption_velocity=adoption_avg,
                total_capital_rotation=rotation_avg,
                sector_momentum=sector_momentum,
                candidate_count=candidate_count,
                inflow_acceleration=inflow_accel,
            )

            metrics[sector] = sector_metrics

            # Store in history
            if sector not in self.sector_history:
                self.sector_history[sector] = []
            self.sector_history[sector].append(sector_metrics)

        return metrics

    def detect_rotation(
        self,
        current_metrics: Dict[str, SectorMetrics],
    ) -> Optional[SectorRotationSignal]:
        """
        Detect sector rotation based on weight changes and inflow acceleration.

        Args:
            current_metrics: Current sector metrics

        Returns:
            SectorRotationSignal if rotation detected, else None
        """
        if not current_metrics:
            return None

        # Calculate sector weights
        total_candidates = sum(m.candidate_count for m in current_metrics.values())
        if total_candidates == 0:
            return None

        sector_weights = {
            name: m.candidate_count / total_candidates
            for name, m in current_metrics.items()
        }

        # Find previous weights (if history exists)
        prev_weights = {}
        for sector, history in self.sector_history.items():
            if len(history) >= 2:
                # Get weight from previous period (N-1)
                prev_candidates = sum(
                    1
                    for asset_score in [m.avg_narm_score for m in self.sector_history.get(sector, [])]
                    if asset_score >= self.ROTATION_THRESHOLD
                )
                prev_weights[sector] = (
                    prev_candidates / total_candidates if total_candidates > 0 else 0
                )

        # Detect major weight changes
        from_sector = None
        to_sector = None
        max_increase = 0.0
        max_decrease = 0.0

        for sector, current_weight in sector_weights.items():
            prev_weight = prev_weights.get(sector, current_weight)
            weight_change = current_weight - prev_weight

            if weight_change > max_increase:
                max_increase = weight_change
                to_sector = sector

            if weight_change < max_decrease:
                max_decrease = weight_change
                from_sector = sector

        # Trigger rotation if weight change >= threshold
        if (
            abs(max_increase) >= self.WEIGHT_CHANGE_MIN
            and from_sector
            and to_sector
        ):
            return self._create_rotation_signal(
                from_sector=from_sector,
                to_sector=to_sector,
                current_metrics=current_metrics,
                weight_change=max_increase,
            )

        return None

    def _create_rotation_signal(
        self,
        from_sector: str,
        to_sector: str,
        current_metrics: Dict[str, SectorMetrics],
        weight_change: float,
    ) -> SectorRotationSignal:
        """Create rotation signal with confidence scoring."""
        to_metrics = current_metrics.get(to_sector)
        if not to_metrics:
            return None

        # Collect top candidates in destination sector
        sector_assets = [
            (asset, narm_score)
            for asset, narm_score in zip(
                to_metrics.assets,
                [to_metrics.top_score if asset == to_metrics.top_scorer else 65.0
                 for asset in to_metrics.assets],
            )
        ]
        top_candidates = sorted(sector_assets, key=lambda x: x[1], reverse=True)[:5]

        # Rotation strength: combination of weight change + inflow acceleration
        strength = (
            min(weight_change * 100, 50.0) +  # Weight change component
            min(to_metrics.inflow_acceleration / 100 * 50, 50.0)  # Inflow component
        ) / 100.0 * 100

        # Confidence based on candidate count and metrics alignment
        candidate_confidence = (
            min(to_metrics.candidate_count / 5, 1.0) * 0.4
        )  # More candidates = higher confidence
        momentum_confidence = (
            to_metrics.sector_momentum / 100.0 * 0.3
        )  # Positive momentum
        inflow_confidence = (
            1.0 if to_metrics.inflow_acceleration > 0 else 0.0
        ) * 0.3  # Inflow positive

        total_confidence = (
            candidate_confidence + momentum_confidence + inflow_confidence
        )

        if total_confidence >= self.CONFIDENCE_HIGH_THRESHOLD:
            confidence = "high"
        elif total_confidence >= self.CONFIDENCE_MEDIUM_THRESHOLD:
            confidence = "medium"
        else:
            confidence = "low"

        # Rotation stage: based on adoption velocity
        if to_metrics.total_adoption_velocity >= 70:
            stage = "late"
        elif to_metrics.total_adoption_velocity >= 50:
            stage = "mid"
        else:
            stage = "early"

        reasoning = [
            f"Weight rotation: {from_sector} → {to_sector} ({weight_change*100:.1f}%)",
            f"Top candidate: {to_metrics.top_scorer} ({to_metrics.top_score:.1f})",
            f"Candidates in sector: {to_metrics.candidate_count}",
            f"Sector momentum: {to_metrics.sector_momentum:.1f}",
            f"Capital inflow acceleration: {to_metrics.inflow_acceleration:.1f}",
            f"Adoption velocity: {to_metrics.total_adoption_velocity:.1f}",
        ]

        signal = SectorRotationSignal(
            timestamp=datetime.utcnow(),
            from_sector=from_sector,
            to_sector=to_sector,
            rotation_strength=strength,
            confidence=confidence,
            top_candidates=top_candidates,
            rotation_stage=stage,
            reasoning=reasoning,
        )

        self.rotation_history.append(signal)
        return signal

    def get_sector_weights(
        self,
        current_metrics: Dict[str, SectorMetrics],
    ) -> List[SectorWeighting]:
        """Get current sector weightings with changes."""
        total_candidates = sum(m.candidate_count for m in current_metrics.values())
        if total_candidates == 0:
            return []

        weightings = []
        for sector, metrics in current_metrics.items():
            current_weight = metrics.candidate_count / total_candidates

            # Calculate previous weight
            prev_weight = 0.0
            if sector in self.sector_history and len(self.sector_history[sector]) >= 2:
                prev_metrics = self.sector_history[sector][-2]
                prev_weight = (
                    prev_metrics.candidate_count / total_candidates
                    if total_candidates > 0
                    else 0
                )

            weight_change = current_weight - prev_weight

            # Momentum direction
            if weight_change > 0.02:
                momentum = "up"
            elif weight_change < -0.02:
                momentum = "down"
            else:
                momentum = "stable"

            weighting = SectorWeighting(
                sector_name=sector,
                weight_pct=current_weight * 100,
                weight_change_pct=weight_change * 100,
                momentum_direction=momentum,
            )
            weightings.append(weighting)

        return sorted(weightings, key=lambda x: x.weight_pct, reverse=True)

    def get_top_narratives(
        self,
        current_metrics: Dict[str, SectorMetrics],
        limit: int = 5,
    ) -> List[Tuple[str, str, float]]:
        """
        Get top narratives by NARM score.

        Returns:
            List of (sector, asset, narm_score) tuples
        """
        narratives = []
        for sector, metrics in current_metrics.items():
            if metrics.candidate_count > 0:
                narratives.append((sector, metrics.top_scorer, metrics.top_score))

        return sorted(narratives, key=lambda x: x[2], reverse=True)[:limit]

    def audit_rotation_history(self) -> Dict:
        """Audit trail for rotation detection."""
        return {
            "total_rotations_detected": len(self.rotation_history),
            "high_confidence_rotations": sum(
                1 for r in self.rotation_history if r.confidence == "high"
            ),
            "tracked_sectors": len(self.sector_history),
            "last_rotation": (
                self.rotation_history[-1].timestamp.isoformat()
                if self.rotation_history
                else None
            ),
        }
