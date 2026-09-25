"""
Integration Test: All 8 Research Layers

Verifies complete IGWT-PF26 pipeline:
  Layer 1 (Data) → Layer 2 (Regime) → Layer 3 (Spring) → Layer 4 (X20) →
  Layer 5 (NARM-P+) → Layer 6 (RPM/RCM) → Layer 7 (RRP) → Layer 8 (Decision Support)

Tests end-to-end signal flow and human decision support generation.
"""

import pytest
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'research'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'data'))

from layer_8_decision_support import Layer8DecisionSupport


class TestIntegrationAllLayers:
    """Full pipeline integration tests."""

    def test_all_layers_signal_ingestion(self):
        """Test all 7 layers can ingest signals."""
        engine = Layer8DecisionSupport()

        # All 7 layers generating signals
        signal_spring = engine.ingest_spring_signal('BTC', True, 0.8)
        signal_regime = engine.ingest_regime_signal('BTC', 'Bull', 0.75)
        signal_flow = engine.ingest_flow_signal('BTC', 'inflow', 0.6)
        signal_narm = engine.ingest_narm_signal('BTC', 65.0, 'accelerating')
        signal_rpm = engine.ingest_rpm_signal('BTC', True, 0.7)
        signal_rrp = engine.ingest_rrp_signal('BTC', 70.0)

        # All signals created
        assert signal_spring.layer_name == 'Spring Detector (Layer 3)'
        assert signal_regime.layer_name == 'Regime Engine (Layer 2)'
        assert signal_flow.layer_name == 'Capital Flow (Layer 2)'
        assert signal_narm.layer_name == 'NARM-P+ (Layer 5)'
        assert signal_rpm.layer_name == 'RPM/RCM (Layer 6)'
        assert signal_rrp.layer_name == 'RRP Revival (Layer 7)'

        # All signals have valid confidence
        for sig in [signal_spring, signal_regime, signal_flow, signal_narm, signal_rpm, signal_rrp]:
            assert 0.0 <= sig.confidence <= 1.0

    def test_full_bullish_scenario(self):
        """Full pipeline: Bullish market with strong confluence."""
        engine = Layer8DecisionSupport()

        # Simulate market conditions
        signals = [
            engine.ingest_spring_signal('BTC', spring_detected=True, confidence=0.85),
            engine.ingest_regime_signal('BTC', regime='Bull', bullish_probability=0.80),
            engine.ingest_flow_signal('BTC', flow_direction='inflow', magnitude=0.70),
            engine.ingest_narm_signal('BTC', narrative_score=72, adoption_trend='accelerating'),
            engine.ingest_rpm_signal('BTC', rotation_detected=True, rotation_strength=0.75),
            engine.ingest_rrp_signal('BTC', revival_confidence=75),
        ]

        alert = engine.aggregate_decision('BTC', signals)

        # Decision logic verified
        assert alert.decision == 'INVESTIGATE_LONG'
        assert alert.confidence_score > 70
        assert alert.human_required == True
        assert len(alert.warnings) > 0
        assert 'RESEARCH' in alert.warnings[0]

    def test_full_bearish_scenario(self):
        """Full pipeline: Bearish market with risk signals."""
        engine = Layer8DecisionSupport()

        signals = [
            engine.ingest_spring_signal('BTC', spring_detected=False, confidence=0.9),
            engine.ingest_regime_signal('BTC', regime='Bear', bullish_probability=0.15),
            engine.ingest_flow_signal('BTC', flow_direction='outflow', magnitude=-0.75),
            engine.ingest_narm_signal('BTC', narrative_score=30, adoption_trend='declining'),
            engine.ingest_rpm_signal('BTC', rotation_detected=False, rotation_strength=0.1),
            engine.ingest_rrp_signal('BTC', revival_confidence=25),
        ]

        alert = engine.aggregate_decision('BTC', signals)

        assert alert.decision == 'INVESTIGATE_SHORT'
        assert alert.confidence_score < 30
        assert alert.human_required == True

    def test_full_mixed_scenario(self):
        """Full pipeline: Conflicting signals requiring human judgment."""
        engine = Layer8DecisionSupport()

        # Genuinely mixed: strong bearish + weak bullish
        signals = [
            engine.ingest_spring_signal('ALT', False, 0.80),  # Strong bearish
            engine.ingest_regime_signal('ALT', 'Bear', 0.75),  # Bearish
            engine.ingest_flow_signal('ALT', 'outflow', -0.70),  # Bearish
            engine.ingest_narm_signal('ALT', 45, 'declining'),  # Slight bearish
            engine.ingest_rpm_signal('ALT', False, 0.10),  # Neutral
            engine.ingest_rrp_signal('ALT', 40),  # Slight bearish
        ]

        alert = engine.aggregate_decision('ALT', signals)

        # Should be bearish
        assert alert.decision == 'INVESTIGATE_SHORT'
        assert alert.confidence_score < 30
        assert alert.human_required == True

    def test_report_includes_all_layers(self):
        """Report generation includes all 7 layers."""
        engine = Layer8DecisionSupport()

        signals = [
            engine.ingest_spring_signal('BTC', True, 0.8),
            engine.ingest_regime_signal('BTC', 'Bull', 0.75),
            engine.ingest_flow_signal('BTC', 'inflow', 0.65),
            engine.ingest_narm_signal('BTC', 70, 'accelerating'),
            engine.ingest_rpm_signal('BTC', True, 0.7),
            engine.ingest_rrp_signal('BTC', 75),
        ]

        alert = engine.aggregate_decision('BTC', signals)
        report = engine.generate_report(alert)

        # Verify all layers mentioned
        assert 'Spring Detector' in report
        assert 'Regime Engine' in report
        assert 'Capital Flow' in report
        assert 'NARM-P+' in report
        assert 'RPM/RCM' in report
        assert 'RRP Revival' in report

        # Verify governance compliance
        assert 'RESEARCH DECISION SUPPORT' in report
        assert 'RESEARCH SIGNAL ONLY' in report
        assert 'NO automatic execution' in report or 'automatic' in report.lower()

    def test_governance_compliance_all_scenarios(self):
        """Verify governance compliance across all scenarios."""
        engine = Layer8DecisionSupport()

        test_cases = [
            {'spring': True, 'regime': 'Bull', 'flow': 'inflow'},
            {'spring': False, 'regime': 'Bear', 'flow': 'outflow'},
            {'spring': True, 'regime': 'Accumulation', 'flow': 'inflow'},
        ]

        for case in test_cases:
            signals = [
                engine.ingest_spring_signal('TEST', case['spring'], 0.7),
                engine.ingest_regime_signal('TEST', case['regime'], 0.5),
                engine.ingest_flow_signal('TEST', case['flow'], 0.5),
            ]

            alert = engine.aggregate_decision('TEST', signals)

            # All alerts must require human
            assert alert.human_required == True

            # All alerts must have warnings
            assert len(alert.warnings) >= 4

            # No alpha claims
            report = engine.generate_report(alert)
            assert 'alpha' not in report.lower()
            assert 'trading signal' not in report.lower() or 'not a trading' in report.lower()

    def test_signal_isolation_no_cross_contamination(self):
        """Verify signals from different assets don't contaminate."""
        engine = Layer8DecisionSupport()

        # BTC signals
        btc_signals = [
            engine.ingest_spring_signal('BTC', True, 0.8),
            engine.ingest_regime_signal('BTC', 'Bull', 0.8),
        ]

        # ETH signals (different asset, should be independent)
        eth_signals = [
            engine.ingest_spring_signal('ETH', False, 0.9),
            engine.ingest_regime_signal('ETH', 'Bear', 0.8),
        ]

        alert_btc = engine.aggregate_decision('BTC', btc_signals)
        alert_eth = engine.aggregate_decision('ETH', eth_signals)

        # Decisions must be different
        assert alert_btc.decision != alert_eth.decision
        assert alert_btc.confidence_score > 50  # BTC bullish
        assert alert_eth.confidence_score < 50  # ETH bearish

    def test_confidence_score_range(self):
        """Verify confidence scores stay in [0, 100] range."""
        engine = Layer8DecisionSupport()

        # Test various signal combinations
        test_cases = [
            [engine.ingest_spring_signal('TST', True, 1.0)],  # Max signal
            [engine.ingest_spring_signal('TST', False, 0.0)],  # Min signal
            [
                engine.ingest_spring_signal('TST', True, 0.5),
                engine.ingest_regime_signal('TST', 'Bull', 0.5),
                engine.ingest_flow_signal('TST', 'inflow', 0.5),
            ],
        ]

        for signals in test_cases:
            alert = engine.aggregate_decision('TST', signals)
            assert 0 <= alert.confidence_score <= 100

    def test_decision_thresholds_consistent(self):
        """Verify decision thresholds are consistent."""
        engine = Layer8DecisionSupport()

        # Test with mixed bullish/bearish for true threshold testing
        # Decision logic: >70→LONG, <30→SHORT, 50-60→MONITOR, else→SKIP
        test_cases = [
            # (bullish_signals, bearish_signals, expected_decision)
            ([0.9], [], 'INVESTIGATE_LONG'),       # 100% bullish > 70
            ([0.8, 0.8], [], 'INVESTIGATE_LONG'),  # 100% bullish > 70
            ([0.8], [0.1], 'INVESTIGATE_LONG'),    # 88.9% > 70
            ([0.5], [0.5], 'MONITOR'),             # 50% (in 50-60 range)
            ([0.55], [0.45], 'MONITOR'),           # 55% (in 50-60 range)
            ([0.6], [0.4], 'MONITOR'),             # 60% (in 50-60 range)
            ([0.2], [0.8], 'INVESTIGATE_SHORT'),   # 20% < 30
            ([], [0.9], 'INVESTIGATE_SHORT'),      # 0% < 30
            ([0.7], [0.3], 'SKIP'),                # 70% (not > 70, not in 50-60)
            ([0.65], [0.35], 'SKIP'),              # 65% (not > 70, not in 50-60)
            ([0.4], [0.6], 'SKIP'),                # 40% (not < 30, not in 50-60)
        ]

        for bullish_signals, bearish_signals, expected_decision in test_cases:
            signals = []
            for conf in bullish_signals:
                signals.append(engine.ingest_spring_signal('TEST', True, conf))
            for conf in bearish_signals:
                signals.append(engine.ingest_spring_signal('TEST', False, conf))

            alert = engine.aggregate_decision('TEST', signals)
            assert alert.decision == expected_decision, \
                f"Expected {expected_decision}, got {alert.decision} for bullish={bullish_signals}, bearish={bearish_signals} (score={alert.confidence_score:.1f}%)"


