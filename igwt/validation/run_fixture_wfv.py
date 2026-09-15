"""Run WFV v2 against REAL-DATA-FIXTURE-001 and emit the gate report.

    python -m igwt.validation.run_fixture_wfv

Writes ``wfv_report.json`` next to the fixture. The gate it evaluates is an
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
from igwt.fixtures import real_data_fixture_001 as fixture
from igwt.validation import wfv

logger = logging.getLogger(__name__)

GATE_ID = "REAL-DATA-FIXTURE-001"
MIN_FOLDS = 3


def verify_raw_integrity(root: Path = fixture.FIXTURE_ROOT) -> dict:
    """Re-hash every raw snapshot and compare it to the manifest."""
    manifest = json.loads((Path(root) / "manifest.json").read_text(encoding="utf-8"))
    results = {}
    for symbol, record in manifest["raw_snapshots"].items():
        path = Path(root) / record["file"]
        if not path.exists():
            results[symbol] = {"present": False, "matches": False}
            continue
        digest = snapshot.sha256_hex(path.read_bytes())
        results[symbol] = {
            "present": True,
            "matches": digest == record["sha256"],
            "sha256": digest,
        }
    return {"manifest": manifest, "snapshots": results}


def build_config(manifest: dict, *, train_days: int, test_days: int) -> wfv.WFVConfig:
    parameters = manifest["parameters"]
    return wfv.WFVConfig(
        horizon_days=parameters["forward_horizon_days"],
        train_days=train_days,
        test_days=test_days,
        mode="rolling",
        extras={"fixture_id": manifest["fixture_id"], "fixture_sha256": manifest["observations"]["sha256"]},
    )


def evaluate_gate(integrity: dict, report: dict) -> dict:
    snapshots = integrity["snapshots"]
    manifest = integrity["manifest"]
    folds = report["folds"]

    checks = [
        {
            "id": "G1",
            "name": "Real dataset identified",
            "passed": bool(manifest["raw_snapshots"]),
            "detail": f"{len(manifest['raw_snapshots'])} assets declared in the fixture manifest",
        },
        {
            "id": "G2",
            "name": "Real dataset accessible and unaltered",
            "passed": bool(snapshots) and all(item["matches"] for item in snapshots.values()),
            "detail": "every raw snapshot re-hashes to its manifest sha256",
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
        "gate_id": GATE_ID,
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
    parser.add_argument("--train-days", type=int, default=180)
    parser.add_argument("--test-days", type=int, default=30)
    parser.add_argument("--out", type=Path, default=fixture.FIXTURE_ROOT / "wfv_report.json")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    integrity = verify_raw_integrity()
    observations = fixture.load_observations()
    config = build_config(integrity["manifest"], train_days=args.train_days, test_days=args.test_days)

    report = wfv.run(observations, config)
    gate = evaluate_gate(integrity, report)
    report["raw_integrity"] = {
        symbol: item["matches"] for symbol, item in integrity["snapshots"].items()
    }
    report["gate"] = gate

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")

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
    logger.info("report written to %s", args.out)
    return 0 if gate["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
