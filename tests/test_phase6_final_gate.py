"""
Phase 6: Final Validation Gate Tests

Tests aggregation of Phase 3, 4, 5 results into production readiness assessment.

Authority: B-004_SPEC.md §"Validation & Walk-Forward Testing"
"""

import pytest
from datetime import datetime
from src.layers.layer3_wyckoff.final_validation_gate import (
    FinalValidationGate,
    ProductionReadiness,
    GateResult,
)
from src.layers.layer3_wyckoff.walkforward_validator import (
    WFVReport,
    WindowResult,
)
from src.layers.layer3_wyckoff.ablation_analyzer import (
    AblationReport,
    ComponentResult,
)
from src.layers.layer3_wyckoff.robustness_validator import (
    RobustnessReport,
    RegimeResult,
)


@pytest.fixture
def gate():
    """Create final validation gate."""
    return FinalValidationGate()


@pytest.fixture
def wfv_report_pass():
    """Create passing WFV report."""
    windows = [
        WindowResult(1, "2024-01-01", "2024-06-30", "2021-01-01", "2023-12-31", "2024-01-01", "2024-06-30", 10, 2, 3, 5, 0.70, 0.77, 0.65, True, "bull", "Pass"),
        WindowResult(2, "2024-02-01", "2024-07-31", "2021-02-01", "2024-01-31", "2024-02-01", "2024-07-31", 10, 1, 2, 7, 0.72, 0.83, 0.68, True, "bull", "Pass"),
        WindowResult(3, "2024-03-01", "2024-08-31", "2021-03-01", "2024-02-28", "2024-03-01", "2024-08-31", 10, 3, 4, 3, 0.68, 0.71, 0.62, True, "bear", "Pass"),
        WindowResult(4, "2024-04-01", "2024-09-30", "2021-04-01", "2024-03-31", "2024-04-01", "2024-09-30", 10, 1, 1, 8, 0.75, 0.91, 0.70, True, "high_vol", "Pass"),
        WindowResult(5, "2024-05-01", "2024-10-31", "2021-05-01", "2024-04-30", "2024-05-01", "2024-10-31", 10, 2, 3, 5, 0.71, 0.77, 0.66, True, "low_vol", "Pass"),
        WindowResult(6, "2024-06-01", "2024-11-30", "2021-06-01", "2024-05-31", "2024-06-01", "2024-11-30", 10, 3, 4, 3, 0.69, 0.70, 0.64, True, "rising_corr", "Pass"),
    ]

    return WFVReport(
        spec_version="b_004_spec_2026_09_25",
        validation_date=datetime.now().isoformat(),
        windows=windows,
        f1_avg=0.66,
        f1_min=0.62,
        f1_max=0.70,
        passes_wfv_gate=True,
        passes_rate=100,
        no_lookahead_bias=True,
        refitting_cadence="monthly",
        next_gate="Phase 4: Ablation Analysis"
    )


@pytest.fixture
def wfv_report_fail():
    """Create failing WFV report."""
    windows = [
        WindowResult(1, "2024-01-01", "2024-06-30", "2021-01-01", "2023-12-31", "2024-01-01", "2024-06-30", 10, 5, 5, 0, 0.50, 0.67, 0.48, False, "bull", "Fail"),
        WindowResult(2, "2024-02-01", "2024-07-31", "2021-02-01", "2024-01-31", "2024-02-01", "2024-07-31", 10, 4, 4, 2, 0.55, 0.71, 0.52, False, "bull", "Fail"),
        WindowResult(3, "2024-03-01", "2024-08-31", "2021-03-01", "2024-02-28", "2024-03-01", "2024-08-31", 10, 4, 5, 1, 0.52, 0.67, 0.50, False, "bear", "Fail"),
        WindowResult(4, "2024-04-01", "2024-09-30", "2021-04-01", "2024-03-31", "2024-04-01", "2024-09-30", 10, 5, 5, 0, 0.51, 0.67, 0.49, False, "high_vol", "Fail"),
        WindowResult(5, "2024-05-01", "2024-10-31", "2021-05-01", "2024-04-30", "2024-05-01", "2024-10-31", 10, 4, 4, 2, 0.53, 0.71, 0.51, False, "low_vol", "Fail"),
        WindowResult(6, "2024-06-01", "2024-11-30", "2021-06-01", "2024-05-31", "2024-06-01", "2024-11-30", 10, 4, 5, 1, 0.52, 0.67, 0.50, False, "rising_corr", "Fail"),
    ]

    return WFVReport(
        spec_version="b_004_spec_2026_09_25",
        validation_date=datetime.now().isoformat(),
        windows=windows,
        f1_avg=0.50,
        f1_min=0.48,
        f1_max=0.52,
        passes_wfv_gate=False,
        passes_rate=0,
        no_lookahead_bias=True,
        refitting_cadence="monthly",
        next_gate="Remediate Phase 3"
    )


