"""
Phase 4: Ablation Analysis Tests

Tests component importance evaluation via F1 drop measurement.

Authority: B-004_SPEC.md §"Validation & Walk-Forward Testing"
"""

import pytest
from datetime import datetime
from src.layers.layer3_wyckoff.ablation_analyzer import (
    AblationAnalyzer,
    ComponentCriticality,
)


@pytest.fixture
def analyzer():
    """Create analyzer with baseline F1 from Phase 3."""
    return AblationAnalyzer(baseline_f1=0.65)


def test_analyzer_init_valid():
    """Test analyzer initialization with valid baseline."""
    analyzer = AblationAnalyzer(baseline_f1=0.65)
    assert analyzer.baseline_f1 == 0.65
    assert len(analyzer.results) == 0


def test_analyzer_init_below_phase3_gate():
    """Test analyzer rejects F1 < 0.55 (Phase 3 requirement)."""
    with pytest.raises(ValueError, match="Baseline F1 must be ≥ 0.55"):
        AblationAnalyzer(baseline_f1=0.50)


def test_ablate_critical_component(analyzer):
    """Test critical component (F1 drop > 5%)."""
    # Baseline: 0.65, Ablated: 0.59 (6% drop)
    result = analyzer.ablate_component(
        component_name="wyckoff_structure",
        ablated_f1=0.59
    )

    assert result.component_name == "wyckoff_structure"
    assert result.baseline_f1 == 0.65
    assert result.ablated_f1 == 0.59
    assert abs(result.f1_drop - 0.06) < 0.001
    assert abs(result.f1_drop_pct - 9.23) < 0.1
    assert result.criticality == "critical"


def test_ablate_important_component(analyzer):
    """Test important component (F1 drop 2-5%)."""
    # Baseline: 0.65, Ablated: 0.62 (3% drop)
    result = analyzer.ablate_component(
        component_name="volume_analysis",
        ablated_f1=0.62
    )

    assert result.criticality == "important"
    assert 2 <= result.f1_drop_pct <= 5


def test_ablate_optional_component(analyzer):
    """Test optional component (F1 drop 0.5-2%)."""
    # Baseline: 0.65, Ablated: 0.6467 (0.507% drop)
    result = analyzer.ablate_component(
        component_name="momentum_confirmation",
        ablated_f1=0.6467
    )

    assert result.criticality == "optional"
    assert 0.5 < result.f1_drop_pct < 2


def test_ablate_redundant_component(analyzer):
    """Test redundant component (F1 drop ≈ 0%)."""
    # Baseline: 0.65, Ablated: 0.6499 (almost no change)
    result = analyzer.ablate_component(
        component_name="market_structure",
        ablated_f1=0.6499
    )

    assert result.criticality == "redundant"
    assert result.f1_drop_pct < 0.5


def test_ablate_all_components(analyzer):
    """Test ablating all 6 components."""
    ablations = [
        ("wyckoff_structure", 0.59),  # critical (9%)
        ("volume_analysis", 0.62),    # important (4.6%)
        ("selling_exhaustion", 0.63), # important (3%)
        ("smart_money_accumulation", 0.60),  # critical (7.7%)
        ("market_structure", 0.6499),  # redundant (<1%)
        ("momentum_confirmation", 0.648),  # optional (0.3%)
    ]

    for component, ablated_f1 in ablations:
        analyzer.ablate_component(component, ablated_f1)

    assert len(analyzer.results) == 6


def test_invalid_component_name(analyzer):
    """Test error on invalid component name."""
    with pytest.raises(ValueError, match="Unknown component"):
        analyzer.ablate_component(
            component_name="fake_component",
            ablated_f1=0.60
        )


def test_generate_report_complete(analyzer):
    """Test report generation with all components."""
    ablations = [
        ("wyckoff_structure", 0.59),
        ("volume_analysis", 0.62),
        ("selling_exhaustion", 0.63),
        ("smart_money_accumulation", 0.60),
        ("market_structure", 0.6499),
        ("momentum_confirmation", 0.648),
    ]

    for component, ablated_f1 in ablations:
        analyzer.ablate_component(component, ablated_f1)

    report = analyzer.generate_report()

    assert report.spec_version == "b_004_spec_2026_09_25"
    assert len(report.components) == 6
    assert report.critical_count == 2  # wyckoff_structure, smart_money
    assert report.important_count == 2  # volume_analysis, selling_exhaustion
    assert report.optional_count == 0   # momentum_confirmation is redundant (0.3% drop)
    assert report.redundant_count == 2  # market_structure, momentum_confirmation
    assert report.critical_components_identified is True


def test_generate_report_incomplete():
    """Test report fails with incomplete ablation."""
    analyzer = AblationAnalyzer(baseline_f1=0.65)

    # Only ablate 3 components
    analyzer.ablate_component("wyckoff_structure", 0.59)
    analyzer.ablate_component("volume_analysis", 0.62)
    analyzer.ablate_component("selling_exhaustion", 0.63)

    with pytest.raises(ValueError, match="Incomplete ablation"):
        analyzer.generate_report()


