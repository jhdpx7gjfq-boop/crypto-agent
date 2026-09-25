# Phase 3: Walk-Forward Validation (PIT/OOS/WFV) Specification
**IGWT-PF26 RRP Alpha Validation**

**Phase:** 3 of 7  
**Sub-Phases:** 3a (PIT) | 3b (OOS) | 3c (WFV)  
**Timeline:** Oct 23 - Nov 20, 2026 (4 weeks)  
**Predecessor:** Phase 2 Ground Truth Freeze ✅ REQUIRED  
**Successor:** Phase 4 Ablation Analysis  
**Input:** Immutable ground truth snapshot from Phase 2  
**Output:** RRP performance metrics (AUC, calibration, stability)  
**Authority:** Human approval required at each gate  

---

## Executive Summary

Walk-forward validation tests RRP predictive power across three distinct time windows:

1. **Phase 3a: PIT (In-Sample)** — RRP performance on training data (2020-2024)
2. **Phase 3b: OOS (Out-of-Sample)** — RRP performance on held-out data (2025-2026)
3. **Phase 3c: WFV (Walk-Forward)** — RRP stability in forward simulation (rolling validation)

**Core Principle:** Baseline is pre-registered. Performance must exceed it to proceed.

---

## Locked Pre-Registration (Phase 0)

### Baseline Methodology (Q6 - LOCKED)
```
Random Classifier Baseline:
  - Method: Predict resurrection probability = base rate in training set
  - Distribution: Use actual dormant/resurrected split from ground truth
  - Metric: AUC (area under ROC curve)
  - Pre-registered: Before any backtest execution
  
Acceptance Threshold:
  AUC(RRP) > AUC(baseline) + 0.10
```

### Tolerances (Q7 - LOCKED)
```
OOS Degradation: ≤ 0.12 (PIT to OOS)
WFV Variance:    ± 0.08 (rolling window stability)
CI Width:        ≤ 0.10 (confidence interval bound)
```

---

## 1. Phase 3a: In-Sample (PIT) Backtest

### 1.1 Objective

Verify RRP implementation works correctly on historical data. Establish in-sample performance ceiling (before OOS testing).

### 1.2 Setup

**Historical Window:** 2020-01-01 to 2024-12-31 (5 years)

**Input Data:**
- Ground truth labels (dormant/resurrected from Phase 2)
- OHLCV data (from Phase 1 snapshot)
- RRP component scores (calculated from feature store)
- Feature snapshots (volume, momentum, narrative, etc.)

**Test Design:**
```
For each coin with dormant_date T0 in [2020-2024]:
  1. Snapshot RRP score at T0 (day dormancy detected)
  2. Actual outcome: resurrected yes/no within T0+180 days
  3. Record: (coin_id, RRP_score, actual_outcome)

Aggregate: AUC, calibration, confidence interval
```

### 1.3 Execution Steps

**Step 1: Calculate Baseline AUC**

```python
ground_truth = load_frozen_gt("rrp_alpha_p2_gt_2026-10-23")
dormant_coins = [coin for coin in ground_truth if coin.dormant]

# Base rate in training set
resurrections = len([coin for coin in dormant_coins if coin.resurrected])
total_dormant = len(dormant_coins)
base_rate = resurrections / total_dormant

# Baseline predictions: all coins get base_rate probability
baseline_predictions = [base_rate] * total_dormant
baseline_outcomes = [coin.resurrected for coin in dormant_coins]

# Pre-registered baseline
from sklearn.metrics import roc_auc_score
AUC_baseline = roc_auc_score(baseline_outcomes, baseline_predictions)

# Document pre-registration
print(f"PRE-REGISTERED BASELINE: AUC = {AUC_baseline:.4f}")
print(f"REQUIRED THRESHOLD: AUC > {AUC_baseline + 0.10:.4f}")
```

**Step 2: Run RRP Backtest (PIT)**

```python
# Calculate RRP score for each dormant coin at T0
rrp_scores = []
actual_outcomes = []

for coin in dormant_coins:
    T0 = coin.dormant_start
    
    # Get RRP components at T0
    volume_trend = calculate_volume_trend(coin, T0)
    narrative_score = calculate_narrative_score(coin, T0)
    capital_flow = calculate_capital_flow(coin, T0)
    momentum = calculate_momentum(coin, T0)
    
    # Combine into RRP score (0-100)
    rrp_score = combine_rrp_components(
        volume_trend, narrative_score, capital_flow, momentum
    )
    
    rrp_scores.append(rrp_score)
    actual_outcomes.append(coin.resurrected)

# Calculate PIT performance
AUC_pit = roc_auc_score(actual_outcomes, rrp_scores)
precision, recall, threshold = precision_recall_curve(actual_outcomes, rrp_scores)
```

**Step 3: Validate Against Baseline**