@pytest.fixture
def ablation_report_pass():
    """Create passing Ablation report."""
    components = [
        ComponentResult("wyckoff_structure", 0.66, 0.60, 0.06, 9.1, "critical", ">5%", "Critical"),
        ComponentResult("volume_analysis", 0.66, 0.63, 0.03, 4.5, "important", "2-5%", "Important"),
        ComponentResult("selling_exhaustion", 0.66, 0.64, 0.02, 3.0, "important", "2-5%", "Important"),
        ComponentResult("smart_money_accumulation", 0.66, 0.61, 0.05, 7.6, "critical", ">5%", "Critical"),
        ComponentResult("market_structure", 0.66, 0.6599, 0.0001, 0.15, "redundant", "~0%", "Redundant"),
        ComponentResult("momentum_confirmation", 0.66, 0.6499, 0.0101, 1.5, "optional", "<2%", "Optional"),
    ]

    return AblationReport(
        spec_version="b_004_spec_2026_09_25",
        validation_date=datetime.now().isoformat(),
        components=components,
        critical_count=2,
        important_count=2,
        optional_count=1,
        redundant_count=1,
        critical_components_identified=True,
        ablation_threshold=0.05,
        next_gate="Phase 5: Robustness Validation"
    )


@pytest.fixture
def ablation_report_fail():
    """Create failing Ablation report (no critical components)."""
    components = [
        ComponentResult("wyckoff_structure", 0.66, 0.6533, 0.0067, 1.0, "optional", "<2%", "Optional"),
        ComponentResult("volume_analysis", 0.66, 0.6532, 0.0068, 1.0, "optional", "<2%", "Optional"),
        ComponentResult("selling_exhaustion", 0.66, 0.6531, 0.0069, 1.0, "optional", "<2%", "Optional"),
        ComponentResult("smart_money_accumulation", 0.66, 0.6530, 0.0070, 1.1, "optional", "<2%", "Optional"),
        ComponentResult("market_structure", 0.66, 0.6529, 0.0071, 1.1, "optional", "<2%", "Optional"),
        ComponentResult("momentum_confirmation", 0.66, 0.6528, 0.0072, 1.1, "optional", "<2%", "Optional"),
    ]

    return AblationReport(
        spec_version="b_004_spec_2026_09_25",
        validation_date=datetime.now().isoformat(),
        components=components,
        critical_count=0,
        important_count=0,
        optional_count=6,
        redundant_count=0,
        critical_components_identified=False,
        ablation_threshold=0.05,
        next_gate="Remediate Phase 4"
    )


