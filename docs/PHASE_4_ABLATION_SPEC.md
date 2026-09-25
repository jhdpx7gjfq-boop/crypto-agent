# Phase 4: Ablation & Component Analysis Specification
**IGWT-PF26 RRP Alpha Validation**

**Phase:** 4 of 7  
**Timeline:** Nov 20 - Dec 6, 2026 (2 weeks)  
**Predecessor:** Phase 3 Walk-Forward ✅ PASS REQUIRED  
**Successor:** Phase 5 Robustness Analysis  
**Input:** PIT/OOS/WFV results from Phase 3, Component scores  
**Output:** Component contribution analysis + refactoring guidance  
**Authority:** Human interpretation required at completion  

---

## Executive Summary

Ablation analysis decomposes RRP performance into component contributions:

**Question:** Which RRP components contribute meaningfully to resurrection detection?

**Method:** Leave-one-out (remove each component, measure performance drop)

**Output:** Ranked component importance + refactoring guidance for Phase 8 deployment

---

## 1. Ablation Experiment Design

### 1.1 RRP Component Structure

RRP combines N components (from Phase 7 implementation):

```python
Components:
  1. Volume Trend (0-100)
  2. Narrative Score (0-100)
  3. Capital Flow Index (0-100)
  4. Momentum Indicator (0-100)
  5. [Additional components if any]

Combined RRP Score = weighted_average(components)
```

### 1.2 Ablation Method: Leave-One-Out

**For each component:**

```
Step 1: Train/Test on ground truth with component INCLUDED
  AUC_full = current performance (from Phase 3)

Step 2: Set component to neutral (50 midpoint)
  modified_score = recalculate_without_component(i)

Step 3: Measure performance WITHOUT component
  AUC_ablated = measure_performance(modified_score)

Step 4: Calculate contribution
  contribution = AUC_full - AUC_ablated
  importance = contribution / AUC_full  (percentage)
```

### 1.3 Ablation Dataset

**Use Phase 3 test data:**
- OOS validation set (2025-2026 dormant coins)
- Ground truth outcomes (resurrected yes/no)
- All component scores frozen at time of original calculation

**Do NOT retrain components** — measure only scoring impact.

---

## 2. Ablation Execution

### 2.1 Full-Model Baseline

```python
# Load Phase 3 results
oos_outcomes = load_oos_ground_truth()  # Actual resurrections
oos_rrp_scores = load_oos_rrp_scores()  # Original RRP scores

# Baseline performance (from Phase 3)
AUC_full = 0.XXXX  # Locked from Phase 3
baseline_performance = {
  "auc": AUC_full,
  "precision": 0.XXXX,
  "recall": 0.XXXX,
  "calibration_r2": 0.XXXX
}
```

### 2.2 Ablation Loops

```python
ablation_results = {}

for component_idx in range(num_components):
    # Create modified scores with this component removed
    modified_scores = []
    
    for coin, original_score in zip(oos_coins, oos_rrp_scores):
        components = get_component_scores(coin)  # [vol, narrative, capital, momentum]
        
        # Set ablated component to neutral
        components[component_idx] = 50  # Midpoint (no contribution)
        
        # Recalculate score without this component
        modified_score = weighted_average(components)
        modified_scores.append(modified_score)
    
    # Measure performance without component
    AUC_ablated = roc_auc_score(oos_outcomes, modified_scores)
    
    # Calculate importance
    contribution = AUC_full - AUC_ablated
    importance_pct = (contribution / AUC_full) * 100
    
    ablation_results[component_idx] = {
        "component": component_names[component_idx],
        "auc_full": AUC_full,
        "auc_ablated": AUC_ablated,
        "contribution": contribution,
        "importance_percent": importance_pct,
        "status": "CRITICAL" if contribution > 0.05 else "USEFUL" if contribution > 0.02 else "MINIMAL"
    }
    
    print(f"{component_names[component_idx]}: "
          f"contribution={contribution:.4f} ({importance_pct:.1f}%), "
          f"status={ablation_results[component_idx]['status']}")
```

### 2.3 Ranking Components

```python
# Sort by contribution (highest first)
ranked_components = sorted(
    ablation_results.items(),
    key=lambda x: x[1]["contribution"],
    reverse=True
)

print("\n=== COMPONENT IMPORTANCE RANKING ===")
for rank, (idx, result) in enumerate(ranked_components, 1):
    print(f"{rank}. {result['component']}: "
          f"ΔAUCs = {result['contribution']:.4f} "
          f"({result['importance_percent']:.1f}%), "
          f"Status: {result['status']}")
```

---

## 3. Ablation Criteria

### 3.1 Component Classification

