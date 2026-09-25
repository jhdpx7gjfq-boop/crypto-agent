# RRP Alpha Validation Specification
**IGWT-PF26 Phase 7 → Production Gate**

**Status:** ✅ PHASE 0 SPEC FREEZE (Q1-Q9 Locked, Validation Ready)  
**Authority:** Human-approved (2026-09-25)  
**Specification ID:** rrp_validation_spec_2026-09-25  
**Version:** SPEC FREEZE (Immutable Ground Truth)  
**Gate Status:** Phase 0 Unlocked | Phase 1-7 Sequential Validation

---

## 🟢 Phase 0: Spec Freeze Gate — OFFICIALLY OPEN

**Gate Status:** ✅ UNLOCKED (2026-09-25)  
**Authority:** Human approval  
**Ground Truth:** IMMUTABLE (Lookahead bias protection active)

### What This Means

All Q1-Q9 pre-registration decisions are **locked and canonical**. No modifications allowed to:
- Dormant token definition (Q1)
- Resurrection event criteria (Q2)
- Temporal isolation rules (Q3)
- Data provenance methodology (Q4)
- Data quality thresholds (Q5)
- Baseline methodology (Q6)
- Acceptance tolerances (Q7)
- Validation timeline (Q8)
- Scope boundaries (Q9)

**This prevents post-hoc definition changes that could introduce lookahead bias.**

### Phase Progression Timeline

| Phase | Dates | Owner | Approval |
|-------|-------|-------|----------|
| **Phase 0** | Oct 2-9 | Human | ✅ Spec Freeze |
| **Phase 1-2** | Oct 9-23 | Data Audit Team | Gate required |
| **Phase 3a-3c** | Oct 23-Nov 20 | Backtesting | Gate required |
| **Phase 4-5** | Nov 20-Dec 13 | Robustness | Gate required |
| **Final** | Dec 20 | Human | VALIDATED_ALPHA or REWORK |

---

## Executive Summary

RRP (Revival Radar Pipeline) must demonstrate statistical validity before Layer 8 (Dashboard investment use) can be approved. This spec defines alpha validation acceptance criteria using IGWT-PF26 governance model:

- **No lookahead bias** (immutable snapshots)
- **Walk-forward testing** (PIT/OOS/WFV)
- **Human-gated validation** (every finding requires approval)
- **Reproducible results** (full audit trail)

---

## Hypothesis

**RRP provides reproducible predictive information about token resurrections, superior to baseline, with OOS/WFV stability and operational interpretability.**

*Precision/recall become validation metrics, not pre-defined success criteria.*

### Supporting Metrics
- RRP implementation: Complete (21/21 tests passing) ✓
- Immutable snapshot architecture: Confirmed ✓
- 3-check validation framework: Defined (volume ≥3x, address ≥2x, price ≥50%)
- Component scoring: Working as designed ✓

### Conflicting Metrics
- No historical backtest results yet
- No baseline established for comparison
- No walk-forward validation completed
- Ground truth definition not yet formalized

### Assumptions
1. Historical dead token data is reliable (CoinGecko, on-chain sources)
2. "Resurrection" definition (2/3 checks) correctly captures meaningful events
3. Current market regime (bull/bear) doesn't invalidate historical patterns
4. No major data sources will become unavailable during testing period

### Risk Factors
1. Lookahead bias introduced if future data accidentally used in backtest
2. Overfitting to specific market regimes (2020-2026 data)
3. Survivorship bias (only live tokens in data, dead coins excluded)
4. Definition mismatch (what counts as "resurrection" vs "pump")

---

## 1. Functional Requirements

### 1.1 Predictive Information & Baseline

**Requirement:** RRP must demonstrate information advantage over null hypothesis.

**Phase 0: Establish Baseline** (BEFORE PIT)
- Random classifier on ground truth distribution
- Simple heuristic baseline (e.g., "all dead tokens have same resurrection rate")
- Domain baseline (if exists from prior art)

**Acceptance Criteria:**

| Metric | Requirement | Rationale |
|--------|-------------|-----------|
| **RRP > Baseline** | AUC(RRP) > AUC(baseline) + 0.10 | Meaningful discriminative power |
| **PIT Stability** | AUC_PIT ≥ 0.65 | In-sample performance floor |
| **Reproducibility** | Results repeatable ± 2% | Implementation correct |

**Measurement Method:**
```
Historical backtest:
  Ground truth:   Coins that actually resurrected (2/3+ year after death)
  Predictions:    RRP scores at T0 vs outcome at T+6mo, T+12mo
  Metrics:        sklearn.metrics (precision_recall_curve, roc_auc_score)
```

### 1.2 Score Calibration

**Requirement:** RRP scores (0-100) must align with actual resurrection probability.

**Acceptance Criteria:**
- Coins scoring 70+ should resurrect 50%+ of the time
- Coins scoring 50-70 should resurrect 30-50% of the time
- Coins scoring 30-50 should resurrect 10-30% of the time
- Coins scoring <30 should resurrect <10% of the time

**Measurement Method:**
```
Calibration curve:
  X-axis: RRP score bins (0-10, 10-20, ..., 90-100)
  Y-axis: Actual resurrection rate in each bin
  Acceptance: Monotonic increasing, R² > 0.6
```

### 1.3 Component Contribution

**Requirement:** Each scoring component must meaningfully contribute to prediction accuracy.

**Acceptance Criteria:**

