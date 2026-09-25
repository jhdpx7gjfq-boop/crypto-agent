# PHASE B-004 SPECIFICATION — RPM/RCM Capital Rotation Engine

**Version**: 1.0 (FROZEN)  
**Date**: 2026-09-25  
**Status**: ✅ FROZEN — OWNER APPROVED FOR B-004 REAL DATA WFV
**Frozen By**: Owner Directive (Option A)
**Effective**: 2026-09-25 15:15 UTC  
**Scope**: Layer 6 — RPM/RCM validation (capital flow detection, rotation confirmation)

---

## Executive Summary

Phase B-004 tests **Rotation/Positioning Model (RPM) and Rotation Confirmation Model (RCM)** as incremental alpha sources on top of baseline momentum. The objective is to measure whether capital rotation signals (sector/market-wide flows) improve prediction accuracy beyond NARM-P+ (Phase B-003 macro layer).

**Key constraint**: This is **NOT** tuning Phase B-003. RPM/RCM is a parallel hypothesis on capital flows. Results are frozen before any regime-based filtering or analysis.

---

## 1. RPM/RCM Architecture

### 1.1 Layers Tested

| Layer | Type | Source | Responsibility |
|-------|------|--------|-----------------|
| **A (Baseline)** | Momentum | Close returns | Contrarian detector (known: IC ≈ −0.12) |
| **H (NARM-P+)** | Macro narrative | Adoption signals | Phase B-003 validated (Δ IC = +0.0359, HR fail) |
| **J (RPM)** | Capital rotation | Flow vectors | THIS PHASE — rotation detector alone |
| **K (RCM)** | Confirmation | Regime × rotation | THIS PHASE — rotation confirmation |
| **L (RPM+RCM)** | Combined | A + H + RPM + RCM | Full stack (4 layers) |

### 1.2 RPM (Rotation/Positioning Model)

**Objective**: Detect capital rotating between sectors/asset classes.

**Input features** (market-wide, NOT per-asset):
- BTC dominance (% of total crypto market cap)
- Altseason strength (ratio of altcoin to BTC returns, 5D)
- Stablecoin reserve flows (inflows/outflows, proxy for leverage)
- ETF flows (Bitcoin + Ethereum ETFs, directional)
- Funding rates (aggregate perpetuals market, long vs short bias)
- Open Interest trends (increase = capital flowing in)

**Processing**:
```
RPM_score = weighted_sum([
    dominance_delta,      # weight: 0.25
    altseason_momentum,   # weight: 0.20
    stablecoin_flow,      # weight: 0.15
    etf_flow,             # weight: 0.20
    funding_bias,         # weight: 0.10
    oi_acceleration       # weight: 0.10
])

rpm_signal = tanh(RPM_score / normalization_factor)  # [-1, +1]
```

**Output range**: [-1, +1] (−1 = capital leaving, +1 = capital flowing in)

**Interpretation**:
- RPM > +0.5: Strong inflow (bullish rotation to BTC/alts)
- RPM ∈ [−0.5, +0.5]: Mixed/neutral capital positioning
- RPM < −0.5: Strong outflow (risk-off, flight to stables)

### 1.3 RCM (Rotation Confirmation Model)

**Objective**: Confirm RPM signal with regime alignment.

**Input**:
- RPM_signal (from Layer J)
- Market regime (Bull/Bear/Accumulation; from Layer 2)
- Historical frequency of rotation-regime pairs

**Processing**:
```
RCM_confirmation = rpm_signal × regime_alignment_factor

regime_alignment = {
  Bull: RPM correlates positively with returns (trust RPM) → +1.2
  Accumulation: RPM less reliable (ambiguous) → +0.8
  Bear: RPM is hedging signal (inverse logic) → +0.5
}

rcm_signal = rpm_signal × regime_alignment
rcm_final = clip(rcm_signal, -1, +1)
```

**Output range**: [-1, +1] (regime-weighted RPM)

---

## 2. Signal & Target Definition

### 2.1 Prediction Target

