"""
Layer 2: Historical Regime Analysis — Tests (Phase 3)

Tests for:
- HistoricalRegimeAnalyzer (timeline, validation, statistics)
- RegimePatternDetector (bull runs, bear markets)
- Validation against historical market events

Status: Phase 3 (historical validation)
"""

import pytest
from datetime import datetime, timedelta
from src.layers.layer2_regime.historical_analyzer import (
    HistoricalRegimeAnalyzer,
    RegimePatternDetector,
    MarketEvent,
    HISTORICAL_EVENTS,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def analyzer():
    """Create analyzer with sample historical data."""
    a = HistoricalRegimeAnalyzer()

    # Add regimes for key historical periods
    test_data = [
        ("2017-01-15", 40, "SIDEWAYS", 1000),
        ("2017-06-15", 60, "BULL", 4000),
        ("2017-12-15", 85, "BULL", 13000),
        ("2018-01-15", 75, "BULL", 9000),
        ("2018-06-15", 40, "TRANSITION", 6500),
        ("2018-12-15", 15, "BEAR", 3600),
        ("2019-01-15", 20, "BEAR", 3500),
        ("2019-06-15", 45, "SIDEWAYS", 10500),
        ("2020-03-15", 10, "BEAR", 6500),
        ("2020-06-15", 50, "TRANSITION", 9300),
        ("2021-01-15", 70, "BULL", 33000),
        ("2021-06-15", 75, "BULL", 39000),
        ("2021-11-10", 90, "BULL", 69000),
        ("2022-01-15", 60, "TRANSITION", 38000),
        ("2022-06-15", 20, "BEAR", 20000),
        ("2022-11-15", 15, "BEAR", 16500),
        ("2023-01-15", 35, "TRANSITION", 19000),
        ("2023-06-15", 55, "SIDEWAYS", 25000),
        ("2024-04-15", 80, "BULL", 60000),
    ]

    for date, score, regime, price in test_data:
        a.add_regime(date, score, regime, price)

    return a


@pytest.fixture
def analyzer_empty():
    """Create empty analyzer."""
    return HistoricalRegimeAnalyzer()


# ============================================================================
# T3.1: Timeline Tests
# ============================================================================

def test_timeline_structure(analyzer):
    """Timeline has required fields."""
    timeline = analyzer.get_timeline()

    assert len(timeline) > 0

    for item in timeline:
        assert "date" in item
        assert "composite_score" in item
        assert "regime_state" in item
        assert "btc_price" in item
        assert "timestamp" in item


def test_timeline_ordered(analyzer):
    """Timeline is sorted by date."""
    timeline = analyzer.get_timeline()

    for i in range(1, len(timeline)):
        assert timeline[i-1]["date"] <= timeline[i]["date"]


def test_timeline_count(analyzer):
    """Timeline contains all added regimes."""
    timeline = analyzer.get_timeline()
    assert len(timeline) == 19


def test_add_regime(analyzer_empty):
    """Adding regimes increases timeline length."""
    assert len(analyzer_empty.get_timeline()) == 0

    analyzer_empty.add_regime("2026-10-06", 50, "SIDEWAYS", 42000)
    assert len(analyzer_empty.get_timeline()) == 1

    analyzer_empty.add_regime("2026-10-07", 55, "BULL", 43000)
    assert len(analyzer_empty.get_timeline()) == 2


# ============================================================================
# T3.2: Regime Lookup Tests
# ============================================================================

def test_get_regime_at_date_found(analyzer):
    """Lookup returns regime when date exists."""
    regime = analyzer.get_regime_at_date("2021-11-10")

    assert regime is not None
    assert regime.date == "2021-11-10"
    assert regime.regime_state == "BULL"
    assert regime.composite_score == 90


def test_get_regime_at_date_not_found(analyzer):
    """Lookup returns None when date doesn't exist."""
    regime = analyzer.get_regime_at_date("2021-11-11")
    assert regime is None


def test_get_regime_at_date_empty_analyzer(analyzer_empty):
    """Lookup on empty analyzer returns None."""
    regime = analyzer_empty.get_regime_at_date("2020-01-01")
    assert regime is None


# ============================================================================
# T3.3: Validation Tests
# ============================================================================

def test_validation_structure(analyzer):
    """Validation results have required fields."""
    result = analyzer.validate_against_events()

    assert "validation_results" in result
    assert "accuracy" in result
    assert "matches" in result
    assert "total_events" in result
    assert "notes" in result


def test_validation_results_count(analyzer):
    """Validation covers all historical events."""
    result = analyzer.validate_against_events()

    assert len(result["validation_results"]) == len(HISTORICAL_EVENTS)


def test_validation_accuracy_type(analyzer):
    """Accuracy is float in [0, 1]."""
    result = analyzer.validate_against_events()

    assert isinstance(result["accuracy"], float)
    assert 0.0 <= result["accuracy"] <= 1.0


def test_validation_with_known_events(analyzer):
    """Validation correctly identifies regime matches."""
    result = analyzer.validate_against_events()

    # Check 2017 bull peak
    bull_peak = [r for r in result["validation_results"] if r["event_name"] == "2017 Bull Peak"][0]
    assert bull_peak["expected_regime"] == "BULL"
    assert bull_peak["actual_regime"] == "BULL"
    assert bull_peak["match"] == True


def test_validation_missing_data(analyzer_empty):
    """Validation handles missing data gracefully."""
    result = analyzer_empty.validate_against_events()

    # All events should be unavailable
    for record in result["validation_results"]:
        assert record["actual_regime"] == "DATA_UNAVAILABLE"
        assert record["match"] == False


# ============================================================================
# T3.4: Statistics Tests
# ============================================================================

def test_statistics_structure(analyzer):
    """Statistics have all required fields."""
    stats = analyzer.get_regime_statistics()

    assert "total_periods" in stats
    assert "bull_periods" in stats
    assert "bear_periods" in stats
    assert "sideways_periods" in stats
    assert "transition_periods" in stats
    assert "avg_score" in stats
    assert "bull_percentage" in stats
    assert "bear_percentage" in stats


def test_statistics_totals(analyzer):
    """Statistics totals sum correctly."""
    stats = analyzer.get_regime_statistics()

    total = (stats["bull_periods"] + stats["bear_periods"] +
             stats["sideways_periods"] + stats["transition_periods"])
    assert total == stats["total_periods"]


def test_statistics_percentages(analyzer):
    """Percentages sum to ~100."""
    stats = analyzer.get_regime_statistics()

    total_pct = (stats["bull_percentage"] + stats["bear_percentage"] +
                 stats["sideways_percentage"] + stats["transition_percentage"])
    assert 99.5 < total_pct <= 100.5


def test_statistics_empty(analyzer_empty):
    """Empty analyzer returns zero statistics."""
    stats = analyzer_empty.get_regime_statistics()

    assert stats["total_periods"] == 0
    assert stats["bull_periods"] == 0
    assert stats["avg_score"] == 0.0


def test_statistics_avg_score(analyzer):
    """Average score calculation."""
    stats = analyzer.get_regime_statistics()

    # Should be reasonable (between min and max seen)
    assert 20 < stats["avg_score"] < 75


# ============================================================================
# T3.5: Transition Detection Tests
# ============================================================================

def test_regime_transitions(analyzer):
    """Transitions are detected correctly."""
    transitions = analyzer.get_regime_transitions()

    assert len(transitions) > 0

    # Each transition should have required fields
    for t in transitions:
        assert "from_date" in t
        assert "to_date" in t
        assert "from_regime" in t
        assert "to_regime" in t
        assert "score_change" in t
        assert "days_apart" in t


def test_regime_transitions_ordered(analyzer):
    """Transitions are chronologically ordered."""
    transitions = analyzer.get_regime_transitions()

    for i in range(1, len(transitions)):
        assert transitions[i-1]["to_date"] <= transitions[i]["from_date"]


def test_transitions_detect_major_changes(analyzer):
    """Transitions detect major regime changes."""
    transitions = analyzer.get_regime_transitions()

    # Should detect 2017 BULL → BEAR transition
    bear_transitions = [t for t in transitions if t["from_regime"] == "BULL" and t["to_regime"] in ["BEAR", "TRANSITION"]]
    assert len(bear_transitions) > 0


# ============================================================================
# T3.6: Pattern Detection — Bull Runs
# ============================================================================

def test_bull_run_detection(analyzer):
    """Bull runs are detected."""
    detector = RegimePatternDetector(analyzer)
    bull_runs = detector.detect_bull_runs()

    assert len(bull_runs) > 0

    for run in bull_runs:
        assert "start_date" in run
        assert "end_date" in run
        assert "duration_days" in run
        assert "avg_score" in run
        assert "peak_score" in run


def test_bull_run_scoring(analyzer):
    """Bull runs have reasonable scores."""
    detector = RegimePatternDetector(analyzer)
    bull_runs = detector.detect_bull_runs()

    for run in bull_runs:
        assert 50 <= run["peak_score"] <= 100
        assert run["avg_score"] >= 50


def test_bull_run_duration(analyzer):
    """Bull runs have positive duration."""
    detector = RegimePatternDetector(analyzer)
    bull_runs = detector.detect_bull_runs()

    for run in bull_runs:
        assert run["duration_days"] >= 0


def test_identifies_2017_bull_run(analyzer):
    """Detector identifies 2017 bull run."""
    detector = RegimePatternDetector(analyzer)
    bull_runs = detector.detect_bull_runs()

    # Should find bull run starting around 2017-06
    early_runs = [r for r in bull_runs if r["start_date"].startswith("2017")]
    assert len(early_runs) > 0


# ============================================================================
# T3.7: Pattern Detection — Bear Markets
# ============================================================================

def test_bear_market_detection(analyzer):
    """Bear markets are detected."""
    detector = RegimePatternDetector(analyzer)
    bear_markets = detector.detect_bear_markets()

    assert len(bear_markets) > 0

    for market in bear_markets:
        assert "start_date" in market
        assert "end_date" in market
        assert "duration_days" in market
        assert "avg_score" in market
        assert "lowest_score" in market


def test_bear_market_scoring(analyzer):
    """Bear markets have low scores."""
    detector = RegimePatternDetector(analyzer)
    bear_markets = detector.detect_bear_markets()

    for market in bear_markets:
        assert market["lowest_score"] < 40
        assert market["avg_score"] < 40


def test_bear_market_duration(analyzer):
    """Bear markets have positive duration."""
    detector = RegimePatternDetector(analyzer)
    bear_markets = detector.detect_bear_markets()

    for market in bear_markets:
        assert market["duration_days"] >= 0


def test_identifies_2018_bear_market(analyzer):
    """Detector identifies 2018 bear market."""
    detector = RegimePatternDetector(analyzer)
    bear_markets = detector.detect_bear_markets()

    # Should find bear market in 2018
    bear_2018 = [m for m in bear_markets if m["start_date"].startswith("2018")]
    assert len(bear_2018) > 0


# ============================================================================
# T3.8: Historical Events Reference
# ============================================================================

def test_historical_events_defined():
    """Historical events are defined."""
    assert len(HISTORICAL_EVENTS) > 0


def test_historical_events_structure():
    """Historical events have required fields."""
    for event in HISTORICAL_EVENTS:
        assert event.date  # YYYY-MM-DD
        assert event.name
        assert event.regime_expected
        assert event.description


def test_historical_events_valid_regimes():
    """Historical event regimes are valid."""
    valid_regimes = {"BULL", "BEAR", "SIDEWAYS", "TRANSITION"}

    for event in HISTORICAL_EVENTS:
        assert event.regime_expected in valid_regimes


def test_historical_events_chronological():
    """Historical events are in order."""
    dates = [e.date for e in HISTORICAL_EVENTS]

    for i in range(1, len(dates)):
        assert dates[i-1] <= dates[i]


# ============================================================================
# T3.9: Integration Tests
# ============================================================================

def test_full_analysis_workflow(analyzer):
    """Complete analysis workflow succeeds."""
    # Timeline
    timeline = analyzer.get_timeline()
    assert len(timeline) > 0

    # Validation
    validation = analyzer.validate_against_events()
    assert validation["accuracy"] >= 0

    # Statistics
    stats = analyzer.get_regime_statistics()
    assert stats["total_periods"] > 0

    # Transitions
    transitions = analyzer.get_regime_transitions()
    assert isinstance(transitions, list)

    # Patterns
    detector = RegimePatternDetector(analyzer)
    bull_runs = detector.detect_bull_runs()
    bear_markets = detector.detect_bear_markets()

    assert len(bull_runs) + len(bear_markets) > 0


def test_regime_consistency(analyzer):
    """Regime data is internally consistent."""
    timeline = analyzer.get_timeline()

    for item in timeline:
        # Score range
        assert 0 <= item["composite_score"] <= 100

        # Valid regime
        assert item["regime_state"] in {"BULL", "BEAR", "SIDEWAYS", "TRANSITION"}

        # Reasonable price
        assert item["btc_price"] > 0
