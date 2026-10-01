"""
Phase 5: Capital Flow Validator for NARM-P+

Validates capital rotation signals using on-chain data:
- Whale address accumulation
- Exchange inflow/outflow patterns
- Smart money tracking
- Institutional address activity
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class WhaleMetrics:
    """Metrics for large address accumulation."""

    asset: str
    large_addresses_count: int  # >$1M
    accumulating_addresses: int  # Net positive balance change
    distribution_addresses: int  # Net negative (selling)
    net_whale_flow: float  # % of supply
    whale_confidence: str  # high/medium/low
    accumulation_rate: float  # % per period


@dataclass
class ExchangeFlowMetrics:
    """Exchange inflow/outflow patterns."""

    asset: str
    total_exchange_inflow: float  # In BTC/ETH equivalent
    total_exchange_outflow: float
    net_exchange_flow: float  # Outflow = bullish
    exchange_net_ratio: float  # Outflow/Inflow ratio
    large_withdrawal_count: int  # >1M USD equivalent
    withdrawal_acceleration: float  # % change rate


@dataclass
class SmartMoneySignal:
    """Smart money tracking signals."""

    asset: str
    smart_money_addresses_active: int
    smart_money_avg_holding_period: int  # Days
    smart_money_recent_accumulation: bool
    smart_money_unrealized_gain: float  # % profit
    confidence_score: float  # 0-1


@dataclass
class CapitalFlowValidation:
    """Complete capital flow validation against NARM signal."""

    asset: str
    narm_rotation_score: float
    capital_flow_confirmed: bool  # True if flows align with NARM
    validation_confidence: float  # 0-1
    whale_metrics: WhaleMetrics
    exchange_metrics: ExchangeFlowMetrics
    smart_money_signal: SmartMoneySignal
    on_chain_alignment: str  # strong/moderate/weak/none
    false_positive_risk: float  # 0-1 (risk that signal is false)
    reasoning: List[str]


class CapitalFlowValidator:
    """Validate capital rotation signals on-chain."""

    # Validation thresholds
    WHALE_CONFIDENCE_THRESHOLD = 0.5
    EXCHANGE_OUTFLOW_SIGNIFICANT = 1000.0  # BTC equivalent
    SMART_MONEY_ACTIVE_MIN = 5  # Addresses
    ALIGNMENT_STRONG_THRESHOLD = 0.75
    ALIGNMENT_MODERATE_THRESHOLD = 0.50

    def __init__(self):
        """Initialize validator."""
        self.validation_history: List[CapitalFlowValidation] = []

    def validate_capital_flow(
        self,
        asset: str,
        narm_rotation_score: float,
        on_chain_data: Dict,
    ) -> CapitalFlowValidation:
        """
        Validate NARM rotation signal against on-chain capital flows.

        Args:
            asset: Asset symbol
            narm_rotation_score: NARM score (0-100)
            on_chain_data: Dict with whale, exchange, smart money data

        Returns:
            CapitalFlowValidation with alignment assessment
        """
        # Extract on-chain metrics
        whale_metrics = self._calculate_whale_metrics(
            asset, on_chain_data.get("whale_data", {})
        )
        exchange_metrics = self._calculate_exchange_metrics(
            asset, on_chain_data.get("exchange_data", {})
        )
        smart_money = self._track_smart_money(
            asset, on_chain_data.get("smart_money_data", {})
        )

        # Calculate alignment
        alignment_score = self._calculate_alignment_score(
            narm_rotation_score,
            whale_metrics,
            exchange_metrics,
            smart_money,
        )

        # Determine alignment strength
        if alignment_score >= self.ALIGNMENT_STRONG_THRESHOLD:
            alignment = "strong"
        elif alignment_score >= self.ALIGNMENT_MODERATE_THRESHOLD:
            alignment = "moderate"
        elif alignment_score > 0.25:
            alignment = "weak"
        else:
            alignment = "none"

        # Calculate false positive risk
        false_positive_risk = 1.0 - alignment_score

        # Capital flow confirmed if alignment >= moderate
        confirmed = alignment_score >= self.ALIGNMENT_MODERATE_THRESHOLD

        # Build reasoning
        reasoning = self._build_validation_reasoning(
            narm_rotation_score,
            whale_metrics,
            exchange_metrics,
            smart_money,
            alignment_score,
        )

        validation = CapitalFlowValidation(
            asset=asset,
            narm_rotation_score=narm_rotation_score,
            capital_flow_confirmed=confirmed,
            validation_confidence=alignment_score,
            whale_metrics=whale_metrics,
            exchange_metrics=exchange_metrics,
            smart_money_signal=smart_money,
            on_chain_alignment=alignment,
            false_positive_risk=false_positive_risk,
            reasoning=reasoning,
        )

        self.validation_history.append(validation)
        return validation

    def _calculate_whale_metrics(
        self,
        asset: str,
        whale_data: Dict,
    ) -> WhaleMetrics:
        """Calculate large address metrics."""
        large_count = whale_data.get("large_addresses_count", 0)
        accumulating = whale_data.get("accumulating_addresses", 0)
        distributing = whale_data.get("distributing_addresses", 0)
        net_flow_pct = whale_data.get("net_whale_flow_pct", 0.0)
        accumulation_rate = whale_data.get("accumulation_rate", 0.0)

        # Whale confidence based on accumulation > distribution
        if accumulating > distributing * 2:
            confidence = "high"
        elif accumulating > distributing:
            confidence = "medium"
        else:
            confidence = "low"

        return WhaleMetrics(
            asset=asset,
            large_addresses_count=large_count,
            accumulating_addresses=accumulating,
            distribution_addresses=distributing,
            net_whale_flow=net_flow_pct,
            whale_confidence=confidence,
            accumulation_rate=accumulation_rate,
        )

    def _calculate_exchange_metrics(
        self,
        asset: str,
        exchange_data: Dict,
    ) -> ExchangeFlowMetrics:
        """Calculate exchange flow patterns."""
        inflow = exchange_data.get("total_inflow", 0.0)
        outflow = exchange_data.get("total_outflow", 0.0)
        net_flow = outflow - inflow  # Positive = withdrawals (bullish)
        ratio = outflow / max(inflow, 1.0)
        large_withdrawals = exchange_data.get("large_withdrawal_count", 0)
        accel = exchange_data.get("withdrawal_acceleration", 0.0)

        return ExchangeFlowMetrics(
            asset=asset,
            total_exchange_inflow=inflow,
            total_exchange_outflow=outflow,
            net_exchange_flow=net_flow,
            exchange_net_ratio=ratio,
            large_withdrawal_count=large_withdrawals,
            withdrawal_acceleration=accel,
        )

    def _track_smart_money(
        self,
        asset: str,
        smart_money_data: Dict,
    ) -> SmartMoneySignal:
        """Track smart money activity."""
        active_addresses = smart_money_data.get("active_addresses", 0)
        avg_holding = smart_money_data.get("avg_holding_period_days", 0)
        recent_accum = smart_money_data.get("recent_accumulation", False)
        unrealized = smart_money_data.get("unrealized_gain_pct", 0.0)

        # Confidence: active addresses + holding period + recent activity
        address_confidence = min(active_addresses / 10.0, 1.0) * 0.4
        holding_confidence = (
            min(avg_holding / 365.0, 1.0) * 0.3
        )  # Longer holding = commitment
        activity_confidence = 0.3 if recent_accum else 0.1

        confidence = address_confidence + holding_confidence + activity_confidence

        return SmartMoneySignal(
            asset=asset,
            smart_money_addresses_active=active_addresses,
            smart_money_avg_holding_period=avg_holding,
            smart_money_recent_accumulation=recent_accum,
            smart_money_unrealized_gain=unrealized,
            confidence_score=confidence,
        )

    def _calculate_alignment_score(
        self,
        narm_score: float,
        whale_metrics: WhaleMetrics,
        exchange_metrics: ExchangeFlowMetrics,
        smart_money: SmartMoneySignal,
    ) -> float:
        """
        Calculate how well on-chain flows align with NARM signal.

        Returns:
            0-1 alignment score
        """
        components = []

        # NARM signal strength (higher = stronger signal)
        narm_component = min(narm_score / 100.0, 1.0) * 0.3

        # Whale accumulation (must be positive)
        whale_component = 0.0
        if whale_metrics.whale_confidence == "high":
            whale_component = 0.8
        elif whale_metrics.whale_confidence == "medium":
            whale_component = 0.5
        whale_component *= 0.25

        # Exchange flows (net outflow is bullish)
        exchange_component = 0.0
        if exchange_metrics.net_exchange_flow > 100:  # Significant outflow
            exchange_component = 0.8
        elif exchange_metrics.net_exchange_flow > 0:
            exchange_component = 0.4
        exchange_component *= 0.25

        # Smart money activity
        smart_component = smart_money.confidence_score * 0.2

        alignment = narm_component + whale_component + exchange_component + smart_component

        return min(1.0, max(0.0, alignment))

    def _build_validation_reasoning(
        self,
        narm_score: float,
        whale_metrics: WhaleMetrics,
        exchange_metrics: ExchangeFlowMetrics,
        smart_money: SmartMoneySignal,
        alignment: float,
    ) -> List[str]:
        """Build detailed reasoning for validation."""
        reasoning = []

        # NARM assessment
        if narm_score >= 75:
            reasoning.append(f"Strong NARM signal: {narm_score:.1f} (high confidence)")
        elif narm_score >= 65:
            reasoning.append(f"Moderate NARM signal: {narm_score:.1f}")
        else:
            reasoning.append(f"Weak NARM signal: {narm_score:.1f} (borderline)")

        # Whale assessment
        accumulation_ratio = (
            whale_metrics.accumulating_addresses / max(whale_metrics.large_addresses_count, 1)
        )
        reasoning.append(
            f"Whale metrics: {whale_metrics.accumulating_addresses} accumulating "
            f"({accumulation_ratio*100:.0f}%), confidence: {whale_metrics.whale_confidence}"
        )

        # Exchange flows
        if exchange_metrics.net_exchange_flow > 500:
            reasoning.append(
                f"Strong exchange outflow detected: {exchange_metrics.net_exchange_flow:.1f} BTC equivalent"
            )
        elif exchange_metrics.net_exchange_flow > 0:
            reasoning.append(
                f"Exchange outflow: {exchange_metrics.net_exchange_flow:.1f} BTC (positive signal)"
            )
        else:
            reasoning.append(
                f"Exchange inflow: {abs(exchange_metrics.net_exchange_flow):.1f} BTC (caution)"
            )

        # Smart money
        reasoning.append(
            f"Smart money: {smart_money.smart_money_addresses_active} active addresses, "
            f"avg holding: {smart_money.smart_money_avg_holding_period} days, "
            f"confidence: {smart_money.confidence_score:.2f}"
        )

        # Overall alignment
        reasoning.append(
            f"Capital flow alignment score: {alignment:.2f} "
            f"({'STRONG' if alignment >= 0.75 else 'MODERATE' if alignment >= 0.50 else 'WEAK'})"
        )

        return reasoning

    def compare_validations(
        self,
        asset: str,
        limit: int = 10,
    ) -> Dict:
        """Compare validation history for an asset."""
        asset_validations = [
            v for v in self.validation_history if v.asset == asset
        ][-limit:]

        if not asset_validations:
            return {}

        return {
            "asset": asset,
            "total_validations": len(asset_validations),
            "confirmed_flows": sum(
                1 for v in asset_validations if v.capital_flow_confirmed
            ),
            "avg_alignment": (
                sum(v.validation_confidence for v in asset_validations)
                / len(asset_validations)
            ),
            "avg_false_positive_risk": (
                sum(v.false_positive_risk for v in asset_validations)
                / len(asset_validations)
            ),
            "latest_validation": asset_validations[-1].on_chain_alignment,
        }

    def audit_validation_accuracy(self) -> Dict:
        """Audit trail for validation accuracy."""
        if not self.validation_history:
            return {"error": "No validation history"}

        confirmed_count = sum(
            1 for v in self.validation_history if v.capital_flow_confirmed
        )
        strong_alignment = sum(
            1 for v in self.validation_history if v.on_chain_alignment == "strong"
        )

        return {
            "total_validations": len(self.validation_history),
            "confirmed_flows_pct": (
                confirmed_count / len(self.validation_history) * 100
            ),
            "strong_alignment_pct": (
                strong_alignment / len(self.validation_history) * 100
            ),
            "avg_alignment_score": (
                sum(v.validation_confidence for v in self.validation_history)
                / len(self.validation_history)
            ),
            "false_positive_rate": (
                sum(v.false_positive_risk for v in self.validation_history)
                / len(self.validation_history)
            ),
        }