| Category | Criterion | Action |
|----------|-----------|--------|
| **CRITICAL** | Contribution ≥ 0.05 | KEEP in production (Phase 8) |
| **USEFUL** | 0.02 ≤ Contribution < 0.05 | KEEP (low marginal cost) |
| **MINIMAL** | Contribution < 0.02 | CONSIDER REMOVING (complexity vs benefit) |
| **NEGATIVE** | Contribution < 0 | **BUG** — investigate why it hurts performance |

### 3.2 Acceptance Requirements

✅ **At least 2 components** ≥ CRITICAL threshold  
✅ **No negative contributions** (if found, debug immediately)  
✅ **Total contribution** ≥ 0.80 × AUC_full (80% explained by components)  
✅ **All components interpretable** (can explain WHY each contributes)  

---

## 4. Ablation Report

```
PHASE 4 ABLATION & COMPONENT ANALYSIS REPORT
Generated: 2026-12-06
Analysis Dataset: OOS validation (2025-2026 dormant coins)
Ground Truth: rrp_alpha_p2_gt_2026-10-23 (FROZEN)
Baseline AUC: 0.XXXX (from Phase 3)

═══════════════════════════════════════════════════════════════

EXECUTIVE SUMMARY
─────────────────
Components Analyzed: N
Critical Components: M
Useful Components: K
Minimal Components: J
Negative Components: 0 (clean analysis)

Total Component Contribution: X.XX% of baseline AUC

═══════════════════════════════════════════════════════════════

1. COMPONENT RANKING

Rank | Component          | Contribution | Importance | Status
─────┼────────────────────┼──────────────┼────────────┼─────────
  1  | Volume Trend       | +0.0245      | 2.8%       | CRITICAL
  2  | Narrative Score    | +0.0198      | 2.3%       | USEFUL
  3  | Capital Flow       | +0.0087      | 1.0%       | USEFUL
  4  | Momentum           | +0.0034      | 0.4%       | MINIMAL

═══════════════════════════════════════════════════════════════

2. COMPONENT DETAILS

Component #1: VOLUME TREND
─────────────────────────
- Definition: 30-day trailing volume growth rate
- Input Range: 0-100 (0=no growth, 100=100x growth)
- Contribution: 0.0245 (ΔAUCs, CRITICAL)
- Interpretation: Strong positive contribution
- When AUC drops from 0.87 → 0.84 when removed
- Conclusion: Highly important for resurrection detection

Component #2: NARRATIVE SCORE
──────────────────────────────
- Definition: Social sentiment + news momentum
- Input Range: 0-100
- Contribution: 0.0198 (ΔAUCs, USEFUL)
- Interpretation: Moderate contribution
- When AUC drops from 0.87 → 0.85 when removed
- Conclusion: Valuable but not dominant

Component #3: CAPITAL FLOW INDEX
─────────────────────────────────
- Definition: Exchange inflow/outflow differential
- Input Range: 0-100
- Contribution: 0.0087 (ΔAUCs, USEFUL)
- Interpretation: Small but measurable contribution
- When AUC drops from 0.87 → 0.86 when removed
- Conclusion: Keep due to low marginal cost

Component #4: MOMENTUM INDICATOR
────────────────────────────────
- Definition: Price velocity + volatility ratio
- Input Range: 0-100
- Contribution: 0.0034 (ΔAUCs, MINIMAL)
- Interpretation: Negligible contribution
- When AUC drops from 0.87 → 0.8696 when removed
- Conclusion: Consider removing (adds complexity, minimal value)

═══════════════════════════════════════════════════════════════

3. COMPONENT INTERACTION ANALYSIS

Do components interact (non-additive effects)?

Test: Measure AUC when removing top 2 components together
  - Contribution #1 + #2 (added): 0.0245 + 0.0198 = 0.0443
  - Contribution #1 + #2 (measured): 0.0421
  - Interaction effect: -0.0022 (slight negative synergy)
  - Interpretation: Components slightly compete, but acceptable

═══════════════════════════════════════════════════════════════

4. REFACTORING RECOMMENDATIONS (PHASE 8 DEPLOYMENT)

KEEP (Production):
  [✅] Volume Trend (CRITICAL - 2.8% contribution)
  [✅] Narrative Score (USEFUL - 2.3% contribution)
  [✅] Capital Flow (USEFUL - 1.0% contribution)

CONSIDER REMOVING:
  [⚠️] Momentum (MINIMAL - 0.4% contribution)
      - Decision: KEEP for now (low cost, 0.4% value)
      - Review if compute budget becomes constrained

OPTIMIZATION OPPORTUNITIES:
  [💡] Volume Trend: Currently linear scaling. Test sqrt/log scaling?
  [💡] Narrative Score: Currently unweighted. Test temporal decay (recent > old)?
  [💡] Capital Flow: Currently raw delta. Test ratio (inflow/(inflow+outflow))?

═══════════════════════════════════════════════════════════════

5. STATISTICAL SIGNIFICANCE

Are ablation results statistically significant?

Bootstrap confidence intervals (1000 resamples):
  Volume Trend:    0.0245 ± 0.0089  (95% CI: [0.0077, 0.0423])
  Narrative Score: 0.0198 ± 0.0124  (95% CI: [0.0021, 0.0456])
  Capital Flow:    0.0087 ± 0.0071  (95% CI: [-0.0013, 0.0238])
  Momentum:        0.0034 ± 0.0058  (95% CI: [-0.0087, 0.0152])

Interpretation:
  - Volume Trend: SIGNIFICANT (CI does not include 0)
  - Narrative Score: SIGNIFICANT (CI does not include 0)
  - Capital Flow: BORDERLINE (CI barely includes 0)
  - Momentum: NOT SIGNIFICANT (CI includes 0)

═══════════════════════════════════════════════════════════════

6. COMPONENT PERFORMANCE BY SEGMENT

Do components perform differently across coin types?

Stratified Analysis (Large cap vs Small cap dormant):

Large Cap Coins (>$50M pre-dormancy):
  - Volume Trend contribution: 0.0298 (CRITICAL)
  - Narrative Score contribution: 0.0201 (USEFUL)

Small Cap Coins (<$50M pre-dormancy):
  - Volume Trend contribution: 0.0187 (USEFUL)
  - Narrative Score contribution: 0.0191 (USEFUL)

Interpretation: Volume Trend more important for large caps.
Consider component weighting by coin size in Phase 8.

═══════════════════════════════════════════════════════════════

CONCLUSION

Phase 4 Ablation Analysis COMPLETE

✅ All components contribute positively (no bugs found)
✅ 2 components are CRITICAL (exceeds requirement)
✅ 80%+ of AUC explained by top 3 components
✅ No significant interactions detected
✅ Components perform consistently across segments

GATE DECISION: ✅ PASS → Phase 5 Robustness Analysis
```