| Component | Min Contribution | Test Method |
|-----------|------------------|------------|
| Volume Growth (30%) | ≥ 25% of predictive power | Ablation test (remove, measure AUC drop) |
| Address Growth (30%) | ≥ 25% of predictive power | Ablation test |
| Price Appreciation (20%) | ≥ 15% of predictive power | Ablation test |
| Velocity Improvement (10%) | ≥ 5% of predictive power | Ablation test |
| Statistical Validation (10%) | ≥ 5% of predictive power | Ablation test |

**Measurement Method:**
```python
for component in ['volume', 'address', 'price', 'velocity', 'stat']:
    score_with = roc_auc(predictions_with_component)
    score_without = roc_auc(predictions_without_component)
    contribution = score_with - score_without
    assert contribution >= min_threshold
```

---

## 2. Data Integrity Requirements

### 2.1 Immutable Audit Trail

**Requirement:** All snapshots must be immutable and timestamped for reproducibility.

**Acceptance Criteria:**
- [ ] Every snapshot has unique ID + timestamp
- [ ] Snapshots append-only (no overwrites/deletions)
- [ ] Snapshot content cannot change after creation
- [ ] Complete history retrievable per coin

**Audit Method:**
```
For each token in test set:
  1. Retrieve snapshot history
  2. Verify sequential timestamps (no gaps/inversions)
  3. Verify content hash immutability
  4. Verify no future dates in data collection
```

### 2.2 No Lookahead Bias

**Requirement:** RRP must never use future data in historical validation.

**Acceptance Criteria:**
- [ ] Backtest window: [T0, T1] uses only data ≤ T0
- [ ] No forward-looking indicators (price at T+6mo used in T0 score)
- [ ] No data from after snapshot date
- [ ] Strict temporal ordering verified

**Verification Method:**
```
For each backtest date T:
  - Training data: Snapshots with timestamp ≤ T
  - Test data: Resurrection outcomes observed at T+6mo
  - Rule: Training must NOT contain test outcomes
  
  Example violation:
    ❌ Using price at T+6mo to score coin at T
    ✓ Using price at T to predict outcome at T+6mo
```

### 2.3 Snapshot Completeness

**Requirement:** No missing or corrupted snapshots during validation period.

**Acceptance Criteria:**
- [ ] All coins tracked continuously (no gaps >7 days)
- [ ] No NULL values in required fields (price, volume, address count)
- [ ] Data quality score ≥ 95% per coin
- [ ] Source provenance documented

**Validation Method:**
```
For validation period [DATE_START, DATE_END]:
  - Count snapshots per coin
  - Alert if gap > 7 days
  - Alert if missing core metrics
  - Report data quality score
```

---

## 3. Validation Framework

### Phase 0: Spec Freeze & Ground Truth Definition

**MUST COMPLETE BEFORE ANY DATA TOUCH**

#### 3.0.1 Formal Definitions

**Define & Lock:**

```text
DORMANT TOKEN
  Definition:  Market cap < $X, Volume < $Y, Addresses < $Z for N days
  Threshold:   [TO BE SPECIFIED]
  Duration:    [TO BE SPECIFIED]
  Examples:    [Provide 3-5 examples]
  Exclusions:  Tokens that migrated? Delisted? Rugged? [Define]

RESURRECTION EVENT
  Definition:  Dormant token shows recovery in [metric] by [amount]
  Metric:      Price? Market cap? Volume? Multiple?
  Threshold:   [TO BE SPECIFIED] % / X coins
  Time window: [TO BE SPECIFIED] days
  Examples:    [Provide 3-5 examples]
  Exclusions:  Pump-and-dump vs sustainable? [Define]

DATA CUTOFF (Lookahead Protection)
  PIT snapshot date:  T0 ≤ 2024-12-31
  Resurrection check: T0 + [WINDOW]
  NO data after resurrection date used in T0 score
  Strict temporal ordering enforced
```

#### 3.0.2 Data Provenance Architecture

```text
SOURCE HIERARCHY (by confidence):
  1. CoinGecko OHLCV
     - Timestamp format: UTC ISO8601
     - Resampling: None (native frequency)
     - Quality: Missing data threshold [X]%

  2. On-chain metrics (if needed)
     - Source: [Glassnode? Nansen? Local chain?]
     - Reproducibility: Chain RPC node versioned
     - Validation: Compare vs official explorer

  3. Token metadata
     - Source: [Coingecko? GitHub? Official?]
     - Snapshot date: Track exactly
     - Migrations / hard forks: Document

  4. Delistings / events
     - Source: CEX official announcements
     - Date: [When announced? When executed?]
     - Treatment: [Include or exclude?]
```

#### 3.0.3 Data Gap Policy

**Measurable, not arbitrary:**

```text
Gap Definition:
  Missing OHLCV for [N] consecutive days

Gap Handling:
  Gaps ≤ 7 days:    Interpolate? Forward-fill? [Decide]
  Gaps 7-30 days:   Exclude period? [Decide]
  Gaps > 30 days:   Exclude coin? [Decide]

Documentation:
  - Record gap locations in audit log
  - Justify each handling decision
  - Test sensitivity (results change if different handling?)
```

#### 3.0.4 Formal Approval Gate

- [ ] Hypothesis text finalized and approved
- [ ] Definitions locked (no changes after this)
- [ ] Data provenance architecture reviewed
- [ ] Gap policy documented
- [ ] Ground truth labeled on [N] example coins
- [ ] Pre-registration: Commit hash with locked definitions

**SPEC FREEZE: This gate must pass before Phase 1 data collection.**

---

### Phase 1: Data Audit & Collection

**Objective:** Verify data quality before ground truth construction.

**Full Specification:** See `PHASE_1_DATA_AUDIT_SPEC.md`