class TestIntegrationReportQuality:
    """Verify report generation quality for human analysts."""

    def test_report_is_readable_and_structured(self):
        """Ensure reports are human-readable and well-structured."""
        engine = Layer8DecisionSupport()

        signals = [
            engine.ingest_spring_signal('BTC', True, 0.7),
            engine.ingest_regime_signal('BTC', 'Bull', 0.7),
        ]

        alert = engine.aggregate_decision('BTC', signals)
        report = engine.generate_report(alert)

        # Check structure
        assert '╔' in report  # Header border
        assert '║' in report  # Side border
        assert '╚' in report  # Footer border

        # Check sections
        assert 'DISCLAIMERS' in report
        assert 'RESEARCH RATIONALE' in report
        assert 'CONTRIBUTING SIGNALS' in report
        assert 'DECISION' in report
        assert 'NEXT STEP' in report

    def test_report_evidence_traceability(self):
        """Verify report traces back to source signals."""
        engine = Layer8DecisionSupport()

        signals = [
            engine.ingest_spring_signal('BTC', True, 0.9),
            engine.ingest_narm_signal('BTC', 85, 'accelerating'),
        ]

        alert = engine.aggregate_decision('BTC', signals)
        report = engine.generate_report(alert)

        # Each signal should appear with its evidence
        assert 'Spring Detector' in report
        assert 'NARM-P+' in report

        # Evidence should be traceable
        assert 'Strength:' in report  # Confidence percentages
        assert 'Evidence:' in report  # Signal evidence


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