**Horizon**: 5-day forward return (same as Phase B-003)

```python
target_return_5d = (price[t+5] - price[t]) / price[t]
target_binary = +1 if target_return_5d > 0 else -1
```

### 2.2 Signal Definition (Blend)

**Per-window signal**:
```python
signal_J = rpm_signal       # RPM alone
signal_K = rcm_final        # RCM (regime-weighted RPM)
signal_L = 0.5 * baseline + 0.3 * narm_p + 0.2 * rpm_signal
          # Full stack blend (baseline + NARM-P+ + RPM)
```

**Clip all signals** to [-1, +1].

### 2.3 IC Calculation

**Information Coefficient**: Spearman rank correlation (target returns vs signal)

```
IC = spearman_corr(signal, target_return_5d)
```

**Acceptable range**: [-1, +1]  
**Target**: IC > 0.005 points (gate criterion 1)

---

## 3. Data & PIT Compliance

### 3.1 Data Source

**Default**: Synthetic data (deterministic, reproducible)
- OHLCV: Binance historical 1D candles (BTC/USDT)
- Features: Computed from price + public market data (Glassnode, CryptoQuant stubs)
- Real data A/B: Separate directive (not blocking B-004)

**Data period**: 2021-01-01 to 2024-09-25 (same as Phase B-003 for consistency)

### 3.2 PIT Compliance Rules

**At prediction time T**:
- Signal receives **only** data strictly before T (exclusive)
- Future prices (T+1, T+2, …, T+5) are NOT visible
- Target (5D return) is computed AFTER test, not during training

**Implementation**:
```python
def signal_func(pit_data, current_idx, params):
    # pit_data = df.iloc[:current_idx+1]
    # Must NOT access df.iloc[current_idx+1:] or beyond
    ...
    return signal_value

# Target computed separately during validation
target = (close[t+5] - close[t]) / close[t]
```

**Verification**: Run `test_pit_future_modification` from Phase 2.1 suite on B-004 data.

---

## 4. Walk-Forward Validation (WFV) Protocol

### 4.1 Window Configuration

**Expanding windows** (train start fixed, test start slides):

```
Training period: Always 180 days (fixed from 2021-01-01)
Testing period: 30 days per window
Overlap: 0 days (no gap, test follows train)
Slide increment: 30 days

Window structure:
├─ Window 0: Train [2021-01-01 : 2021-06-30], Test [2021-07-01 : 2021-07-31]
├─ Window 1: Train [2021-01-01 : 2021-07-30], Test [2021-08-01 : 2021-08-31]
├─ ...
└─ Window 18: Train [2021-01-01 : 2024-06-27], Test [2024-06-28 : 2024-07-28]

Total windows: 19 (confirmed by previous WFV code)
```

### 4.2 Per-Window Execution

**For each window**:

1. **Train**: Fit RPM weights on training data (if applicable; RPM uses fixed weights)
2. **Test**: Validate signal on test data (PIT-compliant)
3. **Predict**: Generate signal_J, signal_K, signal_L for each test timestamp
4. **Target**: Compute 5D forward returns for all test predictions
5. **IC**: Rank correlation between signal and target returns

### 4.3 Result Aggregation

**Per-window metrics**:
- IC_J (RPM alone)
- IC_K (RCM)
- IC_L (full stack)
- Hit_rate_J, Hit_rate_K, Hit_rate_L

**Across all 19 windows**:
```
Mean_IC_J = mean(IC per window)
Std_IC_J = std(IC per window)
Mean_HR_J = mean(Hit_rate per window)
Stability_J = 1 - (Std / (Mean + ε))
```

---

## 5. Ablation & ΔIC Computation

### 5.1 Ablation Models

| Model | Layers | ΔIC vs Baseline | Test |
|-------|--------|-----------------|------|
| A | Baseline momentum | 0.0 (reference) | Known: IC ≈ −0.1208 |
| H | A + NARM-P+ | +0.0359 (B-003) | Known: ΔIC passes, HR fails |
| J | A + RPM | ΔIC_J = IC_J − IC_A | THIS PHASE |
| K | A + RCM | ΔIC_K = IC_K − IC_A | THIS PHASE |
| L | A + H + RPM + RCM | ΔIC_L = IC_L − IC_A | THIS PHASE (full stack) |