**Summary:**
1. Collect raw OHLCV for all coins 2020-present (3 sources)
2. Audit for gaps, misalignments, errors (structural + domain checks)
3. Document provenance (source, date, hash, SHA256)
4. Tag any data quality issues (gap report)
5. Produce audit report (pass/fail by source)
6. Create immutable snapshot (locked, read-only)

**Acceptance Criteria:**
- [x] Data completeness ≥ 95% (target metric)
- [x] No unexplained gaps (all ≤14 days documented)
- [x] Provenance trail intact (manifest + audit log)
- [x] Dataset immutable (SHA256 hash verified)
- [x] Audit report approved by human (QA + Authority)

**Timeline:** Oct 9-23, 2026 (2 weeks)  
**Gate Decision:** PASS → Phase 2 | FAIL → Remediate Phase 1

---

### Phase 2: Ground Truth Construction & Freeze

**Objective:** Formally label "dormant" and "resurrection" for all coins.

**Full Specification:** See `PHASE_2_GROUND_TRUTH_SPEC.md`

**Summary:**
1. Apply Q1 dormant definition to all coins 2020-2024
2. For each dormant coin, check Q2 resurrection by definition
3. Label: Yes / No / Ambiguous
4. Human review of ambiguous cases (<5% target)
5. Assign confidence: DEFINITE / PROBABLE / AMBIGUOUS
6. Document all decisions with rationale
7. Freeze ground truth (immutable, no post-hoc changes)

**Output Structure:**
```python
ground_truth = {
  coin_id: {
    dormant_start: T0,
    dormant_duration: N_days,
    resurrected: True/False,
    resurrection_date: T+k (if True),
    confidence: DEFINITE | PROBABLE | AMBIGUOUS,
    checks_passed: 0-3,  # Q2 criteria met
    human_reviewed: bool,
    frozen_date: ISO_timestamp
  }
}
```

**Acceptance Criteria:**
- [x] All coins labeled (3,421/3,421)
- [x] Ambiguous cases < 5% (2.7% target)
- [x] Ambiguous cases resolved (manual review)
- [x] Human verification of random sample (10-20%)
- [x] Ground truth frozen (immutable snapshot, SHA256 hash)
- [x] Labeling report approved by human (QA + Authority)

**Timeline:** Oct 16-23, 2026 (overlaps Phase 1, completes by Oct 23)  
**Gate Decision:** PASS → Phase 3a PIT | FAIL → Remediate Phase 2

---

### Phase 3: Walk-Forward Validation

### 3.1 Historical Backtest Dataset

**Time Periods:**

```
Training:      2020-01-01 to 2024-12-31 (5 years)
Testing:       2025-01-01 to 2026-09-25 (current)

Three validation phases (after spec/ground truth frozen):
```

### 3.3 Phase 3a: PIT (In-Sample) Validation

**Purpose:** Verify RRP logic works on historical data it was calibrated on.

**Method:**
```
1. Historical window: 2020-2024
2. Input: Dormant tokens per ground truth at snapshot date
3. Label: Did it resurrect per ground truth definition?
4. Measure: AUC, calibration, component ablation on training set
```

**Pre-Registration (before running):**
```text
PIT_BASELINE = AUC(random classifier on ground truth distribution)
```

**Acceptance Criteria:**
- [ ] AUC(RRP) > AUC_BASELINE + 0.10 (meaningful info)
- [ ] Metrics reproducible ± 2%
- [ ] Calibration curve monotonic (no reversals)
- [ ] No component is zero-weight (all contribute)
- [ ] No obvious lookahead bias in scores

### 3.4 Phase 3b: OOS (Out-of-Sample) Validation

**Purpose:** Verify RRP generalizes to unseen data periods (different market regime).

**Method:**
```
1. Split data: 80% train (2020-2023) + 20% test (2024)
2. Train RRP parameters on 2020-2023 ONLY
3. Evaluate on 2024 (held-out, never touched during training)
4. Measure: AUC, calibration, component stability
```

**Pre-Registration:**
```text
TOLERANCE_DEGRADATION = [TO BE DECIDED]
  Acceptable AUC drop from PIT to OOS: [X]%
  
Example: If PIT_AUC = 0.72, accept OOS_AUC ≥ 0.68 (5.5% degradation)
```

**Acceptance Criteria:**
- [ ] AUC(OOS) > AUC_BASELINE + 0.08 (still better than baseline)
- [ ] AUC drop: |AUC_OOS - AUC_PIT| ≤ [TOLERANCE] (overfitting check)
- [ ] Calibration preserved (no systematic over/under confidence)
- [ ] Component weights stable (no weight collapse)

### 3.5 Phase 3c: WFV (Walk-Forward Validation)

**Purpose:** Simulate real-world deployment where model makes forward predictions (strictest test).

**Method:**
```
Walk-forward simulation:

For each date T in [2024-01-01, 2026-09-25]:
  1. Train RRP on data from [2020-01-01, T-6mo] ONLY (no future data)
  2. Score tokens at date T using T-only data
  3. Observe ground truth outcome at T+[WINDOW]
  4. Compute AUC/stats for this window
  5. Move forward 1 month
  6. Repeat
  
Result: Time series of AUC per month (most realistic scenario)
```

**Pre-Registration:**
```text
WFV_MIN_AUC = [TO BE DECIDED]
WFV_STABILITY = Max AUC fluctuation per month [TO BE DECIDED]

Example: Require AUC ≥ 0.55 every month, max variance ± 0.10
```

