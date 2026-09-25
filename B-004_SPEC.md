# B-004 Specification: RPM/RCM Full-Dataset Walk-Forward Validation

**Status**: FROZEN (Pre-Implementation)  
**Effective Date**: 2026-09-25  
**Authorization**: Phase 2.1 Gate PASS → B-004 GO  
**Execution Status**: BLOCKED (awaiting RPM/RCM implementation)

---

## 1. Executive Summary

B-004 is the **definitive quantitative validation** of the RPM/RCM (Rotation Confirmation Model) strategy across the full dataset using 19-window walk-forward validation.

**Scope**: RPM/RCM only. No regime pre-filtering. No Bull/Bear stratification in primary WFV.

**Frozen Gates**:
- ΔIC (Information Coefficient) ≥ threshold
- HR (Hit Rate) ≥ threshold
- Stability (Coefficient of Variation) ≤ threshold

**Verdict Threshold**: ALL THREE gates must PASS for `B-004 PASS`.

---

## 2. RPM/RCM Module Definition

### 2.1 Architecture (Frozen)

**RPM/RCM** = Rotation Confirmation Model

**Input Contract**:
```python
class RPMSignal:
    timestamp: datetime (UTC, point-in-time)
    asset: str (e.g., "BTC", "ETH")
    score: float (0-1, rotation confidence)
    components: dict[str, float]
        - capital_flow: 0-1
        - relative_strength: 0-1
        - narrative_acceleration: 0-1
        - fundamental_confirmation: 0-1
        - derivatives_structure: 0-1
    lookahead_flag: bool (must be False)
```

**Output Contract**:
```python
class RPMPrediction:
    timestamp: datetime
    asset: str
    predicted_direction: Literal["LONG", "NEUTRAL", "SHORT"]
    predicted_return_pct: float (in-period return forecast, NOT annualized)
    confidence: float (0-1)
    provenance: dict
        - model_version: str
        - feature_set_hash: str
        - train_period: (start_date, end_date)
        - lookback_days: int
```

**Constraints**:
- All scores normalized [0, 1]
- Timestamps must be <= observation window end
- No future data access (strict point-in-time)
- Train period must not overlap test period

### 2.2 Component Weights (Frozen)

| Component | Weight | Status |
|-----------|--------|--------|
| capital_flow | 25% | Frozen |
| relative_strength | 25% | Frozen |
| narrative_acceleration | 20% | Frozen |
| fundamental_confirmation | 20% | Frozen |
| derivatives_structure | 10% | Frozen |

**Weighting Formula**:
```
rpm_score = (
    0.25 * capital_flow +
    0.25 * relative_strength +
    0.20 * narrative_acceleration +
    0.20 * fundamental_confirmation +
    0.10 * derivatives_structure
)

predicted_direction = {
    "LONG" if rpm_score >= 0.60,
    "NEUTRAL" if 0.40 <= rpm_score < 0.60,
    "SHORT" if rpm_score < 0.40
}
```

### 2.3 Lookback Window (Frozen)

**Lookback period**: 60 calendar days

**Justification**: Captures medium-term capital rotation cycles without seasonal noise.

**Constraint**: Feature store queries must use `retrieve_features(..., lookback=timedelta(days=60))`.

---

## 3. Dataset Contract

### 3.1 Data Source (Frozen)

| Source | Metric | Frequency | Status |
|--------|--------|-----------|--------|
| CoinGecko | OHLCV | Daily | Primary |
| Glassnode | On-Chain Flow | Daily | Secondary |
| CryptoQuant | Funding Rates | 8h | Secondary |
| DefiLlama | TVL | Daily | Secondary |
| Nansen | Whale Movements | Daily | Secondary |

### 3.2 Asset Universe (Frozen)

**Primary assets**: BTC, ETH  
**Secondary assets**: SOL, AVAX, MATIC (if data complete)

**Inclusion rule**: Must have >= 95% data availability in the period.

### 3.3 Time Period (Frozen)

**Full dataset period**: 2021-01-01 to 2026-09-25

**WFV test period**: 2023-01-01 to 2026-09-25 (only this period is walk-forward tested)

**Reason**: 2021-2022 reserved for initial model development/calibration (not in WFV).

### 3.4 Timestamp Validation (Mandatory)

Before WFV execution, validate:
- All timestamps are UTC
- No gaps > 1 day in OHLCV data
- Timestamps strictly ordered (ascending)
- No duplicates within asset+metric

---

## 4. Walk-Forward Validation Protocol

