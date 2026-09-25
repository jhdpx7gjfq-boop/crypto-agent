"""
Phase 5: Robustness Validation Tests

Tests BCE engine stability across 7 market regimes.

Authority: B-004_SPEC.md §"Validation & Walk-Forward Testing"
"""

import pytest
from src.layers.layer3_wyckoff.robustness_validator import (
    RobustnessValidator,
    MarketRegime,
)


@pytest.fixture
def validator():
    """Create robustness validator."""
    return RobustnessValidator()


def test_validator_init(validator):
    """Test validator initialization."""
    assert len(validator.results) == 0
    assert len(validator.REGIMES) == 7


def test_validate_single_regime_pass(validator):
    """Test single regime validation that passes F1 gate."""
    actual = [1, 1, 0, 0, 1, 1]
    predicted = [1, 1, 0, 0, 1, 1]

    result = validator.validate_regime(
        regime_type=MarketRegime.BULL,
        actual_signals=actual,
        predicted_signals=predicted,
        regime_characteristics="Sustained >20% gain, strong uptrend"
    )

    assert result.regime_name == "bull_market"
    assert result.f1_score == 1.0
    assert result.passes_gate is True


def test_validate_single_regime_fail(validator):
    """Test single regime validation that fails F1 gate."""
    # Poor predictions (F1 < 0.55)
    actual = [1, 1, 1, 0, 0, 0]
    predicted = [0, 0, 0, 1, 1, 1]

    result = validator.validate_regime(
        regime_type=MarketRegime.BEAR,
        actual_signals=actual,
        predicted_signals=predicted,
        regime_characteristics="Sustained >20% loss, strong downtrend"
    )

    assert result.regime_name == "bear_market"
    assert result.f1_score == 0.0
    assert result.passes_gate is False


def test_validate_high_volatility(validator):
    """Test high volatility regime."""
    actual = [1, 1, 0, 0, 1, 1]
    predicted = [1, 1, 0, 0, 1, 1]

    result = validator.validate_regime(
        regime_type=MarketRegime.HIGH_VOLATILITY,
        actual_signals=actual,
        predicted_signals=predicted,
        regime_characteristics=">60-day realized volatility"
    )

    assert result.regime_name == "high_volatility"
    assert result.passes_gate is True


def test_validate_low_volatility(validator):
    """Test low volatility regime."""
    actual = [1, 0, 0, 1, 0, 1]
    predicted = [1, 0, 0, 1, 0, 1]

    result = validator.validate_regime(
        regime_type=MarketRegime.LOW_VOLATILITY,
        actual_signals=actual,
        predicted_signals=predicted,
        regime_characteristics="<20-day realized volatility"
    )

    assert result.regime_name == "low_volatility"
    assert result.passes_gate is True


def test_validate_rising_correlation(validator):
    """Test rising correlation regime."""
    actual = [1, 1, 0, 0]
    predicted = [1, 1, 0, 0]

    result = validator.validate_regime(
        regime_type=MarketRegime.RISING_CORRELATION,
        actual_signals=actual,
        predicted_signals=predicted,
        regime_characteristics="All coins track BTC, corr > 0.8"
    )

    assert result.regime_name == "rising_correlation"
    assert result.f1_score == 1.0


def test_validate_falling_correlation(validator):
    """Test falling correlation regime."""
    actual = [1, 0, 1, 0]
    predicted = [1, 0, 1, 0]

    result = validator.validate_regime(
        regime_type=MarketRegime.FALLING_CORRELATION,
        actual_signals=actual,
        predicted_signals=predicted,
        regime_characteristics="Breakdown of structure, corr < 0.5"
    )

    assert result.regime_name == "falling_correlation"
    assert result.f1_score == 1.0


def test_validate_liquidation_events(validator):
    """Test liquidation events regime."""
    actual = [1, 1, 0, 0, 1]
    predicted = [1, 1, 0, 0, 1]

    result = validator.validate_regime(
        regime_type=MarketRegime.LIQUIDATION,
        actual_signals=actual,
        predicted_signals=predicted,
        regime_characteristics="Extreme volume spikes >3x normal"
    )

    assert result.regime_name == "liquidation_events"
    assert result.f1_score == 1.0