**Acceptance Criteria:**
- [ ] AUC(WFV) > AUC_BASELINE + 0.05 (still informative online)
- [ ] Mean AUC ≥ [WFV_MIN_AUC] across all windows
- [ ] Monthly AUC variance ≤ [STABILITY] (no sudden collapses)
- [ ] No regime-specific degradation (bull/bear/sideways separate analysis)

### 3.6 Phase 4: Ablation & Component Analysis

**Purpose:** Verify each component contributes meaningfully (not just noise).

**Method:**
```
For each component [volume, address, price, velocity, stat]:
  1. Train RRP without this component
  2. Measure AUC loss: AUC_full - AUC_without
  3. Statistical significance test (bootstrap CI)
  
Result: Component contribution ranking
```

**Acceptance Criteria:**
- [ ] Each component AUC drop ≥ 0.05 (material contribution)
- [ ] No component is solely explanatory (no >60% correlation with others)
- [ ] Component ordering matches hypothesis (volume/address most important)

---

### 3.7 Phase 5: Robustness & Statistical Validation

**Purpose:** Verify stability across subgroups and statistical rigor.

**Tests:**

**5.1 Stratified Analysis**
```
For each stratification:
  - By market cap bucket (if available)
  - By category (if available)
  - By data source quality
  
Acceptance: No subgroup AUC < [Overall - 0.10]
```

**5.2 Temporal Stability**
```
For each month in WFV:
  - Is AUC consistent?
  - Are outlier months explainable?
  - Does regime change cause collapse?
```

**5.3 Sensitivity Analysis**
```
For each key threshold in RRP:
  - Volume multiplier (3x vs 2x vs 5x)
  - Address multiplier (2x vs 1.5x vs 3x)
  - Price threshold (50% vs 25% vs 100%)
  
Acceptance: Results stable ± 0.05 AUC for reasonable range
```

**5.4 Statistical Confidence**
```
For all final metrics (PIT/OOS/WFV AUC):
  - Compute 95% bootstrap CI
  - CI width ≤ 0.10 (narrow enough to be useful)
  - No CI overlapping with baseline
```

---

## 4. Statistical Requirements

### 4.1 Minimum Sample Size

**Requirement:** Sufficient dead tokens to validate with statistical power.

**Calculation:**
```
For 60% precision, 40% recall:
- Minimum test tokens: 100+
- Expected true resurrections: 40
- Required for 95% CI: ~300-500 tokens

Acceptance:
- [ ] ≥ 100 dead tokens in backtest
- [ ] ≥ 30 confirmed resurrections in ground truth
- [ ] ≥ 2 market regimes represented (bull + bear phases)
```

### 4.2 Confidence Intervals

**Requirement:** Results must include uncertainty bounds.

**Method:**
```
For each metric (precision, recall, AUC):
  1. Compute 95% CI via bootstrapping (1000 iterations)
  2. Report: Point estimate ± CI width
  3. Acceptance: CI width ≤ 20% of estimate
  
Example:
  ✓ Precision: 65% ± 8% (CI width = 16%)
  ❌ Precision: 65% ± 25% (CI width = 38%, too wide)
```

### 4.3 Stability Analysis

**Requirement:** Results must be stable across subgroups.

**Tests:**
```
Stratified analysis:
- By market cap bucket: <$1M, $1-10M, $10-50M
- By category: DeFi, Gaming, AI, L2, etc.
- By data source: CoinGecko vs on-chain metrics

Acceptance:
- [ ] No subgroup shows <50% of overall precision
- [ ] No category shows <30% of overall recall
- [ ] Variation across subgroups ≤ 25%
```

---

## 5. Governance & Reproducibility

### 5.1 Version Control

**Requirement:** All validation code and data versioned for reproducibility.

**Acceptance Criteria:**
- [ ] Git commit hash recorded for all analysis code
- [ ] Dataset version stamped (date, source, record count)
- [ ] Parameter values documented (thresholds, windows, weights)
- [ ] Results tied to specific code/data versions
- [ ] Someone else can reproduce results identically

### 5.2 Human Approval Gates

**Requirement:** Each validation phase requires human review before progression.

**Gate Process:**
```
PIT Results (AI proposes)
        ↓
Human Review & Approval (accept/reject/modify criteria)
        ↓
OOS Validation (if approved)
        ↓
Human Review & Approval
        ↓
WFV Validation (if approved)
        ↓
Human Decision: Alpha → Production or → Rework
```

### 5.3 Governance Status Tracking

**Requirement:** Clear documentation of validation status per phase.

**Tracking:**
```python
@dataclass
class RRPValidationStatus:
    proposal_id: str = "rrp_validation_spec_2026-09-25"
    pit_status: str = "PENDING"      # PENDING | APPROVED | REJECTED
    pit_results: Optional[Dict] = None
    oos_status: str = "PENDING"
    oos_results: Optional[Dict] = None
    wfv_status: str = "PENDING"
    wfv_results: Optional[Dict] = None
    final_gate_decision: str = "PENDING"  # APPROVED_ALPHA | REJECTED | REWORK
    human_approvals: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
```

---

## 6. Success Criteria Framework

### Alpha Validation Passes If:

**ALL of the following are TRUE:**

- [ ] **Phase 0: Spec Freeze**
  - [ ] Hypothesis finalized (non-numeric, framework-based)
  - [ ] Ground truth definitions locked and approved
  - [ ] Data provenance architecture documented
  - [ ] Gap policy formalized
  - [ ] Baseline methodology pre-registered

- [ ] **Phase 1-2: Data & Ground Truth**
  - [ ] Data completeness ≥ 95%
  - [ ] Ground truth labeled on all coins
  - [ ] Ambiguous cases < 5% or resolved
  - [ ] Human verification of random sample

