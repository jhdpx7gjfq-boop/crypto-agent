"""Dashboard service orchestration."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from .api_models import (
    DashboardSummary, MarketRegimeInfo, SignalAlert, SignalType,
    ActionType, Severity, BCEAnalysis, X20Report, RRPReport, RCMReport,
    AlertSummary, PortfolioReport, RegimeType
)


class DashboardService:
    """Orchestrates data from all layers for dashboard display."""

    def __init__(self):
        """Initialize service."""
        self.alert_history: List[SignalAlert] = []
        self.watchlist: Dict[str, Dict] = {}
        self.last_update: datetime = datetime.utcnow()

    async def generate_summary(
        self,
        regime_data: Dict[str, Any],
        bce_signals: Dict[str, Any],
        x20_scores: Dict[str, Any],
        rrp_candidates: Dict[str, Any],
        rcm_rotations: Dict[str, Any],
    ) -> DashboardSummary:
        """
        Generate dashboard summary from all layers.

        Args:
            regime_data: {regime_type, confidence, expected_duration_days, days_in_regime}
            bce_signals: {asset: {score, validity, confidence, entry_ready}}
            x20_scores: {asset: {score, rank, asymmetric_potential}}
            rrp_candidates: {asset: {score, stage, acceleration_rate}}
            rcm_rotations: {asset: {rotation_type, confidence, capital_flow_strength}}

        Returns:
            DashboardSummary with top signals and alerts
        """
        self.last_update = datetime.utcnow()

        # Build regime info
        regime_info = MarketRegimeInfo(
            regime_type=RegimeType(regime_data.get("regime_type", "ranging")),
            confidence=regime_data.get("confidence", 0.5),
            expected_duration_days=regime_data.get("expected_duration_days", 14),
            days_in_regime=regime_data.get("days_in_regime", 0),
        )

        # Collect all signals
        signals = self._collect_signals(
            regime_data, bce_signals, x20_scores, rrp_candidates, rcm_rotations
        )

        # Sort by severity then confidence
        signals.sort(key=lambda s: (s.severity.value, -s.confidence), reverse=True)
        top_signals = signals[:10]

        critical_count = sum(1 for s in signals if s.severity == Severity.CRITICAL)

        summary = DashboardSummary(
            timestamp=self.last_update,
            market_regime=regime_info,
            top_signals=top_signals,
            critical_alerts=critical_count,
            assets_under_watch=len(set(s.asset for s in signals)),
            last_update=self.last_update.isoformat(),
        )

        return summary

    def _collect_signals(
        self,
        regime_data: Dict,
        bce_signals: Dict,
        x20_scores: Dict,
        rrp_candidates: Dict,
        rcm_rotations: Dict,
    ) -> List[SignalAlert]:
        """Collect signals from all sources."""
        signals = []

        # BCE signals
        for asset, bce_data in bce_signals.items():
            if bce_data.get("entry_ready"):
                score = bce_data.get("score", 0)
                signals.append(
                    SignalAlert(
                        asset=asset,
                        signal_type=SignalType.BCE,
                        score=score / 6 * 100,  # Normalize 0-6 to 0-100
                        confidence=bce_data.get("confidence", 0.5),
                        reasoning=f"BCE {score:.1f}/6 - {bce_data.get('stage', 'mixed')}",
                        action=ActionType.ENTRY_READY,
                        timestamp=datetime.utcnow(),
                        severity=self._score_to_severity(score / 6 * 100),
                        next_action="Monitor for breakout",
                    )
                )

        # X20 signals
        for asset, x20_data in x20_scores.items():
            score = x20_data.get("score", 0)
            if score >= 75:
                signals.append(
                    SignalAlert(
                        asset=asset,
                        signal_type=SignalType.X20,
                        score=score,
                        confidence=0.7,
                        reasoning=f"X20 score {score:.0f} - Asymmetric potential {x20_data.get('asymmetric_potential', 1):.1f}x",
                        action=ActionType.RESEARCH,
                        timestamp=datetime.utcnow(),
                        severity=Severity.MEDIUM if score >= 85 else Severity.LOW,
                        next_action="Deep dive analysis",
                    )
                )

        # RRP signals
        for asset, rrp_data in rrp_candidates.items():
            stage = rrp_data.get("stage", "dormant")
            if stage in ["emerging", "confirmed"]:
                signals.append(
                    SignalAlert(
                        asset=asset,
                        signal_type=SignalType.RRP,
                        score=rrp_data.get("score", 0),
                        confidence=rrp_data.get("confidence", 0.5),
                        reasoning=f"Revival {stage} - Acceleration {rrp_data.get('acceleration_rate', 0):.1f}%",
                        action=ActionType.HOLD,
                        timestamp=datetime.utcnow(),
                        severity=Severity.MEDIUM if stage == "confirmed" else Severity.LOW,
                        next_action="Watch for continuation",
                    )
                )

        # RCM signals
        for asset, rcm_data in rcm_rotations.items():
            cf_strength = rcm_data.get("capital_flow_strength", 0)
            if abs(cf_strength) > 0.6:
                signals.append(
                    SignalAlert(
                        asset=asset,
                        signal_type=SignalType.RCM,
                        score=abs(cf_strength) * 100,
                        confidence=rcm_data.get("confidence", 0.5),
                        reasoning=f"Capital {rcm_data.get('rotation_type', 'unknown')} - Strength {cf_strength:.2f}",
                        action=ActionType.RESEARCH,
                        timestamp=datetime.utcnow(),
                        severity=Severity.MEDIUM,
                        next_action="Monitor capital flows",
                    )
                )

        return signals

    def _score_to_severity(self, score: float) -> Severity:
        """Convert score to severity level."""
        if score >= 85:
            return Severity.CRITICAL
        elif score >= 70:
            return Severity.HIGH
        elif score >= 50:
            return Severity.MEDIUM
        else:
            return Severity.LOW

    async def get_bce_analysis(self, asset: str, bce_data: Dict) -> BCEAnalysis:
        """Convert BCE data to dashboard format."""
        return BCEAnalysis(
            asset=asset,
            overall_score=bce_data.get("score", 0),
            validity=bce_data.get("score", 0) >= 5,
            confidence=bce_data.get("confidence", 0.5),
            components=[],  # Populated from layer3
            stage=bce_data.get("stage", "mixed"),
            reasoning=bce_data.get("reasoning", ""),
            entry_ready=bce_data.get("entry_ready", False),
            risk_rating="high" if bce_data.get("score", 0) < 3 else "low",
            timestamp=datetime.utcnow(),
        )

    async def get_x20_report(self, x20_data: Dict[str, Any]) -> X20Report:
        """Convert X20 scores to report."""
        from .api_models import X20Opportunity

        opportunities = []
        for asset, data in sorted(
            x20_data.items(), key=lambda x: x[1].get("score", 0), reverse=True
        )[:10]:
            opportunities.append(
                X20Opportunity(
                    asset=asset,
                    score=data.get("score", 0),
                    rank=len(opportunities) + 1,
                    fundamental_score=data.get("fundamental_score", 0),
                    narrative_score=data.get("narrative_score", 0),
                    quantitative_score=data.get("quantitative_score", 0),
                    asymmetric_potential=data.get("asymmetric_potential", 1.0),
                    momentum=data.get("momentum", "stable"),
                    recommendation="research" if data.get("score", 0) >= 75 else "hold",
                )
            )

        return X20Report(
            timestamp=datetime.utcnow(), opportunities=opportunities, total_tracked=len(x20_data)
        )

    async def get_rrp_report(self, rrp_data: Dict[str, Any]) -> RRPReport:
        """Convert RRP candidates to report."""
        from .api_models import RRPCandidate

        by_stage: Dict[str, list] = {
            "dormant": [],
            "early_signs": [],
            "emerging": [],
            "confirmed": [],
        }

        for asset, data in rrp_data.items():
            stage = data.get("stage", "dormant")
            candidate = RRPCandidate(
                asset=asset,
                score=data.get("score", 0),
                confidence=data.get("confidence", 0.5),
                stage=stage,
                dormancy_days=data.get("dormancy_days", 0),
                acceleration_rate=data.get("acceleration_rate", 0),
                estimated_peak_days=data.get("estimated_peak_days"),
                momentum_direction=data.get("momentum_direction", "stable"),
            )
            by_stage[stage].append(candidate)

        return RRPReport(
            timestamp=datetime.utcnow(),
            by_stage=by_stage,
            total_candidates=len(rrp_data),
        )

    async def get_rcm_report(self, rcm_data: Dict[str, Any]) -> RCMReport:
        """Convert RCM rotations to report."""
        from .api_models import RCMRotation

        rotations = []
        for asset, data in rcm_data.items():
            cf_strength = data.get("capital_flow_strength", 0)
            if abs(cf_strength) > 0.3:
                rotations.append(
                    RCMRotation(
                        asset=asset,
                        rotation_type=data.get("rotation_type", "unknown"),
                        confidence=data.get("confidence", 0.5),
                        capital_flow_strength=cf_strength,
                        duration_days=data.get("duration_days", 0),
                        next_trigger=data.get("next_trigger", "Continued outflow"),
                    )
                )

        return RCMReport(
            timestamp=datetime.utcnow(),
            active_rotations=rotations,
            key_signals=[s.asset for s in rotations[:3]],
        )

    def add_watchlist_item(self, asset: str, status: str, note: str = ""):
        """Add/update watchlist item."""
        self.watchlist[asset] = {
            "status": status,
            "note": note,
            "added": datetime.utcnow().isoformat(),
        }

    async def get_watchlist(self) -> PortfolioReport:
        """Get current watchlist."""
        from .api_models import PortfolioMetric

        metrics = []
        for asset, data in self.watchlist.items():
            metrics.append(
                PortfolioMetric(
                    asset=asset,
                    watch_status=data.get("status", "research"),
                    entry_price=data.get("entry_price"),
                    current_observation=data.get("observation", ""),
                    note=data.get("note", ""),
                )
            )

        return PortfolioReport(
            timestamp=datetime.utcnow(),
            watchlist=metrics,
            total_positions=len(metrics),
        )
