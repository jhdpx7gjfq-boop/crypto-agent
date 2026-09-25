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

### Environmental Constraint: Daily OHLCV Data Unavailable

**Data source audit (completed 2026-09-25):**
1. Binance API: Blocked by proxy (HTTP 451)
2. CoinGecko MCP: Returns chart widget only, not raw OHLCV
3. TipRanks MCP: Returns monthly aggregates for 730-day windows; quota exhausted (1/10 calls remaining)
4. Alternative exchanges (Kraken, Poloniex, etc.): Not accessible in current network environment

**Conclusion:** Daily OHLCV (730 candles) cannot be acquired in this environment.

### Option A: Continue with Weekly Data (Current Path)

**Status:** Completed. Real data validation executed on weekly OHLCV (27 candles).

**Result:** NEEDS_ITERATION

**Interpretation:**
- RRP signals do not detect revival patterns in real market data (weekly granularity)
- This is valid finding: either RRP needs refinement OR daily data is required for proper detection
- Cannot proceed further without daily data

### Option B: Defer to External Environment

**Approach:** Acquire daily OHLCV via:
- Local development environment (non-cloud)
- Premium data service (Glassnode, Messari)
- Network with different egress policy
- After Layer 8 is unblocked: automated daily pipeline via Kafka/Redis

**When available:**
- Import 730 daily OHLCV files to `./real_market_data/`
- Rerun validation: `python run_real_data_validation.py`
- Expected: 1-5 minutes to decision (calculation only)

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

### Immediate (Governance Lock)

**Do NOT proceed with Layer 8 unblocking.** NEEDS_ITERATION verdict stands.

**Rationale:**
- Real data validation required by IGWT-PF26 governance (3 invariants enforced)
- RRP signals failed to validate on available real market data (weekly OHLCV)
- Cannot conclusively determine if failure is due to:
  - Inadequate signal design (needs RRP refinement)
  - Insufficient data granularity (needs daily OHLCV)
- Both paths require investigation before Layer 8 unblock

### Path 1: Refine RRP Signals (Parallel Track)

While awaiting daily data:
- Analyze stage 1 failure: Why did 0/6 signals show independence?
- Review signal definitions: Dormancy, volume breakout, momentum, structure, sentiment, exhaustion
- Consider: Weekly aggregation masks signals → redesign for weekly granularity?
- Prepare revised RRP candidate for next validation cycle

### Path 2: Acquire Daily Data (External)

- Export current framework to local/non-cloud environment
- Fetch 730 daily OHLCV candles from any accessible source
- Rerun validation stages 1, 4, 6
- Make final VALIDATED ALPHA or NEEDS_ITERATION decision

### Long-term (Post-Decision)

Once Layer 8 is unblocked (either via daily data validation or RRP refinement):
- Establish automated daily data pipeline (Binance, Kraken, or premium vendor)
- Maintain data provenance and immutability versioning
- Archive validation results with decision timestamps

---

**Status:** Real data validation complete on weekly data. NEEDS_ITERATION verdict locked. Layer 8 blocked pending daily data validation OR RRP refinement.

**Owner:** IGWT-PF26 Real Data Validation Pipeline  
**Governance:** All 3 invariants maintained. No compromise on validation rigor.  
**Decision Authority:** Awaiting either (1) daily OHLCV data in any form, or (2) approved RRP signal redesign + restart full 9-stage validation
