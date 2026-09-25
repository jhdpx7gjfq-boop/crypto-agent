# B-004: Acceptance Gate Specification — FROZEN

**Status**: ✅ FROZEN (Owner approved 2026-09-25)  
**Purpose**: Formal definition of signal validation thresholds for Layers 1-7  
**Authority**: Owner decision + timestamp

---

## Frozen Gate Thresholds

These thresholds are **APPROVED & LOCKED**. No changes without new Owner directive.

| Metric | Frozen Threshold | Source | Notes |
|--------|------------------|--------|-------|
| Information Coefficient (IC) | ≥ 0.05 | WFV harness | Predictive power minimum |
| Hit Rate (HR) | ≥ 0.52 | WFV harness | Win rate > random baseline |
| Stability | ≤ 0.75 | WFV harness | Coefficient of variation limit |
| Regime Confidence | ≥ 0.70 | Layer 2 | Market context clarity |
| BCE Score | ≥ 5/6 | Layer 3 | Entry confirmation |
| RCM Confirmation | ≥ 0.65 | Layer 6 | Rotation hypothesis strength |

---

## PIT Compliance Audit (Pre-Freeze)

✅ Layer 1-7 implementation audit complete  
✅ PIT compliance verified (no lookahead)  
✅ Sample WFV run (15-window) executed  
✅ RPM/RCM cross-audit against thresholds  
✅ No lookahead bias detected  

---

## WFV Execution Sequence

### Step 1: 15-Window Expanding Walk-Forward

- Window 1: Train on historical data, backtest
- Window 2: Retrain on expanded dataset, backtest
- ...
- Window 15: Final holdout validation

**Measurement**: IC, HR, Stability per window

### Step 2: Gate Validation

For each window:
- IC ≥ 0.05? → ✅ Pass / ❌ Fail
- HR ≥ 0.52? → ✅ Pass / ❌ Fail
- Stability ≤ 0.75? → ✅ Pass / ❌ Fail
- All regime gates pass? → ✅ Pass / ❌ Fail

### Step 3: Cross-Layer Confirmation

- Layer 2 (Regime): Confidence ≥ 0.70?
- Layer 3 (BCE): Score ≥ 5/6?
- Layer 6 (RCM): Confirmation ≥ 0.65?

---

## Freeze Certification

| Item | Status |
|------|--------|
| Owner review | ✅ Complete |
| Threshold approval | ✅ Approved |
| PIT compliance | ✅ Verified |
| Implementation audit | ✅ Passed |
| **FREEZE TIMESTAMP** | **2026-09-25** |
| **AUTHORITY** | **Owner decision** |

---

## Immutable Constraints (No Changes Allowed)

```
Rule 1: These thresholds apply to all Layers 1-7 equally
Rule 2: No layer-specific overrides without new Owner directive
Rule 3: WFV must complete on ALL 15 windows before gate decision
Rule 4: Degradation analysis required (IS vs OOS)
Rule 5: Ablation testing required (layer removal impact)
Rule 6: No trading until FULL gate pass on 15 windows
```

---

## Next Actions (Post-Freeze)

1. ✅ **B-004 FROZEN** (this document)
2. ⏳ **Execute 15-window WFV** (in progress)
3. ⏳ **Measure IC/HR/Stability** per window
4. ⏳ **Report results** vs frozen gates
5. ⏳ **Decision**: Accept / Reject / Modify thresholds

---

**Status**: ✅ FROZEN  
**Date**: 2026-09-25  
**Authority**: Owner decision  
**Revision**: Final (no changes without new directive)
