"""Snapshot validation: every dropped point must be counted, never absorbed."""

from datetime import date

import pytest

from igwt.features import panel

DAY_MS = 86_400_000
DAY_0 = 1_757_980_800_000  # 2025-09-16T00:00:00Z


def payload(points, volumes=None):
    return {"prices": points, "total_volumes": volumes or []}


class TestIrregularities:
    def test_trailing_intraday_point_is_dropped(self):
        series = panel.parse_market_chart(
            "X", payload([[DAY_0, 10.0], [DAY_0 + DAY_MS, 11.0], [DAY_0 + DAY_MS + 75_000, 11.5]])
        )
        assert series.report["intraday_points_dropped"] == 1
        assert series.closes == [10.0, 11.0]

    def test_duplicate_dates_keep_the_first_occurrence(self):
        series = panel.parse_market_chart("X", payload([[DAY_0, 10.0], [DAY_0, 99.0]]))
        assert series.report["duplicate_dates_dropped"] == 1
        assert series.closes == [10.0]

    @pytest.mark.parametrize("bad_price", [0, -5.0, None, float("nan")])
    def test_non_positive_or_missing_prices_are_dropped(self, bad_price):
        series = panel.parse_market_chart(
            "X", payload([[DAY_0, 10.0], [DAY_0 + DAY_MS, bad_price]])
        )
        assert series.report["invalid_prices_dropped"] == 1
        assert series.closes == [10.0]

    def test_calendar_gaps_are_reported_not_filled(self):
        series = panel.parse_market_chart(
            "X", payload([[DAY_0, 10.0], [DAY_0 + 3 * DAY_MS, 12.0]])
        )
        assert len(series) == 2
        assert series.report["calendar_gaps"] == [
            {"after": "2025-09-16", "before": "2025-09-19", "missing_days": 2}
        ]

    def test_out_of_order_input_is_sorted_and_flagged(self):
        series = panel.parse_market_chart(
            "X", payload([[DAY_0 + DAY_MS, 11.0], [DAY_0, 10.0]])
        )
        assert series.report["out_of_order_input"] is True
        assert series.dates == [date(2025, 9, 16), date(2025, 9, 17)]
        assert series.closes == [10.0, 11.0]

    def test_volume_is_carried_only_when_its_timestamp_matches(self):
        series = panel.parse_market_chart(
            "X",
            payload([[DAY_0, 10.0], [DAY_0 + DAY_MS, 11.0]], volumes=[[DAY_0, 500.0]]),
        )
        assert series.volumes == [500.0, None]


class TestAccounting:
    def test_accepted_plus_dropped_equals_raw(self):
        points = [
            [DAY_0, 10.0],
            [DAY_0, 99.0],
            [DAY_0 + DAY_MS, -1.0],
            [DAY_0 + 2 * DAY_MS, 12.0],
            [DAY_0 + 2 * DAY_MS + 60_000, 12.5],
        ]
        report = panel.parse_market_chart("X", payload(points)).report
        dropped = (
            report["intraday_points_dropped"]
            + report["duplicate_dates_dropped"]
            + report["invalid_prices_dropped"]
        )
        assert report["accepted_points"] + dropped == report["raw_points"]


class TestPanelIndex:
    def test_common_index_is_a_union_so_the_panel_stays_ragged(self):
        first = panel.parse_market_chart("A", payload([[DAY_0, 1.0]]))
        second = panel.parse_market_chart("B", payload([[DAY_0 + DAY_MS, 2.0]]))
        assert panel.common_date_index([first, second]) == [
            date(2025, 9, 16),
            date(2025, 9, 17),
        ]
