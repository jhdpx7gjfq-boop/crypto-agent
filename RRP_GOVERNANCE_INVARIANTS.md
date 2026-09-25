# RRP Governance Invariants (P0 Gate Lock)

**Status:** RESEARCH-CANDIDATE under P0 validation  
**Layer 8:** BLOCKED  
**Effective:** 2026-09-25  
**Authority:** IGWT-PF26 Governance  

---

## Official Status

```
RRP implementation        ✅ GREEN (168 tests, CI passing)
RRP validation spec       ✅ COMMITTED (RRP_VALIDATION_SPEC.md)
Governance / CI           ✅ GREEN
RRP alpha validation      ⏳ NOT YET (awaiting gate P0)
Layer 8 RPM/X20           🔒 BLOCKED
```

---

## Invariant 1: Immutability During Validation

**Rule:** No modifications to RRP code, scoring logic, or snapshot store during validation gate execution.

**Exception:** Blocking bug only. Process:
1. Document blocking bug with evidence (failing test, crash trace)
2. Create new version branch: `rrp-v2` (increment minor version)
3. Fix bug on new branch
4. **Restart entire validation gate from Stage 1** (no partial re-runs)
5. Both v1 and v2 validation results retained for audit trail

**Locked Elements:**
- `rrp_engine.py` code (all 6 signals)
- Snapshot immutability mechanism
- Score calculation formula
- Threshold values (REVIVING ≥60, WAKING 40-59, DORMANT <40)

**Enforcement:** 
- PRs modifying RRP during validation are automatically rejected
- Merge to main only after VALIDATED ALPHA gate pass

---

## Invariant 2: No Tuning on OOS/WFV Data

**Rule:** Zero parameter tuning, threshold adjustment, or signal reweighting based on OOS/WFV performance.

**Why:** Tuning on test data = lookahead bias = strategy death.

**What IS allowed:**
- Observation of OOS/WFV results for documentation
- Comparison vs baselines (unchanged)
- Measurement of regime-dependency (unchanged)

**What IS NOT allowed:**
- Adjusting signal weights (e.g., capital_flow 25% → 30%)
- Changing thresholds (e.g., REVIVING ≥60 → ≥55)
- Adding/removing signals based on OOS results
- Cherry-picking winners or reordering signals

**Enforcement:**
- Validation spec is locked; deviations documented as violations
- Any tuning = gate FAIL, restart from Stage 1 with frozen parameters

---

## Invariant 3: No RRP Consumption Before Formal GO

**Rule:** Layer 8 (RPM X20 Optimizer) has ZERO access to RRP until VALIDATED ALPHA gate PASS.

**Layer 8 Blockers:**
- ❌ Cannot import RRPEngine
- ❌ Cannot call score_rrp()
- ❌ Cannot use RRP snapshots or history
- ❌ Cannot depend on RRP verdict in any form

**Timeline:**
1. RRP validation gate runs (Stages 1-9, ~9 days)
2. Decision memo published (VALIDATED ALPHA / RESEARCH / REJECT)
3. If VALIDATED ALPHA:
   - RRP_VALIDATION_SPEC.md + 10 audit artifacts frozen
   - Data contract locked (version tagged)
   - Layer 8 unblocked for implementation
4. If RESEARCH or REJECT:
   - Layer 8 remains blocked
   - RRP iteration cycle begins (new branch, revalidate)

**Enforcement:**
- Layer 8 code review will reject any RRP dependencies
- CI build fails if Layer 8 imports RRP before gate pass
- Documentation requirement: Layer 8 README must declare "RRP dependency: BLOCKED until validation gate PASS"

---

## Audit Artifact Versioning

### Required Artifacts (Locked at Gate PASS)

All 10 artifacts must be versioned and immutable:

```
RRP_VALIDATION_SPEC.md          (governance document)
├── PIT_AUDIT.md                (Signal independence)
├── LOOKAHEAD_AUDIT.md          (No future leakage)
├── SNAPSHOT_AUDIT.md           (Immutability verification)
├── BASELINE_COMPARISON.md      (IC vs baselines)
├── OOS_REPORT.md               (Overfitting analysis)
├── WFV_REPORT.md               (Daily sim results)
├── ABLATION_REPORT.md          (Signal contribution)
├── ROBUSTNESS_REPORT.md        (Regime + cross-asset)
├── STATISTICAL_TEST.md         (Significance p<0.05)
└── DECISION_MEMO.md            (Final verdict)
```

### Versioning
- Each artifact tagged with:
  - Date generated
  - RRP version (v1, v2, etc.)
  - Validation run ID
  - Committer signature
- No retrospective modification after gate runs
- If audit result must be corrected: new run, new version

### Reproducibility
- All data inputs stamped (OHLCV source, date range, universe)
- Random seeds fixed (if any Monte Carlo)
- Code version locked (commit hash)
- Results traceable back to exact RRP implementation

---

## Gate Decision & Layer 8 Unblock Criteria

### VALIDATED ALPHA ✅
**Conditions:**
- All 9 stages: PASS
- Walk-forward win rate ≥55%
- IC ≥ baseline IC (information advantage confirmed)
- p-value <0.05 (statistically significant)
- Zero lookahead bias
- Snapshots provably immutable
- At least 3 of 6 signals show independent information

**Action:** RRP frozen as input contract, Layer 8 unblocked

**Artifact:** `DECISION_MEMO.md` signed "VALIDATED ALPHA — Layer 8 unblocked"

### RESEARCH (CONDITIONAL) 🟡
**Conditions:**
- Stages 1-3, 9: PASS
- Stages 4-8: MARGINAL (performance <10%, regime-dependent)
- Information present but not robust enough for production

**Action:** Layer 8 remains blocked, RRP iteration cycle begins

**Artifact:** `DECISION_MEMO.md` signed "RESEARCH CANDIDATE — Iterate signal design"

### REJECT ❌
**Conditions:**
- Any of: Stage 2 (lookahead), Stage 3 (immutability), Stage 9 (not significant) = FAIL
- No independent predictive information
- Results attributable to randomness

**Action:** Layer 8 blocked indefinitely; RRP redesign or closure

**Artifact:** `DECISION_MEMO.md` signed "REJECTED — No predictive edge"

---

## Governance Record

| Date | Event | Status | Authority |
|------|-------|--------|-----------|
| 2026-09-25 | RRP implementation complete | ✅ GREEN | Claude Code Session |
| 2026-09-25 | Validation spec committed | ✅ COMMITTED | IGWT-PF26 Gov |
| 2026-09-25 | Invariants locked | 🔒 FROZEN | IGWT-PF26 Gov |
| TBD | Validation gate Stages 1-9 | ⏳ IN PROGRESS | Audit |
| TBD | Decision memo published | TBD | Audit |
| TBD | Layer 8 unblock decision | TBD | Gov |

---

## No Exceptions

This document is the binding governance contract for RRP.

- No expedited path to Layer 8
- No partial gate validation
- No "we'll validate later"
- No tuning on OOS/WFV data
- No code changes during validation (except blocking bugs with full rerun)

**Principle:** Implementation correctness (168 tests) ≠ Strategy validity (validation gate).

---

**Signatures:**  
IGWT-PF26 Governance  
Effective: 2026-09-25  
Next review: Post-validation gate decision
