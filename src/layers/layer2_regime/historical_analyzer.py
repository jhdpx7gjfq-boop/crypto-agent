"""
Layer 2: Historical Regime Analysis — Phase 3

Computes market regimes over historical periods (2013-present).
Validates against known market events.
Generates regime timeline for visualization.

Key Events:
- 2017-12: First bull peak (~$20k)
- 2018-12: Bear bottom
- 2020-03: COVID crash + recovery
- 2021-11: All-time high (~$69k)
- 2022-06: Bear peak (FTX/Luna)
- 2022-11: Bear bottom (FTX collapse)
- 2024-02: Recovery begins
- 2024-11: Presidential cycle (post-election)

Status: Phase 3 (historical validation)
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MarketEvent:
    """Known market event for validation."""
    date: str  # YYYY-MM-DD
    name: str
    regime_expected: str  # Expected regime at this date
    description: str


# Historical market events for validation
HISTORICAL_EVENTS = [
    MarketEvent(
        date="2017-12-15",
        name="2017 Bull Peak",
        regime_expected="BULL",
        description="BTC reached ~$20k, euphoria peak",
    ),
    MarketEvent(
        date="2018-12-15",
        name="2018 Bear Bottom",
        regime_expected="BEAR",
        description="BTC bottomed ~$3.5k, capitulation",
    ),
    MarketEvent(
        date="2020-03-15",
        name="COVID Crash",
        regime_expected="BEAR",
        description="Panic selling, BTC -50% in 1 week",
    ),
    MarketEvent(
        date="2020-08-01",
        name="2020 Recovery Start",
        regime_expected="BULL",
        description="Post-COVID recovery, risk-on",
    ),
    MarketEvent(
        date="2021-11-10",
        name="2021 ATH",
        regime_expected="BULL",
        description="BTC reached ~$69k, all-time high",
    ),
    MarketEvent(
        date="2022-06-15",
        name="2022 Luna/FTX Crisis",
        regime_expected="BEAR",
        description="Luna collapse, FTX issues, strong bearish signals",
    ),
    MarketEvent(
        date="2022-11-15",
        name="2022 Bear Bottom",
        regime_expected="BEAR",
        description="FTX collapse, BTC ~$16k",
    ),
    MarketEvent(
        date="2023-01-15",
        name="2023 Recovery Start",
        regime_expected="TRANSITION",
        description="Post-FTX stabilization, early recovery",
    ),
    MarketEvent(
        date="2024-04-15",
        name="2024 Bull Run",
        regime_expected="BULL",
        description="Halving-driven bull, ETH outperformance",
    ),
]


@dataclass
class RegimeTimestamp:
    """Regime at a point in time."""
    date: str  # YYYY-MM-DD
    composite_score: int  # 0-100
    regime_state: str  # BULL, BEAR, SIDEWAYS, TRANSITION
    btc_price: float  # For context
    timestamp_iso: str  # ISO 8601


class HistoricalRegimeAnalyzer:
    """
    Analyze market regimes over historical periods.
    Validate against known events.
    Generate timeline for visualization.
    """

    def __init__(self):
        """Initialize analyzer with known events."""
        self.events = HISTORICAL_EVENTS
        self.regimes: List[RegimeTimestamp] = []

    def add_regime(
        self,
        date: str,
        composite_score: int,
        regime_state: str,
        btc_price: float,
    ) -> None:
        """
        Add computed regime to timeline.

        Args:
            date: YYYY-MM-DD format
            composite_score: 0-100
            regime_state: BULL, BEAR, SIDEWAYS, TRANSITION
            btc_price: Price at this date (for context)
        """
        self.regimes.append(RegimeTimestamp(
            date=date,
            composite_score=composite_score,
            regime_state=regime_state,
            btc_price=btc_price,
            timestamp_iso=f"{date}T00:00:00Z",
        ))

    def get_timeline(self) -> List[Dict[str, Any]]:
        """
        Get regime timeline as list of dicts (visualization-ready).

        Returns:
            List of regime records sorted by date
        """
        return [
            {
                "date": r.date,
                "composite_score": r.composite_score,
                "regime_state": r.regime_state,
                "btc_price": r.btc_price,
                "timestamp": r.timestamp_iso,
            }
            for r in sorted(self.regimes, key=lambda r: r.date)
        ]

    def get_regime_at_date(self, date: str) -> Optional[RegimeTimestamp]:
        """
        Get regime at specific date.

        Args:
            date: YYYY-MM-DD format

        Returns:
            RegimeTimestamp or None if not found
        """
        for regime in self.regimes:
            if regime.date == date:
                return regime
        return None

    def validate_against_events(self) -> Dict[str, Any]:
        """
        Validate computed regimes against known historical events.

        Returns:
            {
                "validation_results": [
                    {
                        "event_name": str,
                        "event_date": str,
                        "expected_regime": str,
                        "actual_regime": str,
                        "match": bool,
                        "score_at_event": int,
                    },
                    ...
                ],
                "accuracy": float (0-1),
                "notes": str,
            }
        """
        validation_results = []
        matches = 0

        for event in self.events:
            regime = self.get_regime_at_date(event.date)

            if regime is None:
                # Data not available for this period
                result = {
                    "event_name": event.name,
                    "event_date": event.date,
                    "expected_regime": event.regime_expected,
                    "actual_regime": "DATA_UNAVAILABLE",
                    "match": False,
                    "score_at_event": None,
                    "note": "Regime data not available for this date",
                }
            else:
                # Check if expected regime matches
                match = regime.regime_state == event.regime_expected
                if match:
                    matches += 1

                result = {
                    "event_name": event.name,
                    "event_date": event.date,
                    "expected_regime": event.regime_expected,
                    "actual_regime": regime.regime_state,
                    "match": match,
                    "score_at_event": regime.composite_score,
                    "btc_price_at_event": regime.btc_price,
                    "description": event.description,
                }

            validation_results.append(result)

        accuracy = matches / len(self.events) if self.events else 0.0

        return {
            "validation_results": validation_results,
            "accuracy": round(accuracy, 2),
            "matches": matches,
            "total_events": len(self.events),
            "notes": f"Regime detector accuracy: {int(accuracy*100)}% on {len(self.events)} historical events",
        }

    def get_regime_statistics(self) -> Dict[str, Any]:
        """
        Compute statistics on historical regimes.

        Returns:
            {
                "total_periods": int,
                "bull_periods": int,
                "bear_periods": int,
                "sideways_periods": int,
                "transition_periods": int,
                "avg_score": float,
                "bull_percentage": float,
                "bear_percentage": float,
            }
        """
        if not self.regimes:
            return {
                "total_periods": 0,
                "bull_periods": 0,
                "bear_periods": 0,
                "sideways_periods": 0,
                "transition_periods": 0,
                "avg_score": 0.0,
                "bull_percentage": 0.0,
                "bear_percentage": 0.0,
            }

        bull_count = sum(1 for r in self.regimes if r.regime_state == "BULL")
        bear_count = sum(1 for r in self.regimes if r.regime_state == "BEAR")
        sideways_count = sum(1 for r in self.regimes if r.regime_state == "SIDEWAYS")
        transition_count = sum(1 for r in self.regimes if r.regime_state == "TRANSITION")

        avg_score = sum(r.composite_score for r in self.regimes) / len(self.regimes)

        total = len(self.regimes)

        return {
            "total_periods": total,
            "bull_periods": bull_count,
            "bear_periods": bear_count,
            "sideways_periods": sideways_count,
            "transition_periods": transition_count,
            "avg_score": round(avg_score, 2),
            "bull_percentage": round(100 * bull_count / total, 1),
            "bear_percentage": round(100 * bear_count / total, 1),
            "sideways_percentage": round(100 * sideways_count / total, 1),
            "transition_percentage": round(100 * transition_count / total, 1),
        }

    def get_regime_transitions(self) -> List[Dict[str, Any]]:
        """
        Find regime transitions (BULL→BEAR, etc).

        Returns:
            List of transition records with dates and scores
        """
        transitions = []
        sorted_regimes = sorted(self.regimes, key=lambda r: r.date)

        for i in range(1, len(sorted_regimes)):
            prev = sorted_regimes[i - 1]
            curr = sorted_regimes[i]

            if prev.regime_state != curr.regime_state:
                transitions.append({
                    "from_date": prev.date,
                    "to_date": curr.date,
                    "from_regime": prev.regime_state,
                    "to_regime": curr.regime_state,
                    "score_change": curr.composite_score - prev.composite_score,
                    "days_apart": self._days_between(prev.date, curr.date),
                })

        return transitions

    @staticmethod
    def _days_between(date1: str, date2: str) -> int:
        """Calculate days between two YYYY-MM-DD dates."""
        try:
            d1 = datetime.strptime(date1, "%Y-%m-%d")
            d2 = datetime.strptime(date2, "%Y-%m-%d")
            return (d2 - d1).days
        except ValueError:
            return 0


class RegimePatternDetector:
    """
    Detect patterns in historical regime data.

    Examples:
    - Bull run length (days from TRANSITION to peak)
    - Bear drawdown severity
    - Regime persistence (how long before transition)
    """

    def __init__(self, analyzer: HistoricalRegimeAnalyzer):
        """Initialize with analyzer instance."""
        self.analyzer = analyzer

    def detect_bull_runs(self) -> List[Dict[str, Any]]:
        """
        Detect bull run periods (BULL regime segments).

        Returns:
            List of bull run records with start/end dates, duration, scores
        """
        bull_runs = []
        sorted_regimes = sorted(self.analyzer.regimes, key=lambda r: r.date)

        bull_start = None
        bull_scores = []

        for regime in sorted_regimes:
            if regime.regime_state == "BULL":
                if bull_start is None:
                    bull_start = regime.date
                bull_scores.append(regime.composite_score)
            else:
                if bull_start is not None:
                    # Bull run ended
                    bull_runs.append({
                        "start_date": bull_start,
                        "end_date": regime.date,  # Date of transition
                        "duration_days": self._days_between(bull_start, regime.date),
                        "avg_score": round(sum(bull_scores) / len(bull_scores), 2),
                        "peak_score": max(bull_scores),
                        "periods": len(bull_scores),
                    })
                    bull_start = None
                    bull_scores = []

        # Handle case where data ends in bull run
        if bull_start is not None:
            bull_runs.append({
                "start_date": bull_start,
                "end_date": sorted_regimes[-1].date if sorted_regimes else bull_start,
                "duration_days": self._days_between(bull_start, sorted_regimes[-1].date) if sorted_regimes else 0,
                "avg_score": round(sum(bull_scores) / len(bull_scores), 2),
                "peak_score": max(bull_scores),
                "periods": len(bull_scores),
                "status": "ONGOING",
            })

        return bull_runs

    def detect_bear_markets(self) -> List[Dict[str, Any]]:
        """
        Detect bear market periods (BEAR regime segments).

        Returns:
            List of bear market records with start/end dates, duration, scores
        """
        bear_markets = []
        sorted_regimes = sorted(self.analyzer.regimes, key=lambda r: r.date)

        bear_start = None
        bear_scores = []

        for regime in sorted_regimes:
            if regime.regime_state == "BEAR":
                if bear_start is None:
                    bear_start = regime.date
                bear_scores.append(regime.composite_score)
            else:
                if bear_start is not None:
                    # Bear market ended
                    bear_markets.append({
                        "start_date": bear_start,
                        "end_date": regime.date,
                        "duration_days": self._days_between(bear_start, regime.date),
                        "avg_score": round(sum(bear_scores) / len(bear_scores), 2),
                        "lowest_score": min(bear_scores),
                        "periods": len(bear_scores),
                    })
                    bear_start = None
                    bear_scores = []

        # Handle case where data ends in bear market
        if bear_start is not None:
            bear_markets.append({
                "start_date": bear_start,
                "end_date": sorted_regimes[-1].date if sorted_regimes else bear_start,
                "duration_days": self._days_between(bear_start, sorted_regimes[-1].date) if sorted_regimes else 0,
                "avg_score": round(sum(bear_scores) / len(bear_scores), 2),
                "lowest_score": min(bear_scores),
                "periods": len(bear_scores),
                "status": "ONGOING",
            })

        return bear_markets

    @staticmethod
    def _days_between(date1: str, date2: str) -> int:
        """Calculate days between two YYYY-MM-DD dates."""
        try:
            d1 = datetime.strptime(date1, "%Y-%m-%d")
            d2 = datetime.strptime(date2, "%Y-%m-%d")
            return (d2 - d1).days
        except ValueError:
            return 0
