"""REAL-DATA-FULL-001: the acquisition and audit pipeline, end to end.

The dataset itself does not exist yet — Binance is unreachable from this
environment. What *is* testable now is the pipeline: vendor files in, audited
manifest and WFV-contract observations out. The CSVs below are fabricated on
purpose and never leave ``tmp_path``; no synthetic bar is ever committed as a
fixture.
"""

import json
import math
import random
from datetime import date, timedelta

import pytest

from igwt.data import integrity, ohlcv
from igwt.features import contract
from igwt.fixtures import real_data_full_001 as full
from igwt.validation import run_fixture_wfv, wfv

START = date(2025, 1, 1)


def vendor_csv(symbol: str, base_asset: str, days: int, *, seed: int, descending=True) -> str:
    """A vendor-shaped export: preamble line, Unix + Date, base and quote volume."""
    rng = random.Random(seed)
    rows, price = [], 100.0
    for offset in range(days):
        day = START + timedelta(days=offset)
        price *= math.exp(rng.gauss(0, 0.03))
        high = price * (1 + abs(rng.gauss(0, 0.01)))
        low = price * (1 - abs(rng.gauss(0, 0.01)))
        opening = low + (high - low) * rng.random()
        unix = (day - date(1970, 1, 1)).days * 86_400_000
        rows.append(
            f"{unix},{day.isoformat()},{symbol},{opening:.4f},{high:.4f},"
            f"{low:.4f},{price:.4f},{rng.uniform(1, 100):.4f},{rng.uniform(100, 9999):.4f}"
        )
    if descending:
        rows.reverse()
    header = f"Unix,Date,Symbol,Open,High,Low,Close,Volume {base_asset},Volume USDT"
    return "https://example-vendor.test/ data provided as is\n" + header + "\n" + "\n".join(rows) + "\n"


@pytest.fixture
def export_dir(tmp_path):
    directory = tmp_path / "binance"
    directory.mkdir()
    for index, (symbol, base_asset) in enumerate(full.UNIVERSE.items()):
        (directory / f"Binance_{symbol}_d.csv").write_text(
            vendor_csv(symbol, base_asset, 320, seed=index), encoding="utf-8"
        )
    return directory


class TestAcquisition:
    def test_every_universe_symbol_is_ingested(self, export_dir):
        series, raw, context = full.acquire_from_files(export_dir)
        assert set(series) == set(full.UNIVERSE)
        assert set(raw) == set(full.UNIVERSE)
        assert context.market_type == "spot"
        assert context.timeframe == "1d"

    def test_a_missing_symbol_blocks_acquisition_by_name(self, export_dir):
        (export_dir / "Binance_SOLUSDT_d.csv").unlink()
        with pytest.raises(full.AcquisitionBlocked, match="SOLUSDT"):
            full.acquire_from_files(export_dir)

    def test_descending_vendor_rows_are_normalised_to_ascending(self, export_dir):
        series, _, _ = full.acquire_from_files(export_dir)
        btc = series["BTCUSDT"]
        assert btc.dates == sorted(btc.dates)
        assert btc.report["out_of_order_input"] is True

    def test_base_volume_is_the_column_that_gets_read(self, export_dir):
        series, _, _ = full.acquire_from_files(export_dir)
        assert series["BTCUSDT"].source_columns["volume"] == "Volume BTC"


