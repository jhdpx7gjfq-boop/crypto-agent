"""Run WFV v2 against a fixture and emit its gate report.

    python -m igwt.validation.run_fixture_wfv                      # locked control fixture
    python -m igwt.validation.run_fixture_wfv --root <fixture dir> # any other fixture

Writes ``wfv_report.json`` next to the fixture. Both manifest shapes are
accepted — a snapshot-store fixture and an audited OHLCV fixture — so the same
runner, and therefore the same frozen contract, serves every dataset. The gate it evaluates is an
**infrastructure** gate: it asks whether real data flowed through a validator
that cannot see the future. It deliberately does not certify the signal — that
verdict belongs to the research layer and to a human.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from igwt import __version__
from igwt.data import snapshot
from igwt.features import contract
from igwt.fixtures import real_data_fixture_001 as fixture
from igwt.validation import wfv

logger = logging.getLogger(__name__)

GATE_ID = "REAL-DATA-FIXTURE-001"
MIN_FOLDS = 3


def verify_raw_integrity(root: Path = fixture.FIXTURE_ROOT) -> dict:
    """Re-hash every recorded artefact and compare it to the manifest.

    Handles both manifest shapes: a snapshot-store fixture records
    ``raw_snapshots``, an audited OHLCV fixture records ``integrity_audit``.
    Either way the question is the same — do the committed bytes still hash to
    what the manifest claims?
    """
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    results = {}

    for symbol, record in manifest.get("raw_snapshots", {}).items():
        results[symbol] = _rehash(root / record["file"], record["sha256"])

    for symbol, record in manifest.get("integrity_audit", {}).items():
        results[symbol] = _rehash(
            root / "normalized" / f"{symbol}.csv", record["sha256_normalized"]
        )

    return {"manifest": manifest, "snapshots": results}


def _rehash(path: Path, expected: str) -> dict:
    if not path.exists():
        return {"present": False, "matches": False}
    digest = snapshot.sha256_hex(path.read_bytes())
    return {"present": True, "matches": digest == expected, "sha256": digest}


def build_config(manifest: dict, *, train_days: int, test_days: int) -> wfv.WFVConfig:
    parameters = manifest["parameters"]
    return wfv.WFVConfig(
        horizon_days=parameters["forward_horizon_days"],
        train_days=train_days,
        test_days=test_days,
        mode="rolling",
        extras={"fixture_id": manifest["fixture_id"], "fixture_sha256": manifest["observations"]["sha256"]},
    )


def evaluate_gate(integrity: dict, report: dict, *, gate_id: str = GATE_ID) -> dict:
    snapshots = integrity["snapshots"]
    manifest = integrity["manifest"]
    folds = report["folds"]
    declared_assets = len(manifest.get("raw_snapshots") or manifest.get("integrity_audit") or {})

    checks = [
        {
            "id": "G1",
            "name": "Real dataset identified",
            "passed": declared_assets > 0,
            "detail": f"{declared_assets} assets declared in the fixture manifest",
        },
        {
            "id": "G2",
            "name": "Real dataset accessible and unaltered",
            "passed": bool(snapshots) and all(item["matches"] for item in snapshots.values()),
            "detail": "every recorded artefact re-hashes to its manifest sha256",
        },
        {
            "id": "G3",
            "name": "Fixture built to the WFV contract",
            "passed": report["input"]["rows"] > 0
            and manifest["observations"]["columns"] == list(fixture.CONTRACT_COLUMNS),
            "detail": (
                f"{report['input']['rows']} observations, "
                f"{len(report['input']['assets'])} assets, "
                f"{report['input']['first_date']} -> {report['input']['last_date']}"
            ),
        },
        {
            "id": "G4",
            "name": "No lookahead: embargo covers the label horizon",
            "passed": all(
                item["embargo_days"] >= report["config"]["horizon_days"] for item in folds
            ),
            "detail": (
                f"embargo {report['config']['embargo_days']}d >= horizon "
                f"{report['config']['horizon_days']}d on every fold; "
                "per-row leakage re-checked by wfv.assert_no_leakage"
            ),
        },
        {
            "id": "G5",
            "name": "Walk-forward executed on real data",
            "passed": len(folds) >= MIN_FOLDS
            and all(item["sufficient_test_dates"] for item in folds),
            "detail": f"{len(folds)} folds, {report['aggregate']['oos_dates_scored']} scored OOS dates",
        },
    ]

    return {
        "gate_id": gate_id,
        "scope": "infrastructure validation (research pipeline), not a signal verdict",
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "igwt_version": __version__,
        "checks": checks,
        "status": "PASS" if all(item["passed"] for item in checks) else "BLOCKED",
        "explicitly_not_claimed": [
            "the signal in this fixture is predictive",
            "any BCE / X20 / RPM module is validated or modified",
            "this dataset replaces the Binance daily datasets named in the registry",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run WFV v2 on REAL-DATA-FIXTURE-001")
    parser.add_argument(
        "--root",
        type=Path,
        default=fixture.FIXTURE_ROOT,
        help="fixture directory to validate (defaults to the locked control fixture)",
    )
    parser.add_argument("--train-days", type=int, default=180)
    parser.add_argument("--test-days", type=int, default=30)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    root = args.root
    out = args.out or root / "wfv_report.json"

    integrity = verify_raw_integrity(root)
    observations = contract.read_observations(root / "observations.csv")
    config = build_config(integrity["manifest"], train_days=args.train_days, test_days=args.test_days)

    report = wfv.run(observations, config)
    gate = evaluate_gate(integrity, report, gate_id=integrity["manifest"]["fixture_id"])
    report["raw_integrity"] = {
        symbol: item["matches"] for symbol, item in integrity["snapshots"].items()
    }
    report["gate"] = gate

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")

    aggregate = report["aggregate"]
    logger.info("gate %s: %s", gate["gate_id"], gate["status"])
    for check in gate["checks"]:
        logger.info("  %s %-45s %s", check["id"], check["name"], "PASS" if check["passed"] else "FAIL")
    logger.info(
        "folds=%d  oos_dates=%d  mean_oos_ic=%.4f  t=%.2f  spread=%.5f",
        aggregate["folds"],
        aggregate["oos_dates_scored"],
        aggregate["mean_oos_ic"] or 0.0,
        aggregate["oos_ic_t_stat"] or 0.0,
        aggregate["mean_oos_long_short_spread"] or 0.0,
    )
    logger.info("report written to %s", out)
    return 0 if gate["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