### 4.1 Window Configuration (Frozen)

**19 Windows** spanning 2023-01-01 to 2026-09-25 (1,369 days)

| Window | Train Start | Train End | Test Start | Test End | Days |
|--------|-------------|-----------|-----------|---------|------|
| W1 | 2021-01-01 | 2022-12-31 | 2023-01-01 | 2023-03-31 | 90 |
| W2 | 2021-01-01 | 2023-03-31 | 2023-04-01 | 2023-06-30 | 91 |
| W3 | 2021-01-01 | 2023-06-30 | 2023-07-01 | 2023-09-30 | 92 |
| ... | ... | ... | ... | ... | ... |
| W19 | 2021-01-01 | 2026-06-30 | 2026-07-01 | 2026-09-25 | 87 |

**Rules**:
- Train period: 2+ years rolling history (frozen on each window)
- Test period: 90 days (±1 day due to calendar)
- No overlap: train_end < test_start
- Expanding window: train set grows, test set fixed at ~90d

### 4.2 Train Phase (Per Window)

**Task**: Fit RPM/RCM parameters using only train period data.

**Allowed optimizations**:
- Hyperparameter search (grid or Optuna)
- Feature selection from predefined set
- Threshold optimization for direction classification

**Forbidden**:
- Adding new features
- Changing component weights (use frozen weights in 2.2)
- Look-ahead to test period
- Regime-based filtering

**Output per window**:
```python
window_model = {
    "window_id": "W1",
    "train_period": ("2021-01-01", "2022-12-31"),
    "model_params": {...},  # hyperparameters
    "feature_importance": {...},
    "train_metrics": {
        "ic": float,
        "sharpe": float,
        "max_drawdown": float,
    }
}
```

### 4.3 Test Phase (Per Window)

**Task**: Generate RPM predictions for test period using trained model.

**Protocol**:
1. For each day in test period:
   a. Use data up to that day only (strict point-in-time)
   b. Apply 60-day lookback window
   c. Call RPM/RCM(lookback_data) → prediction
   d. Store prediction with timestamp and actual return
   
2. Calculate metrics for the window:
   - IC (Information Coefficient)
   - HR (Hit Rate)
   - Period return
   - Sharpe ratio
   - Max drawdown

**Constraint**: No retraining during test (frozen model from train phase).

### 4.4 No Regime Pre-Filtering (Mandatory)

**During WFV, do NOT**:
- Separate Bull/Bear markets
- Filter by volatility regime
- Filter by macro conditions
- Apply regime-specific thresholds

**Justification**: WFV must test strategy on FULL distribution. Regime-based stratification happens ONLY post-hoc.

---

## 5. Metric Definitions (Frozen)

### 5.1 Information Coefficient (IC)

**Definition**: Spearman correlation between predicted direction and realized return direction.

**Calculation**:
```python
def calculate_ic(predictions: list[RPMPrediction], actuals: list[float]) -> float:
    predicted_signs = [1 if p.predicted_return_pct > 0 else -1 for p in predictions]
    actual_signs = [1 if a > 0 else -1 for a in actuals]
    ic = spearman_correlation(predicted_signs, actual_signs)
    return ic
```

**Range**: [-1, 1]
- IC > 0: strategy has predictive power
- IC = 0: no correlation
- IC < 0: reverse prediction

**Threshold (Frozen)**: IC_mean ≥ 0.05 per window (aggregate across 19 windows)

### 5.2 Hit Rate (HR)

**Definition**: Percentage of predictions with correct directional sign.

**Calculation**:
```python
def calculate_hr(predictions: list[RPMPrediction], actuals: list[float]) -> float:
    correct = sum(
        1 for p, a in zip(predictions, actuals)
        if (p.predicted_direction == "LONG" and a > 0) or
           (p.predicted_direction == "SHORT" and a < 0) or
           (p.predicted_direction == "NEUTRAL" and abs(a) <= 0.5)
    )
    hr = correct / len(predictions)
    return hr
```

**Range**: [0, 1]
- HR = 0.5: random chance
- HR > 0.5: better than random
- HR > 0.55: consistently valuable signal

**Threshold (Frozen)**: HR_mean ≥ 0.52 per window (aggregate)

### 5.3 Stability (Coefficient of Variation)

**Definition**: Measure of consistency: lower = more stable.