---

## 5. Component Refinement Guidance

### For Phase 8 Deployment, consider:

1. **Volume Trend (CRITICAL)**
   - Keep in production
   - Consider: Test exponential scaling (recent vol > old vol)?
   - Monitor: Volume calculation methodology (CEX vs on-chain)

2. **Narrative Score (USEFUL)**
   - Keep in production
   - Consider: Temporal decay (don't count stale sentiment)
   - Monitor: Sentiment data quality + bias

3. **Capital Flow (USEFUL)**
   - Keep in production
   - Consider: Normalize by exchange share (flow / total supply)
   - Monitor: Exchange data completeness

4. **Momentum (MINIMAL)**
   - Decision: KEEP (low cost, some value, 0.4%)
   - Optimize: Compute more efficiently if possible
   - Review: Drop in Phase 9 if compute budget critical

---

## 6. Phase 4 Success Criteria

All of the following must be TRUE:

✅ **At least 2 components** ≥ CRITICAL (contribution ≥ 0.05)  
✅ **No negative contributions** (all components ≥ 0)  
✅ **Total contribution** ≥ 0.80 × AUC_full  
✅ **Statistical significance** At least 2 components CI ∋ 0  
✅ **Interpretability** Can explain each component's role  

**If ANY criterion fails:** Debug component logic, re-examine Phase 3 results.

---

## 7. Phase 4 Timeline

```
Nov 20 | Phase 4 execution begins (use Phase 3 OOS data)
Nov 23 | Leave-one-out calculations complete
Nov 25 | Component ranking + interaction analysis
Nov 27 | Stratified analysis by coin segment
Nov 29 | Report drafted, human interpretation
Dec 06 | Gate decision: PASS → Phase 5
```

---

## Deliverables (Phase 4 Completion)

1. **Component Ranking** (ablation results for each component)
2. **Contribution Quantification** (ΔAUCs for each component)
3. **Statistical Significance** (bootstrap confidence intervals)
4. **Interaction Analysis** (component synergies/conflicts)
5. **Segment Performance** (stratified by coin size/market)
6. **Refactoring Recommendations** (guidance for Phase 8)
7. **Ablation Report** (PASS/FAIL gate decision)

---

**Built:** 2026-09-25  
**Phase:** 4 of 7  
**Status:** Ready for Nov 20 Execution  
**Downstream:** Phase 5 Robustness Analysis (begins upon Phase 4 PASS)
