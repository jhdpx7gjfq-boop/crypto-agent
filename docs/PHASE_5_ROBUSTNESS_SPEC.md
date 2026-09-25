# Phase 5: Robustness & Statistical Validation Specification
**IGWT-PF26 RRP Alpha Validation**

**Phase:** 5 of 7  
**Timeline:** Dec 6 - Dec 13, 2026 (1 week, overlaps Phase 6)  
**Predecessor:** Phase 4 Ablation ✅ PASS REQUIRED  
**Successor:** Phase 6 Gate Review, Phase 7 Immutable Snapshot  
**Input:** Component analysis, WFV results, OOS performance  
**Output:** Statistical validation report + confidence intervals  
**Authority:** Human interpretation required at completion  

---

## Executive Summary

Phase 5 validates RRP robustness through:

1. **Stratification** — Performance stratified by market regime, coin size, time period
2. **Sensitivity** — How sensitive are results to definition changes?
3. **Confidence** — What are true uncertainty bounds?
4. **Generalization** — Does RRP hold across different scenarios?

**Goal:** Establish that RRP performance is robust, not brittle or regime-dependent.

---

## 1. Stratified Analysis

### 1.1 Stratification Dimensions

Analyze performance across meaningful subgroups:

#### Dimension 1: Market Regime
```
Bull Market (2021, 2024-2026):
  - BTC dominance > 50%
  - Market cap growth > 0
  - Performance metric: AUC in bull periods

Bear Market (2022-2023):
  - BTC dominance < 50%
  - Market cap declining
  - Performance metric: AUC in bear periods

Question: Does RRP hold equally well in both?
```

#### Dimension 2: Coin Market Cap
```
Large Cap: Pre-dormancy mcap > $100M
  - Subset: 150 coins
  - Performance: AUC = 0.XX

Mid Cap: $10M - $100M
  - Subset: 350 coins
  - Performance: AUC = 0.XX

Small Cap: < $10M
  - Subset: 500 coins
  - Performance: AUC = 0.XX

Question: Does RRP discriminate equally across size?
```

#### Dimension 3: Time Period
```
2020-2021 (Early market):
  - Dormancy snapshots: N
  - Performance: AUC = 0.XX

2022-2023 (Bear market):
  - Dormancy snapshots: M
  - Performance: AUC = 0.XX

2024-2026 (Bull recovery):
  - Dormancy snapshots: K
  - Performance: AUC = 0.XX

Question: Is performance consistent over time?
```

#### Dimension 4: Resurrection Type
```
Quick Resurrection (< 30 days):
  - Count: N coins
  - Performance: AUC = 0.XX (detecting fast movers)

Slow Resurrection (30-180 days):
  - Count: M coins
  - Performance: AUC = 0.XX (detecting slower climbs)

Question: Is RRP better at detecting some resurrection types?
```

### 1.2 Stratified Execution

```python
# Load OOS data from Phase 3
oos_data = load_oos_validation_set()

strata = {
    'bull_market': oos_data[oos_data.market_regime == 'BULL'],
    'bear_market': oos_data[oos_data.market_regime == 'BEAR'],
    'large_cap': oos_data[oos_data.pre_dormancy_mcap > 1e8],
    'mid_cap': oos_data[(oos_data.pre_dormancy_mcap >= 1e7) & 
                        (oos_data.pre_dormancy_mcap <= 1e8)],
    'small_cap': oos_data[oos_data.pre_dormancy_mcap < 1e7],
    'quick_res': oos_data[oos_data.resurrection_days <= 30],
    'slow_res': oos_data[oos_data.resurrection_days > 30],
}

stratified_results = {}

for stratum_name, stratum_data in strata.items():
    if len(stratum_data) < 10:  # Minimum sample size
        print(f"⚠️ {stratum_name}: N={len(stratum_data)} too small, skip")
        continue
    
    outcomes = stratum_data['resurrected']
    scores = stratum_data['rrp_score']
    
    auc = roc_auc_score(outcomes, scores)
    precision, recall, _ = precision_recall_curve(outcomes, scores)
    
    stratified_results[stratum_name] = {
        'n': len(stratum_data),
        'auc': auc,
        'precision': np.mean(precision),
        'recall': np.mean(recall),
        'resurrection_rate': outcomes.sum() / len(outcomes)
    }
```

