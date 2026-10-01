"""Capital Flow Tracker for Phase 6 RCM/RPM Engine.

Analyzes whale accumulation, exchange flows, and smart money activity.
Outputs capital_flow_score (0-100) measuring conviction of rotation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
import statistics


@dataclass
class WhaleAccumulation:
    """Whale-level accumulation metrics."""

    large_addresses_count: int  # Addresses with >10% of supply
    accumulating_addresses: int  # Addresses increasing position
    distributing_addresses: int  # Addresses decreasing position
    net_accumulation_pct: float  # Net change in large address holdings (%)
    acceleration_rate: float  # Change in accumulation rate (derivative)
    confidence: str  # "high", "medium", "low"
    score: float  # 0-100


@dataclass
class ExchangeFlowMetrics:
    """Exchange inflow/outflow patterns."""

    net_exchange_flow: float  # Outflow - inflow (positive = bullish)
    inflow_velocity: float  # Rate of inflows
    outflow_velocity: float  # Rate of outflows
    large_withdrawal_acceleration: float  # Change in large withdrawal rate
    exchange_net_ratio: float  # Outflow / Inflow ratio
    stablecoin_inflow: float  # USDC/USDT inflow (hedging signal)
    score: float  # 0-100


@dataclass
class SmartMoneySignal:
    """Smart money wallet tracking."""

    active_smart_wallets: int  # Wallets identified as smart money
    avg_holding_period_days: float  # Average holding duration
    recent_accumulation: bool  # Active accumulation in last 7d
    unrealized_gain_pct: float  # Average gains on holdings
    win_rate_pct: float  # % of positions in profit
    follow_count: int  # How many wallets are following this pattern
    score: float  # 0-100


@dataclass
class LargeTransactionCluster:
    """Clustering of large transactions."""

    cluster_count: int  # Number of distinct clusters
    cluster_size_avg: float  # Average transactions per cluster
    time_span_hours: float  # Hours between first and last in cluster
    total_volume: float  # Total volume in clusters
    estimated_cost_basis: float  # Estimated average entry price
    score: float  # 0-100


@dataclass
class CapitalFlowAnalysis:
    """Complete capital flow analysis result."""

    asset: str
    timestamp: datetime
    whale_accumulation: WhaleAccumulation
    exchange_flows: ExchangeFlowMetrics
    smart_money: SmartMoneySignal
    transaction_clusters: LargeTransactionCluster
    capital_flow_score: float  # Weighted 0-100
    scoring_confidence: float  # Confidence in score (0-1)
    bullish_signals: int  # Count of bullish indicators
    bearish_signals: int  # Count of bearish indicators
    analysis_components: Dict[str, float] = field(default_factory=dict)


class CapitalFlowTracker:
    """Tracks capital flows into/out of narratives."""

    def __init__(self):
        """Initialize tracker."""
        self.analysis_history: Dict[str, List[CapitalFlowAnalysis]] = {}

    def analyze_capital_flow(
        self,
        asset: str,
        whale_data: Dict,
        exchange_data: Dict,
        smart_money_data: Dict,
        transaction_data: Dict,
    ) -> CapitalFlowAnalysis:
        """
        Analyze complete capital flow picture.

        Args:
            asset: Asset symbol (e.g. BTC, ETH)
            whale_data: Large address metrics
            exchange_data: Exchange inflow/outflow data
            smart_money_data: Smart wallet tracking data
            transaction_data: Large transaction cluster data

        Returns:
            CapitalFlowAnalysis with component scores and overall score
        """
        whale = self._analyze_whale_accumulation(asset, whale_data)
        exchange = self._analyze_exchange_flows(asset, exchange_data)
        smart_money = self._analyze_smart_money(asset, smart_money_data)
        clusters = self._analyze_transaction_clusters(asset, transaction_data)

        # Calculate weighted score
        capital_flow_score = (
            whale.score * 0.30
            + exchange.score * 0.30
            + smart_money.score * 0.25
            + clusters.score * 0.15
        )
        capital_flow_score = min(100, max(0, capital_flow_score))

        # Count bullish/bearish signals
        bullish = self._count_bullish_signals(
            whale, exchange, smart_money, clusters
        )
        bearish = self._count_bearish_signals(
            whale, exchange, smart_money, clusters
        )

        # Confidence: agreement among signals
        total_signals = bullish + bearish
        confidence = (
            max(bullish, bearish) / total_signals
            if total_signals > 0
            else 0.5
        )

        analysis = CapitalFlowAnalysis(
            asset=asset,
            timestamp=datetime.utcnow(),
            whale_accumulation=whale,
            exchange_flows=exchange,
            smart_money=smart_money,
            transaction_clusters=clusters,
            capital_flow_score=capital_flow_score,
            scoring_confidence=confidence,
            bullish_signals=bullish,
            bearish_signals=bearish,
            analysis_components={
                "whale_score": whale.score,
                "exchange_score": exchange.score,
                "smart_money_score": smart_money.score,
                "cluster_score": clusters.score,
            },
        )

        # Track history
        if asset not in self.analysis_history:
            self.analysis_history[asset] = []
        self.analysis_history[asset].append(analysis)

        return analysis

    def _analyze_whale_accumulation(
        self, asset: str, whale_data: Dict
    ) -> WhaleAccumulation:
        """Analyze large address accumulation patterns."""
        accum = whale_data.get("accumulating_addresses", 0)
        distrib = whale_data.get("distributing_addresses", 0)
        net_accum = whale_data.get("net_accumulation_pct", 0)
        accel = whale_data.get("acceleration_rate", 0)
        total = whale_data.get("large_addresses_count", 0)

        # Determine confidence level
        if total == 0:
            confidence = "low"
            score = 0.0
        elif accum > distrib * 2:
            confidence = "high"
            score = min(100, 70 + (net_accum * 2))
        elif accum > distrib:
            confidence = "medium"
            score = min(100, 50 + (net_accum))
        else:
            confidence = "low"
            score = max(0, 30 + (net_accum * 2))

        # Boost score if acceleration positive
        if accel > 0:
            score = min(100, score + (accel * 10))

        return WhaleAccumulation(
            large_addresses_count=total,
            accumulating_addresses=accum,
            distributing_addresses=distrib,
            net_accumulation_pct=net_accum,
            acceleration_rate=accel,
            confidence=confidence,
            score=max(0, min(100, score)),
        )

    def _analyze_exchange_flows(
        self, asset: str, exchange_data: Dict
    ) -> ExchangeFlowMetrics:
        """Analyze exchange inflow/outflow patterns."""
        inflow = exchange_data.get("total_inflow", 0)
        outflow = exchange_data.get("total_outflow", 0)
        inflow_vel = exchange_data.get("inflow_velocity", 0)
        outflow_vel = exchange_data.get("outflow_velocity", 0)
        large_withdraw_accel = exchange_data.get(
            "large_withdrawal_acceleration", 0
        )
        stablecoin_in = exchange_data.get("stablecoin_inflow", 0)

        net_flow = outflow - inflow  # Positive = bullish
        ratio = outflow / inflow if inflow > 0 else 0

        # Outflow > inflow is bullish (conviction)
        if net_flow > 0 and ratio > 1.5:
            score = min(100, 70 + (ratio * 10))
        elif net_flow > 0:
            score = min(100, 50 + (ratio * 20))
        elif net_flow < 0 and inflow > outflow * 2:
            score = max(0, 30 - (ratio * 20))
        else:
            score = 40

        # Large withdrawal acceleration = bullish conviction
        if large_withdraw_accel > 0:
            score = min(100, score + (large_withdraw_accel * 15))

        # High stablecoin inflow = potential hedging/preparation for sell
        if stablecoin_in > 0:
            score = max(0, score - (stablecoin_in * 0.1))

        return ExchangeFlowMetrics(
            net_exchange_flow=net_flow,
            inflow_velocity=inflow_vel,
            outflow_velocity=outflow_vel,
            large_withdrawal_acceleration=large_withdraw_accel,
            exchange_net_ratio=ratio,
            stablecoin_inflow=stablecoin_in,
            score=max(0, min(100, score)),
        )

    def _analyze_smart_money(
        self, asset: str, smart_money_data: Dict
    ) -> SmartMoneySignal:
        """Analyze smart money wallet activity."""
        active_wallets = smart_money_data.get("active_smart_wallets", 0)
        holding_period = smart_money_data.get("avg_holding_period_days", 0)
        recent_accum = smart_money_data.get("recent_accumulation", False)
        unrealized_gain = smart_money_data.get("unrealized_gain_pct", 0)
        win_rate = smart_money_data.get("win_rate_pct", 50)
        follow_count = smart_money_data.get("follow_count", 0)

        # Base score on activity level
        if active_wallets == 0:
            score = 0.0
        elif active_wallets >= 15:
            score = 60
        elif active_wallets >= 10:
            score = 50
        else:
            score = 40

        # Boost for long-term holding (conviction)
        if holding_period > 365:
            score = min(100, score + 20)
        elif holding_period > 180:
            score = min(100, score + 15)
        elif holding_period > 90:
            score = min(100, score + 10)

        # Recent accumulation = strong signal
        if recent_accum:
            score = min(100, score + 15)

        # Unrealized gains = winners (good timing)
        if unrealized_gain > 50:
            score = min(100, score + 15)
        elif unrealized_gain > 0:
            score = min(100, score + 10)
        elif unrealized_gain < -20:
            score = max(0, score - 10)

        # Win rate confidence
        if win_rate > 70:
            score = min(100, score + 10)
        elif win_rate < 40:
            score = max(0, score - 10)

        # Follow count = consensus
        if follow_count > 50:
            score = min(100, score + 10)

        return SmartMoneySignal(
            active_smart_wallets=active_wallets,
            avg_holding_period_days=holding_period,
            recent_accumulation=recent_accum,
            unrealized_gain_pct=unrealized_gain,
            win_rate_pct=win_rate,
            follow_count=follow_count,
            score=max(0, min(100, score)),
        )

    def _analyze_transaction_clusters(
        self, asset: str, transaction_data: Dict
    ) -> LargeTransactionCluster:
        """Analyze clustering of large transactions."""
        cluster_count = transaction_data.get("cluster_count", 0)
        cluster_size = transaction_data.get("cluster_size_avg", 0)
        time_span = transaction_data.get("time_span_hours", 1)
        total_vol = transaction_data.get("total_volume", 0)
        cost_basis = transaction_data.get("estimated_cost_basis", 0)

        # More clusters = more coordinated buying
        if cluster_count >= 5:
            score = 70
        elif cluster_count >= 3:
            score = 55
        elif cluster_count >= 1:
            score = 40
        else:
            score = 20

        # Tight time clustering = coordinated
        if time_span < 24 and cluster_count >= 3:
            score = min(100, score + 20)
        elif time_span < 72 and cluster_count >= 2:
            score = min(100, score + 10)

        # Large volume in clusters
        if total_vol > 1000:
            score = min(100, score + 15)
        elif total_vol > 100:
            score = min(100, score + 10)

        return LargeTransactionCluster(
            cluster_count=cluster_count,
            cluster_size_avg=cluster_size,
            time_span_hours=time_span,
            total_volume=total_vol,
            estimated_cost_basis=cost_basis,
            score=max(0, min(100, score)),
        )

    def _count_bullish_signals(
        self,
        whale: WhaleAccumulation,
        exchange: ExchangeFlowMetrics,
        smart_money: SmartMoneySignal,
        clusters: LargeTransactionCluster,
    ) -> int:
        """Count bullish signals across components."""
        count = 0

        # Whale signals
        if whale.confidence == "high":
            count += 2
        elif whale.confidence == "medium":
            count += 1
        if whale.acceleration_rate > 0:
            count += 1

        # Exchange signals
        if exchange.net_exchange_flow > 0:
            count += 1
        if exchange.exchange_net_ratio > 2:
            count += 1
        if exchange.large_withdrawal_acceleration > 0:
            count += 1

        # Smart money signals
        if smart_money.recent_accumulation:
            count += 1
        if smart_money.unrealized_gain_pct > 20:
            count += 1
        if smart_money.follow_count > 50:
            count += 1

        # Cluster signals
        if clusters.cluster_count >= 3:
            count += 1

        return count

    def _count_bearish_signals(
        self,
        whale: WhaleAccumulation,
        exchange: ExchangeFlowMetrics,
        smart_money: SmartMoneySignal,
        clusters: LargeTransactionCluster,
    ) -> int:
        """Count bearish signals across components."""
        count = 0

        # Whale signals
        if whale.confidence == "low":
            count += 2
        if whale.acceleration_rate < 0:
            count += 1
        if whale.distributing_addresses > whale.accumulating_addresses * 2:
            count += 1

        # Exchange signals
        if exchange.net_exchange_flow < 0:
            count += 1
        if exchange.inflow_velocity > exchange.outflow_velocity * 2:
            count += 1
        if exchange.stablecoin_inflow > 100:
            count += 1

        # Smart money signals
        if smart_money.unrealized_gain_pct < -20:
            count += 1
        if smart_money.win_rate_pct < 40:
            count += 1

        # Cluster signals
        if clusters.cluster_count == 0:
            count += 1

        return count

    def audit_capital_flow(self, asset: str) -> Dict:
        """Audit capital flow analysis history."""
        if asset not in self.analysis_history:
            return {
                "asset": asset,
                "analyses": 0,
                "avg_score": 0.0,
                "trend": "unknown",
                "latest_analysis": None,
            }

        history = self.analysis_history[asset]
        scores = [a.capital_flow_score for a in history]

        if len(scores) >= 2:
            trend = "up" if scores[-1] > scores[-2] else "down"
        else:
            trend = "unknown"

        return {
            "asset": asset,
            "analyses": len(history),
            "avg_score": statistics.mean(scores) if scores else 0.0,
            "latest_score": scores[-1] if scores else 0.0,
            "trend": trend,
            "min_score": min(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
            "latest_analysis": history[-1] if history else None,
        }