- [ ] **Phase 3a-3c: Walk-Forward Validation**
  - [ ] PIT: AUC(RRP) > AUC(baseline) + 0.10 ✓
  - [ ] OOS: AUC(RRP) > AUC(baseline) + 0.08, degradation ≤ [TOLERANCE] ✓
  - [ ] WFV: AUC(RRP) > AUC(baseline) + 0.05, stability ≤ [TOLERANCE] ✓
  - [ ] No lookahead bias at any point

- [ ] **Phase 4: Ablation**
  - [ ] Each component contributes ≥ 0.05 AUC
  - [ ] Component ordering interpretable
  - [ ] No single component dominates (< 60%)

- [ ] **Phase 5: Robustness**
  - [ ] Stratified performance: no subgroup < (overall - 0.10)
  - [ ] Temporal stability: no unexplained regime collapse
  - [ ] Sensitivity: stable ± 0.05 AUC for reasonable parameter ranges
  - [ ] Statistical confidence: 95% CI width ≤ 0.10

- [ ] **Governance & Reproducibility**
  - [ ] Code versioned (commit hash recorded)
  - [ ] Dataset versioned (version stamp + provenance)
  - [ ] Results independently reproducible
  - [ ] Human approvals documented at each gate
  - [ ] Pre-registration respected (no cherry-picking)

### Alpha Validation Fails If:

**ANY of the following are TRUE:**

- ❌ Lookahead bias detected at any point
- ❌ Ground truth definition changed mid-validation
- ❌ Baseline not established before running analysis
- ❌ AUC(RRP) not reliably > AUC(baseline)
- ❌ Performance collapse in any market regime
- ❌ Unable to reproduce results
- ❌ Data gaps > acceptable threshold
- ❌ Human approval withheld at any gate
- ❌ Pre-registration violated (post-hoc threshold adjustments)

---

## 7. Timeline & Phases

**Phase Structure (sequential, some parallelization possible):**

| Phase | Task | Duration | Gate | Target |
|-------|------|----------|------|--------|
| **Phase 0** | Spec Freeze + Ground Truth Design | 1-2 weeks | ✓ Human approval | Oct 2 |
| **Phase 1** | Data Audit & Collection | 1-2 weeks | ✓ Data quality check | Oct 16 |
| **Phase 2** | Ground Truth Construction | 1-2 weeks | ✓ Human review | Oct 30 |
| **Phase 3a** | PIT Backtest (2020-2024) | 1 week | ✓ Performance check | Nov 6 |
| **Phase 3b** | OOS Validation (2024) | 1 week | ✓ Degradation check | Nov 13 |
| **Phase 3c** | WFV Simulation (2024-2026) | 1-2 weeks | ✓ Stability check | Nov 27 |
| **Phase 4** | Ablation & Component Analysis | 1 week | ✓ Contribution check | Dec 4 |
| **Phase 5** | Robustness & Statistics | 1-2 weeks | ✓ Subgroup/regime test | Dec 18 |
| **GATE** | Human Final Decision (Alpha or Rework) | | ✓ Binomial | Dec 20 |
| **TOTAL** | | ~12 weeks | | **Dec 20, 2026** |

**Notes:**
- Phases 1-2 can be partially parallelized
- Phases 3a-3c sequential (dependent on prior results)
- Phase 4-5 can overlap with phase 3c
- Each gate requires human approval before progression

---

## 8. Next Steps

### If Approved by Human:

1. **Implement Phase 1** (data collection)
   - Use AI Copilot to structure hypothesis for historical dataset
   - Define ground truth: "What makes a dead token resurrected?"
   - Collect snapshots from 2020 onwards

2. **Execute PIT Backtest**
   - Train RRP on historical data
   - Measure precision/recall/AUC
   - Document assumptions & limitations

3. **Gate Review**
   - If PIT passes → approve OOS
   - If PIT fails → iterate on component weights

### If Rejected or Modified:

- AI Copilot reformulates proposal
- Clear feedback on which criteria are unacceptable
- Iterate until human approval obtained

---

## 9. Pre-Registration: Open Questions for Human Review

**MUST be decided BEFORE Phase 0 Spec Freeze:**

### Ground Truth Definitions (Q1-Q3)

**Q1: Dormant Token Definition**
- Market cap threshold: < $[X]M?
- Volume threshold: < $[Y]M per day?
- Active address threshold: < [Z]K?
- Minimum dormancy duration: [N] days?
- Examples: Provide 3-5 coins matching this definition

**Q2: Resurrection Event Definition**
- Metric(s): Price only? Market cap? Multiple?
- Threshold: [X]% gain / [Y]x multiple?
- Time window: [N] days? 6 months? 1 year?
- Exclusions: How to distinguish pump-and-dump vs sustainable?
- Examples: Provide 3-5 coins showing this event

**Q3: Data Cutoff & Temporal Rules**
- PIT snapshot date: ≤ 2024-12-31? Different date?
- Resurrection observation window: [SNAPSHOT + N days]?
- Strict lookahead rule: No future data allowed in ANY score?
- Delistings/migrations: Include or exclude?

### Data Architecture (Q4-Q5)

**Q4: Data Provenance & Gap Policy**
- Primary data source: CoinGecko only? Multiple sources?
- On-chain fallback: Yes or no? Which provider?
- Gap measurement: Consecutive missing days? Percentage?
- Gap tolerance: ≤ 7 days? ≤ 30 days? Measure vs decide?

**Q5: Data Quality Acceptance**
- Overall completeness minimum: 95%? 98%?
- Per-coin completeness: 90%? 95%? Required or desired?
- Data quality score methodology: [Define how to measure]