### 5.2 Delta Computation

```python
delta_ic_j = mean_ic_j - mean_ic_a  # RPM incremental alpha
delta_ic_k = mean_ic_k - mean_ic_a  # RCM incremental alpha
delta_ic_l = mean_ic_l - mean_ic_a  # Full stack incremental alpha
```

**Primary interest**: ΔIC_J (RPM alone contribution)

---

## 6. Gate Criteria

### 6.1 ALL criteria must PASS

| Criterion | Metric | Target | Rationale |
|-----------|--------|--------|-----------|
| **1. ΔIC** | ΔIC_J > 0.005 points | > 0.005 | Statistically meaningful incremental alpha |
| **2. Hit Rate** | HR_J > 0.50 (50% directional accuracy) | > 0.50 | Better than random binary predictions |
| **3. Stability** | Stability_J > 0.65 (low variance) | > 0.65 | Signal consistent across windows |

**Pass decision**: ALL THREE must be TRUE  
**Fail decision**: ANY ONE is FALSE

### 6.2 Interpretation

| Outcome | Decision | Next Action |
|---------|----------|------------|
| ✅ ΔIC pass, HR pass, Stability pass | **GATE PASS** | Proceed to combined macro layer (Phase 3) |
| ❌ ΔIC fail OR HR fail OR Stability fail | **GATE FAIL** | Document findings, consider alternative hypotheses |
| ⚠️ ΔIC pass, HR/Stability fail | **GATE FAIL** (like B-003) | Research signal detected but NOT production-ready |

---

## 7. Regime Analysis (Post-Hoc Only)

### 7.1 Rule: FREEZE Before Regime Filtering

**Critical**: Do NOT pre-filter B-004 data to Bull/Bear based on B-003 observations.

**Correct workflow**:
1. Run full WFV on complete dataset (19 windows, all regimes)
2. **FREEZE** ΔIC, HR, Stability results
3. Test gate criteria (PASS/FAIL on frozen results)
4. **THEN**: Post-hoc, decompose by regime (Bull, Bear, Accumulation, Recovery)

### 7.2 Post-Hoc Regime Breakdown

**After gate decision**:
```
Per-regime ΔIC (informational, NOT gating):
├─ Bull 2021 (N windows in regime)
├─ Bear 2022
├─ Recovery 2023
└─ Bull 2024 (partial)

Question: Does RPM work better in Bull? (exploratory, not predictive)
Answer: Provides hypothesis for Phase 3, requires external validation.
```

**Important**: This analysis is **exploratory**, not authoritative. Regime heterogeneity detected in-sample is prone to overfitting across 19 windows.

---

## 8. Ablation Plan

### 8.1 If Gate Passes

```
├─ Step 1: Confirm ΔIC_J standalone
├─ Step 2: Test ΔIC_K (RCM regime weighting)
├─ Step 3: Compare ΔIC_J vs ΔIC_K vs ΔIC_L
├─ Step 4: Decompose by regime (post-hoc)
└─ Step 5: Recommend for Phase 3 (combined macro)
```

### 8.2 If Gate Fails

```
├─ Document: Which criterion failed (ΔIC, HR, Stability)
├─ Analyze: Per-window variance (high = unstable)
├─ Check: Pre-hoc assumptions (RPM weights, target definition)
├─ Decision: Iterate on RPM features OR accept as non-predictive
└─ Status: RPM layer frozen pending alternative hypothesis
```

---

## 9. Results Freeze & Governance

### 9.1 Freeze Protocol

**Once WFV completes across all 19 windows**:

1. Compute: ΔIC_J, ΔIC_K, ΔIC_L, HR, Stability (frozen)
2. Test gate criteria (no changes to results)
3. Record decision (PASS/FAIL, immutable)
4. Document post-hoc regime findings (exploratory, tagged)
5. **LOCK**: No tuning, no re-weighting, no cherry-picking regimes

