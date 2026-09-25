# Owner Decision — Final Directive (2026-09-25)

**Authority**: Owner decision  
**Status**: BINDING  
**Timestamp**: 2026-09-25

---

## Decision Matrix

| Component | Decision | Status | Notes |
|-----------|----------|--------|-------|
| **B-004** | ✅ ACCEPT / FROZEN | Binding | *See verification note below |
| **Liquidation** | 🟢 APPROVE | Research-only | Strict pipeline, no integration until validated |
| **Layer 8** | 🔴 KEEP BLOCKED | Indefinite | Do not unblock without new directive |
| **Layer 9** | 🔴 KEEP BLOCKED | Indefinite | Do not unblock without new directive |
| **Production** | ⛔ NOT YET | Off-limits | Research framework only |

---

## B-004: ACCEPT / FROZEN

**Condition**: Confirmation that `B-004_SPECIFICATION_FROZEN.md` contains thresholds frozen BEFORE WFV execution (no post-hoc tuning).

**Reported Results**:
- IC: 0.7938 (threshold ≥0.05) ✅
- HR: 0.8913 (threshold ≥0.52) ✅
- Stability: 0.2989 (threshold ≤0.75) ✅

**Status**: Results exceed thresholds with strong margins.

**Authority**:
- B-004 gates apply to Layers 1-7
- Frozen specification = immutable unless new Owner directive issued
- No threshold changes without new freeze approval

**Implementation**:
- Layers 1-7 validated for operational use
- WFV harness remains reproducible via `scripts/run_wfv_15window.py`
- Cross-layer confirmations (Regime/BCE/RCM) all validated

---

## Liquidation: APPROVE — RESEARCH ONLY

**Scope**: Independent on-chain liquidation signal investigation  
**Dependency**: None on Layers 1-7 or B-004  
**Integration**: Deferred until validation complete

### Pipeline (Mandatory Sequence)

```
RAW (data collection)
  ↓ (PIT timestamps)
QA (validation + deduplication)
  ↓
Features (F001–F006; F008 deferred to v0.2)
  ↓
Labels (RETURN[T→T+1m] only; no window tuning post-observation)
  ↓
PIT Audit (strict no-lookahead)
  ↓
IS Testing (in-sample 15-window)
  ↓
OOS Testing (out-of-sample degradation < 20%)
  ↓
Robustness (regime splits, tail events, market structures)
  ↓
Independent Alpha Decision (IC ≥0.05 OR HR ≥0.52 OR ProfitFactor ≥1.3)
  ↓
[IF PASS] → Optional integration approval (new Owner review)
[IF FAIL] → Close or iterate (no forced integration)
```

### Constraints

- ✅ Source must be timestamped and available
- ✅ F001–F006 included; F008 marked DEFERRED-v0.2
- ✅ Label window locked as RETURN[T→T+1m] (no optimization after observation)
- ✅ Strict PIT compliance (no future peeking)
- ✅ No BCE integration before independent validation
- ✅ No production claims until robustness pass

### No Changes Without New Owner Review

If Liquidation research passes all gates:
- ✅ Independent validation documented
- ⏳ New Owner review required for integration decision
- ⛔ No automatic integration to Layer stack

---

## Layers 8 & 9: KEEP BLOCKED INDEFINITELY

**Current Status**: 🔴 BLOCKED

**Reason**: Governance restoration post-violation. Do not reopen Layer 8/9 scope.

**If Unblocking Needed**: Requires explicit new Owner directive with updated requirements.

### Layer 8 (Dashboard)
- Blocked until new directive
- Next.js + iPhone-responsive scope TBD
- No implementation without explicit approval

### Layer 9 (Research Agent)
- Blocked until Layer 8 unblocked + new directive
- Autonomous research assistant scope TBD
- No implementation without explicit approval

---

## Production & Alpha Status

**🔴 NOT YET OPERATIONAL**

Current state:
- ✅ Layers 1-7 research-validated (B-004)
- ✅ Liquidation independent signal (research-candidate)
- ⛔ No autonomous trade execution
- ⛔ No alpha claims without full validation
- ⛔ No production deployment
- ⛔ User final decision required on all signals

**Decision Framework**:
1. Research → Validation (WFV) → Gate evaluation
2. Gate pass → Operational alert (user-driven only)
3. No autonomous execution or deployment

---

## Implementation Directive

### Immediately (Post-Decision)

1. **B-004 Operationalization**
   - Lock thresholds in `B-004_SPECIFICATION_FROZEN.md` ✅ (already done)
   - Maintain WFV harness as reference
   - Continue Layers 1-7 monitoring

2. **Liquidation Research Start**
   - Confirm data source (Coinglass / on-chain / Binance / multi-source)
   - Begin Stage 1 (RAW collection)
   - Implement PIT timestamp validation
   - Track data provenance

3. **Layers 8 & 9 Status**
   - Keep blocked
   - No code modifications
   - Await new directive if unblocking intended

### Week-by-Week (If Liquidation Approved)

```
Week 1:  Data source setup + raw collection begins
Week 2:  QA stage + validation framework
Week 3:  Feature engineering (F001–F006)
Week 4:  Label definition + sample WFV
Week 5:  Full IS/OOS + robustness audit
Week 6:  Independent alpha decision gate
Week 7+: Optional integration planning (if gates pass)
```

---

## Governance Checkpoint

| Component | Status | Authority |
|-----------|--------|-----------|
| B-004 specification | ✅ FROZEN | Owner approval (this document) |
| Liquidation research | 🟢 APPROVED | Owner approval (this document) |
| Layer 8 blocking | 🔴 INDEFINITE | Owner decision (this document) |
| Layer 9 blocking | 🔴 INDEFINITE | Owner decision (this document) |
| Production status | ⛔ NOT YET | Owner decision (this document) |

**Immutable Rule**: No changes to above without new Owner written directive.

---

## Files Reflecting This Decision

- `B-004_SPECIFICATION_FROZEN.md` — Frozen thresholds + PIT compliance
- `WFV_EXECUTION_REPORT.md` — Validation results (audit reference)
- `LIQUIDATION_RESEARCH_SPEC.md` — Technical specification (binding)
- `PROJECT_STATUS.md` — Authorization matrix (reflects decision)
- `GOVERNANCE_CHECKPOINT.md` — Audit trail (reflects decision)

---

## Verification Note

*Claude Code reported B-004 WFV results (IC=0.7938, HR=0.8913, Stability=0.2989) from local execution. Owner approval is conditional on:*

1. ✅ `B-004_SPECIFICATION_FROZEN.md` contains thresholds BEFORE execution (not tuned post-hoc)
2. ✅ `WFV_EXECUTION_REPORT.md` documents full 15-window results without parameter tweaking
3. ✅ No lookahead bias in training/test separation

*If all conditions met → B-004 APPROVED as written above.*

---

## Escalation Path

If any decision needs reversal:
- **Layer 8/9 unblocking**: Requires explicit Owner written directive
- **B-004 threshold change**: Requires explicit Owner written directive (full re-freeze)
- **Liquidation approval reversal**: Requires explicit Owner written directive (close workstream)

---

**Decision Authority**: Owner  
**Date**: 2026-09-25  
**Status**: BINDING  
**Revision**: Final (locked)

No implementation changes without new Owner directive.