def test_validate_all_regimes(validator):
    """Test validating all 7 regimes."""
    regimes_data = [
        (MarketRegime.BULL, [1, 1, 0, 0, 1, 1], [1, 1, 0, 0, 1, 1]),
        (MarketRegime.BEAR, [1, 0, 1, 0, 1, 0], [1, 0, 1, 0, 1, 0]),
        (MarketRegime.HIGH_VOLATILITY, [1, 1, 0, 0], [1, 1, 0, 0]),
        (MarketRegime.LOW_VOLATILITY, [1, 0, 1, 0], [1, 0, 1, 0]),
        (MarketRegime.RISING_CORRELATION, [1, 1, 0, 0, 1], [1, 1, 0, 0, 1]),
        (MarketRegime.FALLING_CORRELATION, [1, 0, 1, 0, 1], [1, 0, 1, 0, 1]),
        (MarketRegime.LIQUIDATION, [1, 1, 0, 0], [1, 1, 0, 0]),
    ]

    for regime_type, actual, predicted in regimes_data:
        validator.validate_regime(
            regime_type=regime_type,
            actual_signals=actual,
            predicted_signals=predicted,
            regime_characteristics="Test regime"
        )

    assert len(validator.results) == 7


def test_signal_length_mismatch(validator):
    """Test error on signal length mismatch."""
    actual = [1, 1, 0]
    predicted = [1, 1, 0, 0]

    with pytest.raises(AssertionError):
        validator.validate_regime(
            regime_type=MarketRegime.BULL,
            actual_signals=actual,
            predicted_signals=predicted,
            regime_characteristics="Test"
        )


def test_generate_report_all_pass(validator):
    """Test report with all regimes passing."""
    regimes_data = [
        (MarketRegime.BULL, [1, 1, 0, 0, 1, 1], [1, 1, 0, 0, 1, 1]),
        (MarketRegime.BEAR, [1, 0, 1, 0, 1, 0], [1, 0, 1, 0, 1, 0]),
        (MarketRegime.HIGH_VOLATILITY, [1, 1, 0, 0], [1, 1, 0, 0]),
        (MarketRegime.LOW_VOLATILITY, [1, 0, 1, 0], [1, 0, 1, 0]),
        (MarketRegime.RISING_CORRELATION, [1, 1, 0, 0, 1], [1, 1, 0, 0, 1]),
        (MarketRegime.FALLING_CORRELATION, [1, 0, 1, 0, 1], [1, 0, 1, 0, 1]),
        (MarketRegime.LIQUIDATION, [1, 1, 0, 0], [1, 1, 0, 0]),
    ]

    for regime_type, actual, predicted in regimes_data:
        validator.validate_regime(
            regime_type=regime_type,
            actual_signals=actual,
            predicted_signals=predicted,
            regime_characteristics="Test regime"
        )

    report = validator.generate_report()

    assert report.spec_version == "b_004_spec_2026_09_25"
    assert len(report.regimes) == 7
    assert report.f1_avg == 1.0
    assert report.passes_count == 7
    assert report.passes_rate == 100
    assert report.passes_robustness_gate is True


def test_generate_report_mixed_results(validator):
    """Test report with mixed pass/fail results."""
    regimes_data = [
        (MarketRegime.BULL, [1, 1, 0, 0, 1, 1], [1, 1, 0, 0, 1, 1]),        # Pass
        (MarketRegime.BEAR, [1, 0, 1, 0, 1, 0], [0, 1, 0, 1, 0, 1]),        # Fail
        (MarketRegime.HIGH_VOLATILITY, [1, 1, 0, 0], [1, 1, 0, 0]),         # Pass
        (MarketRegime.LOW_VOLATILITY, [1, 0, 1, 0], [1, 0, 1, 0]),          # Pass
        (MarketRegime.RISING_CORRELATION, [1, 1, 0, 0, 1], [1, 1, 0, 0, 1]), # Pass
        (MarketRegime.FALLING_CORRELATION, [1, 0, 1, 0, 1], [0, 1, 0, 1, 0]), # Fail
        (MarketRegime.LIQUIDATION, [1, 1, 0, 0], [1, 1, 0, 0]),             # Pass
    ]

    for regime_type, actual, predicted in regimes_data:
        validator.validate_regime(
            regime_type=regime_type,
            actual_signals=actual,
            predicted_signals=predicted,
            regime_characteristics="Test regime"
        )

    report = validator.generate_report()

    # 5 out of 7 pass (71%)
    assert report.passes_count == 5
    assert report.passes_rate == 71
    # 71% < 75%, so gate fails
    assert report.passes_robustness_gate is False