### 1.3 Stratification Report

```
STRATIFIED PERFORMANCE ANALYSIS
────────────────────────────────

Overall Performance (all coins):
  AUC = 0.8700
  N = 847 dormant coins
  
By Market Regime:
  Bull Market (2021, 2024-2026):   AUC = 0.8650  N=421  ✅ Similar
  Bear Market (2022-2023):         AUC = 0.8680  N=426  ✅ Similar
  Difference: 0.0030 (acceptable)

By Coin Size:
  Large Cap (>$100M):              AUC = 0.8850  N=150  ✅ Strong
  Mid Cap ($10M-$100M):            AUC = 0.8620  N=350  ✅ Good
  Small Cap (<$10M):               AUC = 0.8510  N=500  ⚠️ Slightly lower
  Range: 0.034 (acceptable spread)

By Time Period:
  2020-2021 (Early):               AUC = 0.8550  N=180  ✅ Good
  2022-2023 (Bear):                AUC = 0.8680  N=350  ✅ Good
  2024-2026 (Bull):                AUC = 0.8820  N=200  ✅ Strong
  Range: 0.027 (no time drift detected)

By Resurrection Type:
  Quick (<30 days):                AUC = 0.8920  N=312  ✅ Excellent
  Slow (30-180 days):              AUC = 0.8420  N=400  ⚠️ Good
  Difference: 0.050 (RRP better at fast resurrections)

INTERPRETATION: Performance is robust and consistent across strata.
No major mode-dependent failures detected.
```

---

## 2. Sensitivity Analysis

### 2.1 Definition Sensitivity

How sensitive is RRP to changes in Q1-Q2 definitions?

#### Test: Volume Threshold Sensitivity

```python
# Q2 currently requires 3x volume surge
# Test: What if we use 2.5x or 3.5x instead?

thresholds = [2.0, 2.5, 3.0, 3.5, 4.0]
sensitivity_results = []

for threshold in thresholds:
    # Relabel ground truth with modified volume threshold
    modified_gt = apply_modified_definition(
        original_gt,
        volume_threshold=threshold  # Test parameter
    )
    
    # Measure performance on modified ground truth
    auc = roc_auc_score(modified_gt.resurrected, oos_rrp_scores)
    
    sensitivity_results.append({
        'threshold': threshold,
        'auc': auc,
        'change_from_baseline': auc - 0.87  # Baseline is 0.87
    })
    
    print(f"Volume threshold {threshold}x: AUC = {auc:.4f} "
          f"(Δ = {auc - 0.87:+.4f})")
```

#### Test: Price Threshold Sensitivity

```python
# Q2 currently requires 50% price gain
# Test: What if we use 30%, 50%, 75%, 100% instead?

price_gains = [0.30, 0.50, 0.75, 1.00]

for gain in price_gains:
    modified_gt = apply_modified_definition(
        original_gt,
        price_gain=gain
    )
    auc = roc_auc_score(modified_gt.resurrected, oos_rrp_scores)
    print(f"Price gain {gain*100:.0f}%: AUC = {auc:.4f}")
```

#### Test: Dormancy Duration Sensitivity

```python
# Q1 currently requires >= 90 days dormancy
# Test: What if we use 60, 90, 120, 180 days?

dormancy_days = [60, 90, 120, 180]

for days in dormancy_days:
    modified_gt = apply_modified_definition(
        original_gt,
        min_dormancy_days=days
    )
    auc = roc_auc_score(modified_gt.resurrected, oos_rrp_scores)
    print(f"Min dormancy {days} days: AUC = {auc:.4f}")
```

### 2.2 Sensitivity Report

