# Layer 7: RRP (Revival Radar Pipeline) — Validation Specification

**Status:** VALIDATED IMPLEMENTATION / RESEARCH-CANDIDATE ALPHA  
**Governance:** Mandatory P0 gate before Layer 8 integration  
**Author:** IGWT-PF26 Quant Intelligence OS  
**Date:** 2026-09-25

---

## Executive Summary

RRP implements revival detection with 6 independent signals across dormancy analysis, momentum recovery, and exhaustion patterns. Implementation is structurally sound (168/168 tests passing). **Validation gate tests whether RRP has independent predictive information—not just implementation correctness.**

---

## Data Contract

### Inputs
- **OHLCV**: Daily candles, 365-day lookback minimum
  - Timestamp (UTC), open, high, low, close, volume, quote_asset_volume
  - Source: Binance public API
  - Validation: No gaps > 24h, quotes strictly positive

### Outputs
```json
{
  "rrp_score": 0-100,
  "is_dormant": bool,
  "volume_breakout": 0-25,
  "price_momentum": 0-25,
  "structure_recovery": 0-20,
  "sentiment_shift": 0-20,
  "exhaustion_recovery": 0-10,
  "current_price": float,
  "dormancy_info": {
    "is_dormant": bool,
    "dormancy_days": int,
    "avg_dormant_volume": float,
    "dormancy_duration": int
  },
  "timestamp": ISO8601,
  "verdict": "REVIVING|WAKING|DORMANT"
}
```

### Immutability
- Snapshots append-only to `engine.snapshots[]`
- Each snapshot locked with timestamp at generation time
- No retrospective modification allowed
- Audit trail: timestamp, score, verdict, price immutable post-generation

---

## Validation Gate Stages

### Stage 1: PIT Audit (Predictive Information Test)

**Objective:** Confirm RRP signals have information independent of price/volume alone.

**Method:**
1. Generate RRP scores on 365-day historical daily OHLCV
2. For each signal component (volume_breakout, price_momentum, etc.):
   - Correlation with lagged close price (t-1 to t-30)
   - Correlation with lagged volume (t-1 to t-30)
   - Partial correlation controlling for price + volume
3. If all components show >0.7 correlation to price/volume alone → **FAIL**
4. If any component shows <0.3 correlation to price/volume → **PASS** (has independent info)

**Pass Criteria:** At least 3 of 6 signals show independent information (partial R² > 0.15 vs price/vol baseline).

---

### Stage 2: Look-Ahead Audit

**Objective:** Verify no future data leaks into score calculation.

**Method:**
1. Code review: Trace each calculation
   - `_detect_dormancy()`: Uses ohlcv[-90:] only ✓
   - `_detect_volume_breakout()`: Uses ohlcv[-10:] and ohlcv[-90:-10] only ✓
   - `_detect_price_momentum()`: Uses ohlcv[-90:] only ✓
   - `_detect_structure_recovery()`: Uses ohlcv[-90:] only ✓
   - `_detect_sentiment_shift()`: Uses ohlcv[-30:] only ✓
   - `_detect_exhaustion_recovery()`: Uses ohlcv[-20:] only ✓

2. Implementation check: Confirm no functions call `get_ohlcv()` with future-biased intervals
3. Snapshot validation: Timestamp locked at generation, never updated

**Pass Criteria:** Zero look-ahead bias confirmed in code review + snapshot timestamps verified immutable.

---

### Stage 3: Signal Timestamp / Snapshot Immutability Audit

**Objective:** Confirm snapshot store is truly immutable and timestamps are generation-time locked.

**Method:**
1. Generate snapshot at time T with OHLCV data as of T
2. Attempt to modify snapshot in-place → Should fail or raise error
3. Verify timestamp in snapshot matches generation time (±1 minute)
4. Confirm snapshot cannot be updated retroactively
5. Test: Generate 10 snapshots, verify order and immutability

**Pass Criteria:** 100% snapshot immutability, timestamps locked, append-only store confirmed.

---

### Stage 4: Baseline Comparison

**Objective:** Compare RRP predictive signal vs 3 baselines.

**Baselines:**
- **B1 (Price Momentum):** Simple 30-day price change
- **B2 (Volume Surge):** Recent volume / 90-day average
- **B3 (Combined):** B1 + B2 equally weighted

