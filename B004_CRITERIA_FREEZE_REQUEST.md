# B-004: Criteria Freeze Request

**Date:** 2026-09-25  
**Status:** AWAITING OWNER APPROVAL  
**Authority:** IGWT-PF26 Phase 6 Gate Governance  
**Blocker:** B-004 WFV cannot execute until criteria frozen

---

## Issue

Two different criteria sets exist for B-004 gate decision:

### Set A (In current b004_wfv.py implementation):
```python
IC threshold:        >= 0.05
HR threshold:        >= 0.55 (55%)
Stability threshold: <  0.50
```

### Set B (Previously proposed):
```python
IC threshold:        >= 0.05
HR threshold:        >= 0.52 (52%)
Stability threshold: <= 0.75
```

### Difference Impact:
- **HR:** 55% vs 52% = 3% difference → affects PASS/FAIL outcome
- **Stability:** 0.50 vs 0.75 = 0.25 difference → affects PASS/FAIL outcome

A single B-004 execution with wrong thresholds invalidates the entire validation gate.

---

## Governance Constraint

**B-004 Immutability Invariant #1:** Criteria must be frozen BEFORE execution.

**B-004 Immutability Invariant #2:** Post-hoc threshold adjustment is forbidden.

**Consequence:** We must freeze one criteria set NOW, before running B-004, or risk compromising the entire validation gate.

---

## Proposed Resolution

### Option 1: Approve Set A (Current Implementation)
```yaml
IC:        >= 0.05
HR:        >= 55%
Stability: < 0.50
```

**Rationale:** Tighter thresholds = higher bar for PASS = more conservative  
**Owner sign-off:** Required with timestamp

### Option 2: Approve Set B (Previously Proposed)
```yaml
IC:        >= 0.05
HR:        >= 52%
Stability: <= 0.75
```

**Rationale:** Relaxed thresholds = reflects earlier negotiation  
**Owner sign-off:** Required with timestamp

### Option 3: Define New Set C
```yaml
IC:        >= 0.05
HR:        >= X%
Stability: <= Y
```

**Rationale:** Owner-specified thresholds  
**Owner sign-off:** Required with timestamp and justification

---

## Execution Timeline

**Current state:** BLOCKED
```
Data acquisition     ✅ READY (scripts written)
Data validation      ✅ READY (scripts written)
B-004 WFV            🔴 BLOCKED (waiting for frozen criteria)
Gate decision        🔴 BLOCKED (depends on WFV)
Layer 8 unblock      🔴 BLOCKED (depends on gate PASS)
```

**After criteria frozen:**
```
Criteria frozen      ⏳ AWAITING OWNER
Data acquisition     ✅ EXECUTE (local machine)
Data push            ✅ EXECUTE (commit/push)
B-004 WFV            ✅ EXECUTE (cloud, 4-8 hours)
Gate evaluation      ✅ EXECUTE (frozen thresholds)
Layer 8 decision     ✅ CONDITIONAL (if PASS + VALIDATED_ALPHA)
```

---

## Recommendation

**Propose Set A** (current implementation: IC ≥ 0.05, HR ≥ 55%, Stability < 0.50)

**Rationale:**
1. More stringent = more defensible against market regime variability
2. Matches governance principle: "Validation > intuition"
3. If B-004 passes stricter thresholds, confidence in alpha is higher

**But this is Owner's decision.** Set B is also valid; the key is to FREEZE one before execution.

---

## Implementation Path (Post-Freeze)

Once criteria frozen and approved:

1. Update `b004_wfv.py` line 172-174 with frozen thresholds
2. Add frozen timestamp to code comment
3. Commit: `"B-004: Freeze criteria (Owner approved YYYYMMDD)"`
4. Proceed with Option A data acquisition
5. Execute B-004 WFV
6. Evaluate against frozen thresholds (no adjustments)

---

## Blocking Questions

**Q1:** Which criteria set (A, B, or new C)?  
**Q2:** Timestamp of approval?  
**Q3:** Any written justification for choice?

**Answer required before:** Running `b004_wfv.py`

---

## Current Code State

**b004_wfv.py (lines 172-174) — Set A (SUBJECT TO CHANGE):**
```python
pass_ic = mean_ic >= 0.05
pass_hr = mean_hr >= 0.55
pass_stability = stability < 0.50
```

---

## Files Affected by Freeze

Once approved:
- `b004_wfv.py` (update thresholds + timestamp comment)
- `B-004_SPECIFICATION.md` (update with frozen values + approval)
- Commit message (reference Owner approval date)

---

**Status:** AWAITING OWNER DECISION  
**Impact:** Critical path blocker for Layer 8 unblock  
**Timeline:** Decision required before Option A execution can proceed to WFV step

Owner approval required on specific criteria set + timestamp before committing frozen code.