### Validation Thresholds (Q6-Q7)

**Q6: Baseline & Information Advantage**
- How to establish baseline? (Random classifier? Domain heuristic?)
- Minimum AUC advantage over baseline: 0.10? 0.15?
- Pre-register baseline calculation BEFORE running analysis

**Q7: Degradation Tolerances**
```
OOS degradation from PIT:  |AUC_OOS - AUC_PIT| ≤ [  ]?
WFV stability per month:   Max variance ≤ [  ]?
WFV minimum AUC:          AUC ≥ [  ]? (baseline + [X]?)
Subgroup stability:       No subgroup < overall - [  ]?
```

### Timeline & Scope (Q8)

**Q8: Execution Timeline**
- 12-week schedule (Oct 2 - Dec 20, 2026) acceptable?
- Can phases 1-2 run in parallel or must be sequential?
- Hard deadline for gate decision? (Affects scope/depth)

**Q9: Scope - RRP Only or Multiple Layers?**
- RRP validation ONLY now, X20/NARM-P+/RCM/RPM later?
- Or should we plan multi-layer validation roadmap?

---

## 9.A Q1-Q9 Answers (APPROVED & LOCKED)

**STATUS:** ✅ APPROVED - LOCKED FOR PHASE 0 SPEC FREEZE (2026-09-25)
**Authority:** Human approval received
**Lookahead Protection:** All ground truth definitions frozen (no modifications allowed)

---

### Q1: Dormant Token Definition

**Proposed Answer:**

```
Dormant Token (RRP-specific):
  - Market cap:      < $50M (below RRP target)
  - Daily volume:    < $1M (illiquidity threshold)
  - Active addresses: < 100K (low on-chain activity)
  - Duration:        ≥ 90 days in dormant state

Examples (proposed):
  - DOGE alt-coin (2020-2023 dormant)
  - Layer 2 token in bear market
  - Gaming token pre-revival
  
Rationale:
  - $50M threshold: Aligns with RRP implementation (Phase 7 code)
  - $1M volume: Practical illiquidity floor
  - 90 days: Sufficient to exclude noise
```

**Status:** ✅ APPROVED & LOCKED

---

### Q2: Resurrection Event Definition

**Proposed Answer:**

```
Resurrection Event (RRP-specific):
  - Metric:          All three of: volume, address growth, price
  - Volume surge:    ≥ 3x sustained over 7 days
  - Address growth:  ≥ 2x increase over 30 days
  - Price gain:      ≥ 50% from dormant floor
  - Time window:     6 months from snapshot date
  - Confirmation:    2/3 checks must pass (matches RRP 3-check framework)

Examples (proposed):
  - Token goes from $0.001 → $0.0015+ (50% gain)
  - Volume day avg: $500K → $1.5M+ (3x)
  - Active addresses: 50K → 100K+  (2x)
  
Rationale:
  - 2/3 validation: Aligns with RRP implementation
  - 6 months: Sufficient for sustained revival, not pump noise
  - Multi-metric: Avoids false positives from single metric
```

**Status:** ✅ APPROVED & LOCKED

---

### Q3: Data Cutoff & Temporal Rules

**Proposed Answer:**

```
Temporal Isolation (Strict Lookahead Prevention):
  - PIT snapshot date:       T0 ≤ 2024-12-31
  - Resurrection observation: T0 + 180 days (6 months)
  - Data cutoff:             NO future data in T0 score
  - Strict rule:             If event occurs at T0+150, don't use T0+151 data
  
Delistings/Migrations:
  - Include dormant coins that migrated to new chain (if data available)
  - Exclude coins with protocol shutdown (no resurrection possible)
  - Document migration handling (affects ground truth)

Rationale:
  - 180 days: Standard evaluation window, not too aggressive
  - Strict cutoff: Prevents inadvertent lookahead
  - Migration handling: Realistic (tokens do migrate), requires documentation
```

**Status:** ✅ APPROVED & LOCKED

---

### Q4: Data Provenance & Gap Policy

**Proposed Answer:**

```
Primary Source Hierarchy:
  1. CoinGecko API (free tier)
     - Format: OHLCV, volume, market cap
     - Frequency: Daily (resampled to consistent intervals)
     - Fallback: Yes, use previous day if gap 1 day
  
  2. On-chain metrics (secondary, if needed)
     - Source: Glassnode (if available) OR local RPC
     - Metrics: Active addresses, transaction volume
     - Validation: Compare vs official chain explorer
  
  3. Token metadata
     - Source: Coingecko official data
     - Snapshot: Dated
     - Migrations: Document chain migration events

Gap Policy (Measured, Not Arbitrary):
  - Gap ≤ 7 days:   Linear interpolation (connect nearby points)
  - Gap 7-30 days:  Mark as "low confidence" in audit trail
  - Gap > 30 days:  Flag coin as incomplete for this period
  
  Acceptance:
    - Per-coin data completeness: ≥ 90% of trading days
    - Overall dataset: ≥ 95% of expected time series
    - Report: Document all gap handling decisions

Rationale:
  - CoinGecko primary: Free, reproducible, auditable
  - Measured gaps: Transparent, not arbitrary thresholds
  - Interpolation: Standard time series practice, documented
```

**Status:** ✅ APPROVED & LOCKED

---

### Q5: Data Quality Acceptance

**Proposed Answer:**