**Method:**
1. On 365-day historical data:
   - Score RRP at each day t
   - Score all baselines at each day t
   - Predict forward 30 days (target: `return_30d = (close[t+30] - close[t]) / close[t]`)

2. Correlation with forward returns:
   - RRP score vs return_30d
   - B1 vs return_30d
   - B2 vs return_30d
   - B3 vs return_30d

3. Information coefficient (IC):
   - Spearman rank correlation (daily predictions vs next-30d returns)
   - RRP should have IC ≥ B3's IC to justify complexity

**Pass Criteria:** RRP IC ≥ baseline IC (show informational advantage despite higher complexity).

---

### Stage 5: Out-of-Sample (OOS) Validation

**Objective:** Test on data never seen during development.

**Method:**
1. Split 365-day history into:
   - In-sample (IS): First 255 days (70%)
   - Out-of-sample (OOS): Last 110 days (30%)
   
2. On IS data only:
   - Recalibrate if needed (none needed for RRP—fully rule-based)
   - Note thresholds: REVIVING ≥60, WAKING 40-59, DORMANT <40

3. On OOS data:
   - Generate RRP scores
   - Measure predictive power (correlation with 30-day forward returns)
   - Compare IS vs OOS correlation
   - If OOS correlation drops >30% vs IS → **FAIL** (overfitting)

**Pass Criteria:** OOS correlation within 90% of IS correlation (no material overfitting).

---

### Stage 6: Walk-Forward Validation (WFV)

**Objective:** Simulate real-time daily scoring; verify no lookahead leakage.

**Method:**
1. Simulation window: 365 days daily
2. At each day t (starting t=90):
   - Data available: ohlcv[0:t]
   - Generate RRP score using ohlcv[-90:t] only
   - Lock snapshot with timestamp = t
   - Store prediction

3. Forward testing (t=90 to t=365):
   - 30-day forward return = (close[min(t+30, 365)] - close[t]) / close[t]
   - Compare RRP verdict at t with actual return t to t+30

4. Metrics:
   - Precision (% REVIVING signals that had positive 30d return)
   - Recall (% positive 30d returns that RRP flagged REVIVING)
   - Win rate (% trades entering on REVIVING verdict that closed positive)
   - Average return on REVIVING vs WAKING vs DORMANT

**Pass Criteria:**
- Win rate ≥ 55% (positive edge vs 50% random)
- Precision ≥ 50% (majority of signals correct direction)
- Information ratio > 0 (risk-adjusted return positive)

---

### Stage 7: Ablation Testing

**Objective:** Verify each of 6 signals contributes independently to prediction.

**Method:**
1. Generate full RRP scores on 365-day OOS data
2. For each signal (volume_breakout, momentum, etc.):
   - Set that signal to 0, recalculate rrp_score
   - Measure correlation with forward returns (ablated vs full)
   - If ablation drops correlation <5% → signal is noise

3. Test combinations:
   - Only volume_breakout + price_momentum
   - Only structure_recovery + sentiment_shift
   - Full 6-signal combination

**Pass Criteria:** All 6 signals contribute independently (each ablation reduces correlation by ≥5%); no redundant signals.

---

### Stage 8: Robustness Testing

**Objective:** Confirm RRP signal is stable across different market regimes.

**Method:**
1. Identify regime windows in 365-day history:
   - Bull market (close > 200-day MA, trending up)
   - Bear market (close < 200-day MA, trending down)
   - Range-bound (close oscillating ±5% of 200-day MA)

2. For each regime:
   - Generate RRP scores during that regime only
   - Measure predictive power within regime
   - Compare correlation across regimes

3. Cross-asset robustness:
   - If data available: Run same validation on 3 other tokens (ETHUSD, AVAX, SOL)
   - RRP should generalize; if IC drops >40% on new assets → regime-specific

**Pass Criteria:** 
- Correlation within regimes ≥ 0.12 (minimal)
- Correlation across regimes stable (±0.03)
- Generalizes to other tokens (IC drop <30%)

---

### Stage 9: Statistical Validation

**Objective:** Confirm results are not due to randomness.

