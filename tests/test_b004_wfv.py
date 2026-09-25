"""
Integration tests for B-004 Walk-Forward Validation Orchestrator
"""

import pytest
import numpy as np
import json
from pathlib import Path
import tempfile

from b004_wfv import B004WFVOrchestrator


@pytest.fixture
def temp_ohlcv_dir():
    """Create temporary directory with synthetic OHLCV data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Generate 250 synthetic daily candles for each symbol
        np.random.seed(42)
        for symbol in ["BTC", "ETH", "SOL", "AVAX"]:
            closes = 100 + np.cumsum(np.random.normal(0, 1, 250))
            volumes = 1000000 + np.random.normal(0, 100000, 250)

            candles = []
            for i in range(250):
                candles.append({
                    "timestamp": i * 86400,
                    "open": closes[i] - 0.5,
                    "high": closes[i] + 1,
                    "low": closes[i] - 1,
                    "close": closes[i],
                    "volume": max(100000, volumes[i]),
                })

            filepath = Path(tmpdir) / f"{symbol}_daily_730d.json"
            with open(filepath, "w") as f:
                json.dump({"candles": candles}, f)

        yield tmpdir


def test_orchestrator_initialization(temp_ohlcv_dir):
    """Test orchestrator initializes correctly."""
    orchestrator = B004WFVOrchestrator(
        ohlcv_dir=temp_ohlcv_dir,
        output_dir=temp_ohlcv_dir,
    )

    assert len(orchestrator.datasets) == 4
    for symbol in ["BTC", "ETH", "SOL", "AVAX"]:
        assert symbol in orchestrator.datasets
        assert len(orchestrator.datasets[symbol]) == 250


def test_construct_windows(temp_ohlcv_dir):
    """Test window construction for 19-window protocol."""
    orchestrator = B004WFVOrchestrator(
        ohlcv_dir=temp_ohlcv_dir,
        output_dir=temp_ohlcv_dir,
    )

    ohlcv = orchestrator.datasets["BTC"]
    windows = orchestrator.construct_windows(ohlcv, total_candles=len(ohlcv))

    # With 250 candles: train=180, test=30, stride=30
    # W1: [0-180] train, [180-210] test
    # W2: [30-210] train, [210-240] test
    # No W3 (240+30 > 250)
    expected_windows = 2
    assert len(windows) == expected_windows


def test_run_single_window(temp_ohlcv_dir):
    """Test single window execution."""
    orchestrator = B004WFVOrchestrator(
        ohlcv_dir=temp_ohlcv_dir,
        output_dir=temp_ohlcv_dir,
    )

    ohlcv = orchestrator.datasets["BTC"]
    result = orchestrator.run_single_window(ohlcv, "BTC", window_idx=1, train_end=180, test_end=210)

    assert result["window"] == 1
    assert result["symbol"] == "BTC"
    assert result["status"] in ["SUCCESS", "INSUFFICIENT_DATA"]
    if result["status"] == "SUCCESS":
        assert -1.0 <= result["ic"] <= 1.0
        assert 0.0 <= result["hit_rate"] <= 1.0


def test_run_full_validation_produces_output(temp_ohlcv_dir):
    """Test full validation runs and produces output."""
    output_dir = Path(temp_ohlcv_dir) / "b004_results"
    output_dir.mkdir(exist_ok=True)

    orchestrator = B004WFVOrchestrator(
        ohlcv_dir=temp_ohlcv_dir,
        output_dir=str(output_dir),
    )

    results = orchestrator.run_full_validation()

    assert "validation_run" in results
    assert results["validation_run"] == "B-004_PHASE6"
    assert "windows" in results
    assert "aggregate" in results or len(results["windows"]) == 0


def test_gate_decision_structure(temp_ohlcv_dir):
    """Test gate decision has correct structure when data is sufficient."""
    output_dir = Path(temp_ohlcv_dir) / "b004_results"
    output_dir.mkdir(exist_ok=True)

    orchestrator = B004WFVOrchestrator(
        ohlcv_dir=temp_ohlcv_dir,
        output_dir=str(output_dir),
    )

    results = orchestrator.run_full_validation()

    if "gate_decision" in results:
        gate = results["gate_decision"]
        assert gate["status"] in ["PASS", "FAIL"]
        assert "criteria" in gate
        assert "ic_pass" in gate["criteria"]
        assert "hr_pass" in gate["criteria"]
        assert "stability_pass" in gate["criteria"]
