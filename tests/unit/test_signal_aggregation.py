"""Unit tests for Signal Aggregation & Risk Controls."""

import pytest
from src.layers.layer7_decision.signal_aggregation import SignalAggregator, AggregatedSignal


@pytest.fixture
def aggregator():
    """Create SignalAggregator instance."""
    return SignalAggregator()


class TestConfluenceCount:
    def test_count_confluent_signals_all_true(self, aggregator):
        """Test all gates signal True."""
        count = aggregator.count_confluent_signals(
            bce_signal=True,
            x20_signal=True,
            narm_p_signal=True,
            rpm_signal=True,
            rrp_signal=True,
        )
        assert count == 5

    def test_count_confluent_signals_all_false(self, aggregator):
        """Test all gates signal False."""
        count = aggregator.count_confluent_signals(
            bce_signal=False,
            x20_signal=False,
            narm_p_signal=False,
            rpm_signal=False,
            rrp_signal=False,
        )
        assert count == 0

    def test_count_confluent_signals_partial(self, aggregator):
        """Test partial confluence."""
        count = aggregator.count_confluent_signals(
            bce_signal=True,
            x20_signal=True,
            narm_p_signal=False,
            rpm_signal=True,
            rrp_signal=False,
        )
        assert count == 3


class TestMultiGateConfluence:
    def test_validate_multi_gate_confluence_meets_threshold(self, aggregator):
        """Test confluence meets minimum."""
        valid = aggregator.validate_multi_gate_confluence(confluence_count=3, min_confluent_gates=2)
        assert valid is True

    def test_validate_multi_gate_confluence_below_threshold(self, aggregator):
        """Test confluence below minimum."""
        valid = aggregator.validate_multi_gate_confluence(confluence_count=1, min_confluent_gates=2)
        assert valid is False

    def test_validate_multi_gate_confluence_at_boundary(self, aggregator):
        """Test confluence at exact boundary."""
        assert aggregator.validate_multi_gate_confluence(confluence_count=2, min_confluent_gates=2) is True
        assert aggregator.validate_multi_gate_confluence(confluence_count=1, min_confluent_gates=2) is False


class TestFOMODetection:
    def test_detect_fomo_euphoria_all_extreme(self, aggregator):
        """Test euphoria with all conditions extreme."""
        is_fomo, adjustment = aggregator.detect_fomo_euphoria(
            price_change_pct=50.0,
            volume_spike=5.0,
            social_velocity=9.0,
            sentiment_extreme=9.5,
        )
        assert is_fomo is True
        assert 0.5 <= adjustment <= 1.0

    def test_detect_fomo_euphoria_none(self, aggregator):
        """Test no euphoria."""
        is_fomo, adjustment = aggregator.detect_fomo_euphoria(
            price_change_pct=5.0,
            volume_spike=1.0,
            social_velocity=2.0,
            sentiment_extreme=3.0,
        )
        assert is_fomo is False
        assert adjustment == 1.0

    def test_detect_fomo_euphoria_partial(self, aggregator):
        """Test partial euphoria conditions."""
        is_fomo, adjustment = aggregator.detect_fomo_euphoria(
            price_change_pct=40.0,
            volume_spike=4.0,
            social_velocity=8.0,
            sentiment_extreme=2.0,
        )
        assert isinstance(is_fomo, bool)
        assert 0.5 <= adjustment <= 1.0

    def test_detect_fomo_adjustment_factor_range(self, aggregator):
        """Test adjustment factor stays in valid range."""
        for price in [10, 30, 50, 80]:
            for volume in [1, 3, 5, 8]:
                for social in [2, 5, 8, 10]:
                    for sentiment in [2, 5, 8, 10]:
                        _, adjustment = aggregator.detect_fomo_euphoria(price, volume, social, sentiment)
                        assert 0.5 <= adjustment <= 1.0


class TestRegimeFilter:
    def test_apply_regime_filter_bullish(self, aggregator):
        """Test bullish regime requires only 1 gate."""
        is_valid, note = aggregator.apply_regime_filter(confluence_count=1, market_regime="bullish")
        assert is_valid is True

    def test_apply_regime_filter_neutral(self, aggregator):
        """Test neutral regime requires 2 gates."""
        is_valid, note = aggregator.apply_regime_filter(confluence_count=2, market_regime="neutral")
        assert is_valid is True
        is_valid, note = aggregator.apply_regime_filter(confluence_count=1, market_regime="neutral")
        assert is_valid is False

    def test_apply_regime_filter_bearish(self, aggregator):
        """Test bearish regime requires 3 gates."""
        is_valid, note = aggregator.apply_regime_filter(confluence_count=3, market_regime="bearish")
        assert is_valid is True
        is_valid, note = aggregator.apply_regime_filter(confluence_count=2, market_regime="bearish")
        assert is_valid is False

    def test_apply_regime_filter_ranging(self, aggregator):
        """Test ranging regime requires 2 gates."""
        is_valid, note = aggregator.apply_regime_filter(confluence_count=2, market_regime="ranging")
        assert is_valid is True