@pytest.fixture
def robustness_report_pass():
    """Create passing Robustness report."""
    regimes = [
        RegimeResult("bull_market", "BULL", 0.65, 0.70, 0.60, 10, 2, 3, 5, True, "Bull market conditions", 50, "Pass"),
        RegimeResult("bear_market", "BEAR", 0.62, 0.68, 0.58, 10, 3, 4, 3, True, "Bear market conditions", 50, "Pass"),
        RegimeResult("high_volatility", "HIGH_VOLATILITY", 0.60, 0.65, 0.55, 10, 4, 5, 1, True, "High vol", 50, "Pass"),
        RegimeResult("low_volatility", "LOW_VOLATILITY", 0.68, 0.73, 0.63, 10, 1, 1, 8, True, "Low vol", 50, "Pass"),
        RegimeResult("rising_correlation", "RISING_CORRELATION", 0.64, 0.69, 0.59, 10, 3, 4, 3, True, "Rising corr", 50, "Pass"),
        RegimeResult("falling_correlation", "FALLING_CORRELATION", 0.59, 0.63, 0.55, 10, 4, 6, 0, False, "Falling corr", 50, "Fail"),
        RegimeResult("liquidation_events", "LIQUIDATION", 0.63, 0.68, 0.58, 10, 3, 4, 3, True, "Liquidation", 50, "Pass"),
    ]

    return RobustnessReport(
        spec_version="b_004_spec_2026_09_25",
        validation_date=datetime.now().isoformat(),
        regimes=regimes,
        f1_avg=0.63,
        f1_min=0.59,
        f1_max=0.68,
        passes_robustness_gate=True,
        passes_count=6,
        passes_rate=86,
        next_gate="Phase 6: Final Validation Gate"
    )


@pytest.fixture
def robustness_report_fail():
    """Create failing Robustness report."""
    regimes = [
        RegimeResult("bull_market", "BULL", 0.48, 0.50, 0.46, 10, 5, 5, 0, False, "Bull", 50, "Fail"),
        RegimeResult("bear_market", "BEAR", 0.49, 0.51, 0.47, 10, 5, 5, 0, False, "Bear", 50, "Fail"),
        RegimeResult("high_volatility", "HIGH_VOLATILITY", 0.50, 0.52, 0.48, 10, 4, 6, 0, False, "High vol", 50, "Fail"),
        RegimeResult("low_volatility", "LOW_VOLATILITY", 0.51, 0.53, 0.49, 10, 4, 5, 1, False, "Low vol", 50, "Fail"),
        RegimeResult("rising_correlation", "RISING_CORRELATION", 0.50, 0.52, 0.48, 10, 4, 6, 0, False, "Rising corr", 50, "Fail"),
        RegimeResult("falling_correlation", "FALLING_CORRELATION", 0.48, 0.50, 0.46, 10, 5, 5, 0, False, "Falling corr", 50, "Fail"),
        RegimeResult("liquidation_events", "LIQUIDATION", 0.52, 0.55, 0.50, 10, 4, 4, 2, False, "Liquidation", 50, "Fail"),
    ]

    return RobustnessReport(
        spec_version="b_004_spec_2026_09_25",
        validation_date=datetime.now().isoformat(),
        regimes=regimes,
        f1_avg=0.50,
        f1_min=0.48,
        f1_max=0.52,
        passes_robustness_gate=False,
        passes_count=0,
        passes_rate=0,
        next_gate="Remediate Phase 5"
    )


def test_gate_init(gate):
    """Test gate initialization."""
    assert gate.wfv_report is None
    assert gate.ablation_report is None
    assert gate.robustness_report is None


def test_load_wfv_report(gate, wfv_report_pass):
    """Test loading WFV report."""
    gate.load_wfv_report(wfv_report_pass)
    assert gate.wfv_report == wfv_report_pass


def test_load_ablation_report(gate, ablation_report_pass):
    """Test loading Ablation report."""
    gate.load_ablation_report(ablation_report_pass)
    assert gate.ablation_report == ablation_report_pass


def test_load_robustness_report(gate, robustness_report_pass):
    """Test loading Robustness report."""
    gate.load_robustness_report(robustness_report_pass)
    assert gate.robustness_report == robustness_report_pass


def test_load_invalid_wfv_type(gate):
    """Test error on invalid WFV type."""
    with pytest.raises(TypeError, match="WFVReport"):
        gate.load_wfv_report("not a report")


def test_load_invalid_ablation_type(gate):
    """Test error on invalid Ablation type."""
    with pytest.raises(TypeError, match="AblationReport"):
        gate.load_ablation_report("not a report")


def test_load_invalid_robustness_type(gate):
    """Test error on invalid Robustness type."""
    with pytest.raises(TypeError, match="RobustnessReport"):
        gate.load_robustness_report("not a report")


