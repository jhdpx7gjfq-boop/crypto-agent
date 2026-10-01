# Phase 5: NARM-P+ Production — Complete Specification

**Status**: IN PROGRESS  
**Version**: v0.1.0  
**Date**: 2026-10-01  
**Target**: Production-ready by 2026-10-20

---

## Mission

NARM-P+ (Narrative Adoption Rotation Model + Premium) is **Layer 5** for detecting **narrative-driven opportunities** before widespread adoption.

**Goal**: Identify sectors/narratives rotating into investor attention, measure adoption velocity, and detect capital flows.

**NOT a primary entry signal** — used for **opportunity discovery** and **sector watchlist filtering**.

---

## Current Status

### ✅ Implemented (Core Engine)

| Component | Status | Details |
|-----------|--------|---------|
| **NARM Engine** | ✅ | Core scoring logic (4 dimensions) |
| **Narrative Scoring** | ✅ | Momentum, sentiment, engagement, clarity |
| **Adoption Scoring** | ✅ | User growth, dev activity, tx volume, network effects |
| **Capital Rotation** | ✅ | Inflow, sector rotation, whale accumulation, fund flows |
| **Momentum Scoring** | ✅ | Price momentum, volume trend, volatility, breakout |
| **Integration Tests** | ✅ | 13/13 core tests passing |

### 🔲 TODO (Production Hardening)

1. **Multi-Asset Rotation Analysis** — Compare narratives across assets
2. **Sector Rotation Engine** — Detect category-level capital flows
3. **Narrative Trend Tracking** — Track adoption curve progression
4. **Capital Flow Confirmation** — On-chain inflow validation
5. **Layer 5 ↔ Layer 3/4 Integration** — Combined decision scoring
6. **Sensitivity Analysis** — Parameter robustness testing
7. **Walk-Forward Validation** — Historical narrative performance
8. **Documentation** — Usage guide, tuning parameters

---

## Architecture

### 4 Dimensions (30/25/25/20 weights)

```
NARM Score (0-100)
├── Narrative Strength (30%)
│   ├── Narrative Momentum (30/100)
│   ├── Media Sentiment (25/100)
│   ├── Community Engagement (25/100)
│   └── Story Clarity (20/100)
├── Adoption Velocity (25%)
│   ├── User Growth Rate (30/100)
│   ├── Developer Activity (25/100)
│   ├── Transaction Growth (25/100)
│   └── Network Effects (20/100)
├── Capital Rotation (25%)
│   ├── Capital Inflow (30/100)
│   ├── Sector Rotation (25/100)
│   ├── Whale Accumulation (25/100)
│   └── Institutional Interest (20/100)
└── Momentum (20%)
    ├── Price Momentum (30/100)
    ├── Volume Trend (25/100)
    ├── Volatility Expansion (25/100)
    └── Breakout Strength (20/100)
```

### Rotation Candidate Threshold

- **Threshold**: NARM score ≥ 65/100
- **Confidence Tiers**:
  - High: ≥75
  - Medium: 60-75
  - Low: <60
- **Timing Assessment**:
  - Early: <50 adoption + <60 narrative
  - Mid: 50+ adoption OR 60+ narrative
  - Late: 70+ adoption AND 70+ narrative

---

## New Components (Phase 5)

### 1. Sector Rotation Tracker

```python
class SectorRotationTracker:
    """Track capital flows between narrative sectors."""
    
    def detect_sector_rotation(
        self,
        assets_data: Dict[str, NARMSignal],
    ) -> SectorRotationSignal:
        """Detect rotation patterns across sectors."""
```

**Tracks**:
- Top 5 narratives by NARM score
- Sector weighting changes
- Inflow acceleration by sector
- Narrative lifecycle stage

---

### 2. Narrative Trend Analyzer

```python
class NarrativeTrendAnalyzer:
    """Analyze adoption lifecycle and narrative strength trends."""
    
    def track_narrative_progression(
        self,
        asset: str,
        historical_narm: List[NARMSignal],
    ) -> NarrativeTrendReport:
        """Track narrative from early→mid→late stage."""
```

**Metrics**:
- Adoption acceleration (slope of user growth)
- Narrative momentum (trend direction)
- Peak detection (when narrative peaks)
- Reversal signals (adoption decline)

---

### 3. Capital Flow Validator

```python
class CapitalFlowValidator:
    """Validate capital rotation signals on-chain."""
    
    def validate_capital_flow(
        self,
        asset: str,
        narm_rotation_score: float,
        on_chain_data: Dict,
    ) -> CapitalFlowValidation:
        """Confirm NARM rotation with on-chain inflow."""
```

**Validates**:
- Whale address accumulation
- Exchange inflow/outflow
- Smart money tracking
- Institutional address activity

---

### 4. Layer 5 Integration Scorer