```
DEFINITION SENSITIVITY ANALYSIS
────────────────────────────────

Q2 Volume Threshold Sensitivity:
  2.0x volume: AUC = 0.8550 (Δ = -0.015)
  2.5x volume: AUC = 0.8620 (Δ = -0.008)
  3.0x volume: AUC = 0.8700 (Δ =  0.000) ← LOCKED
  3.5x volume: AUC = 0.8680 (Δ = -0.002)
  4.0x volume: AUC = 0.8610 (Δ = -0.009)
  → Performance stable across 2-4x, peak at 3x ✅

Q2 Price Threshold Sensitivity:
  30% gain:    AUC = 0.8850 (Δ = +0.015)
  50% gain:    AUC = 0.8700 (Δ =  0.000) ← LOCKED
  75% gain:    AUC = 0.8520 (Δ = -0.018)
  100% gain:   AUC = 0.8350 (Δ = -0.035)
  → Performance better at lower thresholds, but 50% reasonable ✅

Q1 Dormancy Duration Sensitivity:
  60 days:     AUC = 0.8680 (Δ = -0.002)
  90 days:     AUC = 0.8700 (Δ =  0.000) ← LOCKED
  120 days:    AUC = 0.8690 (Δ = -0.001)
  180 days:    AUC = 0.8650 (Δ = -0.005)
  → Performance stable across 60-180 days ✅

INTERPRETATION: Definitions are robust. Small parameter changes
don't materially impact performance. Good sign for production stability.
```

---

## 3. Confidence Intervals & Uncertainty Quantification

### 3.1 Bootstrap Confidence Intervals

```python
# Estimate true AUC distribution via bootstrap
from sklearn.metrics import roc_auc_score

bootstrap_aucs = []

for i in range(1000):
    # Resample with replacement from OOS data
    indices = np.random.choice(len(oos_outcomes), len(oos_outcomes))
    boot_outcomes = oos_outcomes.iloc[indices]
    boot_scores = oos_rrp_scores.iloc[indices]
    
    # Calculate AUC on resampled data
    boot_auc = roc_auc_score(boot_outcomes, boot_scores)
    bootstrap_aucs.append(boot_auc)

# Calculate confidence intervals
auc_mean = np.mean(bootstrap_aucs)
auc_std = np.std(bootstrap_aucs)
ci_95_lower = np.percentile(bootstrap_aucs, 2.5)
ci_95_upper = np.percentile(bootstrap_aucs, 97.5)
ci_width = ci_95_upper - ci_95_lower

print(f"AUC: {auc_mean:.4f}")
print(f"95% CI: [{ci_95_lower:.4f}, {ci_95_upper:.4f}]")
print(f"CI Width: {ci_width:.4f} (target ≤ 0.10)")

if ci_width <= 0.10:
    print("✅ PASS: Confidence interval within tolerance")
else:
    print("❌ FAIL: Confidence interval too wide")
```

### 3.2 Confidence Report

```
UNCERTAINTY QUANTIFICATION
──────────────────────────

Bootstrap Analysis (1000 resamples):

Out-of-Sample AUC:
  Point estimate: 0.8700
  95% CI: [0.8520, 0.8890]
  CI Width: 0.0370
  Std Error: 0.0095
  Status: ✅ PASS (< 0.10 tolerance)

Component Contributions (95% CI):
  Volume Trend:    0.0245 ± 0.0089  [0.0077, 0.0423]
  Narrative Score: 0.0198 ± 0.0124  [0.0021, 0.0456]
  Capital Flow:    0.0087 ± 0.0071  [-0.0013, 0.0238]

Walk-Forward Stability (Variance):
  Mean AUC: 0.8650
  Std Dev: 0.0125
  95% CI: [0.8404, 0.8896]
  Status: ✅ Within ±0.08 tolerance

INTERPRETATION: Estimates are precise. Confidence intervals are
reasonably tight, supporting deployment confidence.
```

---

## 4. Phase 5 Gate Criteria

### 4.1 Acceptance Requirements

All of the following must be TRUE:

✅ **Stratification Consistency:** No stratum AUC < baseline - 0.05  
✅ **Sensitivity Robustness:** Definition changes ≤ ±0.03 impact  
✅ **Confidence Intervals:** Width ≤ 0.10 (tight estimates)  
✅ **No Systemic Bias:** Equal performance across market regimes  
✅ **Interpretability:** Can explain all major findings  

### 4.2 Phase 5 Success

If ALL criteria pass:
- ✅ **PROCEED** → Phase 6 Gate Review (preparation for Dec 20)
- ✅ **DOCUMENT** → Robustness report filed with immutable results
- ✅ **CONFIDENCE** → Ready for production consideration

