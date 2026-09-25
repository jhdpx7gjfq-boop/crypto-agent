# RRP Alpha Validation Roadmap
**IGWT-PF26 Phase 7 → Production Gate**

**Master Timeline:** Oct 2 - Dec 20, 2026 (11 weeks)  
**Authority:** Human approval at every phase gate  
**Principle:** Specification first, execution second, no post-hoc tuning  

---

## Executive Summary

RRP (Revival Radar Pipeline) validation follows a 7-phase sequential gate structure to establish alpha validity before production deployment in Layer 8 (Dashboard).

**Key Constraint:** Ground truth definitions frozen in Phase 0. Zero modifications allowed during validation (prevents lookahead bias and post-hoc tuning).

**Current Status:** Phase 0 Spec Freeze OPEN (Oct 2). Phases 1-5 specifications complete. Execution awaits Oct 9.

---

## Phase Roadmap

### ✅ Phase 0: Spec Freeze & Q1-Q9 Definition (ACTIVE)

**Timeline:** Sept 25 - Oct 9, 2026  
**Status:** OPEN (Spec Freeze Gate Unlocked 2026-09-25)  
**Owner:** Human Authority + AI Research Copilot  

**Deliverables:**
- [x] Q1: Dormant token definition (LOCKED)
- [x] Q2: Resurrection event definition (LOCKED)
- [x] Q3: Temporal rules (LOCKED)
- [x] Q4: Data provenance (LOCKED)
- [x] Q5: Data quality standards (LOCKED)
- [x] Q6: Baseline methodology (LOCKED)
- [x] Q7: Tolerances (LOCKED)
- [x] Q8: Timeline (LOCKED)
- [x] Q9: Scope (LOCKED)

**Gate Status:** ✅ PASS → Proceed to Phase 1

---

### ⏳ Phase 1: Data Audit & Collection (READY)

**Timeline:** Oct 9-23, 2026 (2 weeks)  
**Status:** Specification complete, awaiting execution  
**Owner:** Data Team + QA Lead  
**Input:** Phase 0 locked definitions  
**Output:** Immutable data snapshot (SHA256 hash)  

**Specification:** `PHASE_1_DATA_AUDIT_SPEC.md`

**Key Tasks:**
- [ ] Collect OHLCV from 3 sources (CoinGecko, Glassnode, Crypto.com)
- [ ] Audit data quality (structural, domain, temporal checks)
- [ ] Document all gaps (≤14 days acceptable)
- [ ] Create immutable snapshot (read-only, hashed)
- [ ] Produce audit report (PASS/FAIL decision)

**Gate Criteria:**
- Data completeness ≥ 95%
- No unexplained gaps > 14 days
- Provenance trail complete
- Human QA approval

**Gate Decision:** PASS → Phase 2 | FAIL → Remediate

---

### ⏳ Phase 2: Ground Truth Construction & Freeze (READY)

**Timeline:** Oct 16-23, 2026 (overlaps Phase 1, completes by Oct 23)  
**Status:** Specification complete, awaiting execution  
**Owner:** Labeling Team + Human Reviewer  
**Input:** Immutable data snapshot from Phase 1  
**Output:** Frozen ground truth (IMMUTABLE)  

**Specification:** `PHASE_2_GROUND_TRUTH_SPEC.md`

**Key Tasks:**
- [ ] Apply Q1 definition (label all dormant coins)
- [ ] Apply Q2 definition (identify resurrections)
- [ ] Resolve ambiguous cases (manual review, <5% threshold)
- [ ] Assign confidence levels (DEFINITE/PROBABLE/AMBIGUOUS)
- [ ] Freeze ground truth (immutable snapshot)

**Gate Criteria:**
- All 3,421 coins labeled
- Ambiguous cases < 5% (or resolved)
- Human verification sample (10-20%)
- Ground truth frozen (no post-hoc changes)

**Gate Decision:** PASS → Phase 3a | FAIL → Remediate

---

### ⏳ Phase 3a: PIT In-Sample Backtest (READY)

**Timeline:** Oct 23 - Oct 28, 2026  
**Status:** Specification complete, awaiting execution  
**Owner:** Data Science Team  
**Input:** Ground truth snapshot + OHLCV data (2020-2024)  
**Output:** Baseline AUC + RRP in-sample performance  

**Specification:** `PHASE_3_WALKFORWARD_SPEC.md` (Section 1)

**Key Tasks:**
- [ ] Pre-register baseline AUC (random classifier on ground truth distribution)
- [ ] Calculate RRP scores (all dormant coins 2020-2024)
- [ ] Measure PIT performance (AUC, precision, recall)
- [ ] Validate: AUC(RRP) > AUC(baseline) + 0.10