def test_generate_report_threshold_gate(validator):
    """Test report at threshold (exactly 6 of 7 pass = 85%)."""
    regimes_data = [
        (MarketRegime.BULL, [1, 1, 0, 0, 1, 1], [1, 1, 0, 0, 1, 1]),        # Pass
        (MarketRegime.BEAR, [1, 0, 1, 0, 1, 0], [0, 1, 0, 1, 0, 1]),        # Fail
        (MarketRegime.HIGH_VOLATILITY, [1, 1, 0, 0], [1, 1, 0, 0]),         # Pass
        (MarketRegime.LOW_VOLATILITY, [1, 0, 1, 0], [1, 0, 1, 0]),          # Pass
        (MarketRegime.RISING_CORRELATION, [1, 1, 0, 0, 1], [1, 1, 0, 0, 1]), # Pass
        (MarketRegime.FALLING_CORRELATION, [1, 0, 1, 0, 1], [1, 0, 1, 0, 1]), # Pass
        (MarketRegime.LIQUIDATION, [1, 1, 0, 0], [1, 1, 0, 0]),             # Pass
    ]

    for regime_type, actual, predicted in regimes_data:
        validator.validate_regime(
            regime_type=regime_type,
            actual_signals=actual,
            predicted_signals=predicted,
            regime_characteristics="Test regime"
        )

    report = validator.generate_report()

    # 6 out of 7 pass (85%)
    assert report.passes_count == 6
    assert report.passes_rate == 85
    # 85% > 75%, so gate passes
    assert report.passes_robustness_gate is True


def test_regime_ranking(validator):
    """Test regime ranking by F1 score."""
    regimes_data = [
        (MarketRegime.BULL, [1, 1, 0, 0, 1, 1], [1, 1, 0, 0, 1, 1]),        # F1=1.0
        (MarketRegime.BEAR, [1, 0, 1, 0], [1, 0, 1, 0]),                    # F1=1.0
        (MarketRegime.HIGH_VOLATILITY, [1, 1, 0, 0, 1], [1, 1, 0, 0, 0]),   # F1=0.8
        (MarketRegime.LOW_VOLATILITY, [1, 0, 1, 0], [1, 0, 0, 1]),          # F1=0.5
        (MarketRegime.RISING_CORRELATION, [1, 1, 0], [0, 0, 1]),            # F1=0.0
        (MarketRegime.FALLING_CORRELATION, [1, 0], [1, 0]),                 # F1=1.0
        (MarketRegime.LIQUIDATION, [1, 1], [1, 1]),                         # F1=1.0
    ]

    for regime_type, actual, predicted in regimes_data:
        validator.validate_regime(
            regime_type=regime_type,
            actual_signals=actual,
            predicted_signals=predicted,
            regime_characteristics="Test"
        )

    ranking = validator.get_regime_ranking()

    assert len(ranking) == 7
    # Top should be F1=1.0
    assert ranking[0][1] == 1.0
    # Bottom should be F1=0.0
    assert ranking[-1][1] == 0.0


def test_get_failing_regimes(validator):
    """Test getting list of failing regimes."""
    regimes_data = [
        (MarketRegime.BULL, [1, 1, 0, 0, 1, 1], [1, 1, 0, 0, 1, 1]),        # Pass
        (MarketRegime.BEAR, [1, 0, 1, 0, 1, 0], [0, 1, 0, 1, 0, 1]),        # Fail
        (MarketRegime.HIGH_VOLATILITY, [1, 1, 0, 0], [1, 1, 0, 0]),         # Pass
        (MarketRegime.LOW_VOLATILITY, [1, 0, 1, 0], [1, 0, 1, 0]),          # Pass
        (MarketRegime.RISING_CORRELATION, [1, 1, 0, 0, 1], [0, 0, 1, 1, 0]), # Fail
        (MarketRegime.FALLING_CORRELATION, [1, 0, 1, 0, 1], [1, 0, 1, 0, 1]), # Pass
        (MarketRegime.LIQUIDATION, [1, 1, 0, 0], [1, 1, 0, 0]),             # Pass
    ]

    for regime_type, actual, predicted in regimes_data:
        validator.validate_regime(
            regime_type=regime_type,
            actual_signals=actual,
            predicted_signals=predicted,
            regime_characteristics="Test regime"
        )

    failing = validator.get_failing_regimes()

    assert len(failing) == 2
    assert "bear_market" in failing
    assert "rising_correlation" in failing


