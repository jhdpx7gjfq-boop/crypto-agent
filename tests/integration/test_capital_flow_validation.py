"""
Integration tests for Phase 5 Capital Flow Validator.

Tests whale accumulation, exchange flows, smart money, and on-chain alignment.
"""

import pytest

from src.layers.layer5_narm.capital_flow_validator import CapitalFlowValidator


class TestCapitalFlowValidator:
    """Test capital flow validation."""

    @pytest.fixture
    def validator(self):
        """Create capital flow validator."""
        return CapitalFlowValidator()

    def test_whale_metrics_calculation(self, validator):
        """Calculate large address accumulation."""
        whale_data = {
            "large_addresses_count": 50,
            "accumulating_addresses": 40,  # More accum than dist
            "distributing_addresses": 10,
            "net_whale_flow_pct": 2.5,
            "accumulation_rate": 1.2,
        }

        metrics = validator._calculate_whale_metrics("BTC", whale_data)

        assert metrics.large_addresses_count == 50
        assert metrics.accumulating_addresses == 40
        assert metrics.whale_confidence == "high"  # 40 > 10*2
        assert metrics.accumulation_rate == 1.2

    def test_exchange_flow_analysis(self, validator):
        """Analyze exchange inflow/outflow patterns."""
        exchange_data = {
            "total_inflow": 500.0,  # BTC
            "total_outflow": 800.0,  # More outflow (bullish)
            "large_withdrawal_count": 8,
            "withdrawal_acceleration": 0.15,  # Accelerating
        }

        metrics = validator._calculate_exchange_metrics("BTC", exchange_data)

        assert metrics.net_exchange_flow == 300.0  # Outflow > inflow
        assert metrics.exchange_net_ratio > 1.0  # Outflow > inflow
        assert metrics.large_withdrawal_count == 8

    def test_smart_money_tracking(self, validator):
        """Track smart money activity."""
        smart_money_data = {
            "active_addresses": 12,  # Multiple smart addresses
            "avg_holding_period_days": 240,  # Long-term holders
            "recent_accumulation": True,
            "unrealized_gain_pct": 45.0,
        }

        signal = validator._track_smart_money("BTC", smart_money_data)

        assert signal.smart_money_addresses_active == 12
        assert signal.smart_money_avg_holding_period == 240
        assert signal.smart_money_recent_accumulation is True
        assert signal.confidence_score > 0.5

    def test_narm_capital_flow_alignment(self, validator):
        """Validate NARM signal against on-chain flows."""
        narm_score = 78.0  # Strong rotation signal

        on_chain_data = {
            "whale_data": {
                "accumulating_addresses": 35,
                "distributing_addresses": 5,
                "net_whale_flow_pct": 2.0,
                "accumulation_rate": 1.5,
                "large_addresses_count": 40,
            },
            "exchange_data": {
                "total_inflow": 300.0,
                "total_outflow": 700.0,
                "large_withdrawal_count": 10,
                "withdrawal_acceleration": 0.2,
            },
            "smart_money_data": {
                "active_addresses": 15,
                "avg_holding_period_days": 300,
                "recent_accumulation": True,
                "unrealized_gain_pct": 50.0,
            },
        }

        validation = validator.validate_capital_flow(
            asset="BTC",
            narm_rotation_score=narm_score,
            on_chain_data=on_chain_data,
        )

        # Strong NARM with bullish on-chain = confirmed
        assert validation.capital_flow_confirmed
        assert validation.validation_confidence > 0.6
        assert validation.false_positive_risk < 0.4

    def test_false_positive_detection(self, validator):
        """Detect false positive NARM signals."""
        narm_score = 72.0  # Moderate rotation signal

        on_chain_data = {
            "whale_data": {
                "accumulating_addresses": 10,
                "distributing_addresses": 30,  # More distribution
                "net_whale_flow_pct": -1.5,
                "accumulation_rate": -0.5,
                "large_addresses_count": 40,
            },
            "exchange_data": {
                "total_inflow": 600.0,  # High inflow (bearish)
                "total_outflow": 200.0,
                "large_withdrawal_count": 2,
                "withdrawal_acceleration": -0.1,
            },
            "smart_money_data": {
                "active_addresses": 3,  # Few active
                "avg_holding_period_days": 60,  # Short-term
                "recent_accumulation": False,
                "unrealized_gain_pct": -15.0,  # Negative
            },
        }

        validation = validator.validate_capital_flow(
            asset="BTC",
            narm_rotation_score=narm_score,
            on_chain_data=on_chain_data,
        )

        # Bearish on-chain vs bullish NARM = false positive risk
        assert not validation.capital_flow_confirmed
        assert validation.false_positive_risk > 0.5

    def test_whale_confidence_levels(self, validator):
        """Whale confidence based on accumulation ratio."""
        # High confidence: many accumulating, few distributing
        high_conf_data = {
            "accumulating_addresses": 50,
            "distributing_addresses": 5,
            "large_addresses_count": 60,
            "net_whale_flow_pct": 3.0,
            "accumulation_rate": 2.0,
        }

        high_metrics = validator._calculate_whale_metrics("BTC", high_conf_data)
        assert high_metrics.whale_confidence == "high"

        # Medium confidence: roughly equal
        med_conf_data = {
            "accumulating_addresses": 25,
            "distributing_addresses": 20,
            "large_addresses_count": 50,
            "net_whale_flow_pct": 0.5,
            "accumulation_rate": 0.3,
        }

        med_metrics = validator._calculate_whale_metrics("BTC", med_conf_data)
        assert med_metrics.whale_confidence == "medium"

        # Low confidence: more distributing
        low_conf_data = {
            "accumulating_addresses": 10,
            "distributing_addresses": 40,
            "large_addresses_count": 50,
            "net_whale_flow_pct": -1.5,
            "accumulation_rate": -1.0,
        }

        low_metrics = validator._calculate_whale_metrics("BTC", low_conf_data)
        assert low_metrics.whale_confidence == "low"

    def test_exchange_outflow_bullish_signal(self, validator):
        """Exchange outflow is bullish signal."""
        # Significant outflow
        bullish_data = {
            "total_inflow": 200.0,
            "total_outflow": 1200.0,  # 6x inflow
            "large_withdrawal_count": 25,
            "withdrawal_acceleration": 0.35,
        }

        metrics = validator._calculate_exchange_metrics("BTC", bullish_data)

        assert metrics.net_exchange_flow == 1000.0
        assert metrics.exchange_net_ratio == 6.0
        # High ratio indicates strong outflow conviction

    def test_validation_history_tracking(self, validator):
        """Track validation history for audit."""
        on_chain_data = {
            "whale_data": {
                "accumulating_addresses": 30,
                "distributing_addresses": 10,
                "net_whale_flow_pct": 1.5,
                "accumulation_rate": 1.0,
                "large_addresses_count": 50,
            },
            "exchange_data": {
                "total_inflow": 400.0,
                "total_outflow": 600.0,
                "large_withdrawal_count": 8,
                "withdrawal_acceleration": 0.1,
            },
            "smart_money_data": {
                "active_addresses": 10,
                "avg_holding_period_days": 200,
                "recent_accumulation": True,
                "unrealized_gain_pct": 30.0,
            },
        }

        # Run multiple validations
        for i in range(3):
            validator.validate_capital_flow(
                asset="BTC",
                narm_rotation_score=70.0 + i * 5,
                on_chain_data=on_chain_data,
            )

        audit = validator.audit_validation_accuracy()

        assert audit["total_validations"] == 3
        assert audit["confirmed_flows_pct"] > 50
        assert audit["avg_alignment_score"] > 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