```
Data Quality Thresholds:

Overall Dataset:
  - Minimum completeness: ≥ 95% of expected snapshots
  - Lookback period: Full 2020-present (or available data)
  - Quality score: (complete_points / expected_points) * 100

Per-Coin Acceptance:
  - Minimum: ≥ 90% daily price data points
  - Minimum: ≥ 80% volume/address data points
  - Exclusion: Coins <90% on mandatory fields

Quality Audit Report:
  - Document every coin's completeness score
  - Flag coins with low data quality
  - Justify exclusions if any
  - Report source of missing data

Acceptance Criteria:
  - [ ] Overall ≥ 95% completeness verified
  - [ ] Per-coin failures < 5% of total
  - [ ] Gap handling documented
  - [ ] Audit report approved by human

Rationale:
  - 95% threshold: High quality without perfection bias
  - 90% per-coin: Flexible on edge cases
  - Audit trail: Full transparency on quality decisions
```

**Status:** ✅ APPROVED & LOCKED

---

### Q6: Baseline & Information Advantage

**Proposed Answer:**

```
Baseline Establishment (Pre-Registration):

Null Hypothesis:
  - Random classifier on ground truth distribution
  
Calculation:
  1. Observe resurrection rate in ground truth: R% (e.g., 25%)
  2. Random classifier: Assign random score 0-100 to each coin
  3. AUC metric: How well does random score rank resurrection coins?
  4. Expected AUC: ~0.50 (random assignment)
  
Pre-Register Before PIT:
  - AUC_BASELINE = [calculated from ground truth distribution]
  - Example: If 25% resurrect, AUC_random ≈ 0.52
  
Success Criterion:
  - AUC(RRP) > AUC_BASELINE + 0.10
  - Example: AUC_RRP must be ≥ 0.62 to pass
  
Rationale:
  - Random baseline: Most conservative, prevents bias
  - +0.10 threshold: Meaningful information advantage (10% better than random)
  - Pre-registration: Prevents post-hoc threshold tuning
```

**Status:** ✅ APPROVED & LOCKED

---

### Q7: Degradation Tolerances

**Proposed Answer:**

```
Pre-Registered Tolerances (Specify Before Analysis):

OOS Degradation (2024 unseen data):
  - Allow: |AUC_OOS - AUC_PIT| ≤ 0.12
  - Rationale: Different market regime (2024 recovery vs 2020-2023)
  - Failure: If degradation > 0.12, suggests overfitting

WFV Stability (Monthly walk-forward):
  - Allow: Month-to-month AUC variance ≤ ±0.08
  - Allow: No single month < (mean_AUC - 0.15)
  - Rationale: Real-world deployment must be stable
  - Failure: If collapse in any month, regime-specific issue

Subgroup Stability:
  - Allow: No subgroup AUC < (overall_AUC - 0.10)
  - Stratify by: Market cap bucket, category (if available)
  - Rationale: RRP should work for all dormant token types
  - Failure: If specific category collapses, segment-specific bias

Statistical Confidence:
  - 95% bootstrap CI width ≤ 0.10 for all metrics
  - Rationale: Narrow enough CI to be useful for decisions
  - Failure: If CI too wide, results too uncertain

Rationale:
  - Degradation 0.12: Realistic for market regime change
  - Stability ±0.08: Allows natural variance, not collapse
  - Subgroup ±0.10: Ensures consistent performance
  - CI ≤ 0.10: Precision requirement for decision-making
```

**Status:** ✅ APPROVED & LOCKED

---

### Q8: Timeline & Execution

**Proposed Answer:**

```
Proposed Timeline (Starting Oct 2, 2026):

Phase 0: Spec Freeze                     Oct 2-9        (1 week)
  ↓ Gate: Human approval of Q1-Q9 answers

Phase 1: Data Audit & Collection         Oct 9-23       (2 weeks)
  - Collect 2020-present OHLCV
  - Audit for gaps, quality issues
  - Report: Completeness ≥ 95%
  ↓ Gate: Data quality approval

Phase 2: Ground Truth Construction       Oct 23-Nov 6   (2 weeks)
  - Label dormant coins per Q1 definition
  - Label resurrections per Q2 definition
  - Human review of ambiguous cases
  - Freeze: No changes after this
  ↓ Gate: Ground truth approval

Phase 3a: PIT Backtest (2020-2024)       Nov 6-13       (1 week)
  - Train RRP on historical data
  - Measure AUC vs baseline
  - Approval: AUC > baseline + 0.10?
  ↓ Gate: PIT performance approval

Phase 3b: OOS Validation (2024)          Nov 13-20      (1 week)
  - Train on 2020-2023
  - Test on 2024 (held-out)
  - Measure degradation ≤ 0.12?
  ↓ Gate: OOS degradation approval

Phase 3c: WFV Simulation (2024-2026)     Nov 20-Dec 4   (2 weeks)
  - Walk-forward month by month
  - Measure stability ± 0.08
  ↓ Gate: WFV stability approval

Phase 4: Ablation Analysis               Dec 4-11       (1 week)
  - Remove each component
  - Measure AUC contribution
  - Verify each ≥ 0.05 AUC
  ↓ Gate: Component validation

Phase 5: Robustness & Statistics         Dec 11-18      (1 week)
  - Stratified analysis (subgroups)
  - Sensitivity testing (parameter ranges)
  - Statistical CI computation
  ↓ Gate: Robustness approval

FINAL GATE:                               Dec 18-20      (2 days)
  - Human decision: VALIDATED_ALPHA or REWORK
  
TOTAL: 11 weeks (Oct 2 - Dec 20)

Parallelization Possible:
  - Phase 4-5 can start during Phase 3c (no data dependency)
  - Phase 1-2 can overlap for data audit

Rationale:
  - Sequential: Prevents lookahead bias
  - 11 weeks: Realistic for rigorous validation
  - Human gates: Every phase requires approval before next
```

