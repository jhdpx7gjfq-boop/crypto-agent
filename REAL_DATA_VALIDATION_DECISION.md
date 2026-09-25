# Real Data Validation - Decision Memo

**Date:** 2026-09-25  
**Status:** NEEDS_ITERATION (real data fails to validate RRP signals)  
**Layer 8 Status:** BLOCKED (unchanged)

---

## Executive Summary

Real market data validation (stages 1, 4, 6) executed on 27-week OHLCV dataset (6 months: Mar-Sep 2026).

**Results:**
- Stage 1 (PIT Audit): FAIL - 0 of 6 signals show independent information
- Stage 4 (Baseline Comparison): PASS - (0 samples, vacuous truth)
- Stage 6 (Walk-Forward Validation): FAIL - 0 REVIVING signals detected in real data

**Verdict:** NEEDS_ITERATION

Real market data does not confirm RRP signal validity. This is expected given data granularity constraints.

---

## Root Cause Analysis

### Data Granularity Issue

**Weekly data (27 candles, 6 months):**
- Window size: 90 days ÷ 7 days/week ≈ 13 weeks
- Available: 27 weeks
- Coverage: Adequate for window construction, but limited signal variance

**Problem:** RRP signal components designed for daily granularity:
- Dormancy detection: Requires consistent 90-day no-volume pattern
- Volume breakout: Discrete daily volume spikes; weekly aggregation masks individual breakouts
- Price momentum: Weekly closes smooth daily volatility; momentum signals dampened
- Structure recovery: Weekly bars insufficient for micro-structure detection

**Why Stage 1 Failed (0 signals independent):**
- 27 weekly candles insufficient for correlation analysis
- Large window/sample ratio reduces statistical power
- Weekly aggregation correlates signals with baseline (price + volume)

**Why Stage 6 Failed (0 wins):**
- Test period (day 90-150 → week 13-21) spans only 9 weeks of 27 available
- No REVIVING signals triggered in this lookback window
- Real market didn't exhibit pattern RRP detects in synthetic data

---

## Comparison: Synthetic vs Real Data

| Aspect | Synthetic Data | Real Market Data |
|--------|---|---|
| **Source** | Deterministic recovery patterns | Actual OHLCV (weekly aggr.) |
| **Dormancy** | Perfect 90-day zero-volume → sharp revival | Gradual volume decay, no revival detected |
| **Signal detection** | 100% accuracy in synthetic patterns | 0% accuracy in real patterns |
| **Stage 1 result** | PASS (4/6 signals independent) | FAIL (0/6 signals independent) |
| **Stage 6 result** | PASS (win rate 76%) | FAIL (win rate 0%) |

**Interpretation:** Synthetic data validated framework implementation. Real data shows framework cannot detect revival patterns in actual market behavior with weekly granularity.

---

## Technical Findings

### Data Requirements (Frozen Criteria)

For valid RRP detection (locked before real data run):
- **Minimum window:** 90 days (90 daily candles)
- **Data granularity:** Daily (730 candles for 2 years)
- **Stage 1 threshold:** ≥3 signals with R² < 0.15
- **Stage 4 threshold:** RRP IC ≥ baseline IC
- **Stage 6 threshold:** Win rate ≥55%

**Current gap:**
- Weekly data provides 1 candle per 7 days
- 27 weekly candles = ~6 months, only 3.86x minimum window size
- Daily data requirement cannot be relaxed without losing statistical rigor

---

## Path Forward

### Option A: Daily Data Acquisition (Recommended)

**Approach:** Fetch 730 daily OHLCV candles for BTC, ETH, SOL, AVAX

**Data source priority:**
1. ~~Binance API~~ (blocked by proxy 451)
2. CoinGecko free tier (limited to recent data, may work via proxy)
3. Alternative exchange APIs (Kraken, Poloniex)
4. Premium data vendor (Glassnode, Messari)

**Effort:** 
- Proxy bypass / alternative source: 1-2 hours
- Fetch + save: 10 minutes
- Rerun validation: 1 minute
- **Total:** 1-2 hours to decision

**Expected outcome:**
- If all stages PASS: VALIDATED ALPHA gate PASS → Layer 8 unblock authorized
- If any stage FAIL: Continue RRP refinement → Restart 9-stage validation

### Option B: Adjust Validation Windows (Not recommended)

Modify stages 1, 4, 6 to work with weekly timeframes:
- Stage 1: 4-week signal windows instead of 90-day
- Stage 4: 1-week forward returns instead of 30-day
- Stage 6: 4-week walk-forward loop instead of day-by-day

**Trade-off:** Loses temporal precision; signals become less actionable

### Option C: Accept Real Data Results

Treat NEEDS_ITERATION as binding decision:
- RRP signals not validated on real data → Unsuitable for Layer 8
- Redesign RRP based on findings
- Return to full 9-stage validation with refined criteria

---

## Governance Impact

### Invariants Maintained ✅

1. **Immutability:** Synthetic results (RESEARCH-CANDIDATE) unchanged
2. **No tuning:** Validation criteria locked before real data execution
3. **No Layer 8:** Remains BLOCKED; this result does not unblock it

### Decision Authority

VALIDATED ALPHA gate requires:
- All stages (1, 4, 6) PASS on real data with ≥730 daily candles
- Current result: NEEDS_ITERATION → Gate does not pass

**Layer 8 stays BLOCKED pending daily data validation.**

---

## Files Generated

```
real_validation_reports/
├── REAL_DATA_VALIDATION_RESULTS.json    (Detailed audit results)
├── REAL_VS_SYNTHETIC_COMPARISON.md       (Side-by-side comparison)
└── REAL_DATA_VALIDATION_DECISION.md      (This document)
```

---

## Recommendations

1. **Immediate (Next 1-2 hours):**
   - Resolve Binance proxy block OR find alternative daily data source
   - Fetch 730 daily candles for BTC, ETH, SOL, AVAX
   - Rerun validation stages 1, 4, 6

2. **Decision points:**
   - If all stages PASS → Issue VALIDATED ALPHA memo, unblock Layer 8
   - If any stage FAIL → Document specific signal failure, redesign RRP, restart validation

3. **Long-term:**
   - Establish automated daily data pipeline (post-Layer 8)
   - Maintain data provenance and immutability guarantees
   - Version control real data validation results

---

**Status:** Awaiting daily OHLCV data acquisition and revalidation.  
**Owner:** IGWT-PF26 Real Data Validation Pipeline  
**Governance:** Invariants locked, Layer 8 blocked, decision pending daily data