```python
AUC_delta = AUC_pit - AUC_baseline

if AUC_delta >= 0.10:
    print(f"✅ PASS: AUC improvement = {AUC_delta:.4f} (required ≥0.10)")
    pit_status = "PASS"
else:
    print(f"❌ FAIL: AUC improvement = {AUC_delta:.4f} (required ≥0.10)")
    pit_status = "FAIL"
```

### 1.4 PIT Acceptance Criteria

All of the following must be TRUE:

✅ **Performance vs Baseline:** AUC(RRP) > AUC(baseline) + 0.10  
✅ **Calibration:** Monotonic increasing (higher scores → higher actual rate)  
✅ **Minimum Performance:** AUC ≥ 0.60 (statistical significance floor)  
✅ **Stability:** Score distribution normal or bimodal (no extreme outliers)  
✅ **Documentation:** Backtest code + output + assumptions recorded  

**If FAIL:** Debug RRP logic, return to Phase 2 data review, or redesign components.

---

## 2. Phase 3b: Out-of-Sample (OOS) Validation

### 2.1 Objective

Test RRP on held-out data to measure generalization. Detect overfitting.

### 2.2 Setup

**Held-Out Window:** 2025-01-01 to 2026-09-25 (OOS data, not seen during design)

**Note:** RRP components were calibrated on 2020-2024. OOS tests prediction quality on recent data.

### 2.3 Execution Steps

**Step 1: Identify OOS Dormant Coins**

```python
ground_truth = load_frozen_gt("rrp_alpha_p2_gt_2026-10-23")

# Find coins that became dormant in OOS period (2025-2026)
# But only if observation window completed by now (2026-09-25)
oos_dormant_coins = [
    coin for coin in ground_truth 
    if coin.dormant_start >= "2025-01-01" 
    and coin.dormant_start <= "2026-03-25"  # Allows ≥180 day observation
]

print(f"OOS dormant coins: {len(oos_dormant_coins)}")
```

**Step 2: Calculate RRP Scores (OOS)**

```python
oos_rrp_scores = []
oos_actual_outcomes = []

for coin in oos_dormant_coins:
    T0 = coin.dormant_start
    
    # Use SAME RRP logic as PIT, but on 2025-2026 data
    # Components are recalculated (not retuned)
    rrp_score = calculate_rrp_score(coin, T0)  # Same method as PIT
    
    oos_rrp_scores.append(rrp_score)
    oos_actual_outcomes.append(coin.resurrected)
```

**Step 3: Measure OOS Performance**

```python
AUC_oos = roc_auc_score(oos_actual_outcomes, oos_rrp_scores)

# Measure degradation
AUC_degradation = AUC_pit - AUC_oos

if AUC_degradation <= 0.12:  # Q7 tolerance
    print(f"✅ PASS: OOS degradation = {AUC_degradation:.4f} (tolerance ≤0.12)")
    oos_status = "PASS"
else:
    print(f"❌ FAIL: OOS degradation = {AUC_degradation:.4f} (tolerance ≤0.12)")
    oos_status = "FAIL"

print(f"PIT: {AUC_pit:.4f}, OOS: {AUC_oos:.4f}, Degradation: {AUC_degradation:.4f}")
```

### 2.4 OOS Acceptance Criteria

✅ **Degradation Control:** AUC(PIT) - AUC(OOS) ≤ 0.12  
✅ **Minimum OOS Performance:** AUC(OOS) ≥ AUC(baseline) + 0.08  
✅ **Stability:** Similar ranking of coins PIT vs OOS (Spearman corr ≥ 0.65)  
✅ **No Systemic Bias:** No consistent over/under-prediction by season or market regime  

**If FAIL:** Overfitting suspected, return to Phase 2 or redesign components.

---

## 3. Phase 3c: Walk-Forward Validation (WFV)

### 3.1 Objective

Simulate rolling-window deployment to test forward stability. Answer: "Does this hold up in continuous deployment?"

### 3.2 Setup

**Rolling Windows:** 5 iterations of (train → test)

```
Window 1: Train 2020-2023, Test 2024-01
Window 2: Train 2020-2024, Test 2025-06
Window 3: Train 2020-2025, Test 2026-03
Window 4: Train 2020-2025H1, Test 2025H2-2026-03
Window 5: Train 2020-2025H2, Test 2026-01-2026-06
```

### 3.3 Execution Steps

**Step 1: Run 5 Walking Windows**

