"""REAL-DATA-FIXTURE-001: provenance, contract, determinism, and the
end-to-end proof that the build is blind to the future.
"""

import csv
import json
from datetime import date
from pathlib import Path

import pytest

from igwt.data import snapshot
from igwt.fixtures import real_data_fixture_001 as fixture
from igwt.validation import run_fixture_wfv, wfv

ROOT = fixture.FIXTURE_ROOT
pytestmark = pytest.mark.skipif(
    not (ROOT / "manifest.json").exists(), reason="fixture artefacts not present"
)


@pytest.fixture(scope="module")
def manifest():
    return json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rows():
    return fixture.load_observations()


class TestProvenance:
    def test_every_raw_snapshot_matches_its_recorded_hash(self, manifest):
        for symbol, record in manifest["raw_snapshots"].items():
            data = (ROOT / record["file"]).read_bytes()
            assert snapshot.sha256_hex(data) == record["sha256"], symbol

    def test_observations_match_their_recorded_hash(self, manifest):
        data = (ROOT / "observations.csv").read_bytes()
        assert snapshot.sha256_hex(data) == manifest["observations"]["sha256"]

    def test_the_manifest_declares_the_data_as_non_synthetic(self, manifest):
        assert manifest["data_source"]["synthetic_data"] is False
        assert manifest["data_source"]["provider"] == "CoinGecko"

    def test_the_manifest_explains_the_substituted_source(self, manifest):
        note = manifest["provenance_note"]
        assert "Binance" in note and "CoinGecko" in note

    def test_every_universe_asset_has_a_snapshot(self, manifest):
        assert set(manifest["raw_snapshots"]) == set(fixture.UNIVERSE)


class TestContract:
    def test_header_is_exactly_the_contract(self):
        with (ROOT / "observations.csv").open(encoding="utf-8") as handle:
            assert next(csv.reader(handle)) == list(fixture.CONTRACT_COLUMNS)

    def test_the_fixture_satisfies_the_wfv_contract(self, rows):
        wfv.validate_contract(rows)  # raises on any violation

    def test_rows_are_sorted_by_date_then_asset(self, rows):
        keys = [(row["date"], row["asset"]) for row in rows]
        assert keys == sorted(keys)

    def test_no_row_predates_the_lookback_warmup(self, rows, manifest):
        earliest_raw = min(
            date.fromisoformat(item["first_date"]) for item in manifest["snapshot_validation"]
        )
        first_row = min(row["date"] for row in rows)
        warmup = fixture.MOMENTUM_LOOKBACK_DAYS
        assert (first_row - earliest_raw).days >= warmup

    def test_no_row_extends_past_the_last_resolvable_label(self, rows, manifest):
        latest_raw = max(
            date.fromisoformat(item["last_date"]) for item in manifest["snapshot_validation"]
        )
        last_row = max(row["date"] for row in rows)
        assert (latest_raw - last_row).days >= fixture.FORWARD_HORIZON_DAYS

    def test_regime_vol_is_positive(self, rows):
        assert all(row["regimeVol"] > 0 for row in rows)

    def test_the_cross_section_is_wide_enough_on_every_date(self, rows):
        per_date = {}
        for row in rows:
            per_date[row["date"]] = per_date.get(row["date"], 0) + 1
        assert min(per_date.values()) >= fixture.MIN_CROSS_SECTION


class TestDeterminism:
    def test_rebuilding_from_raw_reproduces_the_committed_observations(self, rows):
        rebuilt, _ = fixture.build()
        assert len(rebuilt) == len(rows)
        for built, loaded in zip(rebuilt, rows):
            assert built["date"] == loaded["date"].isoformat()
            assert built["asset"] == loaded["asset"]
            assert built["signal"] == pytest.approx(loaded["signal"], abs=1e-9)
            assert built["fwdRet"] == pytest.approx(loaded["fwdRet"], abs=1e-9)
            assert built["regimeVol"] == pytest.approx(loaded["regimeVol"], abs=1e-9)


class TestBlindToTheFuture:
    """The decisive end-to-end check.

    Rebuild the whole fixture from raw data that has been *truncated* — as if
    today were three months ago. Every feature that both builds share must be
    bit-for-bit identical. If any step of the pipeline peeked forward, the
    shorter build would disagree.
    """

    @staticmethod
    def _truncate(raw_root: Path, destination: Path, drop_days: int) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        cutoff_ms = drop_days * 86_400_000
        for symbol in fixture.UNIVERSE:
            payload = snapshot.read_snapshot(raw_root, symbol)
            last_ts = max(int(ts) for ts, _ in payload["prices"])
            limit = last_ts - cutoff_ms
            truncated = {
                "prices": [point for point in payload["prices"] if int(point[0]) <= limit],
                "market_caps": [
                    point for point in payload["market_caps"] if int(point[0]) <= limit
                ],
                "total_volumes": [
                    point for point in payload["total_volumes"] if int(point[0]) <= limit
                ],
            }
            snapshot.write_snapshot(destination, symbol, truncated)

    def test_truncated_rebuild_agrees_on_every_shared_observation(self, tmp_path, rows):
        self._truncate(ROOT / "raw", tmp_path / "raw", drop_days=90)
        past_rows, _ = fixture.build(raw_root=tmp_path / "raw")

        assert past_rows, "truncated rebuild produced nothing"
        full = {(row["date"].isoformat(), row["asset"]): row for row in rows}

        compared = 0
        for row in past_rows:
            key = (row["date"], row["asset"])
            if key not in full:
                continue
            reference = full[key]
            assert row["signal"] == pytest.approx(reference["signal"], abs=1e-9), key
            assert row["regimeVol"] == pytest.approx(reference["regimeVol"], abs=1e-9), key
            assert row["fwdRet"] == pytest.approx(reference["fwdRet"], abs=1e-9), key
            compared += 1

        assert compared > 100, f"only {compared} shared observations compared"


class TestGate:
    def test_the_gate_reproduces_from_the_committed_artefacts(self):
        integrity = run_fixture_wfv.verify_raw_integrity()
        observations = fixture.load_observations()
        config = run_fixture_wfv.build_config(
            integrity["manifest"], train_days=180, test_days=30
        )
        report = wfv.run(observations, config)
        gate = run_fixture_wfv.evaluate_gate(integrity, report)

        assert gate["status"] == "PASS"
        assert [check["id"] for check in gate["checks"]] == ["G1", "G2", "G3", "G4", "G5"]
        assert report["aggregate"]["folds"] >= run_fixture_wfv.MIN_FOLDS

    def test_the_gate_does_not_claim_a_signal_verdict(self):
        integrity = run_fixture_wfv.verify_raw_integrity()
        observations = fixture.load_observations()
        config = run_fixture_wfv.build_config(integrity["manifest"], train_days=180, test_days=30)
        gate = run_fixture_wfv.evaluate_gate(integrity, wfv.run(observations, config))
        assert "not a signal verdict" in gate["scope"]
        assert any("predictive" in item for item in gate["explicitly_not_claimed"])
