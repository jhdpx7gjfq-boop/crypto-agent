"""WFV v2 — purged, embargoed walk-forward validation (IGWT Layer 8).

Contract
--------
An *observation* is a mapping with exactly the five registry columns::

    date       datetime.date   the point-in-time stamp
    asset      str             instrument symbol
    signal     float           model input, computed from data <= date
    fwdRet     float           label, realised over (date, date + horizon]
    regimeVol  float           trailing volatility at date, a conditioner

Why purge and embargo
---------------------
``fwdRet`` at date *t* is only known at *t + horizon*. Training on *t* and then
testing on *t + 1* therefore tests on an outcome the training label already
contained. Every fold here leaves a gap of at least ``horizon`` days between
the last training date and the first test date, and ``assert_no_leakage``
re-checks that property on the rows actually used, not on the fold boundaries
alone.

What is fitted
--------------
One parameter: the **sign** of the signal, taken from the training window. No
grid search, no threshold tuning, no re-use of the test window. A validator
that optimises inside the fold measures its own optimiser, not the signal.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

from igwt.validation import stats

logger = logging.getLogger(__name__)

CONTRACT_COLUMNS = ("date", "asset", "signal", "fwdRet", "regimeVol")
MIN_CROSS_SECTION = 3


class ContractError(ValueError):
    """Raised when observations do not satisfy the WFV contract."""


class LeakageError(AssertionError):
    """Raised when a fold's training labels reach into its test window."""


@dataclass(frozen=True)
class Fold:
    index: int
    train_start: date
    train_end: date
    test_start: date
    test_end: date

    @property
    def embargo_days(self) -> int:
        return (self.test_start - self.train_end).days - 1

    def as_dict(self) -> dict:
        return {
            "index": self.index,
            "train_start": self.train_start.isoformat(),
            "train_end": self.train_end.isoformat(),
            "test_start": self.test_start.isoformat(),
            "test_end": self.test_end.isoformat(),
            "embargo_days": self.embargo_days,
        }


@dataclass
class WFVConfig:
    horizon_days: int
    train_days: int = 180
    test_days: int = 30
    embargo_days: int | None = None  # defaults to horizon_days
    step_days: int | None = None  # defaults to test_days (non-overlapping tests)
    mode: str = "rolling"  # "rolling" | "expanding"
    quantile_size: int = 2  # assets per leg of the long/short spread
    min_cross_section: int = MIN_CROSS_SECTION
    min_test_dates: int = 5
    extras: dict = field(default_factory=dict)

    def resolved_embargo(self) -> int:
        embargo = self.horizon_days if self.embargo_days is None else self.embargo_days
        if embargo < self.horizon_days:
            raise ValueError(
                f"embargo_days={embargo} is shorter than horizon_days={self.horizon_days}: "
                "training labels would overlap the test window"
            )
        return embargo

    def resolved_step(self) -> int:
        return self.test_days if self.step_days is None else self.step_days


def validate_contract(observations: Sequence[dict]) -> None:
    """Fail loudly on anything the downstream maths would otherwise average away."""
    if not observations:
        raise ContractError("no observations")

    seen: set[tuple[date, str]] = set()
    for position, row in enumerate(observations):
        missing = [column for column in CONTRACT_COLUMNS if column not in row]
        if missing:
            raise ContractError(f"row {position}: missing columns {missing}")
        if not isinstance(row["date"], date):
            raise ContractError(f"row {position}: 'date' must be a datetime.date")
        for column in ("signal", "fwdRet", "regimeVol"):
            value = row[column]
            if not isinstance(value, (int, float)) or value != value:
                raise ContractError(f"row {position}: {column!r} is not a finite number: {value!r}")
        if row["regimeVol"] < 0:
            raise ContractError(f"row {position}: negative regimeVol {row['regimeVol']!r}")
        key = (row["date"], row["asset"])
        if key in seen:
            raise ContractError(f"duplicate observation for {key[1]} on {key[0].isoformat()}")
        seen.add(key)