**Gate Criteria:**
- Baseline AUC pre-registered
- RRP performance ≥ baseline + 0.10
- Calibration curve monotonic
- Scores reproducible

**Gate Decision:** PASS → Phase 3b | FAIL → Debug components

---

### ⏳ Phase 3b: OOS Out-of-Sample Validation (READY)

**Timeline:** Oct 31 - Nov 10, 2026  
**Status:** Specification complete, awaiting execution  
**Owner:** Data Science Team  
**Input:** PIT results + OOS data (2025-2026)  
**Output:** OOS performance + degradation measurement  

**Specification:** `PHASE_3_WALKFORWARD_SPEC.md` (Section 2)

**Key Tasks:**
- [ ] Apply RRP logic to OOS period (no retuning)
- [ ] Measure performance on held-out data
- [ ] Quantify PIT→OOS degradation
- [ ] Validate: Degradation ≤ 0.12

**Gate Criteria:**
- OOS AUC ≥ baseline + 0.08
- Degradation ≤ 0.12 (no overfitting)
- Similar ranking across PIT/OOS
- No systemic bias (seasonal, regime)

**Gate Decision:** PASS → Phase 3c | FAIL → Overfitting suspected

---

### ⏳ Phase 3c: WFV Walk-Forward Simulation (READY)

**Timeline:** Nov 13 - Nov 17, 2026  
**Status:** Specification complete, awaiting execution  
**Owner:** Data Science Team  
**Input:** 5 rolling-window tests (train→test iterations)  
**Output:** Forward stability metrics  

**Specification:** `PHASE_3_WALKFORWARD_SPEC.md` (Section 3)

**Key Tasks:**
- [ ] Run 5 rolling windows (2020→2024, 2021→2025, etc.)
- [ ] Measure AUC stability across windows
- [ ] Check for time trends (degradation over time?)
- [ ] Validate: Variance ≤ ±0.08

**Gate Criteria:**
- All 5 windows AUC ≥ baseline + 0.05
- Variance ≤ ±0.08 (stability)
- No trend detected (p > 0.05)
- 4 of 5 windows within ±0.10 of mean

**Gate Decision:** PASS → Phase 4 | FAIL → Deployment stability risk

---

### ⏳ Phase 4: Ablation & Component Analysis (READY)

**Timeline:** Nov 20 - Dec 6, 2026 (2 weeks)  
**Status:** Specification complete, awaiting execution  
**Owner:** Data Science Team  
**Input:** Phase 3 results + component scores  
**Output:** Component importance ranking  

**Specification:** `PHASE_4_ABLATION_SPEC.md`

**Key Tasks:**
- [ ] Leave-one-out ablation (remove each component)
- [ ] Rank components by AUC contribution
- [ ] Classify: CRITICAL (≥0.05) | USEFUL (0.02-0.05) | MINIMAL (<0.02)
- [ ] Analyze component interactions
- [ ] Stratify by coin size, market regime
- [ ] Generate refactoring guidance

**Gate Criteria:**
- At least 2 components CRITICAL
- No negative contributions (no bugs)
- Total contribution ≥ 80% of AUC
- Components interpretable

**Gate Decision:** PASS (provides Phase 8 guidance) | INFORMATIONAL

---

### ⏳ Phase 5: Robustness & Statistical Validation (READY)

**Timeline:** Dec 6 - Dec 13, 2026 (1 week, overlaps Phase 4)  
**Status:** Specification complete, awaiting execution  
**Owner:** Data Science Team  
**Input:** OOS performance + component analysis  
**Output:** Stratified performance report + confidence intervals  

**Specification:** `PHASE_5_ROBUSTNESS_SPEC.md`

**Key Tasks:**
- [ ] Stratify performance (market regime, coin size, time, type)
- [ ] Sensitivity analysis (definition robustness)
- [ ] Bootstrap confidence intervals (1000 resamples)
- [ ] Uncertainty quantification (CI width ≤ 0.10)

**Gate Criteria:**
- No stratum AUC < baseline - 0.05
- Definition sensitivity ≤ ±0.03 impact
- CI width ≤ 0.10 (tight estimates)
- No systemic bias across segments

**Gate Decision:** PASS (production confidence) | PASS_WITH_CAVEATS (known limitations)

---

### ⏳ Phase 6: Final Gate Review (READY)

**Timeline:** Dec 13 - Dec 20, 2026 (1 week)  
**Status:** Specification complete, awaiting execution  
**Owner:** Human Authority + Technical Team  
**Input:** All Phase 1-5 results + reports  
**Output:** VALIDATED_ALPHA or REWORK decision  

**Specification:** `PHASE_6_FINAL_GATE_SPEC.md`