```python
windows = [
    {"train_end": "2023-12-31", "test_start": "2024-01-01", "test_end": "2024-06-30"},
    {"train_end": "2024-12-31", "test_start": "2025-01-01", "test_end": "2025-06-30"},
    {"train_end": "2025-06-30", "test_start": "2025-07-01", "test_end": "2025-12-31"},
    {"train_end": "2025-12-31", "test_start": "2026-01-01", "test_end": "2026-03-31"},
    {"train_end": "2026-03-31", "test_start": "2026-04-01", "test_end": "2026-09-25"},
]

wfv_results = []

for i, window in enumerate(windows):
    # Train on historical data up to train_end
    train_coins = get_dormant_coins(up_to=window["train_end"])
    # Component recalibration (if needed) on train window
    
    # Test on test window
    test_coins = get_dormant_coins(
        start=window["test_start"], 
        end=window["test_end"]
    )
    
    # Calculate RRP scores & performance
    test_scores = [calculate_rrp_score(coin, coin.dormant_start) for coin in test_coins]
    test_outcomes = [coin.resurrected for coin in test_coins]
    
    auc_window = roc_auc_score(test_outcomes, test_scores)
    wfv_results.append({
        "window": i+1,
        "train_end": window["train_end"],
        "test_period": f"{window['test_start']} to {window['test_end']}",
        "auc": auc_window
    })
    
    print(f"Window {i+1}: AUC = {auc_window:.4f}")
```

**Step 2: Measure Stability**

```python
wfv_aucs = [r["auc"] for r in wfv_results]
wfv_mean = np.mean(wfv_aucs)
wfv_std = np.std(wfv_aucs)
wfv_min = np.min(wfv_aucs)
wfv_max = np.max(wfv_aucs)
wfv_variance = wfv_max - wfv_min

print(f"WFV Mean AUC: {wfv_mean:.4f}")
print(f"WFV Std Dev:  {wfv_std:.4f}")
print(f"WFV Range:    {wfv_min:.4f} to {wfv_max:.4f}")
print(f"WFV Variance: ±{wfv_variance/2:.4f}")

if wfv_variance <= 0.16:  # Q7 tolerance ±0.08
    print(f"✅ PASS: WFV variance = ±{wfv_variance/2:.4f} (tolerance ±0.08)")
    wfv_status = "PASS"
else:
    print(f"❌ FAIL: WFV variance = ±{wfv_variance/2:.4f} (tolerance ±0.08)")
    wfv_status = "FAIL"
```

### 3.4 WFV Acceptance Criteria

✅ **Stability:** AUC variance ≤ ±0.08 across 5 windows  
✅ **Minimum Performance:** All windows AUC ≥ AUC(baseline) + 0.05  
✅ **No Trend:** No significant decline over time (slope test p > 0.05)  
✅ **Consistency:** 4 of 5 windows within ±0.10 of mean  

**If FAIL:** Deployment stability at risk, return to component redesign.

---

## 4. Phase 3 Reporting

### 4.1 Walk-Forward Validation Report

```
PHASE 3 WALK-FORWARD VALIDATION REPORT
Generated: 2026-11-20
Test Period: Oct 23 - Nov 20, 2026
Ground Truth: rrp_alpha_p2_gt_2026-10-23 (FROZEN)

═══════════════════════════════════════════════════════════════

EXECUTIVE SUMMARY
─────────────────
Status: [PASS | FAIL]
RRP Performance: [Exceed | Meet | Below] baseline by [ΔAUCs]

PIT Result:  AUC = [0.XX]
OOS Result:  AUC = [0.XX] (degradation ±[0.XX])
WFV Result:  Mean AUC = [0.XX] ± [0.XX]

═══════════════════════════════════════════════════════════════

1. PRE-REGISTRATION AUDIT

Baseline (Q6):
  Method: Random classifier (base rate prediction)
  AUC: 0.XXXX (calculated from ground truth)
  Threshold: AUC(RRP) > 0.XXXX + 0.10 = 0.XXXX

Locked Tolerances (Q7):
  OOS degradation: ≤0.12
  WFV variance: ±0.08
  CI width: ≤0.10

═══════════════════════════════════════════════════════════════

2. PHASE 3a: IN-SAMPLE (PIT) RESULTS

Dataset:
  Dormant coins: [N]
  Observation period: 2020-2024
  Resurrections: [M] ([M/N]%)

Performance Metrics:
  AUC:           0.XXXX
  Precision:     0.XXXX (at threshold 50)
  Recall:        0.XXXX
  F1 Score:      0.XXXX
  Calibration R²: 0.XXXX

vs Baseline:
  AUC improvement: ΔAUCs
  Status: [✅ PASS | ❌ FAIL]

═══════════════════════════════════════════════════════════════

3. PHASE 3b: OUT-OF-SAMPLE (OOS) RESULTS

Dataset:
  Dormant coins (2025-2026): [N]
  Observation period: 2025-2026
  Resurrections: [M] ([M/N]%)

Performance Metrics:
  AUC:           0.XXXX
  Degradation:   0.XXXX (PIT→OOS)
  Status: [✅ PASS ≤0.12 | ❌ FAIL >0.12]

Generalization:
  Spearman correlation (PIT ranking vs OOS): 0.XXXX
  Bias analysis: [No systematic bias | Bias detected]

═══════════════════════════════════════════════════════════════

4. PHASE 3c: WALK-FORWARD VALIDATION (WFV) RESULTS

5-Window Rolling Test:

Window | Train End    | Test Period      | AUC    | vs Baseline
─────────────────────────────────────────────────────────────
  1    | 2023-12-31   | 2024-01 to 06    | 0.XXXX | +0.XXXX
  2    | 2024-12-31   | 2025-01 to 06    | 0.XXXX | +0.XXXX
  3    | 2025-06-30   | 2025-07 to 12    | 0.XXXX | +0.XXXX
  4    | 2025-12-31   | 2026-01 to 03    | 0.XXXX | +0.XXXX
  5    | 2026-03-31   | 2026-04 to 09    | 0.XXXX | +0.XXXX
─────────────────────────────────────────────────────────────
Mean:                                     0.XXXX | +0.XXXX
Std Dev:                                  0.XXXX |
Range:                                    ±0.XXXX |
Status:                                   [✅ PASS | ❌ FAIL]

Stability Analysis:
  Variance: ±0.XXXX (target ±0.08)
  Trend: [No trend detected | Declining/improving trend]
  Consistency: [N]/5 windows within ±0.10

═══════════════════════════════════════════════════════════════

5. GATE APPROVAL

Phase 3 Gate Requirements (ALL REQUIRED):
  [✅ or ❌] Phase 3a PIT: AUC > baseline + 0.10
  [✅ or ❌] Phase 3b OOS: Degradation ≤ 0.12
  [✅ or ❌] Phase 3c WFV: Variance ≤ ±0.08
  [✅ or ❌] All windows: AUC ≥ baseline + 0.05

═══════════════════════════════════════════════════════════════

HUMAN SIGN-OFF

Reviewed By: ____________________
Title: Data Scientist / Human Authority
Date: ____________________
Comments: ____________________

═══════════════════════════════════════════════════════════════

GATE DECISION: [ ] PASS → Phase 4 | [ ] FAIL → Debug & Rework
```

