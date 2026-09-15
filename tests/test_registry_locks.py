"""Enforcement of the registry's governance locks.

A freeze that nothing verifies is a comment. These tests fail the build if a
locked artefact drifts, so the lock has teeth in CI rather than in prose.
"""

import json
from pathlib import Path

import pytest

from igwt.data import snapshot
from igwt.features import contract
from igwt.fixtures import real_data_fixture_001 as fixture
from igwt.validation import wfv

REGISTRY = Path("docs/registry")


def load(name):
    return json.loads((REGISTRY / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fixture_lock():
    return load("REAL-DATA-FIXTURE-001.lock.json")


@pytest.fixture(scope="module")
def contract_lock():
    return load("WFV-V2-CONTRACT.lock.json")


class TestFixtureLock:
    def test_the_lock_declares_the_fixture_locked(self, fixture_lock):
        assert fixture_lock["status"] == "LOCKED"

    def test_every_locked_file_still_hashes_to_its_recorded_digest(self, fixture_lock):
        for relative, expected in fixture_lock["hashes"].items():
            data = (fixture.FIXTURE_ROOT / relative).read_bytes()
            assert snapshot.sha256_hex(data) == expected, f"{relative} has drifted from its lock"

    def test_rebuilding_from_raw_reproduces_the_locked_observations(self, fixture_lock, tmp_path):
        rows, _ = fixture.build()
        rebuilt = tmp_path / "observations.csv"
        contract.write_observations(rows, rebuilt)
        assert (
            snapshot.sha256_hex(rebuilt.read_bytes())
            == fixture_lock["hashes"]["observations.csv"]
        ), "a rebuild no longer reproduces the locked bytes"

    def test_the_locked_scope_still_describes_the_fixture(self, fixture_lock):
        rows = fixture.load_observations()
        scope = fixture_lock["scope"]
        assert len(rows) == scope["rows"]
        assert sorted({row["asset"] for row in rows}) == scope["assets"]
        assert min(row["date"] for row in rows).isoformat() == scope["first_date"]
        assert max(row["date"] for row in rows).isoformat() == scope["last_date"]

    def test_the_locked_parameters_still_match_the_builder(self, fixture_lock):
        for key, value in fixture_lock["parameters"].items():
            assert getattr(fixture.PARAMS, key) == value


class TestContractFreeze:
    def test_the_columns_are_frozen(self, contract_lock):
        assert list(contract.CONTRACT_COLUMNS) == contract_lock["columns"]

    def test_the_serialisation_precision_is_frozen(self, contract_lock):
        assert contract.DECIMALS == contract_lock["serialisation_decimals"]

    def test_the_default_feature_params_are_frozen(self, contract_lock):
        defaults = contract.FeatureParams()
        for key, value in contract_lock["default_feature_params"].items():
            assert getattr(defaults, key) == value

    def test_the_validator_reads_the_same_columns(self, contract_lock):
        assert list(wfv.CONTRACT_COLUMNS) == contract_lock["columns"]

    def test_the_embargo_invariants_still_hold(self):
        assert wfv.WFVConfig(horizon_days=7).resolved_embargo() == 7
        with pytest.raises(ValueError, match="shorter than horizon"):
            wfv.WFVConfig(horizon_days=7, embargo_days=6).resolved_embargo()

    def test_one_implementation_serves_every_fixture(self, contract_lock):
        """The claim in the lock is that there is a single builder. Check it."""
        assert "build_observations" in contract_lock["single_implementation"]
        assert callable(contract.build_observations)
        source = Path("igwt/fixtures/real_data_fixture_001.py").read_text(encoding="utf-8")
        assert "contract.build_observations" in source


class TestResultRecord:
    def test_the_momentum_result_is_recorded_as_no_evidence(self):
        record = load("MOMENTUM-30D-WFV-001.json")
        assert record["status"] == "INCONCLUSIVE / NO EVIDENCE OF EDGE"
        assert record["production"] == "FORBIDDEN"

    def test_the_record_refuses_the_overreaching_conclusion(self):
        record = load("MOMENTUM-30D-WFV-001.json")
        assert any("definitively invalidated" in item for item in record["explicitly_not_claimed"])

    def test_the_recorded_numbers_match_the_committed_report(self):
        record = load("MOMENTUM-30D-WFV-001.json")
        report = json.loads(
            (fixture.FIXTURE_ROOT / "wfv_report.json").read_text(encoding="utf-8")
        )
        aggregate = report["aggregate"]
        assert record["result"]["mean_oos_ic"] == pytest.approx(aggregate["mean_oos_ic"])
        assert record["result"]["oos_folds"] == aggregate["folds"]
        assert record["result"]["fold_ics"] == pytest.approx(
            [fold["oos_ic"] for fold in report["folds"]]
        )