**Calculation**:
```python
def calculate_stability(window_metrics: list[dict]) -> float:
    ics = [w["ic"] for w in window_metrics]
    hrs = [w["hr"] for w in window_metrics]
    
    ic_cv = std(ics) / (abs(mean(ics)) + 1e-6)
    hr_cv = std(hrs) / mean(hrs)
    
    stability = (ic_cv + hr_cv) / 2
    return stability
```

**Range**: [0, ∞)
- Stability < 0.50: high consistency across windows
- Stability 0.50-1.00: moderate variation
- Stability > 1.00: highly inconsistent

**Threshold (Frozen)**: Stability ≤ 0.75 (no extreme volatility across windows)

---

## 6. Pass/Fail Criteria (Frozen)

### 6.1 Gate Definitions

```
Gate ΔIC:
  ΔIC = IC_mean - 0.00 (null hypothesis: no signal)
  PASS if ΔIC ≥ 0.05
  FAIL otherwise

Gate HR:
  HR_mean across 19 windows
  PASS if HR_mean ≥ 0.52
  FAIL otherwise

Gate Stability:
  Coefficient of Variation of IC and HR across windows
  PASS if Stability ≤ 0.75
  FAIL otherwise
```

### 6.2 Official B-004 Verdict

```
B-004 VERDICT = PASS only if:
  Gate ΔIC = PASS AND
  Gate HR = PASS AND
  Gate Stability = PASS

Otherwise: B-004 = FAIL
```

---

## 7. Anti-Lookahead Rules (Mandatory)

### 7.1 Point-in-Time Constraints

**Every prediction must satisfy**:
1. `prediction.timestamp <= test_period.end`
2. `lookback_start = prediction.timestamp - 60 days`
3. Features used: `feature_store.retrieve_features(start=lookback_start, end=prediction.timestamp)`
4. No access to: future OHLCV, future on-chain data, future news/narrative

### 7.2 Validation

**Before WFV execution**:
- Audit feature retrieval timestamps
- Verify no test data appears in train features
- Cross-check prediction.timestamp vs feature timestamps

**During WFV**:
- Log feature source timestamps
- Assert `feature_timestamp <= prediction_timestamp`

**Post-WFV**:
- Generate anti-lookahead report with sample predictions and their source data

---

## 8. Cost & Transaction Model (Frozen)

### 8.1 Trading Costs (Optional, if applicable)

If B-004 includes simulated P&L:
- Taker fee: 0.1% per trade (representative of Binance)
- Slippage: 0.05% (mid-price execution)
- No borrowing costs (spot trading only)

### 8.2 Signal-to-Trade Mapping

**Assumption**: Every RPM prediction translates to a trade attempt.
- LONG → buy at close-of-day
- SHORT → sell (or short if leverage allowed)
- NEUTRAL → no trade (hold)

**Capital allocation**: 10% of portfolio per trade (no leverage).

---

## 9. Protocol for Freeze & Reporting

### 9.1 Execution Sequence

1. **Load data** → validate timestamps and completeness
2. **Window W1 train** → fit model on 2021-01-01 to 2022-12-31
3. **Window W1 test** → generate predictions on 2023-01-01 to 2023-03-31
4. **Calculate W1 IC, HR, Sharpe**
5. **Repeat for W2 through W19**
6. **Aggregate metrics across all 19 windows**
7. **Freeze results** (no modification, no regime stratification yet)
8. **Evaluate gates** (ΔIC, HR, Stability)
9. **Return official verdict**

### 9.2 Output Format (Frozen)

```
B-004 VALIDATION REPORT
═══════════════════════════════════════════════════════════

Dataset
  Period: 2023-01-01 to 2026-09-25
  Assets: BTC, ETH (+ SOL, AVAX, MATIC if complete)
  Lookback: 60 days
  Train period: 2021-01-01 to 2026-06-30 (expanding)

WFV Windows: 19/19
  W1:  [2021-01-01, 2022-12-31] train | [2023-01-01, 2023-03-31] test
  W2:  [2021-01-01, 2023-03-31] train | [2023-04-01, 2023-06-30] test
  ...
  W19: [2021-01-01, 2026-06-30] train | [2026-07-01, 2026-09-25] test

METRICS (Aggregate across 19 windows)
  ΔIC:         [value]    | Gate: PASS/FAIL
  IC_mean:     [value]    | Threshold: ≥ 0.05
  IC_std:      [value]    | (for stability tracking)
  
  HR:          [value]    | Gate: PASS/FAIL
  HR_mean:     [value]    | Threshold: ≥ 0.52
  HR_std:      [value]    | (for stability tracking)
  
  Stability:   [value]    | Gate: PASS/FAIL
  CV(IC):      [value]    | Threshold: ≤ 0.75
  CV(HR):      [value]    |
  
OFFICIAL B-004 VERDICT: [PASS / FAIL]

═══════════════════════════════════════════════════════════

Post-hoc Analysis (EXPLORATORY ONLY, not part of verdict)
  Bull vs Bear stratification: [separate section]
  Regime analysis: [separate section]
  Temporal stability: [separate section]

PRODUCTION STATUS: [BLOCKED until verdict = PASS]
Layer 8 DASHBOARD: [BLOCKED]
```