def test_component_ranking(analyzer):
    """Test component ranking by importance."""
    ablations = [
        ("wyckoff_structure", 0.59),
        ("volume_analysis", 0.62),
        ("selling_exhaustion", 0.63),
        ("smart_money_accumulation", 0.60),
        ("market_structure", 0.6499),
        ("momentum_confirmation", 0.648),
    ]

    for component, ablated_f1 in ablations:
        analyzer.ablate_component(component, ablated_f1)

    ranking = analyzer.get_component_ranking()

    # Check ranking is sorted by F1 drop (descending)
    assert len(ranking) == 6
    for i in range(len(ranking) - 1):
        assert ranking[i][2] >= ranking[i + 1][2]

    # Top should be wyckoff_structure (9.2% drop)
    assert ranking[0][0] == "wyckoff_structure"
    assert ranking[0][1] == "critical"


def test_get_critical_components(analyzer):
    """Test getting critical component list."""
    ablations = [
        ("wyckoff_structure", 0.59),
        ("volume_analysis", 0.62),
        ("selling_exhaustion", 0.63),
        ("smart_money_accumulation", 0.60),
        ("market_structure", 0.6499),
        ("momentum_confirmation", 0.648),
    ]

    for component, ablated_f1 in ablations:
        analyzer.ablate_component(component, ablated_f1)

    critical = analyzer.get_critical_components()

    assert len(critical) == 2
    assert "wyckoff_structure" in critical
    assert "smart_money_accumulation" in critical


def test_get_removable_components(analyzer):
    """Test getting removable component list."""
    ablations = [
        ("wyckoff_structure", 0.59),
        ("volume_analysis", 0.62),
        ("selling_exhaustion", 0.63),
        ("smart_money_accumulation", 0.60),
        ("market_structure", 0.6499),
        ("momentum_confirmation", 0.648),
    ]

    for component, ablated_f1 in ablations:
        analyzer.ablate_component(component, ablated_f1)

    removable = analyzer.get_removable_components()

    assert len(removable) == 2
    assert "market_structure" in removable
    assert "momentum_confirmation" in removable


def test_save_report(analyzer, tmp_path):
    """Test saving report to JSON."""
    ablations = [
        ("wyckoff_structure", 0.59),
        ("volume_analysis", 0.62),
        ("selling_exhaustion", 0.63),
        ("smart_money_accumulation", 0.60),
        ("market_structure", 0.6499),
        ("momentum_confirmation", 0.648),
    ]

    for component, ablated_f1 in ablations:
        analyzer.ablate_component(component, ablated_f1)

    report = analyzer.generate_report()
    output_path = str(tmp_path / "ablation_report.json")

    analyzer.save_report(report, output_path)

    # Verify file exists
    import json
    with open(output_path) as f:
        saved = json.load(f)

    assert saved["spec_version"] == "b_004_spec_2026_09_25"
    assert len(saved["components"]) == 6
    assert saved["critical_count"] == 2


def test_audit_trail_component_coverage(analyzer):
    """Test component coverage audit."""
    ablations = [
        ("wyckoff_structure", 0.59),
        ("volume_analysis", 0.62),
        ("selling_exhaustion", 0.63),
        ("smart_money_accumulation", 0.60),
        ("market_structure", 0.6499),
        ("momentum_confirmation", 0.648),
    ]

    for component, ablated_f1 in ablations:
        analyzer.ablate_component(component, ablated_f1)

    audit = analyzer.audit_trail_component_consistency()

    assert audit["component_coverage"] == "PASS"
    assert audit["total_components"] == 6
    assert audit["tested_components"] == 6
    assert len(audit["missing_components"]) == 0


def test_audit_trail_missing_component(analyzer):
    """Test audit detects missing component."""
    # Only ablate 5 components
    ablations = [
        ("wyckoff_structure", 0.59),
        ("volume_analysis", 0.62),
        ("selling_exhaustion", 0.63),
        ("smart_money_accumulation", 0.60),
        ("market_structure", 0.6499),
    ]

    for component, ablated_f1 in ablations:
        analyzer.ablate_component(component, ablated_f1)

    audit = analyzer.audit_trail_component_consistency()

    assert audit["component_coverage"] == "FAIL"
    assert audit["tested_components"] == 5
    assert "momentum_confirmation" in audit["missing_components"]


def test_criticality_thresholds():
    """Test criticality threshold boundaries."""
    # Baseline 0.60
    analyzer = AblationAnalyzer(baseline_f1=0.60)

    # Exactly 5% drop (just over critical threshold)
    result = analyzer.ablate_component("wyckoff_structure", 0.57)
    assert result.f1_drop_pct > 5
    assert result.criticality == "critical"

    # Exactly 2% drop (important)
    analyzer2 = AblationAnalyzer(baseline_f1=0.60)
    result2 = analyzer2.ablate_component("volume_analysis", 0.588)
    assert 1.9 < result2.f1_drop_pct < 2.1
    assert result2.criticality == "important"