class TestRiskLevel:
    def test_calculate_risk_level_extreme_fomo(self, aggregator):
        """Test FOMO conditions produce EXTREME risk."""
        risk = aggregator.calculate_risk_level(confluence_count=5, is_fomo=True, bce_score=6.0)
        assert risk == "EXTREME"

    def test_calculate_risk_level_high_confluence(self, aggregator):
        """Test 4+ gates = LOW risk."""
        risk = aggregator.calculate_risk_level(confluence_count=4, is_fomo=False, bce_score=6.0)
        assert risk == "LOW"

    def test_calculate_risk_level_low_confluence(self, aggregator):
        """Test 0-1 gates = HIGH risk."""
        risk = aggregator.calculate_risk_level(confluence_count=0, is_fomo=False, bce_score=2.0)
        assert risk == "HIGH"

    def test_calculate_risk_level_medium_confluence(self, aggregator):
        """Test 2-3 gates = MEDIUM or LOW."""
        risk2 = aggregator.calculate_risk_level(confluence_count=2, is_fomo=False, bce_score=3.0)
        assert risk2 == "MEDIUM"


class TestAggregateSignals:
    def test_aggregate_signals_returns_object(self, aggregator):
        """Test aggregation returns AggregatedSignal object."""
        signal = aggregator.aggregate_signals(
            symbol="BTC",
            bce_score=5.5,
            x20_score=60.0,
            narm_p_score=70.0,
            rpm_score=60.0,
            rrp_score=55.0,
        )
        assert isinstance(signal, AggregatedSignal)
        assert signal.symbol == "BTC"

    def test_aggregate_signals_high_confluence(self, aggregator):
        """Test high confluence produces valid signal."""
        signal = aggregator.aggregate_signals(
            symbol="BTC",
            bce_score=5.5,
            x20_score=75.0,
            narm_p_score=80.0,
            rpm_score=70.0,
            rrp_score=65.0,
            market_regime="bullish",
        )
        assert signal.confluence_count >= 4
        assert signal.final_signal is True

    def test_aggregate_signals_low_confluence(self, aggregator):
        """Test low confluence produces invalid signal."""
        signal = aggregator.aggregate_signals(
            symbol="ALT",
            bce_score=2.0,
            x20_score=30.0,
            narm_p_score=40.0,
            rpm_score=40.0,
            rrp_score=30.0,
        )
        assert signal.confluence_count <= 1
        assert signal.final_signal is False

    def test_aggregate_signals_fomo_override(self, aggregator):
        """Test FOMO conditions override positive signals."""
        signal = aggregator.aggregate_signals(
            symbol="MEME",
            bce_score=5.5,
            x20_score=75.0,
            narm_p_score=80.0,
            rpm_score=70.0,
            rrp_score=65.0,
            price_change_pct=100.0,
            volume_spike=10.0,
            social_velocity=10.0,
            sentiment_extreme=10.0,
        )
        assert signal.final_signal is False
        assert signal.risk_level == "EXTREME"

    def test_aggregate_signals_regime_filtering(self, aggregator):
        """Test regime filtering adjusts requirements."""
        # Bearish regime with 2 gates should fail
        signal_bearish = aggregator.aggregate_signals(
            symbol="BTC",
            bce_score=5.5,
            x20_score=75.0,
            narm_p_score=30.0,
            rpm_score=30.0,
            rrp_score=30.0,
            market_regime="bearish",
        )
        assert signal_bearish.final_signal is False

        # Same scores in bullish regime should pass
        signal_bullish = aggregator.aggregate_signals(
            symbol="BTC",
            bce_score=5.5,
            x20_score=75.0,
            narm_p_score=30.0,
            rpm_score=30.0,
            rrp_score=30.0,
            market_regime="bullish",
        )
        assert signal_bullish.final_signal is True

    def test_aggregate_signals_fomo_adjustment(self, aggregator):
        """Test FOMO adjustment reduces score."""
        signal_normal = aggregator.aggregate_signals(
            symbol="BTC",
            bce_score=5.5,
            x20_score=75.0,
            narm_p_score=80.0,
            rpm_score=70.0,
            rrp_score=65.0,
        )

        signal_fomo = aggregator.aggregate_signals(
            symbol="BTC",
            bce_score=5.5,
            x20_score=75.0,
            narm_p_score=80.0,
            rpm_score=70.0,
            rrp_score=65.0,
            price_change_pct=100.0,
            volume_spike=10.0,
            social_velocity=10.0,
            sentiment_extreme=10.0,
        )

        assert signal_fomo.fomo_adjusted_score < signal_normal.fomo_adjusted_score