def test_phase3_gate_pass(gate, wfv_report_pass):
    """Test Phase 3 gate passing."""
    gate.load_wfv_report(wfv_report_pass)
    result = gate.validate_phase3_gate()

    assert result.phase_name == "Phase 3: Walk-Forward Validation"
    assert result.passes is True
    assert "F1_avg=0.660" in result.actual_result


def test_phase3_gate_fail(gate, wfv_report_fail):
    """Test Phase 3 gate failing."""
    gate.load_wfv_report(wfv_report_fail)
    result = gate.validate_phase3_gate()

    assert result.passes is False
    assert result.actual_result == "F1_avg=0.500, pass_rate=0%"


def test_phase3_gate_not_loaded(gate):
    """Test error when Phase 3 not loaded."""
    with pytest.raises(ValueError, match="WFV report not loaded"):
        gate.validate_phase3_gate()


def test_phase4_gate_pass(gate, ablation_report_pass):
    """Test Phase 4 gate passing."""
    gate.load_ablation_report(ablation_report_pass)
    result = gate.validate_phase4_gate()

    assert result.phase_name == "Phase 4: Ablation Analysis"
    assert result.passes is True
    assert "Critical: 2" in result.actual_result


def test_phase4_gate_fail(gate, ablation_report_fail):
    """Test Phase 4 gate failing."""
    gate.load_ablation_report(ablation_report_fail)
    result = gate.validate_phase4_gate()

    assert result.passes is False
    assert "Critical: 0" in result.actual_result


def test_phase4_gate_not_loaded(gate):
    """Test error when Phase 4 not loaded."""
    with pytest.raises(ValueError, match="Ablation report not loaded"):
        gate.validate_phase4_gate()


def test_phase5_gate_pass(gate, robustness_report_pass):
    """Test Phase 5 gate passing."""
    gate.load_robustness_report(robustness_report_pass)
    result = gate.validate_phase5_gate()

    assert result.phase_name == "Phase 5: Robustness Validation"
    assert result.passes is True
    assert "86%" in result.actual_result


def test_phase5_gate_fail(gate, robustness_report_fail):
    """Test Phase 5 gate failing."""
    gate.load_robustness_report(robustness_report_fail)
    result = gate.validate_phase5_gate()

    assert result.passes is False
    assert "0%" in result.actual_result


def test_phase5_gate_not_loaded(gate):
    """Test error when Phase 5 not loaded."""
    with pytest.raises(ValueError, match="Robustness report not loaded"):
        gate.validate_phase5_gate()


def test_generate_report_all_pass(gate, wfv_report_pass, ablation_report_pass, robustness_report_pass):
    """Test report generation with all gates passing."""
    gate.load_wfv_report(wfv_report_pass)
    gate.load_ablation_report(ablation_report_pass)
    gate.load_robustness_report(robustness_report_pass)

    report = gate.generate_report()

    assert report.all_gates_pass is True
    assert report.production_readiness == "approved_for_production"
    assert report.wfv_f1_avg == 0.66
    assert report.ablation_critical_count == 2
    assert report.robustness_pass_rate == 86


def test_generate_report_phase3_fail(gate, wfv_report_fail, ablation_report_pass, robustness_report_pass):
    """Test report generation with Phase 3 failing."""
    gate.load_wfv_report(wfv_report_fail)
    gate.load_ablation_report(ablation_report_pass)
    gate.load_robustness_report(robustness_report_pass)

    report = gate.generate_report()

    assert report.all_gates_pass is False
    assert report.production_readiness == "conditional_approval"
    assert report.phase3_gate.passes is False


def test_generate_report_conditional_2of3(gate, wfv_report_fail, ablation_report_pass, robustness_report_pass):
    """Test conditional approval with 2 of 3 gates passing."""
    gate.load_wfv_report(wfv_report_fail)
    gate.load_ablation_report(ablation_report_pass)
    gate.load_robustness_report(robustness_report_pass)

    report = gate.generate_report()

    assert report.production_readiness == "conditional_approval"


