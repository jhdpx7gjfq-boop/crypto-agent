# B-004: Acceptance Gate Specification

**Status**: DRAFT (awaiting Owner freeze)  
**Purpose**: Formal definition of signal validation thresholds for Layers 1-7

---

## Gate Thresholds (Candidate Values — Not Yet Frozen)

These are **research suggestions only**. Owner approval required to freeze.

| Metric | Candidate Threshold | Source | Notes |
|--------|-------------------|--------|-------|
| Information Coefficient (IC) | ≥ 0.05 | WFV harness | Predictive power |
| Hit Rate (HR) | ≥ 0.52 | WFV harness | Win rate > random |
| Stability | ≤ 0.75 | WFV harness | Coefficient of variation |
| Regime Confidence | ≥ 0.70 | Layer 2 | Market context clarity |
| BCE Score | ≥ 5/6 | Layer 3 | Entry confirmation |
| RCM Confirmation | ≥ 0.65 | Layer 6 | Rotation hypothesis |

---

## Validation Process (Pre-Freeze Checklist)

- [ ] Layer 1-7 implementation audit complete
- [ ] PIT compliance verified (no lookahead)
- [ ] Sample WFV run (15-window) executed
- [ ] RPM/RCM cross-audit against thresholds
- [ ] Owner review & approval
- [ ] **FREEZE** thresholds in this document
- [ ] Full WFV run (all historical windows)
- [ ] IC/HR/Stability measurement vs frozen gates
- [ ] Ablation testing (remove each layer, measure degradation)
- [ ] Robustness testing (different market regimes)
- [ ] Final gate decision

---

## Candidate Rationale

**IC ≥ 0.05**: Minimal Spearman correlation to demonstrate non-random signal  
**HR ≥ 0.52**: Win rate 2% above 50% random baseline  
**Stability ≤ 0.75**: Consistent performance across windows  

**Regime Confidence ≥ 0.70**: Market context sufficiently clear to trade  
**BCE ≥ 5/6**: Wyckoff structure well-defined for entry  
**RCM ≥ 0.65**: Capital rotation hypothesis confirmed  

---

## Not Yet Decided

- Phase-out timing (how long to run gates?)
- Lookback windows (30d vs 60d vs 90d?)
- Regime-specific adjustments (different thresholds for RISK_ON vs RISK_OFF?)
- Layer-specific overrides (e.g., can Layer 4 override if X20 score > 0.85?)
- Drawdown tolerance (max % loss before circuit-breaker?)

---

## Owner Action Required

To freeze B-004:

```text
1. Review candidate thresholds above
2. Approve or modify each threshold
3. Confirm PIT/no-lookahead compliance
4. Sign off on validation process
5. Date & timestamp this freeze
6. Archive frozen version
```

**Once frozen**: No changes without new Owner review.

---

## Status

- **Candidate thresholds**: Posted 2026-09-25
- **Owner review**: AWAITING
- **Freeze date**: TBD
- **Full WFV**: TBD (after freeze)
- **Final gate decision**: TBD (post WFV)

---

*This is a template. Actual B-004 specification requires Owner approval before execution.*