**Key Tasks:**
- [ ] Compile all phase results (1-5)
- [ ] Pre-specification integrity audit (Phase 0-5 deliverables verified)
- [ ] Performance validation (all metrics calculated against thresholds)
- [ ] Assumptions validation (Q1-Q9 remain valid)
- [ ] Critical findings synthesis
- [ ] Final gate decision: VALIDATED_ALPHA or REWORK

**Gate Criteria:**
- All phases PASS (or documented remediation)
- All performance thresholds met (≥95% likelihood)
- All pre-registration assumptions valid
- No major surprises or failure modes
- Component ranking interpretable
- Confidence intervals tight (≤ 0.10)

**Gate Decision:** VALIDATED_ALPHA → Phase 7 | REWORK → Return to specific phases

---

### ⏳ Phase 7: Immutable Snapshot & Deployment Readiness (READY)

**Timeline:** Dec 20 - Dec 27, 2026  
**Status:** Specification complete, awaiting execution  
**Owner:** Data Team + Technical Lead  
**Input:** Phase 6 VALIDATED_ALPHA decision  
**Output:** Immutable RRP snapshot for production deployment  

**Specification:** `PHASE_7_DEPLOYMENT_READINESS_SPEC.md`

**Key Tasks:**
- [ ] Freeze all component definitions (immutable)
- [ ] Create immutable RRP model snapshot (versioned, SHA256 hashed)
- [ ] Serialize model + ground truth reference
- [ ] Generate model card (VALIDATED_ALPHA 1.0.0)
- [ ] Write deployment guide (installation, usage, monitoring)
- [ ] Create Layer 8 integration checklist
- [ ] Archive immutable artifact for permanent storage

**Deliverables:**
- Immutable RRP model artifact (tar.gz, hashed)
- Model metadata + component definitions + performance metrics
- Ground truth reference snapshot (frozen)
- Model card (performance, assumptions, limitations, deployment restrictions)
- Deployment guide (installation, usage, Layer 8 integration)
- Layer 8 integration checklist (pre-integration, integration steps, post-deployment SLA)
- Archival certificate (SHA256, signatures)

---

## Timeline Chart

```
Sep 2026                                              Dec 2026
  │
  ├─ Sep 25: PHASE 0 SPEC FREEZE OPEN
  │           Q1-Q9 definitions locked
  │
  ├─ Oct 02-09: Phase 0 Complete
  │             Timeline begins
  │
  ├─ Oct 09-23: PHASE 1 Data Audit ═════════════════════
  │             (Collection, quality checks, immutable snap)
  │
  ├─ Oct 16-23: PHASE 2 Ground Truth ═════════════════════
  │             (Overlaps Phase 1, completes by Oct 23)
  │
  ├─ Oct 23-28: PHASE 3a PIT Backtest ═══
  │             (In-sample 2020-2024)
  │
  ├─ Oct 31-11/10: PHASE 3b OOS Validation ═════════
  │                (Out-of-sample 2025-2026)
  │
  ├─ 11/13-17: PHASE 3c WFV Simulation ════
  │            (Walk-forward 5 windows)
  │
  ├─ 11/20-12/6: PHASE 4 Ablation ═════════════════
  │              (Component importance)
  │
  ├─ 12/6-13: PHASE 5 Robustness ════════════
  │           (Stratification, sensitivity, CI)
  │           (Overlaps with Phase 4)
  │
  ├─ 12/13-20: PHASE 6 Gate Review ════════════════
  │            (Final decision: VALIDATED_ALPHA or REWORK)
  │
  └─ 12/20-27: PHASE 7 Deployment Ready ═════════
              (Immutable snapshot, model card, integration)
```

---

## Critical Pre-Requisites

### Before Phase 1 Begins (Oct 9)
- [x] Phase 0 Spec Freeze complete
- [x] Q1-Q9 definitions locked and immutable
- [x] Baseline methodology pre-registered
- [x] Data audit specification ready
- [x] Human approval for Phase 0

### Before Phase 3 Begins (Oct 23)
- [x] Phase 1 data collection complete (Oct 23)
- [x] Phase 2 ground truth frozen (Oct 23)
- [x] All definitions immutable
- [x] No data collection occurs before Phase 0 Spec Freeze

### Before Phase 6 Begins (Dec 13)
- [x] All Phases 1-5 complete and PASS
- [x] All gate decisions documented
- [x] Any FAIL phases remediated

---

## Governance Checkpoints

