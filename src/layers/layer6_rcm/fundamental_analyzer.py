"""Fundamental Analyzer for Phase 6 RCM/RPM.

Validates on-chain metrics, TVL, token unlocks, and developer activity.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import statistics


@dataclass
class OnChainMetrics:
    """On-chain activity and health metrics."""

    daily_active_users: int  # DAU trend (7d avg)
    dau_growth_rate: float  # % change week-over-week
    transaction_volume: float  # 7d average transaction volume
    transaction_volume_growth: float  # % growth
    whale_transaction_count: int  # Large tx count per day
    exchange_withdrawal_net: float  # Net exchange withdrawals (positive = bullish)
    score: float  # 0-100


@dataclass
class TVLAnalysis:
    """Total Value Locked (TVL) for DeFi narratives."""

    current_tvl: float  # Current TVL in USD or protocol units
    tvl_7d_change: float  # % change
    tvl_30d_change: float  # % change over 30 days
    tvl_trend: str  # "growing", "stable", "declining"
    major_deposits_7d: int  # Count of large deposits
    major_withdrawals_7d: int  # Count of large withdrawals
    score: float  # 0-100


@dataclass
class TokenUnlockRisk:
    """Token unlock schedule risk assessment."""

    next_unlock_date: Optional[datetime]
    days_to_next_unlock: Optional[int]
    unlock_percentage: float  # % of supply that unlocks
    total_unlock_events_90d: int  # Events in next 90 days
    concentration_risk: float  # 0-1 (how concentrated are unlocks)
    estimated_sell_pressure: float  # Expected price impact
    score: float  # 0-100


@dataclass
class DeveloperActivity:
    """Developer engagement and ecosystem health."""

    weekly_commits: int  # Code commits per week
    commit_growth: float  # % change in commits
    active_developers: int  # Count of active devs
    ecosystem_projects_count: int  # Number of projects building
    security_audit_status: str  # "passed", "in_progress", "none"
    score: float  # 0-100


@dataclass
class FundamentalAnalysis:
    """Complete fundamental analysis."""

    asset: str
    timestamp: datetime
    on_chain_metrics: OnChainMetrics
    tvl_analysis: Optional[TVLAnalysis]
    token_unlock_risk: TokenUnlockRisk
    developer_activity: DeveloperActivity
    fundamental_score: float  # Weighted 0-100
    risk_level: str  # "low", "medium", "high"
    confidence_level: float  # 0-1


class FundamentalAnalyzer:
    """Analyzes on-chain fundamentals and ecosystem health."""

    def __init__(self):
        """Initialize analyzer."""
        self.analysis_history: Dict[str, List[FundamentalAnalysis]] = {}

    def analyze_fundamentals(
        self,
        asset: str,
        on_chain_data: Dict,
        tvl_data: Optional[Dict] = None,
        unlock_data: Optional[Dict] = None,
        dev_data: Optional[Dict] = None,
    ) -> FundamentalAnalysis:
        """
        Analyze fundamental health of asset.

        Args:
            asset: Asset symbol
            on_chain_data: DAU, transactions, whale activity
            tvl_data: TVL trends (optional, for DeFi)
            unlock_data: Token unlock schedule
            dev_data: Developer activity and security

        Returns:
            FundamentalAnalysis with component scores
        """
        on_chain = self._analyze_on_chain(asset, on_chain_data)
        tvl = self._analyze_tvl(tvl_data) if tvl_data else None
        unlocks = self._analyze_unlock_risk(asset, unlock_data or {})
        devs = self._analyze_developer_activity(asset, dev_data or {})

        # Calculate weighted score
        on_chain_weight = 0.35
        tvl_weight = 0.20 if tvl else 0.0
        unlock_weight = 0.20
        dev_weight = 0.25

        # Normalize weights if TVL not present
        if tvl is None:
            on_chain_weight = 0.40
            unlock_weight = 0.25
            dev_weight = 0.35

        fundamental_score = (
            on_chain.score * on_chain_weight
            + (tvl.score * tvl_weight if tvl else 0)
            + unlocks.score * unlock_weight
            + devs.score * dev_weight
        )
        fundamental_score = min(100, max(0, fundamental_score))

        # Assess risk level
        risk_level = self._assess_risk_level(on_chain, tvl, unlocks, devs)

        # Confidence based on data completeness
        confidence = (
            1.0
            if (tvl is not None and unlock_data and dev_data)
            else 0.8 if (unlock_data or dev_data) else 0.6
        )

        analysis = FundamentalAnalysis(
            asset=asset,
            timestamp=datetime.utcnow(),
            on_chain_metrics=on_chain,
            tvl_analysis=tvl,
            token_unlock_risk=unlocks,
            developer_activity=devs,
            fundamental_score=fundamental_score,
            risk_level=risk_level,
            confidence_level=confidence,
        )

        # Track history
        if asset not in self.analysis_history:
            self.analysis_history[asset] = []
        self.analysis_history[asset].append(analysis)

        return analysis

    def _analyze_on_chain(
        self, asset: str, on_chain_data: Dict
    ) -> OnChainMetrics:
        """Analyze on-chain activity metrics."""
        dau = on_chain_data.get("daily_active_users", 0)
        dau_growth = on_chain_data.get("dau_growth_rate", 0)
        tx_vol = on_chain_data.get("transaction_volume", 0)
        tx_growth = on_chain_data.get("transaction_volume_growth", 0)
        whale_txs = on_chain_data.get("whale_transaction_count", 0)
        exchange_net = on_chain_data.get("exchange_withdrawal_net", 0)

        # Score based on DAU and growth
        if dau > 100000:
            score = 80
        elif dau > 50000:
            score = 70
        elif dau > 10000:
            score = 60
        elif dau > 1000:
            score = 40
        else:
            score = 20

        # Boost for growth
        if dau_growth > 20:
            score = min(100, score + 20)
        elif dau_growth > 10:
            score = min(100, score + 15)
        elif dau_growth > 0:
            score = min(100, score + 10)
        elif dau_growth < -10:
            score = max(0, score - 15)

        # Transaction activity
        if tx_growth > 15:
            score = min(100, score + 10)

        # Whale activity
        if whale_txs > 50:
            score = min(100, score + 10)

        # Exchange net (positive = outflow, bullish)
        if exchange_net > 100:
            score = min(100, score + 5)

        return OnChainMetrics(
            daily_active_users=dau,
            dau_growth_rate=dau_growth,
            transaction_volume=tx_vol,
            transaction_volume_growth=tx_growth,
            whale_transaction_count=whale_txs,
            exchange_withdrawal_net=exchange_net,
            score=max(0, min(100, score)),
        )

    def _analyze_tvl(self, tvl_data: Dict) -> Optional[TVLAnalysis]:
        """Analyze TVL trends (for DeFi)."""
        if not tvl_data:
            return None

        current = tvl_data.get("current_tvl", 0)
        change_7d = tvl_data.get("tvl_7d_change", 0)
        change_30d = tvl_data.get("tvl_30d_change", 0)
        deposits = tvl_data.get("major_deposits_7d", 0)
        withdrawals = tvl_data.get("major_withdrawals_7d", 0)

        # Determine trend
        if change_7d > 10:
            trend = "growing"
        elif change_7d < -10:
            trend = "declining"
        else:
            trend = "stable"

        # Score based on TVL and trend
        if current > 1_000_000_000:
            score = 75  # Multi-billion TVL
        elif current > 100_000_000:
            score = 65  # 100M+ TVL
        elif current > 10_000_000:
            score = 55  # 10M+ TVL
        else:
            score = 30

        # Boost for growth
        if change_7d > 20:
            score = min(100, score + 20)
        elif change_7d > 10:
            score = min(100, score + 15)
        elif change_30d < -30:
            score = max(0, score - 20)

        # Deposit/withdrawal ratio
        if deposits > withdrawals * 2:
            score = min(100, score + 10)

        return TVLAnalysis(
            current_tvl=current,
            tvl_7d_change=change_7d,
            tvl_30d_change=change_30d,
            tvl_trend=trend,
            major_deposits_7d=deposits,
            major_withdrawals_7d=withdrawals,
            score=max(0, min(100, score)),
        )

    def _analyze_unlock_risk(
        self, asset: str, unlock_data: Dict
    ) -> TokenUnlockRisk:
        """Analyze token unlock schedule risks."""
        next_unlock = unlock_data.get("next_unlock_date")
        days_to = unlock_data.get("days_to_next_unlock")
        unlock_pct = unlock_data.get("unlock_percentage", 0)
        events_90d = unlock_data.get("total_unlock_events_90d", 0)
        concentration = unlock_data.get("concentration_risk", 0.5)

        # Base score: penalize near-term unlocks
        if days_to is None or days_to > 90:
            score = 80  # No near-term risk
        elif days_to > 30:
            score = 60 - (unlock_pct * 0.5)
        elif days_to > 14:
            score = 40 - (unlock_pct * 0.5)
        else:
            score = 20 - (unlock_pct * 0.5)

        # Penalize concentrated unlocks
        if concentration > 0.7:
            score = max(0, score - 20)

        # Multiple events coming = pressure
        if events_90d > 5:
            score = max(0, score - 15)

        # Estimate sell pressure
        if days_to and days_to < 30:
            sell_pressure = unlock_pct * 0.5
        else:
            sell_pressure = 0

        return TokenUnlockRisk(
            next_unlock_date=next_unlock,
            days_to_next_unlock=days_to,
            unlock_percentage=unlock_pct,
            total_unlock_events_90d=events_90d,
            concentration_risk=concentration,
            estimated_sell_pressure=sell_pressure,
            score=max(0, min(100, score)),
        )

    def _analyze_developer_activity(
        self, asset: str, dev_data: Dict
    ) -> DeveloperActivity:
        """Analyze developer engagement and ecosystem."""
        commits = dev_data.get("weekly_commits", 0)
        commit_growth = dev_data.get("commit_growth", 0)
        dev_count = dev_data.get("active_developers", 0)
        ecosystem_projects = dev_data.get("ecosystem_projects_count", 0)
        audit_status = dev_data.get("security_audit_status", "none")

        # Base score on developer count
        if dev_count >= 50:
            score = 80
        elif dev_count >= 20:
            score = 70
        elif dev_count >= 10:
            score = 60
        elif dev_count >= 5:
            score = 45
        else:
            score = 25

        # Commit activity
        if commits > 200:
            score = min(100, score + 15)
        elif commits > 100:
            score = min(100, score + 10)
        elif commits > 50:
            score = min(100, score + 5)

        # Growth in commits
        if commit_growth > 20:
            score = min(100, score + 10)

        # Ecosystem activity
        if ecosystem_projects > 100:
            score = min(100, score + 15)
        elif ecosystem_projects > 50:
            score = min(100, score + 10)
        elif ecosystem_projects > 20:
            score = min(100, score + 5)

        # Security audit status
        if audit_status == "passed":
            score = min(100, score + 10)
        elif audit_status == "in_progress":
            score = min(100, score + 5)

        return DeveloperActivity(
            weekly_commits=commits,
            commit_growth=commit_growth,
            active_developers=dev_count,
            ecosystem_projects_count=ecosystem_projects,
            security_audit_status=audit_status,
            score=max(0, min(100, score)),
        )

    def _assess_risk_level(
        self,
        on_chain: OnChainMetrics,
        tvl: Optional[TVLAnalysis],
        unlocks: TokenUnlockRisk,
        devs: DeveloperActivity,
    ) -> str:
        """Assess overall risk level."""
        risk_factors = 0

        # On-chain metrics
        if on_chain.score < 40:
            risk_factors += 2

        # TVL declining
        if tvl and tvl.tvl_trend == "declining":
            risk_factors += 1

        # Near-term unlocks
        if unlocks.days_to_next_unlock and unlocks.days_to_next_unlock < 30:
            risk_factors += 2

        # Low dev activity
        if devs.active_developers < 5:
            risk_factors += 1

        if risk_factors >= 4:
            return "high"
        elif risk_factors >= 2:
            return "medium"
        else:
            return "low"

    def audit_fundamentals(self, asset: str) -> Dict:
        """Audit fundamental analysis history."""
        if asset not in self.analysis_history:
            return {
                "asset": asset,
                "analyses": 0,
                "avg_score": 0.0,
                "risk_trend": "unknown",
            }

        history = self.analysis_history[asset]
        scores = [a.fundamental_score for a in history]
        risks = [a.risk_level for a in history]

        return {
            "asset": asset,
            "analyses": len(history),
            "avg_score": statistics.mean(scores) if scores else 0.0,
            "latest_score": scores[-1] if scores else 0.0,
            "current_risk": risks[-1] if risks else "unknown",
            "min_score": min(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
        }