class TestIntegrityAudit:
    def test_the_manifest_record_carries_every_required_field(self, export_dir, tmp_path):
        series, raw, context = full.acquire_from_files(export_dir)
        _, manifest = full.build(series, raw, context, root=tmp_path / "out")

        required = {
            "source", "endpoint", "symbol", "market_type", "timeframe",
            "start_date", "end_date", "retrieval_timestamp", "row_count",
            "missing_dates", "duplicate_rows", "sha256_raw", "sha256_normalized",
            "timezone", "price_field", "volume_field",
        }
        for symbol, record in manifest["integrity_audit"].items():
            assert required <= set(record), f"{symbol} is missing {required - set(record)}"

    def test_a_clean_export_audits_as_pass(self, export_dir, tmp_path):
        series, raw, context = full.acquire_from_files(export_dir)
        _, manifest = full.build(series, raw, context, root=tmp_path / "out")
        assert manifest["integrity_summary"]["verdict"] == "PASS"
        assert manifest["integrity_summary"]["symbols_with_findings"] == []

    def test_descending_row_order_is_recorded_but_is_not_a_defect(self, export_dir, tmp_path):
        """Vendor exports are conventionally descending; that is formatting, not a defect."""
        series, raw, context = full.acquire_from_files(export_dir)
        _, manifest = full.build(series, raw, context, root=tmp_path / "out")
        record = manifest["integrity_audit"]["BTCUSDT"]
        assert record["out_of_order_input"] is True
        assert record["findings"] == []

    def test_a_gap_downgrades_the_verdict_to_warn_and_is_enumerated(self, tmp_path):
        rows = [
            {"date": "2026-01-01", "open": "1", "high": "2", "low": "1", "close": "1.5"},
            {"date": "2026-01-05", "open": "1", "high": "2", "low": "1", "close": "1.5"},
        ]
        series = ohlcv.normalise("BTCUSDT", rows)
        record = integrity.audit(
            series,
            context=integrity.AcquisitionContext("Binance", "x", "spot", "1d"),
            raw_bytes=b"raw",
            normalised_bytes=b"normalised",
        )
        assert record["verdict"] == "WARN"
        assert record["missing_dates_count"] == 3
        assert record["missing_dates"] == ["2026-01-02", "2026-01-03", "2026-01-04"]

    def test_an_empty_series_fails_the_audit(self):
        record = integrity.audit(
            ohlcv.normalise("BTCUSDT", []),
            context=integrity.AcquisitionContext("Binance", "x", "spot", "1d"),
            raw_bytes=b"",
            normalised_bytes=b"",
        )
        assert record["verdict"] == "FAIL"

    def test_a_failing_audit_blocks_the_build(self, export_dir, tmp_path):
        series, raw, context = full.acquire_from_files(export_dir)
        series["BTCUSDT"] = ohlcv.normalise("BTCUSDT", [])
        raw["BTCUSDT"] = b""
        with pytest.raises(full.AcquisitionBlocked, match="integrity audit failed"):
            full.build(series, raw, context, root=tmp_path / "out")

    def test_missing_volume_is_reported_rather_than_invented(self):
        rows = [{"date": "2026-01-01", "open": "1", "high": "2", "low": "1", "close": "1.5"}]
        record = integrity.audit(
            ohlcv.normalise("BTCUSDT", rows),
            context=integrity.AcquisitionContext("Binance", "x", "spot", "1d"),
            raw_bytes=b"raw",
            normalised_bytes=b"normalised",
        )
        assert record["volume_field"] is None
        assert any("volume is unavailable" in finding for finding in record["findings"])


class TestContractIsUnchangedByTheSourceSwap:
    """The point of the shared builder: a new source, the same contract."""

    def test_the_observations_satisfy_the_frozen_wfv_contract(self, export_dir, tmp_path):
        series, raw, context = full.acquire_from_files(export_dir)
        root = tmp_path / "out"
        rows, manifest = full.build(series, raw, context, root=root)
        full.write_outputs(rows, manifest, root=root)

        observations = full.load_observations(root)
        wfv.validate_contract(observations)  # raises on any violation
        assert manifest["observations"]["columns"] == list(contract.CONTRACT_COLUMNS)

    def test_the_parameters_match_the_locked_control_fixture(self):
        from igwt.fixtures import real_data_fixture_001 as control

        assert full.PARAMS == control.PARAMS

    def test_walk_forward_runs_on_the_new_fixture_through_the_same_runner(
        self, export_dir, tmp_path
    ):
        series, raw, context = full.acquire_from_files(export_dir)
        root = tmp_path / "out"
        rows, manifest = full.build(series, raw, context, root=root)
        full.write_outputs(rows, manifest, root=root)

        verified = run_fixture_wfv.verify_raw_integrity(root)
        assert all(item["matches"] for item in verified["snapshots"].values())

        config = run_fixture_wfv.build_config(manifest, train_days=180, test_days=30)
        report = wfv.run(full.load_observations(root), config)
        gate = run_fixture_wfv.evaluate_gate(verified, report, gate_id=full.FIXTURE_ID)

        assert gate["gate_id"] == full.FIXTURE_ID
        assert gate["status"] == "PASS"
        assert report["config"]["embargo_days"] >= report["config"]["horizon_days"]

    def test_the_build_declares_itself_ohlc_and_bce_capable(self, export_dir, tmp_path):
        series, raw, context = full.acquire_from_files(export_dir)
        _, manifest = full.build(series, raw, context, root=tmp_path / "out")
        assert manifest["ohlc_available"] is True
        assert manifest["bce_compatible"] is True


class TestControlFixtureIsUntouched:
    def test_the_full_fixture_writes_to_its_own_directory(self):
        assert full.FIXTURE_ROOT != __import__(
            "igwt.fixtures.real_data_fixture_001", fromlist=["FIXTURE_ROOT"]
        ).FIXTURE_ROOT

    def test_the_manifest_names_the_control_and_its_own_role(self, export_dir, tmp_path):
        series, raw, context = full.acquire_from_files(export_dir)
        _, manifest = full.build(series, raw, context, root=tmp_path / "out")
        assert manifest["control_fixture"] == "REAL-DATA-FIXTURE-001"
        assert "is not modified" in manifest["relationship_to_control"]


class TestPreflightReporting:
    def test_preflight_reports_a_block_without_raising(self, monkeypatch):
        monkeypatch.setattr(
            full.binance,
            "preflight",
            lambda **_: {
                "reachable": None,
                "probes": [{"endpoint": "x", "status": 451, "detail": "HTTP 451"}],
            },
        )
        report = full.preflight()
        assert report["api_reachable"] is False
        assert report["verdict"].startswith("BLOCKED")
        assert report["file_ingress_available"] is True
        json.dumps(report)  # the CLI prints it; it must stay serialisable