```python
class Layer5IntegrationScorer:
    """Combine NARM + Layer 3 (BCE) + Layer 4 (X20)."""
    
    def score_combined(
        self,
        bce_signal: BCESignal,
        x20_score: X20Score,
        narm_score: NARMSignal,
    ) -> Layer5Decision:
        """Combined Layer 3+4+5 opportunity scoring."""
```

**Decision Matrix**:
```
┌─────────────┬──────────────────────────────────────┐
│ BCE Valid   │ X20 Score │ NARM ≥65 │ → Decision   │
├─────────────┼──────────────────────────────────────┤
│ ✓ (≥5/6)    │ ≥75       │ ✓        │ STRONG_BUY   │
│ ✓ (≥5/6)    │ ≥65       │ ✓        │ BUY_ROTATION │
│ ✓ (≥5/6)    │ ≥50       │ ✓        │ RESEARCH     │
│ ✗           │ Any       │ ✓        │ WATCHLIST    │
│ Any         │ Any       │ ✗        │ HOLD         │
└─────────────┴──────────────────────────────────────┘
```

---

## Test Coverage

### Test Files (Phase 5)

1. **test_sector_rotation.py** (NEW) — 8 tests
   - Detect rotation between narratives
   - Sector weighting analysis
   - Inflow concentration
   - Top-N narrative filtering

2. **test_narrative_trends.py** (NEW) — 10 tests
   - Adoption acceleration detection
   - Narrative peak identification
   - Reversal signals
   - Lifecycle stage progression

3. **test_capital_flow_validation.py** (NEW) — 8 tests
   - Whale accumulation patterns
   - Exchange flow confirmation
   - Smart money tracking
   - False positive detection

4. **test_layer5_integration.py** (NEW) — 12 tests
   - Combined scoring with Layer 3/4
   - Decision matrix validation
   - Confidence thresholds
   - Multi-asset ranking

### Total Phase 5 Tests: 38 new tests + 13 core = **51 tests**

---

## Integration Points

### Layer 5 ↔ Layer 3 (BCE)

```
NARM score ≥65 + BCE valid
→ Higher confidence in entry signal
→ Supports narrative-driven thesis
```

### Layer 5 ↔ Layer 4 (X20)

```
NARM rotation signal + X20 opportunity
→ Combined opportunity discovery
→ Weighted by adoption stage
```

### Layer 5 ↔ Pipeline

```
DecisionPipeline.process_asset():
├── Layer 3: BCE validity check
├── Layer 4: X20 opportunity score
├── Layer 5: NARM rotation detection ← NEW
└── Output: Combined decision signal
```

---

## Phase 5 Implementation Roadmap

### Week 1: Components 1-2
- [ ] SectorRotationTracker (15 tests)
- [ ] NarrativeTrendAnalyzer (12 tests)

### Week 2: Components 3-4
- [ ] CapitalFlowValidator (8 tests)
- [ ] Layer5IntegrationScorer (10 tests)

### Week 3: Integration & Validation
- [ ] End-to-end pipeline tests (8 tests)
- [ ] Walk-forward validation
- [ ] Sensitivity analysis

### Week 4: Documentation
- [ ] API documentation
- [ ] Tuning guide
- [ ] Architecture diagrams

---

## Example: NARM-Driven Discovery

```
1. Scan all top 100 assets for NARM ≥65
   → AI sector: 12 candidates
   → DeFi sector: 5 candidates
   → RWA sector: 3 candidates

2. Detect sector rotation (AI gaining weight)

3. For each AI candidate with NARM ≥65:
   ├─ Check BCE validity (≥5/6)
   ├─ Check X20 score (≥50)
   └─ Generate combined decision

4. Output watchlist + entry signals
```

---

## Success Criteria

- ✅ All 51 tests passing
- ✅ Zero false positives (sector rotation)
- ✅ Capital flow validation >85% accuracy
- ✅ Narrative peak detection working
- ✅ Integration with Layer 3+4 complete
- ✅ Documentation complete

---

## Files to Create/Modify

```
src/layers/layer5_narm/
├── __init__.py (updated)
├── narm_engine.py (existing)
├── sector_rotation.py (NEW)
├── narrative_trends.py (NEW)
├── capital_flow_validator.py (NEW)
└── layer5_integration.py (NEW)

tests/integration/
├── test_narm.py (existing: 13 tests)
├── test_sector_rotation.py (NEW: 8 tests)
├── test_narrative_trends.py (NEW: 10 tests)
├── test_capital_flow_validation.py (NEW: 8 tests)
└── test_layer5_integration.py (NEW: 12 tests)
```

---

## Next: Phase 6

- RCM/RPM Engine (Capital Rotation Confirmation Model)
- Walk-forward backtesting framework
- Combined Layer 3-6 validation

---

**Phase 5 Spec locked. Ready for implementation.**