def test_save_report(validator, tmp_path):
    """Test saving report to JSON."""
    regimes_data = [
        (MarketRegime.BULL, [1, 1, 0, 0, 1, 1], [1, 1, 0, 0, 1, 1]),
        (MarketRegime.BEAR, [1, 0, 1, 0, 1, 0], [1, 0, 1, 0, 1, 0]),
        (MarketRegime.HIGH_VOLATILITY, [1, 1, 0, 0], [1, 1, 0, 0]),
        (MarketRegime.LOW_VOLATILITY, [1, 0, 1, 0], [1, 0, 1, 0]),
        (MarketRegime.RISING_CORRELATION, [1, 1, 0, 0, 1], [1, 1, 0, 0, 1]),
        (MarketRegime.FALLING_CORRELATION, [1, 0, 1, 0, 1], [1, 0, 1, 0, 1]),
        (MarketRegime.LIQUIDATION, [1, 1, 0, 0], [1, 1, 0, 0]),
    ]

    for regime_type, actual, predicted in regimes_data:
        validator.validate_regime(
            regime_type=regime_type,
            actual_signals=actual,
            predicted_signals=predicted,
            regime_characteristics="Test"
        )

    report = validator.generate_report()
    output_path = str(tmp_path / "robustness_report.json")

    validator.save_report(report, output_path)

    # Verify file exists
    import json
    with open(output_path) as f:
        saved = json.load(f)

    assert saved["spec_version"] == "b_004_spec_2026_09_25"
    assert len(saved["regimes"]) == 7
    assert saved["passes_rate"] == 100


def test_audit_trail_regime_coverage(validator):
    """Test regime coverage audit passes."""
    regimes_data = [
        (MarketRegime.BULL, [1, 1, 0, 0], [1, 1, 0, 0]),
        (MarketRegime.BEAR, [1, 0, 1, 0], [1, 0, 1, 0]),
        (MarketRegime.HIGH_VOLATILITY, [1, 1, 0, 0], [1, 1, 0, 0]),
        (MarketRegime.LOW_VOLATILITY, [1, 0, 1, 0], [1, 0, 1, 0]),
        (MarketRegime.RISING_CORRELATION, [1, 1, 0, 0], [1, 1, 0, 0]),
        (MarketRegime.FALLING_CORRELATION, [1, 0, 1, 0], [1, 0, 1, 0]),
        (MarketRegime.LIQUIDATION, [1, 1, 0, 0], [1, 1, 0, 0]),
    ]

    for regime_type, actual, predicted in regimes_data:
        validator.validate_regime(
            regime_type=regime_type,
            actual_signals=actual,
            predicted_signals=predicted,
            regime_characteristics="Test"
        )

    audit = validator.audit_trail_regime_coverage()

    assert audit["regime_coverage"] == "PASS"
    assert audit["total_regimes"] == 7
    assert audit["tested_regimes"] == 7
    assert len(audit["missing_regimes"]) == 0


def test_audit_trail_missing_regime(validator):
    """Test audit detects missing regime."""
    # Only validate 6 regimes
    regimes_data = [
        (MarketRegime.BULL, [1, 1, 0, 0], [1, 1, 0, 0]),
        (MarketRegime.BEAR, [1, 0, 1, 0], [1, 0, 1, 0]),
        (MarketRegime.HIGH_VOLATILITY, [1, 1, 0, 0], [1, 1, 0, 0]),
        (MarketRegime.LOW_VOLATILITY, [1, 0, 1, 0], [1, 0, 1, 0]),
        (MarketRegime.RISING_CORRELATION, [1, 1, 0, 0], [1, 1, 0, 0]),
        (MarketRegime.FALLING_CORRELATION, [1, 0, 1, 0], [1, 0, 1, 0]),
    ]

    for regime_type, actual, predicted in regimes_data:
        validator.validate_regime(
            regime_type=regime_type,
            actual_signals=actual,
            predicted_signals=predicted,
            regime_characteristics="Test"
        )

    audit = validator.audit_trail_regime_coverage()

    assert audit["regime_coverage"] == "FAIL"
    assert audit["tested_regimes"] == 6
    assert "liquidation_events" in audit["missing_regimes"]