class TestRanking:
    def test_rank_opportunities_by_score(self, aggregator):
        """Test ranking by FOMO-adjusted score."""
        signal1 = aggregator.aggregate_signals(
            symbol="BTC", bce_score=5.5, x20_score=70.0, narm_p_score=75.0, rpm_score=65.0, rrp_score=60.0,
        )
        signal2 = aggregator.aggregate_signals(
            symbol="ETH", bce_score=4.0, x20_score=55.0, narm_p_score=60.0, rpm_score=50.0, rrp_score=45.0,
        )
        signal3 = aggregator.aggregate_signals(
            symbol="ALT", bce_score=3.0, x20_score=40.0, narm_p_score=45.0, rpm_score=35.0, rrp_score=30.0,
        )

        signals = [signal2, signal3, signal1]
        ranked = aggregator.rank_opportunities(signals)

        assert ranked[0].symbol == "BTC"
        assert ranked[1].symbol == "ETH"
        assert ranked[2].symbol == "ALT"

    def test_rank_empty_list(self, aggregator):
        """Test ranking empty list."""
        ranked = aggregator.rank_opportunities([])
        assert ranked == []


class TestFiltering:
    def test_filter_valid_signals(self, aggregator):
        """Test filtering only valid signals."""
        signal_valid = aggregator.aggregate_signals(
            symbol="BTC",
            bce_score=5.5,
            x20_score=75.0,
            narm_p_score=80.0,
            rpm_score=70.0,
            rrp_score=65.0,
            market_regime="bullish",
        )
        signal_invalid = aggregator.aggregate_signals(
            symbol="ALT",
            bce_score=2.0,
            x20_score=30.0,
            narm_p_score=40.0,
            rpm_score=30.0,
            rrp_score=25.0,
        )

        signals = [signal_valid, signal_invalid]
        filtered = aggregator.filter_valid_signals(signals)

        assert len(filtered) == 1
        assert filtered[0].symbol == "BTC"

    def test_filter_by_risk_level(self, aggregator):
        """Test filtering by risk level."""
        signal_low = aggregator.aggregate_signals(
            symbol="BTC",
            bce_score=5.5,
            x20_score=75.0,
            narm_p_score=80.0,
            rpm_score=70.0,
            rrp_score=65.0,
        )
        signal_high = aggregator.aggregate_signals(
            symbol="ALT",
            bce_score=2.0,
            x20_score=30.0,
            narm_p_score=40.0,
            rpm_score=30.0,
            rrp_score=25.0,
        )

        signals = [signal_low, signal_high]
        filtered = aggregator.filter_by_risk_level(signals, max_risk="MEDIUM")

        assert len(filtered) >= 1
        filtered_strict = aggregator.filter_by_risk_level(signals, max_risk="LOW")
        assert len(filtered_strict) <= 1

    def test_filter_empty_list(self, aggregator):
        """Test filtering empty list."""
        filtered = aggregator.filter_valid_signals([])
        assert filtered == []


class TestSummary:
    def test_generate_summary_valid(self, aggregator):
        """Test summary generation for valid signal."""
        signal = aggregator.aggregate_signals(
            symbol="BTC",
            bce_score=5.5,
            x20_score=75.0,
            narm_p_score=80.0,
            rpm_score=70.0,
            rrp_score=65.0,
            market_regime="bullish",
        )
        summary = aggregator.generate_summary(signal)

        assert summary["symbol"] == "BTC"
        assert summary["recommendation"] == "ACCEPT"
        assert "gates" in summary
        assert "confidence" in summary
        assert "risk_level" in summary

    def test_generate_summary_invalid(self, aggregator):
        """Test summary generation for invalid signal."""
        signal = aggregator.aggregate_signals(
            symbol="ALT",
            bce_score=2.0,
            x20_score=30.0,
            narm_p_score=40.0,
            rpm_score=30.0,
            rrp_score=25.0,
        )
        summary = aggregator.generate_summary(signal)

        assert summary["symbol"] == "ALT"
        assert summary["recommendation"] == "REJECT"


class TestEdgeCases:
    def test_aggregate_signals_all_zeros(self, aggregator):
        """Test with all zero scores."""
        signal = aggregator.aggregate_signals(
            symbol="ZERO",
            bce_score=0.0,
            x20_score=0.0,
            narm_p_score=0.0,
            rpm_score=0.0,
            rrp_score=0.0,
        )
        assert signal.confluence_count == 0
        assert signal.final_signal is False
        assert signal.risk_level == "HIGH"

    def test_aggregate_signals_all_perfect(self, aggregator):
        """Test with perfect scores."""
        signal = aggregator.aggregate_signals(
            symbol="PERFECT",
            bce_score=6.0,
            x20_score=100.0,
            narm_p_score=100.0,
            rpm_score=100.0,
            rrp_score=100.0,
        )
        assert signal.confluence_count == 5
        assert signal.final_signal is True
        assert signal.risk_level == "LOW"

    def test_aggregate_signals_mixed_regimes(self, aggregator):
        """Test across different market regimes."""
        base_scores = dict(
            symbol="BTC",
            bce_score=4.0,
            x20_score=60.0,
            narm_p_score=65.0,
            rpm_score=55.0,
            rrp_score=50.0,
        )

        for regime in ["bullish", "neutral", "bearish", "ranging"]:
            signal = aggregator.aggregate_signals(**base_scores, market_regime=regime)
            assert isinstance(signal, AggregatedSignal)