### 9.3 Freeze Protocol

**Once metrics are calculated**:
1. Lock results file (checksum hash)
2. Do NOT modify numbers based on regime inspection
3. Do NOT re-run with different gates
4. Publish frozen results first
5. Then perform exploratory post-hoc analysis (clearly labeled as exploratory)

---

## 10. Post-Hoc Analysis (Exploratory Only)

### 10.1 Analysis Types (NOT part of official verdict)

**Bull Market Analysis**:
- Filter to periods where BTC close > 200-day MA
- Re-calculate IC, HR for Bull subset
- Compare vs all-market metrics

**Bear Market Analysis**:
- Filter to periods where BTC close < 200-day MA
- Re-calculate IC, HR for Bear subset
- Compare vs all-market metrics

**Regime Stability**:
- Split by volatility quartiles
- IC/HR per quartile
- Identify if model is regime-dependent

**Temporal Consistency**:
- IC/HR by half-year
- Visual inspection for degradation

### 10.2 Constraints

**These analyses**:
- Cannot modify the official verdict
- Cannot be used to justify post-hoc gating
- Cannot retroactively change model parameters
- Must be clearly marked as "exploratory"

---

## 11. Success Criteria (Frozen)

| Criterion | Required | Status |
|-----------|----------|--------|
| Dataset complete | Yes | TBD (validation phase) |
| 19 windows executed | Yes | TBD |
| No lookahead detected | Yes | TBD (audit phase) |
| ΔIC ≥ 0.05 | Yes | TBD (gate) |
| HR ≥ 0.52 | Yes | TBD (gate) |
| Stability ≤ 0.75 | Yes | TBD (gate) |
| All 3 gates PASS | Yes | TBD (verdict) |

---

## 12. Governance & Sign-Off

**Specification frozen by**: Claude Haiku 4.5  
**Date frozen**: 2026-09-25  
**Authorization**: Phase 2.1 Gate PASS → B-004 GO

**Next step**: Owner validation of this spec before RPM/RCM implementation begins.

**No implementation, testing, or WFV execution proceeds until owner confirms spec is correct and complete.**

---

## Appendix: Window Boundaries (Reference)

```
Window | Train Start | Train End | Test Start | Test End | Test Days
W1     | 2021-01-01  | 2022-12-31| 2023-01-01 | 2023-03-31| 90
W2     | 2021-01-01  | 2023-03-31| 2023-04-01 | 2023-06-30| 91
W3     | 2021-01-01  | 2023-06-30| 2023-07-01 | 2023-09-30| 92
W4     | 2021-01-01  | 2023-09-30| 2023-10-01 | 2023-12-31| 92
W5     | 2021-01-01  | 2023-12-31| 2024-01-01 | 2024-03-31| 91
W6     | 2021-01-01  | 2024-03-31| 2024-04-01 | 2024-06-30| 91
W7     | 2021-01-01  | 2024-06-30| 2024-07-01 | 2024-09-30| 92
W8     | 2021-01-01  | 2024-09-30| 2024-10-01 | 2024-12-31| 92
W9     | 2021-01-01  | 2024-12-31| 2025-01-01 | 2025-03-31| 90
W10    | 2021-01-01  | 2025-03-31| 2025-04-01 | 2025-06-30| 91
W11    | 2021-01-01  | 2025-06-30| 2025-07-01 | 2025-09-30| 92
W12    | 2021-01-01  | 2025-09-30| 2025-10-01 | 2025-12-31| 92
W13    | 2021-01-01  | 2025-12-31| 2026-01-01 | 2026-03-31| 90
W14    | 2021-01-01  | 2026-03-31| 2026-04-01 | 2026-06-30| 91
W15    | 2021-01-01  | 2026-06-30| 2026-07-01 | 2026-09-25| 87
```

(Note: Windows 16-19 pending schedule confirmation)

---

**END OF SPECIFICATION**

Status: FROZEN — Ready for Owner Validation