def test_generate_report_rejected_1of3(gate, wfv_report_fail, ablation_report_fail, robustness_report_pass):
    """Test rejection with only 1 of 3 gates passing."""
    gate.load_wfv_report(wfv_report_fail)
    gate.load_ablation_report(ablation_report_fail)
    gate.load_robustness_report(robustness_report_pass)

    report = gate.generate_report()

    assert report.production_readiness == "not_ready_for_production"


def test_generate_report_rejected_0of3(gate, wfv_report_fail, ablation_report_fail, robustness_report_fail):
    """Test rejection with all gates failing."""
    gate.load_wfv_report(wfv_report_fail)
    gate.load_ablation_report(ablation_report_fail)
    gate.load_robustness_report(robustness_report_fail)

    report = gate.generate_report()

    assert report.production_readiness == "not_ready_for_production"


def test_generate_report_incomplete(gate, wfv_report_pass, ablation_report_pass):
    """Test error when reports incomplete."""
    gate.load_wfv_report(wfv_report_pass)
    gate.load_ablation_report(ablation_report_pass)

    with pytest.raises(ValueError, match="All phase reports must be loaded"):
        gate.generate_report()


def test_save_report(gate, wfv_report_pass, ablation_report_pass, robustness_report_pass, tmp_path):
    """Test saving report to JSON."""
    gate.load_wfv_report(wfv_report_pass)
    gate.load_ablation_report(ablation_report_pass)
    gate.load_robustness_report(robustness_report_pass)

    report = gate.generate_report()
    output_path = str(tmp_path / "final_gate_report.json")

    gate.save_report(report, output_path)

    import json
    with open(output_path) as f:
        saved = json.load(f)

    assert saved["all_gates_pass"] is True
    assert saved["production_readiness"] == "approved_for_production"
    assert saved["wfv_f1_avg"] == 0.66


def test_get_failing_phases_all_pass(gate, wfv_report_pass, ablation_report_pass, robustness_report_pass):
    """Test failing phases with all gates passing."""
    gate.load_wfv_report(wfv_report_pass)
    gate.load_ablation_report(ablation_report_pass)
    gate.load_robustness_report(robustness_report_pass)

    failing = gate.get_failing_phases()

    assert len(failing) == 0


def test_get_failing_phases_mixed(gate, wfv_report_fail, ablation_report_fail, robustness_report_pass):
    """Test failing phases with mixed results."""
    gate.load_wfv_report(wfv_report_fail)
    gate.load_ablation_report(ablation_report_fail)
    gate.load_robustness_report(robustness_report_pass)

    failing = gate.get_failing_phases()

    assert len(failing) == 2
    assert "Phase 3: Walk-Forward Validation" in failing
    assert "Phase 4: Ablation Analysis" in failing


def test_get_readiness_summary(gate, wfv_report_pass, ablation_report_pass, robustness_report_pass):
    """Test readiness summary."""
    gate.load_wfv_report(wfv_report_pass)
    gate.load_ablation_report(ablation_report_pass)
    gate.load_robustness_report(robustness_report_pass)

    summary = gate.get_readiness_summary()

    assert summary["production_readiness"] == "approved_for_production"
    assert summary["gates_passed"] == 3
    assert summary["gates_total"] == 3
    assert summary["wfv_f1_avg"] == 0.66


def test_audit_trail_all_loaded(gate, wfv_report_pass, ablation_report_pass, robustness_report_pass):
    """Test audit trail with all reports loaded."""
    gate.load_wfv_report(wfv_report_pass)
    gate.load_ablation_report(ablation_report_pass)
    gate.load_robustness_report(robustness_report_pass)

    audit = gate.audit_trail_all_gates_evaluated()

    assert audit["all_gates_evaluated"] == "PASS"
    assert audit["phase3_loaded"] is True
    assert audit["phase4_loaded"] is True
    assert audit["phase5_loaded"] is True


def test_audit_trail_incomplete(gate, wfv_report_pass):
    """Test audit trail with incomplete loading."""
    gate.load_wfv_report(wfv_report_pass)

    audit = gate.audit_trail_all_gates_evaluated()

    assert audit["all_gates_evaluated"] == "FAIL"
    assert audit["phase3_loaded"] is True
    assert audit["phase4_loaded"] is False
    assert audit["phase5_loaded"] is False
