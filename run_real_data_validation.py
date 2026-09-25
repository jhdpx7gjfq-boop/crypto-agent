#!/usr/bin/env python3
"""
RRP Real Data Validation Execution.

Runs stages 1, 4, 6 on real historical OHLCV.
Compares to synthetic results.
Generates decision memo.
"""

import json
import logging
from pathlib import Path
from datetime import datetime

from real_data_rrp_validation import RealDataRRPValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def load_synthetic_results():
    """Load synthetic validation results from previous run."""
    results_dir = Path("./validation_reports")
    synthetic = {}

    for stage_num in [1, 4, 6]:
        stage_name = {1: "PIT", 4: "BASELINE", 6: "WFV"}[stage_num]
        filename = f"{stage_name}_AUDIT.json"
        filepath = results_dir / filename

        if filepath.exists():
            with open(filepath) as f:
                synthetic[stage_num] = json.load(f)
        else:
            logger.warning(f"Synthetic {stage_name} results not found: {filepath}")
            synthetic[stage_num] = None

    return synthetic


def generate_real_vs_synthetic_comparison(synthetic: dict, real: dict) -> str:
    """Generate markdown comparison of synthetic vs real data results."""
    comparison = """# RRP Validation: Synthetic vs Real Data Comparison

**Generated:** {timestamp}

## Executive Summary

Comparison of RRP validation gate (stages 1, 4, 6) results:
- Synthetic data: Mechanical dormancy→revival patterns
- Real data: Actual market OHLCV with noise, regimes, stochasticity

---

## Stage 1: PIT Audit (Signal Independence)

### Criteria (LOCKED)
≥3 of 6 signals show independent information (low correlation with price/volume baseline)

### Synthetic Results
{synthetic_stage1}

### Real Data Results
{real_stage1}

### Analysis
{stage1_analysis}

---

## Stage 4: Baseline Comparison (Information Coefficient)

### Criteria (LOCKED)
RRP IC ≥ baseline IC (price momentum + volume surge)

### Synthetic Results
{synthetic_stage4}

### Real Data Results
{real_stage4}

### Analysis
{stage4_analysis}

---

## Stage 6: Walk-Forward Validation (Win Rate)

### Criteria (LOCKED)
REVIVING signals with positive 30-day forward return ≥55%

### Synthetic Results
{synthetic_stage6}

### Real Data Results
{real_stage6}

### Analysis
{stage6_analysis}

---

## Decision Matrix

| Stage | Synthetic | Real Data | Status |
|-------|-----------|-----------|--------|
| 1 PIT | {s1_synth} | {s1_real} | {s1_decision} |
| 4 Baseline | {s4_synth} | {s4_real} | {s4_decision} |
| 6 WFV | {s6_synth} | {s6_real} | {s6_decision} |

---

## Verdict

**Synthetic Data Gate:** RESEARCH-CANDIDATE (conditional)
**Real Data Gate:** {real_verdict}

### Path Forward

1. If ALL real data stages PASS → **VALIDATED ALPHA** gate PASS
   - Layer 8 (RPM/X20) unblock authorized
   - RRP frozen as immutable data contract

2. If ANY real data stage FAIL → **Continue research iteration**
   - Analyze failure root cause
   - Redesign RRP signals
   - Restart full 9-stage validation with frozen criteria

---

**Governance:** This comparison is binding. No criteria changes post-observation.
**Date:** {timestamp}
""".format(
        timestamp=datetime.utcnow().isoformat() + "Z",
        synthetic_stage1=json.dumps(synthetic.get(1, {}), indent=2)[:200] + "...",
        real_stage1=json.dumps(real["stages"].get(1, {}), indent=2)[:200] + "...",
        stage1_analysis="[Details from real data results]",
        synthetic_stage4=json.dumps(synthetic.get(4, {}), indent=2)[:200] + "...",
        real_stage4=json.dumps(real["stages"].get(4, {}), indent=2)[:200] + "...",
        stage4_analysis="[Details from real data results]",
        synthetic_stage6=json.dumps(synthetic.get(6, {}), indent=2)[:200] + "...",
        real_stage6=json.dumps(real["stages"].get(6, {}), indent=2)[:200] + "...",
        stage6_analysis="[Details from real data results]",
        s1_synth=synthetic.get(1, {}).get("result", "N/A"),
        s1_real=real["stages"].get(1, {}).get("result", "N/A"),
        s1_decision="✅" if real["stages"].get(1, {}).get("result") == "PASS" else "❌",
        s4_synth=synthetic.get(4, {}).get("result", "N/A"),
        s4_real=real["stages"].get(4, {}).get("result", "N/A"),
        s4_decision="✅" if real["stages"].get(4, {}).get("result") == "PASS" else "❌",
        s6_synth=synthetic.get(6, {}).get("result", "N/A"),
        s6_real=real["stages"].get(6, {}).get("result", "N/A"),
        s6_decision="✅" if real["stages"].get(6, {}).get("result") == "PASS" else "❌",
        real_verdict=real["summary"]["verdict"],
    )

    return comparison


def main():
    """Execute real data validation pipeline."""
    logger.info("Starting RRP Real Data Validation Pipeline")
    logger.info("=" * 70)

    # Load synthetic results for comparison
    logger.info("Loading synthetic validation results...")
    synthetic_results = load_synthetic_results()

    # Run real data validation
    logger.info("Loading real market data (2 years monthly OHLCV)...")
    validator = RealDataRRPValidator(symbols=["BTC", "ETH", "SOL", "AVAX"], data_dir="./real_market_data")

    logger.info("Executing validation stages 1, 4, 6 on real data...")
    real_results = validator.run_real_data_stages()

    # Generate comparison
    logger.info("Generating comparison report...")
    comparison = generate_real_vs_synthetic_comparison(synthetic_results, real_results)

    comparison_file = Path("./real_validation_reports/REAL_VS_SYNTHETIC_COMPARISON.md")
    comparison_file.parent.mkdir(exist_ok=True)
    with open(comparison_file, "w") as f:
        f.write(comparison)

    logger.info(f"Comparison saved to {comparison_file}")

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("REAL DATA VALIDATION COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Verdict: {real_results['summary']['verdict']}")
    logger.info(f"Results: {Path('./real_validation_reports/REAL_DATA_VALIDATION_RESULTS.json').absolute()}")
    logger.info(f"Comparison: {comparison_file.absolute()}")

    return real_results


if __name__ == "__main__":
    results = main()
