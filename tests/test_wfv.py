"""WFV v2: leakage guards, and the sensitivity/specificity of the verdict."""

import random
from datetime import date, timedelta

import pytest

from igwt.validation import wfv

ASSETS = ["A", "B", "C", "D", "E", "F", "G"]
START = date(2025, 1, 1)


def observations(days, *, relation, seed=7, vol=0.5):
    """Build a synthetic panel.

    Synthetic data is the right tool *here* — these tests interrogate the
    validator, where the answer must be known in advance. The fixture itself
    never uses it.
    """
    rng = random.Random(seed)
    rows = []
    for offset in range(days):
        day = START + timedelta(days=offset)
        for asset in ASSETS:
            forward = rng.gauss(0, 0.05)
            rows.append(
                {
                    "date": day,
                    "asset": asset,
                    "signal": relation(forward, rng),
                    "fwdRet": forward,
                    "regimeVol": abs(rng.gauss(vol, 0.1)),
                }
            )
    return rows


def config(**overrides):
    defaults = {"horizon_days": 7, "train_days": 90, "test_days": 30}
    return wfv.WFVConfig(**{**defaults, **overrides})


class TestEmbargo:
    def test_embargo_defaults_to_the_label_horizon(self):
        assert config(horizon_days=7).resolved_embargo() == 7

    def test_embargo_shorter_than_the_horizon_is_rejected(self):
        with pytest.raises(ValueError, match="shorter than horizon"):
            config(horizon_days=7, embargo_days=3).resolved_embargo()

    def test_every_fold_keeps_the_embargo(self):
        rows = observations(400, relation=lambda forward, rng: rng.gauss(0, 1))
        folds = wfv.make_folds(rows, config())
        assert folds
        assert all(fold.embargo_days >= 7 for fold in folds)

    def test_test_windows_do_not_overlap_by_default(self):
        rows = observations(400, relation=lambda forward, rng: rng.gauss(0, 1))
        folds = wfv.make_folds(rows, config())
        for earlier, later in zip(folds, folds[1:]):
            assert earlier.test_end < later.test_start

    def test_too_short_a_history_raises_rather_than_silently_skipping(self):
        rows = observations(40, relation=lambda forward, rng: rng.gauss(0, 1))
        with pytest.raises(ValueError, match="cannot host a single fold"):
            wfv.make_folds(rows, config())


class TestLeakageGuard:
    def test_a_training_label_reaching_the_test_window_is_caught(self):
        fold = wfv.Fold(
            index=0,
            train_start=date(2025, 1, 1),
            train_end=date(2025, 3, 31),
            test_start=date(2025, 4, 3),  # only 2 days of embargo
            test_end=date(2025, 4, 30),
        )
        train_rows = [
            {
                "date": date(2025, 3, 31),
                "asset": "A",
                "signal": 0.0,
                "fwdRet": 0.0,
                "regimeVol": 0.5,
            }
        ]
        with pytest.raises(wfv.LeakageError, match="label resolving on"):
            wfv.assert_no_leakage(fold, train_rows, config(horizon_days=7))

    def test_a_properly_embargoed_fold_passes(self):
        fold = wfv.Fold(
            index=0,
            train_start=date(2025, 1, 1),
            train_end=date(2025, 3, 31),
            test_start=date(2025, 4, 8),
            test_end=date(2025, 4, 30),
        )
        train_rows = [
            {
                "date": date(2025, 3, 31),
                "asset": "A",
                "signal": 0.0,
                "fwdRet": 0.0,
                "regimeVol": 0.5,
            }
        ]
        wfv.assert_no_leakage(fold, train_rows, config(horizon_days=7))

    def test_run_enforces_the_guard_on_every_fold(self):
        rows = observations(400, relation=lambda forward, rng: rng.gauss(0, 1))
        report = wfv.run(rows, config())  # would raise LeakageError if violated
        assert report["aggregate"]["folds"] >= 3


class TestVerdictSensitivity:
    def test_a_perfect_signal_is_detected(self):
        rows = observations(400, relation=lambda forward, rng: forward)
        report = wfv.run(rows, config())
        assert report["aggregate"]["mean_oos_ic"] == pytest.approx(1.0)
        assert all(fold["fitted_direction"] == 1 for fold in report["folds"])

    def test_an_inverted_signal_has_its_sign_learned_on_training_data(self):
        rows = observations(400, relation=lambda forward, rng: -forward)
        report = wfv.run(rows, config())
        assert all(fold["fitted_direction"] == -1 for fold in report["folds"])
        assert report["aggregate"]["mean_oos_ic"] == pytest.approx(1.0)

    def test_pure_noise_is_not_mistaken_for_an_edge(self):
        rows = observations(400, relation=lambda forward, rng: rng.gauss(0, 1))
        report = wfv.run(rows, config())
        assert abs(report["aggregate"]["mean_oos_ic"]) < 0.15
        assert abs(report["aggregate"]["oos_ic_t_stat"]) < 2.0

    def test_a_perfect_signal_produces_a_positive_long_short_spread(self):
        rows = observations(400, relation=lambda forward, rng: forward)
        report = wfv.run(rows, config())
        assert report["aggregate"]["mean_oos_long_short_spread"] > 0


class TestContract:
    def _row(self, **overrides):
        base = {
            "date": date(2025, 1, 1),
            "asset": "A",
            "signal": 0.1,
            "fwdRet": 0.2,
            "regimeVol": 0.5,
        }
        return {**base, **overrides}

    def test_empty_input_rejected(self):
        with pytest.raises(wfv.ContractError, match="no observations"):
            wfv.validate_contract([])

    def test_missing_column_rejected(self):
        row = self._row()
        del row["regimeVol"]
        with pytest.raises(wfv.ContractError, match="missing columns"):
            wfv.validate_contract([row])

    def test_string_date_rejected(self):
        with pytest.raises(wfv.ContractError, match="must be a datetime.date"):
            wfv.validate_contract([self._row(date="2025-01-01")])

    def test_nan_rejected(self):
        with pytest.raises(wfv.ContractError, match="not a finite number"):
            wfv.validate_contract([self._row(fwdRet=float("nan"))])

    def test_negative_regime_vol_rejected(self):
        with pytest.raises(wfv.ContractError, match="negative regimeVol"):
            wfv.validate_contract([self._row(regimeVol=-0.1)])

    def test_duplicate_asset_date_rejected(self):
        with pytest.raises(wfv.ContractError, match="duplicate observation"):
            wfv.validate_contract([self._row(), self._row()])


class TestReportShape:
    def test_report_carries_per_fold_and_aggregate_detail(self):
        rows = observations(400, relation=lambda forward, rng: rng.gauss(0, 1))
        report = wfv.run(rows, config())
        assert set(report) >= {"config", "input", "folds", "aggregate"}
        for fold in report["folds"]:
            assert set(fold) >= {
                "train_ic",
                "fitted_direction",
                "oos_ic",
                "oos_hit_rate",
                "regime_conditioned",
                "embargo_days",
            }

    def test_direction_flips_are_counted(self):
        reports = [
            {"fitted_direction": 1},
            {"fitted_direction": -1},
            {"fitted_direction": -1},
            {"fitted_direction": 1},
        ]
        assert wfv._direction_flips(reports) == 2

    def test_daily_ic_skips_a_thin_cross_section(self):
        rows = [
            {"date": START, "asset": "A", "signal": 1.0, "fwdRet": 1.0, "regimeVol": 0.5},
            {"date": START, "asset": "B", "signal": 2.0, "fwdRet": 2.0, "regimeVol": 0.5},
        ]
        assert wfv.daily_information_coefficient(rows) == []
