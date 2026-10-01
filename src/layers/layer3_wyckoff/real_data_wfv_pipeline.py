"""
Phase 3 Real-Data WFV Pipeline
Orchestrates walk-forward validation on real Binance OHLCV data.

Governance constraints:
- Real data ONLY (no synthetic, no fallback)
- PIT validation (no lookahead bias)
- Immutable gates: OOS trades >= 200, PF >= 1.30, Max DD < 25%, Degradation < 30%, Consistency >= 50%
- Walk-forward: 60-day train, 30-day test, 30-day step
- No recalibration or threshold changes mid-pipeline
- Metrics computed on OOS trades only
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from .data_provenance_audit import DataProvenanceAudit
from .bce import BottomConfirmationEngine
from .validators.pit_checks import PITValidator


@dataclass
class WFVWindow:
    """Single walk-forward window."""

    window_id: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    train_candles: int
    test_candles: int


@dataclass
class WindowMetrics:
    """Metrics for single WFV window."""

    window_id: int
    oos_trade_count: int
    profit_factor: float
    max_drawdown: float
    degradation: float
    consistency: float
    gates_pass: bool


class RealDataWFVPipeline:
    """Walk-forward validation on real Binance data with strict governance."""

    # Immutable gates (frozen)
    MIN_OOS_TRADES = 200
    MIN_PROFIT_FACTOR = 1.30
    MAX_DRAWDOWN = 0.25
    MAX_DEGRADATION = 0.30
    MIN_CONSISTENCY = 0.50

    def __init__(self, data_base_path: str = "data/real_binance"):
        self.data_base_path = Path(data_base_path)
        self.pit_validator = PITValidator()
        self.real_data: Dict[str, List[Dict]] = {}
        self.audit_results: Dict[str, Dict] = {}

    def load_and_audit_real_data(self) -> Dict[str, Any]:
        """Load real Binance data with full provenance audit."""
        results = {"status": "loading", "audits": {}, "errors": []}

        for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
            symbol_short = symbol.replace("USDT", "")
            data_path = self.data_base_path / symbol / f"{symbol}_1d.json"

            # Run provenance audit
            auditor = DataProvenanceAudit(symbol_short, str(data_path))
            audit = auditor.run_full_audit()
            results["audits"][symbol] = audit

            # Check audit pass/fail
            if not data_path.exists():
                results["errors"].append(
                    f"{symbol}: File not found at {data_path}. Awaiting user to download from Binance Data Portal."
                )
                continue

            if "error" in audit.get("metadata", {}):
                results["errors"].append(f"{symbol}: Metadata error: {audit['metadata']['error']}")
                continue

            if "error" in audit.get("content", {}):
                results["errors"].append(f"{symbol}: Content error: {audit['content']['error']}")
                continue

            if "error" in audit.get("coverage", {}):
                results["errors"].append(f"{symbol}: Coverage error: {audit['coverage']['error']}")
                continue

            # Load data
            try:
                with open(data_path, "r") as f:
                    self.real_data[symbol] = json.load(f)
            except Exception as e:
                results["errors"].append(f"{symbol}: Load error: {e}")
                continue

        if self.real_data:
            results["status"] = "loaded"
            results["loaded_symbols"] = list(self.real_data.keys())
        else:
            results["status"] = "blocked"

        return results

    def compute_wfv_windows(
        self, total_candles: int, train_days: int = 60, test_days: int = 30, step_days: int = 30
    ) -> List[WFVWindow]:
        """Compute walk-forward windows (daily candles = days)."""
        windows = []
        window_id = 0

        position = 0
        while position + train_days + test_days <= total_candles:
            window = WFVWindow(
                window_id=window_id,
                train_start=position,
                train_end=position + train_days,
                test_start=position + train_days,
                test_end=position + train_days + test_days,
                train_candles=train_days,
                test_candles=test_days,
            )
            windows.append(window)
            position += step_days
            window_id += 1

        return windows

    def validate_pit_for_window(self, ohlcv: List[Dict], window: WFVWindow, asset: str) -> Dict[str, bool]:
        """Run PIT checks on window (no lookahead bias)."""
        train_data = ohlcv[window.train_start : window.train_end]
        test_data = ohlcv[window.test_start : window.test_end]

        pit_checks = {
            "no_forward_fill": self.pit_validator.check_no_forward_fill(train_data),
            "ma_lookback_valid": self.pit_validator.check_ma_lookback(train_data),
            "smart_money_lag": self.pit_validator.check_smart_money_lag(train_data),
            "train_test_split": self.pit_validator.check_train_test_split(train_data, test_data),
            "rsi_volume_correctness": self.pit_validator.check_rsi_volume_correctness(train_data),
        }

        return pit_checks

    def compute_window_metrics(self, window: WFVWindow) -> WindowMetrics:
        """Compute metrics for single window (placeholder for actual BCE backtest)."""
        # Placeholder: In real implementation, this runs BCE backtest on test window
        # and computes OOS trade metrics.
        return WindowMetrics(
            window_id=window.window_id,
            oos_trade_count=0,
            profit_factor=0.0,
            max_drawdown=0.0,
            degradation=0.0,
            consistency=0.0,
            gates_pass=False,
        )

    def check_immutable_gates(self, metric: WindowMetrics) -> Dict[str, Any]:
        """Apply immutable gates to metrics."""
        gates = {
            "oos_trades_gate": {
                "requirement": f">= {self.MIN_OOS_TRADES}",
                "actual": metric.oos_trade_count,
                "pass": metric.oos_trade_count >= self.MIN_OOS_TRADES,
            },
            "profit_factor_gate": {
                "requirement": f">= {self.MIN_PROFIT_FACTOR}",
                "actual": metric.profit_factor,
                "pass": metric.profit_factor >= self.MIN_PROFIT_FACTOR,
            },
            "max_drawdown_gate": {
                "requirement": f"< {self.MAX_DRAWDOWN}",
                "actual": metric.max_drawdown,
                "pass": metric.max_drawdown < self.MAX_DRAWDOWN,
            },
            "degradation_gate": {
                "requirement": f"< {self.MAX_DEGRADATION}",
                "actual": metric.degradation,
                "pass": metric.degradation < self.MAX_DEGRADATION,
            },
            "consistency_gate": {
                "requirement": f">= {self.MIN_CONSISTENCY}",
                "actual": metric.consistency,
                "pass": metric.consistency >= self.MIN_CONSISTENCY,
            },
        }

        all_pass = all(g["pass"] for g in gates.values())
        return {"gates": gates, "all_pass": all_pass}

    def run_phase3_real_data_wfv(self) -> Dict[str, Any]:
        """Execute full Phase 3 real-data WFV pipeline."""
        report = {
            "phase": 3,
            "pipeline_name": "Real Data WFV",
            "execution_timestamp": datetime.utcnow().isoformat(),
            "stage": "initialization",
            "results": None,
            "errors": [],
        }

        # Stage 1: Load & Audit
        report["stage"] = "data_load_and_audit"
        load_result = self.load_and_audit_real_data()
        report["data_load"] = load_result

        if load_result["status"] != "loaded":
            report["errors"].extend(load_result.get("errors", []))
            report["result"] = "BLOCKED"
            return report

        # Stage 2: Generate WFV windows
        report["stage"] = "wfv_window_generation"
        all_windows = {}
        for symbol, ohlcv in self.real_data.items():
            windows = self.compute_wfv_windows(len(ohlcv))
            all_windows[symbol] = windows
            report[f"wfv_windows_{symbol}"] = {
                "total_candles": len(ohlcv),
                "window_count": len(windows),
                "window_summary": [
                    {
                        "window_id": w.window_id,
                        "train": f"{w.train_start}-{w.train_end}",
                        "test": f"{w.test_start}-{w.test_end}",
                    }
                    for w in windows[:5]
                ],  # First 5 windows
            }

        # Stage 3: PIT Validation
        report["stage"] = "pit_validation"
        pit_results = {}
        for symbol, windows in all_windows.items():
            pit_results[symbol] = {}
            for window in windows[:3]:  # Validate first 3 windows as sample
                pit_checks = self.validate_pit_for_window(self.real_data[symbol], window, symbol)
                pit_results[symbol][f"window_{window.window_id}"] = pit_checks

        report["pit_validation"] = pit_results

        # Stage 4: WFV Execution (placeholder)
        report["stage"] = "wfv_execution"
        report["status"] = "ready_for_real_data_processing"
        report["next_step"] = (
            "Upon data provision, execute WFV on each symbol and apply immutable gates"
        )

        return report


if __name__ == "__main__":
    pipeline = RealDataWFVPipeline()
    result = pipeline.run_phase3_real_data_wfv()
    print(json.dumps(result, indent=2))