| Phase | Gate Required | Authority | PASS Condition |
|-------|---------------|-----------|----------------|
| 0 | Spec Freeze | Human | Q1-Q9 locked |
| 1 | Data Quality | QA + Human | ≥95% complete + approved |
| 2 | Ground Truth | QA + Human | 100% labeled + frozen |
| 3a | PIT Performance | Data Scientist | AUC > baseline + 0.10 |
| 3b | OOS Generalization | Data Scientist | Degradation ≤ 0.12 |
| 3c | WFV Stability | Data Scientist | Variance ≤ ±0.08 |
| 4 | Component Analysis | Data Scientist | ≥2 CRITICAL components |
| 5 | Robustness | Data Scientist | Strata consistent + robust |
| 6 | Final Review | Human Authority | VALIDATED_ALPHA decision |
| 7 | Deployment Ready | Technical Lead | Snapshot ready for Layer 8 |

---

## Key Principles

### 1. Immutability
Once Phase 0 Spec Freeze opens, Q1-Q9 definitions are LOCKED. Zero post-hoc modifications, even if results suggest changes.

### 2. Pre-Registration
Baseline, tolerances, acceptance criteria all specified BEFORE data collection or testing.

### 3. Sequential Gates
Each phase blocks the next. No skipping phases. All phases must PASS (or document caveats) before Phase 6.

### 4. Human Authority
Every phase gate requires human approval. Automation enforces pre-specified criteria, but humans decide interpretation.

### 5. Lookahead Bias Prevention
- Q2 ground truth definitions frozen before Phase 1 data collection
- Component scoring fixed before Phase 3 backtesting
- No retraining on test sets (OOS/WFV)

### 6. Isolation
RRP validation is isolated from IGWT-PF26 Layers 1-6 until VALIDATED_ALPHA gate passes. No integration until Phase 7.

---

## Known Risks & Mitigations

### Risk 1: Data Quality Issues Cause Phase 1 FAIL

**Mitigation:** Phase 1 includes 2-week buffer for gap remediation and re-audit.

### Risk 2: RRP Underperforms Baseline in Phase 3a

**Mitigation:** Phase 4 ablation will identify weak components. Fallback: redesign components and return to Phase 1-3.

### Risk 3: OOS Degradation > 0.12 (Overfitting)

**Mitigation:** Phase 4 component analysis + Phase 5 robustness will diagnose. Possible fallback: simplify RRP scoring.

### Risk 4: Definition Changes Suggested by Early Results

**Mitigation:** Q1-Q9 are LOCKED and immutable. Changes require formal change-control process (out of scope for this alpha validation).

---

## Integration with IGWT-PF26

### Current Status
- Phases 0-7 are **isolated from** Layers 1-8
- RRP validation is research experiment, not production system

### Post-Validation (Dec 20+)
- If Phase 6 → **VALIDATED_ALPHA:** Proceed to Phase 7 (immutable snapshot)
- If Phase 7 completes: Ready for **optional** Layer 8 (Dashboard) integration
- Layer 8 integration requires separate governance review (not covered in this spec)

### Never
- No automatic execution of trade signals from RRP
- No integration into automated systems
- All RRP outputs are research only until human approval at Layer 8

---

## Success Criteria (Overall)

RRP alpha validation is **complete and successful** when:

✅ Phase 0: Q1-Q9 definitions locked and immutable  
✅ Phase 1: Data complete and quality-audited  
✅ Phase 2: Ground truth labeled and frozen  
✅ Phase 3: Walk-forward testing shows reproducible performance  
✅ Phase 4: Components ranked and interpreted  
✅ Phase 5: Robustness confirmed across strata  
✅ Phase 6: Human authority grants VALIDATED_ALPHA decision  
✅ Phase 7: Immutable snapshot created for deployment readiness  

**If all phases PASS:** RRP is **statistically valid, robust, and ready for potential production use** (subject to Layer 8 governance).

**If any phase FAIL:** Specific phase is remediated, or RRP is determined to **require redesign before production consideration**.

---

## Documents Reference

| Document | Coverage |
|----------|----------|
| `RRP_VALIDATION_SPEC.md` | Master specification + Q1-Q9 framework |
| `PHASE_1_DATA_AUDIT_SPEC.md` | Data collection + quality validation |
| `PHASE_2_GROUND_TRUTH_SPEC.md` | Ground truth labeling + freeze |
| `PHASE_3_WALKFORWARD_SPEC.md` | PIT/OOS/WFV testing methodology |
| `PHASE_4_ABLATION_SPEC.md` | Component importance analysis |
| `PHASE_5_ROBUSTNESS_SPEC.md` | Stratification + sensitivity + CI |
| `RRP_VALIDATION_ROADMAP.md` | This document (master timeline) |

---

**Master Timeline Frozen:** 2026-09-25  
**Execution Begins:** 2026-10-09  
**Final Gate:** 2026-12-20  
**Status:** Ready for Phase 1 execution