**No deviations** allowed after freeze.

### 9.2 Non-Negotiable Rules

| Rule | Enforcement |
|------|-------------|
| ✋ No Bull/Bear pre-filtering | Verified in window creation |
| ✋ No weight tuning after observation | Fixed weights recorded before WFV |
| ✋ No threshold adjustment | Gate criteria frozen before test |
| ✋ No selective window dropping | All 19 windows counted |
| ✋ No regime-based selection | Full dataset first, analysis post-hoc |

---

## 10. Validation Criteria (Success Definition)

### 10.1 VALIDATED ALPHA

```
Condition:
├─ ΔIC_J > 0.005 ✓
├─ HR_J > 0.50 ✓
└─ Stability_J > 0.65 ✓

Result: RPM is production-ready alpha
Status: Can proceed to Phase 3 (combined macro layer)
Recommendation: Integrate RPM into Layer 6 for live evaluation
```

### 10.2 RESEARCH SIGNAL

```
Condition:
├─ ΔIC_J > 0.005 ✓
├─ HR_J ≤ 0.50 ✗
└─ (Stability_J may vary)

Result: ΔIC improves ranking, but directional accuracy insufficient
Status: GATE FAIL (like Phase B-003 macro)
Recommendation: Document findings, consider alternative architectures
```

### 10.3 NON-PREDICTIVE

```
Condition:
├─ ΔIC_J ≤ 0.005 ✗

Result: No meaningful incremental alpha
Status: GATE FAIL
Recommendation: RPM layer does not contribute; freeze until new hypothesis
```

---

## 11. Implementation Notes

### 11.1 Code Structure

**Expected modules** (subject to audit):
- `src/research/rpm_layer.py` — RPM signal computation
- `src/research/rcm_layer.py` — RCM confirmation
- `src/research/phase_b_004_runner.py` — WFV pipeline orchestration
- `tests/test_rpm_rcm.py` — PIT compliance, signal sanity checks

### 11.2 Integration Points

- **Data layer**: Use `EquityBacktester` (Phase 2.1) for backtesting
- **PIT layer**: Verify no future data leakage (Phase 2.1 audits apply)
- **Metrics**: IC, Hit_rate, Stability (same as Phase B-003)
- **WFV**: 19-window expanding protocol (verified from Phase B-003 code)

### 11.3 Testing Requirements

```
✓ test_pit_future_modification — no look-ahead
✓ test_rpm_signal_in_range — RPM output ∈ [-1, +1]
✓ test_rcm_regime_alignment — RCM weighting applied correctly
✓ test_wfv_window_boundaries — train/test split enforced
✓ test_ic_calculation — Spearman correlation correct
✓ test_ablation_delta — ΔIC computed accurately
```

---

## 12. Status & Approval

### 12.1 Spec Status

**Current**: ✅ FROZEN (Owner approved 2026-09-25)  
**Authority**: dvdlgustin@gmail.com  
**Lock date**: 2026-09-25  
**Modifications**: PROHIBITED (must create new version if changes needed)

### 12.2 Freeze Certification

**Owner**: dvdlgustin@gmail.com  
**Decision**: ✅ APPROVE (proceed to Phase B-004 implementation)  
**Date**: 2026-09-25  
**Authority**: FINAL (immutable protocol)

---

## 13. Related Documents

- `docs/SPRING-PHASE-B-003-SPEC.md` — Macro layer (NARM-P+) protocol
- `docs/SPRING-PHASE-B-003-RESULTS.md` — B-003 gate results (ΔIC pass, HR fail)
- `src/validation/backtester_hardening.py` — Phase 2.1 EquityBacktester
- `CLAUDE.md` — Project governance and phase sequencing

---

**PHASE B-004 SPECIFICATION v1.0**  
**Status**: AWAITING OWNER APPROVAL → FREEZE  
**Date**: 2026-09-25
