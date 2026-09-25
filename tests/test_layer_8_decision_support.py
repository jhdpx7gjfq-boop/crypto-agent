"""
Test suite for Layer 8 Decision Support Engine

Verification that research aggregation works correctly
(NOT testing for alpha, as alpha validation is blocked per governance)
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'research'))

from layer_8_decision_support import Layer8DecisionSupport, DecisionSignal, DecisionAlert


class TestDecisionSignalCreation:
    """Test individual signal creation."""

    def test_spring_signal_bullish(self):
        """Create bullish Spring signal."""
        engine = Layer8DecisionSupport()
        signal = engine.ingest_spring_signal('BTC', spring_detected=True, confidence=0.8)

        assert signal.layer_name == 'Spring Detector (Layer 3)'
        assert signal.signal_type == 'bullish'
        assert signal.confidence == 0.8
        assert 'spring' in signal.evidence.lower()

    def test_regime_signal_bull(self):
        """Create Bull regime signal."""
        engine = Layer8DecisionSupport()
        signal = engine.ingest_regime_signal('ETH', regime='Bull', bullish_probability=0.75)

        assert signal.layer_name == 'Regime Engine (Layer 2)'
        assert signal.signal_type == 'bullish'
        assert 0.7 <= signal.confidence <= 0.8

    def test_rrp_signal_revival(self):
        """Create revival signal."""
        engine = Layer8DecisionSupport()
        signal = engine.ingest_rrp_signal('SOL', revival_confidence=75.0)

        assert signal.layer_name == 'RRP Revival (Layer 7)'
        assert signal.signal_type == 'bullish'
        assert signal.confidence == 0.75


class TestDecisionAggregation:
    """Test signal aggregation and decision logic."""

    def test_aggregate_all_bullish(self):
        """Aggregate strongly bullish signals."""
        engine = Layer8DecisionSupport()

        signals = [
            engine.ingest_spring_signal('BTC', True, 0.9),
            engine.ingest_regime_signal('BTC', 'Bull', 0.8),
            engine.ingest_rrp_signal('BTC', 80.0),
        ]

        alert = engine.aggregate_decision('BTC', signals)

        assert alert.decision == 'INVESTIGATE_LONG'
        assert alert.confidence_score > 70
        assert len(alert.warnings) > 0
        assert alert.human_required

    def test_aggregate_all_bearish(self):
        """Aggregate strongly bearish signals."""
        engine = Layer8DecisionSupport()

        signals = [
            engine.ingest_regime_signal('BTC', 'Bear', 0.8),
            engine.ingest_flow_signal('BTC', 'outflow', -0.7),
            engine.ingest_rrp_signal('BTC', 20.0),
        ]

        alert = engine.aggregate_decision('BTC', signals)

        assert alert.decision == 'INVESTIGATE_SHORT'
        assert alert.confidence_score < 30

    def test_aggregate_mixed_signals(self):
        """Aggregate mixed signals."""
        engine = Layer8DecisionSupport()

        signals = [
            engine.ingest_spring_signal('BTC', True, 0.6),
            engine.ingest_regime_signal('BTC', 'Accumulation', 0.5),
            engine.ingest_flow_signal('BTC', 'outflow', -0.4),
        ]

        alert = engine.aggregate_decision('BTC', signals)

        assert alert.decision in ['MONITOR', 'SKIP']
        assert 30 <= alert.confidence_score <= 70

    def test_empty_signals(self):
        """Handle empty signal list."""
        engine = Layer8DecisionSupport()
        alert = engine.aggregate_decision('BTC', [])

        assert alert.decision == 'SKIP'
        assert alert.confidence_score == 0


class TestReportGeneration:
    """Test human-readable report generation."""

    def test_report_includes_disclaimers(self):
        """Report should include research disclaimers."""
        engine = Layer8DecisionSupport()

        signal = engine.ingest_spring_signal('BTC', True, 0.7)
        alert = engine.aggregate_decision('BTC', [signal])

        report = engine.generate_report(alert)

        assert 'RESEARCH DECISION SUPPORT' in report
        assert 'RESEARCH SIGNAL ONLY' in report
        assert 'human' in report.lower()
        assert 'manual' in report.lower()

    def test_report_includes_all_signals(self):
        """Report should list all contributing signals."""
        engine = Layer8DecisionSupport()

        signals = [
            engine.ingest_spring_signal('BTC', True, 0.8),
            engine.ingest_regime_signal('BTC', 'Bull', 0.7),
            engine.ingest_rrp_signal('BTC', 70.0),
        ]

        alert = engine.aggregate_decision('BTC', signals)
        report = engine.generate_report(alert)

        assert 'Spring Detector' in report
        assert 'Regime Engine' in report
        assert 'RRP Revival' in report

    def test_report_no_auto_execution_warning(self):
        """Report must warn against auto execution."""
        engine = Layer8DecisionSupport()
        signal = engine.ingest_spring_signal('BTC', True, 0.9)
        alert = engine.aggregate_decision('BTC', [signal])
        report = engine.generate_report(alert)

        assert 'NO automatic execution' in report or 'automatic' in report.lower()


class TestGovernanceCompliance:
    """Verify Layer 8 complies with governance constraints."""

    def test_decision_support_not_trading(self):
        """Layer 8 is decision support, NOT trading."""
        engine = Layer8DecisionSupport()
        signal = engine.ingest_spring_signal('BTC', True, 0.9)
        alert = engine.aggregate_decision('BTC', [signal])

        # Must always require human decision
        assert alert.human_required == True

        # Must warn about research-only status
        has_research_warning = any('RESEARCH' in w for w in alert.warnings)
        assert has_research_warning

    def test_no_new_alpha_claims(self):
        """Layer 8 does not claim independent alpha."""
        engine = Layer8DecisionSupport()
        signal = engine.ingest_spring_signal('BTC', True, 0.9)
        alert = engine.aggregate_decision('BTC', [signal])

        report = engine.generate_report(alert)

        # Should NOT claim alpha
        assert 'alpha' not in report.lower()
        assert 'independent' not in report.lower()

        # Should emphasize research
        assert 'research' in report.lower()

    def test_all_signals_have_confidence_interval(self):
        """All signals must specify confidence [0, 1]."""
        engine = Layer8DecisionSupport()

        signals = [
            engine.ingest_spring_signal('BTC', True, 0.8),
            engine.ingest_regime_signal('BTC', 'Bull', 0.7),
            engine.ingest_rrp_signal('BTC', 70.0),
        ]

        for signal in signals:
            assert 0.0 <= signal.confidence <= 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