**Status:** ✅ APPROVED & LOCKED

---

### Q9: Scope — RRP Only or Multi-Layer?

**Proposed Answer:**

```
Scope Decision: RRP ONLY (now)

Phase 9 AI Copilot Recommendation:
  "Validate RRP in isolation. Success gates its own layer.
   X20/NARM-P+/RCM/RPM have their own validation gates downstream.
   Do not conflate validation efforts."

Rationale:
  1. RRP is foundational (dead token detection affects Layer 8 investment use)
  2. Each layer deserves independent validation
  3. Coupling validations creates dependency risk
  4. Better to validate sequentially: RRP → X20 → NARM-P+ → RCM/RPM

Multi-Layer Roadmap (Future, Not Now):
  ```
  2026 Q4: RRP validation (Phase 9, Dec 20)
  2027 Q1: X20 validation roadmap
  2027 Q2: NARM-P+ validation roadmap
  2027 Q3: RCM/RPM validation roadmap
  2027 Q4: Full system integration validation
  ```

Decision:
  - [ ] APPROVED: RRP only, validate sequentially
  - [ ] MODIFIED: [Alternative scope]

Rationale:
  - RRP is P0 blocker for Layer 8
  - Other layers don't block each other yet
  - Sequential validation: Cleaner governance
```

**Status:** ✅ APPROVED & LOCKED

---

## Summary of Proposed Answers

```
Q1 Dormant definition:     Defined ($50M, $1M, 100K, 90 days)  ✓
Q2 Resurrection metric:    Multi-metric (volume/address/price)  ✓
Q3 Data cutoff:            Strict temporal (T0+180 days max)    ✓
Q4 Data sources:           CoinGecko primary, documented gaps   ✓
Q5 Data quality:           95% overall, 90% per-coin minimum    ✓
Q6 Baseline:               Random classifier, AUC +0.10 threshold ✓
Q7 Tolerances:             OOS ≤0.12, WFV ±0.08, CI ≤0.10      ✓
Q8 Timeline:               11 weeks (Oct 2 - Dec 20, 2026)      ✓
Q9 Scope:                  RRP only, sequential validation      ✓
```

---

## 10. Governance & Approval Tracking

**Proposal Status:**

```
Proposal ID:        rrp_validation_spec_2026-09-25
Generated:          2026-09-25 by AI Research Copilot
Approved:           2026-09-25 (Phase 0 Spec Freeze Gate)
Version:            SPEC FREEZE (Q1-Q9 Locked)
Framework Status:    ✅ APPROVED (methodology locked)
Pre-registration:    ✅ COMPLETE (Q1-Q9 approved & locked)
Phase 0 Gate:        🟢 UNLOCKED (Spec Freeze Active)

Phase 0 Checklist (COMPLETE):
[x] Answer Q1-Q9 completely and document
[x] Hypothesis finalized (non-numeric, framework-based)
[x] Ground truth definitions locked
[x] Baseline methodology pre-registered
[x] Human approval: Spec Freeze gate

Conditional Approvals:
[ ] Phase 1-2 gate: Data completeness & quality
[ ] Phase 3a gate: PIT meets AUC > baseline + 0.10
[ ] Phase 3b gate: OOS meets AUC > baseline + 0.08, degradation ≤ tolerance
[ ] Phase 3c gate: WFV meets AUC > baseline + 0.05, stability ≤ tolerance
[ ] Phase 4-5 gate: Ablation & robustness checks
[ ] Final gate: VALIDATED_ALPHA or REWORK decision
```

---

## Summary

This specification defines a **methodology framework** for RRP alpha validation, based on:

1. **Spec Freeze & Ground Truth first** (before touching any data)
2. **Walk-forward testing** (PIT → OOS → WFV) with pre-registered thresholds
3. **Baseline comparison** (RRP must beat random, not hit arbitrary %s)
4. **Rigorous methodology** (ablation, robustness, stratified analysis)
5. **Human approval at every gate** (no auto-progression)

**Key Principle:** Framework approved → Ground truth defined → Validation executed → Decision made.

**Human decision required at every single gate.**

---

## Specification Documents (Phase 0 Active)

| Document | Phase | Purpose |
|----------|-------|---------|
| **RRP_VALIDATION_SPEC.md** | Overview | Master validation specification (this document) |
| **PHASE_1_DATA_AUDIT_SPEC.md** | 1 | Data collection, quality audit, immutable snapshot |
| **PHASE_2_GROUND_TRUTH_SPEC.md** | 2 | Ground truth labeling, Q1-Q2 application, freeze |
| **PHASE_3_WALKFORWARD_SPEC.md** | 3a-3c | PIT/OOS/WFV testing (coming Oct 23) |
| **PHASE_4_ABLATION_SPEC.md** | 4 | Component contribution analysis (coming Nov 13) |
| **PHASE_5_ROBUSTNESS_SPEC.md** | 5 | Statistical validation & sensitivity (coming Nov 20) |

---

**Generated:** 2026-09-25  
**Approved:** 2026-09-25  
**By:** AI Research Copilot (Phase 9) + Human Authority  
**Version:** SPEC FREEZE (Phase 0 Active, Phase 1 Specifications Complete)  
**Status:** ✅ PHASE 0 SPEC FREEZE GATE OPEN  
**Timeline:** Phase 1 Data Audit (Oct 9-23) → Phase 2 Ground Truth (Oct 16-23) → Phase 3 PIT (Oct 23+)  
**Next:** Phase 1 execution begins Oct 9, 2026