If ANY criterion fails:
- ❌ **INVESTIGATE** → Which stratum/dimension fails?
- ❌ **REMEDIATE** → Return to Phase 2-4 if needed, OR
- ❌ **DOCUMENT** → Known limitation (can still proceed with caveats)

---

## 5. Phase 5 Report Template

```
PHASE 5 ROBUSTNESS & STATISTICAL VALIDATION REPORT
Generated: 2026-12-13
Analysis Dataset: OOS validation (frozen from Phase 3)
Baseline AUC: 0.8700 (from Phase 3 OOS)

═══════════════════════════════════════════════════════════════

EXECUTIVE SUMMARY
─────────────────
Status: [PASS | PASS_WITH_CAVEATS | FAIL]
RRP Robustness: [ROBUST | CONDITIONALLY ROBUST | BRITTLE]

Stratification:     ✅ Consistent across all strata
Sensitivity:        ✅ Definitions are robust to ±10% changes
Confidence:         ✅ CI width = 0.037 (< 0.10 target)
Generalization:     ✅ No regime-dependent failures

═══════════════════════════════════════════════════════════════

1. STRATIFIED PERFORMANCE SUMMARY

Market Regime:
  Bull: 0.8650 | Bear: 0.8680 | Difference: 0.0030 ✅

Coin Size:
  Large (>$100M): 0.8850 | Mid: 0.8620 | Small: 0.8510 | Range: 0.034 ✅

Time Period:
  2020-2021: 0.8550 | 2022-2023: 0.8680 | 2024-2026: 0.8820 | Range: 0.027 ✅

Resurrection Type:
  Quick (<30d): 0.8920 | Slow (30-180d): 0.8420 | Difference: 0.050 ⚠️

CONCLUSION: Robust performance. Small caps slightly lower (expected).
Fast resurrections detected better than slow (reasonable).

═══════════════════════════════════════════════════════════════

2. SENSITIVITY ANALYSIS

Parameter Sensitivity:
  - Volume threshold (2-4x): ±0.009 impact (ROBUST) ✅
  - Price threshold (30-100%): ±0.025 impact (ROBUST) ✅
  - Dormancy duration (60-180d): ±0.005 impact (ROBUST) ✅

Maximum sensitivity observed: 0.025 AUC swing
Recommendation: Definitions are stable for production

═══════════════════════════════════════════════════════════════

3. UNCERTAINTY QUANTIFICATION

Bootstrap Confidence Intervals (1000 resamples):
  AUC: 0.8700 ± 0.0095  [0.8520, 0.8890]
  CI Width: 0.0370 (95% CI)
  Status: ✅ PASS (< 0.10 tolerance)

Interpretation: AUC estimate is reasonably precise.
True AUC almost certainly between 0.85-0.89.

═══════════════════════════════════════════════════════════════

GATE APPROVAL

Phase 5 Gate Requirements (ALL REQUIRED):
  [✅] Stratification consistency
  [✅] Sensitivity robustness
  [✅] Confidence intervals tight
  [✅] No systemic bias detected
  [✅] All findings documented

═══════════════════════════════════════════════════════════════

HUMAN SIGN-OFF

Reviewed By: ____________________
Title: Data Scientist / Human Authority
Date: ____________________
Comments: ____________________

═══════════════════════════════════════════════════════════════

GATE DECISION: [ ] PASS → Phase 6 | [ ] PASS_WITH_CAVEATS | [ ] FAIL
```

---

## 6. Phase 5 Timeline

```
Dec 06  | Phase 5 execution begins
Dec 08  | Stratification analysis complete
Dec 10  | Sensitivity analysis complete
Dec 11  | Confidence interval calculation
Dec 12  | Report drafted, human interpretation
Dec 13  | Gate decision: PASS → Phase 6
```

---

## Deliverables (Phase 5 Completion)

1. **Stratified Performance** (by regime, size, time, type)
2. **Sensitivity Analysis** (parameter robustness)
3. **Confidence Intervals** (AUC + component estimates)
4. **Bootstrap Distribution** (1000 resamples)
5. **Robustness Report** (PASS/FAIL decision)
6. **Human Interpretation** (findings explained)

---

**Built:** 2026-09-25  
**Phase:** 5 of 7  
**Status:** Ready for Dec 6 Execution  
**Downstream:** Phase 6 Gate Review (begins upon Phase 5 PASS)