**Method:**
1. Null hypothesis: RRP scores are independent of forward returns (correlation = 0)
2. Calculate Spearman correlation over 275 daily predictions (OOS window)
3. T-stat = r * sqrt(n-2) / sqrt(1-r²)
4. P-value from t-distribution with df = n-2
5. Require p-value < 0.05 (95% confidence results not due to chance)

**Pass Criteria:** p-value < 0.05; reject null hypothesis of independence.

---

## Decision Matrix

| Stage | Pass | Fail | Action |
|-------|------|------|--------|
| 1. PIT | ≥3 signals independent | <3 signals independent | CONTINUE / ITERATE signal design |
| 2. Look-ahead | Zero bias confirmed | Lookahead detected | **FAIL** — redesign |
| 3. Immutability | Snapshots immutable | Mutation detected | **FAIL** — fix store |
| 4. Baseline | RRP ≥ B3 IC | RRP < B3 IC | CONTINUE (no advantage) / ITERATE |
| 5. OOS | Corr drop ≤30% | Corr drop >30% | CONTINUE / ITERATE parameters |
| 6. WFV | Win rate ≥55% | Win rate <55% | CONTINUE (marginal) / REJECT (no edge) |
| 7. Ablation | All 6 contribute | Redundant signals | CONTINUE / OPTIMIZE signal set |
| 8. Robustness | Stable across regimes | Regime-dependent | CONTINUE (regimes documented) / ITERATE |
| 9. Statistical | p < 0.05 | p ≥ 0.05 | CONTINUE / **FAIL** — not significant |

---

## Final Decision Criteria

### VALIDATED ALPHA ✓
- **All stages: PASS**
- RRP demonstrated independent predictive information
- Walk-forward win rate ≥55%
- Statistical significance confirmed (p < 0.05)
- Immutability verified
- **→ Lock as input for Layer 8**

### RESEARCH CANDIDATE (CONDITIONAL)
- Stages 1-3, 9: PASS
- Stages 4-8: MARGINAL (performance edge <10%, regime-dependent)
- **→ Document findings; do not advance to Layer 8 yet; iterate signal design**

### REJECT ✗
- Any of stages 2, 3, 9: **FAIL** (lookahead, immutability, or not statistically significant)
- **→ Halt progression; redesign or close**

---

## Audit Outputs

### Required Artifacts
1. **PIT_AUDIT.md** — Signal independence results, partial R² by component
2. **LOOKAHEAD_AUDIT.md** — Code review trace, confirmation of no future leakage
3. **SNAPSHOT_AUDIT.md** — Immutability test results, timestamp verification
4. **BASELINE_COMPARISON.md** — IC table (RRP vs B1/B2/B3)
5. **OOS_REPORT.md** — IS vs OOS correlation; overfitting analysis
6. **WFV_REPORT.md** — Daily predictions, forward returns, win rate, metrics
7. **ABLATION_REPORT.md** — Contribution of each signal; redundancy analysis
8. **ROBUSTNESS_REPORT.md** — Regime-dependent results; cross-asset generalization
9. **STATISTICAL_TEST.md** — Correlation, t-stat, p-value
10. **DECISION_MEMO.md** — Final gate decision (VALIDATED ALPHA / RESEARCH / REJECT)

---

## Timeline & Ownership

| Phase | Owner | Duration | Gate |
|-------|-------|----------|------|
| Stages 1-3 (PIT/Lookahead/Immutability) | Code audit | 1 day | MUST PASS |
| Stage 4 (Baseline) | Backtesting | 2 days | INFORMATIONAL |
| Stages 5-6 (OOS/WFV) | Walk-forward engine | 3 days | CRITICAL |
| Stages 7-9 (Ablation/Robustness/Stat) | Validation pipeline | 2 days | PASS/MARGINAL |
| Decision + Documentation | Governance | 1 day | FINAL |

**Total:** ~9 days to full validation gate completion.

---

## Layer 8 Pre-Requisite

Layer 8 (RPM X20 Optimizer) **cannot begin** until RRP achieves **VALIDATED ALPHA** status.

**Data Contract Lock:** Once frozen, RRP code, scoring logic, and snapshot immutability become read-only inputs to Layer 8. No changes to RRP scoring without re-running full validation gate.

---

## Governance Note

This validation gate implements the principle: **No Implementation → Alpha → Production without proof of predictive power.**

Tests prove correctness of implementation, not correctness of strategy. Validation gate proves information content.