def make_folds(observations: Sequence[dict], config: WFVConfig) -> list[Fold]:
    """Lay out walk-forward folds over the observed date range."""
    embargo = config.resolved_embargo()
    step = config.resolved_step()
    dates = sorted({row["date"] for row in observations})
    first, last = dates[0], dates[-1]

    folds: list[Fold] = []
    train_start = first
    index = 0
    while True:
        train_end = train_start + timedelta(days=config.train_days - 1)
        test_start = train_end + timedelta(days=embargo + 1)
        test_end = test_start + timedelta(days=config.test_days - 1)
        if test_end > last:
            break
        folds.append(
            Fold(
                index=index,
                train_start=first if config.mode == "expanding" else train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
        index += 1
        train_start += timedelta(days=step)

    if not folds:
        span = (last - first).days + 1
        needed = config.train_days + embargo + config.test_days
        raise ValueError(
            f"date span of {span} days cannot host a single fold "
            f"(train {config.train_days} + embargo {embargo} + test {config.test_days} = {needed})"
        )
    return folds


def assert_no_leakage(fold: Fold, train_rows: Sequence[dict], config: WFVConfig) -> None:
    """Every training label must resolve strictly before the test window opens."""
    for row in train_rows:
        label_resolves_on = row["date"] + timedelta(days=config.horizon_days)
        if label_resolves_on >= fold.test_start:
            raise LeakageError(
                f"fold {fold.index}: training row {row['asset']} {row['date'].isoformat()} "
                f"has a label resolving on {label_resolves_on.isoformat()}, "
                f"at or after test_start {fold.test_start.isoformat()}"
            )


def daily_information_coefficient(
    rows: Iterable[dict], *, min_cross_section: int = MIN_CROSS_SECTION
) -> list[tuple[date, float]]:
    """Cross-sectional Spearman IC per date.

    Computed *within* a date so that a market-wide move cannot masquerade as
    signal skill, then averaged across dates by the caller.
    """
    by_date: dict[date, list[dict]] = {}
    for row in rows:
        by_date.setdefault(row["date"], []).append(row)

    series: list[tuple[date, float]] = []
    for day in sorted(by_date):
        group = by_date[day]
        if len(group) < min_cross_section:
            continue
        correlation = stats.spearman(
            [item["signal"] for item in group], [item["fwdRet"] for item in group]
        )
        if correlation is not None:
            series.append((day, correlation))
    return series


def daily_long_short_spread(
    rows: Iterable[dict], *, direction: int, quantile_size: int
) -> list[tuple[date, float]]:
    """Per-date mean fwdRet of the top leg minus the bottom leg, by signed signal."""
    by_date: dict[date, list[dict]] = {}
    for row in rows:
        by_date.setdefault(row["date"], []).append(row)

    series: list[tuple[date, float]] = []
    for day in sorted(by_date):
        group = by_date[day]
        if len(group) < 2 * quantile_size:
            continue
        ordered = sorted(group, key=lambda item: direction * item["signal"])
        short_leg = ordered[:quantile_size]
        long_leg = ordered[-quantile_size:]
        spread = stats.mean([item["fwdRet"] for item in long_leg]) - stats.mean(
            [item["fwdRet"] for item in short_leg]
        )
        series.append((day, spread))
    return series


def run(observations: Sequence[dict], config: WFVConfig) -> dict:
    """Run the full walk-forward validation and return a report."""
    validate_contract(observations)
    folds = make_folds(observations, config)

    fold_reports = []
    pooled_oos_ic: list[float] = []
    pooled_oos_spread: list[float] = []

    for fold in folds:
        train_rows = [row for row in observations if fold.train_start <= row["date"] <= fold.train_end]
        test_rows = [row for row in observations if fold.test_start <= row["date"] <= fold.test_end]
        assert_no_leakage(fold, train_rows, config)

        train_ic_series = [
            value
            for _, value in daily_information_coefficient(
                train_rows, min_cross_section=config.min_cross_section
            )
        ]
        train_ic = stats.mean(train_ic_series)

        # The single fitted parameter, decided on training data only.
        direction = 0 if not train_ic else (1 if train_ic > 0 else -1)

        test_ic_pairs = daily_information_coefficient(
            test_rows, min_cross_section=config.min_cross_section
        )
        signed_test_ic = [direction * value for _, value in test_ic_pairs]
        # A direction of 0 means training gave no usable sign: there is no
        # position to take, so there is no spread to report either.
        spreads = (
            [
                value
                for _, value in daily_long_short_spread(
                    test_rows, direction=direction, quantile_size=config.quantile_size
                )
            ]
            if direction
            else []
        )

        regime = _regime_split(train_rows, test_rows, test_ic_pairs, direction, config)

        pooled_oos_ic.extend(signed_test_ic)
        pooled_oos_spread.extend(spreads)

        fold_reports.append(
            {
                **fold.as_dict(),
                "train_rows": len(train_rows),
                "test_rows": len(test_rows),
                "train_dates_scored": len(train_ic_series),
                "test_dates_scored": len(signed_test_ic),
                "train_ic": train_ic,
                "fitted_direction": direction,
                "oos_ic": stats.mean(signed_test_ic),
                "oos_ic_t_stat": stats.t_statistic(signed_test_ic),
                "oos_hit_rate": _hit_rate(signed_test_ic),
                "oos_long_short_spread": stats.mean(spreads),
                "regime_conditioned": regime,
                "sufficient_test_dates": len(signed_test_ic) >= config.min_test_dates,
            }
        )

    return {
        "config": {
            "horizon_days": config.horizon_days,
            "train_days": config.train_days,
            "test_days": config.test_days,
            "embargo_days": config.resolved_embargo(),
            "step_days": config.resolved_step(),
            "mode": config.mode,
            "quantile_size": config.quantile_size,
            "min_cross_section": config.min_cross_section,
            **config.extras,
        },
        "input": {
            "rows": len(observations),
            "assets": sorted({row["asset"] for row in observations}),
            "first_date": min(row["date"] for row in observations).isoformat(),
            "last_date": max(row["date"] for row in observations).isoformat(),
        },
        "folds": fold_reports,
        "aggregate": {
            "folds": len(fold_reports),
            "oos_dates_scored": len(pooled_oos_ic),
            "mean_oos_ic": stats.mean(pooled_oos_ic),
            "oos_ic_t_stat": stats.t_statistic(pooled_oos_ic),
            "oos_ic_hit_rate": _hit_rate(pooled_oos_ic),
            "folds_with_positive_oos_ic": sum(
                1 for item in fold_reports if (item["oos_ic"] or 0) > 0
            ),
            "mean_oos_long_short_spread": stats.mean(pooled_oos_spread),
            "direction_flips": _direction_flips(fold_reports),
        },
    }


def _regime_split(
    train_rows: Sequence[dict],
    test_rows: Sequence[dict],
    test_ic_pairs: Sequence[tuple[date, float]],
    direction: int,
    config: WFVConfig,
) -> dict:
    """Split out-of-sample dates by a volatility threshold learned on training data."""
    train_market_vol = _market_volatility_by_date(train_rows)
    threshold = stats.median(list(train_market_vol.values()))
    if threshold is None:
        return {"threshold": None, "low_vol_ic": None, "high_vol_ic": None}

    test_market_vol = _market_volatility_by_date(test_rows)
    low, high = [], []
    for day, value in test_ic_pairs:
        volatility = test_market_vol.get(day)
        if volatility is None:
            continue
        (low if volatility <= threshold else high).append(direction * value)

    return {
        "threshold": threshold,
        "low_vol_dates": len(low),
        "high_vol_dates": len(high),
        "low_vol_ic": stats.mean(low),
        "high_vol_ic": stats.mean(high),
    }


def _market_volatility_by_date(rows: Iterable[dict]) -> dict[date, float]:
    """Cross-sectional mean of regimeVol — a market-wide volatility proxy."""
    buckets: dict[date, list[float]] = {}
    for row in rows:
        buckets.setdefault(row["date"], []).append(row["regimeVol"])
    return {day: sum(values) / len(values) for day, values in buckets.items()}


def _hit_rate(values: Sequence[float]) -> float | None:
    return (sum(1 for value in values if value > 0) / len(values)) if values else None


def _direction_flips(fold_reports: Sequence[dict]) -> int:
    """How often the fitted sign changed between consecutive folds.

    A sign that will not sit still across folds is the signal telling you it is
    not stable, whatever the average IC says.
    """
    directions = [item["fitted_direction"] for item in fold_reports]
    return sum(1 for a, b in zip(directions, directions[1:]) if a != b and a and b)