---

## 5. Phase 3 Success Criteria

All of the following must be TRUE:

✅ **PIT Baseline Delta** ≥ 0.10  
✅ **OOS Degradation** ≤ 0.12  
✅ **WFV Stability** ≤ ±0.08 variance  
✅ **Minimum Performance** All windows ≥ baseline + 0.05  
✅ **Documentation** Code + outputs + assumptions recorded  

**If ANY criterion fails:** Return to component debugging, data review, or methodology redesign.

---

## 6. Phase 3 Timeline

```
Oct 23 | Phase 3a PIT backtest execution
Oct 28 | PIT complete, baseline calculated
Oct 31 | Phase 3b OOS validation execution
Nov 10 | OOS complete, degradation measured
Nov 13 | Phase 3c WFV rolling windows
Nov 17 | WFV complete, stability measured
Nov 18 | Report generated, human review
Nov 20 | Gate decision: PASS → Phase 4 or FAIL → Rework
```

---

## 7. Risk Mitigation

### Risk: AUC < Baseline + 0.10 (No Information Advantage)

**Mitigation:**
- RRP components are additive (can debug individually)
- Phase 4 ablation will show which components fail
- Fallback: Extend Phase 1 to include additional data sources
- Last resort: Redesign RRP component logic (return to Phases 1-2)

### Risk: OOS Degradation > 0.12 (Overfitting)

**Mitigation:**
- WFV will confirm if degradation is consistent or isolated
- Component review in Phase 4 (which components overfit?)
- Data review: Check for lookahead bias in feature calculation
- Possible fix: Regularize component scoring or reduce feature dimensionality

### Risk: WFV Variance > ±0.08 (Instability)

**Mitigation:**
- Analyze which windows fail (seasonal effect?)
- Check for regime change (bull vs bear market)
- Phase 5 robustness analysis will stratify by market condition
- Possible fix: Add market regime detector to RRP scoring

---

## Deliverables (Phase 3 Completion)

1. **PIT Backtest Results** (code + outputs)
2. **OOS Validation Results** (code + outputs)
3. **WFV Rolling Window Results** (5 windows documented)
4. **Baseline Pre-Registration** (AUC + threshold documented)
5. **Performance Comparison** (RRP vs baseline, all metrics)
6. **Stability Analysis** (degradation + variance quantified)
7. **Walk-Forward Validation Report** (PASS/FAIL gate decision)
8. **Human Approval Sign-Off** (Data Scientist + Authority)

---

**Built:** 2026-09-25  
**Phase:** 3 of 7  
**Status:** Ready for Oct 23 Execution  
**Authority:** Human approval required at gate completion  
**Downstream:** Phase 4 Ablation Analysis (begins upon Phase 3 PASS)
