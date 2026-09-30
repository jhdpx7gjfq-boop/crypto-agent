# Phase 4: X20 Opportunity Engine

**Version**: 1.0  
**Status**: Specification  
**Date**: 2026-09-30  
**Phase**: 4 of 9  
**Base Commit**: 822a0c2 (Phase 3 complete)

---

## Executive Summary

Phase 4 productionizes the X20 Opportunity Engine (Layer 4) for identifying asymmetric investment opportunities in crypto. Building on Phase 1-3 foundation (Layer 1-3 complete, BCE engine validated), this phase:

1. Implements opportunity scoring framework
2. Adds fundamental analysis engine
3. Implements narrative rotation detection
4. Develops risk/reward analysis
5. Creates opportunity ranking and filtering

**Goal**: Identify assets with 10-20x potential, validated across fundamental, narrative, and quantitative dimensions.

---

## Objectives

### Primary

1. **Fundamental Scoring**: Analyze team, tokenomics, adoption, revenue
2. **Narrative Detection**: Identify sector rotations and emerging themes
3. **Quantitative Metrics**: Momentum, volatility, relative strength, liquidity
4. **Risk Assessment**: Drawdown limits, concentration, execution risk
5. **Opportunity Ranking**: Multi-factor scoring (0-100)

### Secondary

- Market cap filtering (focus on emerging/micro-cap)
- Liquidity validation (minimum trading volume)
- Time-to-catalyst analysis (upcoming events/unlocks)
- Portfolio concentration limits
- Correlation analysis (avoid concentrated bets)

---

## Scope

### In Scope

| Component | Description | Priority |
|-----------|-------------|----------|
| Fundamental Analyzer | Team, investor quality, tokenomics | P0 |
| Narrative Engine | Sector trends, adoption metrics, theme detection | P0 |
| Quantitative Scorer | Momentum, volatility, risk metrics | P0 |
| Risk Assessment | Drawdown simulation, concentration analysis | P1 |
| Opportunity Ranker | Multi-factor scoring and ranking | P1 |
| Integration Filter | Combine BCE + X20 signals | P1 |
| Backtesting | Historical opportunity validation | P2 |

### Out of Scope

- Automatic portfolio allocation
- Risk parity optimization
- Options/derivatives strategies
- Cross-exchange arbitrage
- Market-making
- Execution algorithms

---

## Architecture

### X20 Engine Pipeline

```
Layer 1: Data (on-chain, market, social)
        ↓
Fundamental Analyzer
  - Team quality assessment
  - Investor quality (VCs, angels)
  - Tokenomics analysis
  - Revenue/adoption metrics
  - Competitive advantage
        ↓
Narrative Detection Engine
  - Sector rotation tracking
  - Narrative strength scoring
  - Social mention trends
  - Adoption acceleration
  - AI/RWA/DeFi theme detection
        ↓
Quantitative Scorer
  - Momentum analysis (RSI, MACD)
  - Volatility assessment
  - Relative strength vs sector
  - Liquidity scoring
  - Price structure analysis
        ↓
Risk Assessment
  - Maximum drawdown estimate
  - Concentration check
  - Execution risk scoring
  - Correlation matrix
        ↓
Opportunity Ranker
  - Multi-factor scoring (0-100)
  - Weighting: Fundamental (35%), Narrative (25%), Quant (25%), Risk (15%)
  - Top opportunity identification
        ↓
Integration Filter
  - Combine with BCE signals (Layer 3)
  - High BCE + High X20 score = Priority entry
  - Filter low-confidence opportunities
        ↓
Final Score: X20 Opportunity 0-100
  (requires >= 65/100 for consideration)
```

### Data Flow

```
Feature Store (Layer 1: Market data)
  ├─ Top 50-100 altcoins (market cap filtered)
  ├─ Daily OHLCV + on-chain metrics
        ↓
X20 Engine v1
  - Compute 4 factor scores
  - Rank by composite X20 score
  - Filter by constraints
        ↓
Feature Store (Layer 4 v1)
  - X20 opportunity scores
  - Component breakdown (fundamental, narrative, quant, risk)
  - Catalyst timeline
  - Risk flags
        ↓
Integration Layer (Layer 3 + Layer 4)
  - Match BCE signals to X20 opportunities
  - Generate ranked entry candidates
  - Signal quality check
        ↓
Signal Output
  - High-confidence opportunities (BCE >= 5/6 AND X20 >= 65)
  - Medium-confidence (BCE >= 4/6 OR X20 >= 70)
  - Watch list (X20 >= 60, waiting for BCE)
```

---

## Components & Deliverables

### Component 1: Fundamental Analyzer

**Files**:
- `src/layers/layer4_x20/fundamental_analyzer.py` (new)
- `tests/unit/test_fundamental_analyzer.py` (new)

**Tasks**:
1. Implement team quality scoring (founders, advisors, track record)
2. Investor quality assessment (tier-1 VCs, angel networks)
3. Tokenomics analysis (supply, unlocks, distribution)
4. Revenue/adoption metrics (users, TVL, transaction volume)
5. Competitive positioning (market share, differentiation)

**Success Criteria**:
- ✅ Team quality score 0-100 with clear rubric
- ✅ Investor tier classification (Tier-1, Tier-2, Other)
- ✅ Tokenomics red-flags detection (high unlock risk, poor distribution)
- ✅ Unit tests 85%+ coverage

---

### Component 2: Narrative Detection Engine

**Files**:
- `src/layers/layer4_x20/narrative_engine.py` (new)
- `tests/unit/test_narrative_engine.py` (new)

**Tasks**:
1. Implement sector/theme detection (AI, RWA, DeFi, Gaming, L2)
2. Narrative strength scoring from social/mention volume
3. Adoption acceleration detection
4. Capital rotation tracking (which narratives are hot)
5. Time-based sentiment trending

**Success Criteria**:
- ✅ Narrative categories clearly defined
- ✅ Strength score 0-100 from multiple signals
- ✅ Acceleration detection (week-over-week growth)
- ✅ Unit tests 85%+ coverage

---

### Component 3: Quantitative Scorer

**Files**:
- `src/layers/layer4_x20/quantitative_scorer.py` (new)
- `tests/unit/test_quantitative_scorer.py` (new)

**Tasks**:
1. Implement momentum metrics (RSI, MACD, price position in range)
2. Volatility analysis (recent vs historical)
3. Relative strength vs sector (vs top 10)
4. Liquidity scoring (bid-ask spread, volume)
5. Price structure quality (support, resistance, breakout readiness)

**Success Criteria**:
- ✅ Momentum score 0-100 normalized
- ✅ Volatility assessment (explosive vs stable)
- ✅ Liquidity validation (minimum 1M USD daily volume)
- ✅ Unit tests 85%+ coverage

---

### Component 4: Risk Assessment

**Files**:
- `src/layers/layer4_x20/risk_assessor.py` (new)
- `tests/unit/test_risk_assessor.py` (new)

**Tasks**:
1. Implement maximum drawdown estimation
2. Concentration risk (position size vs portfolio)
3. Execution risk scoring (slippage, market impact)
4. Correlation analysis (avoid highly correlated bets)
5. Timeline risk (pre-unlock periods, regulatory events)

**Success Criteria**:
- ✅ Drawdown estimate based on volatility
- ✅ Concentration limits enforced
- ✅ Risk score 0-100 (lower = safer)
- ✅ Unit tests 85%+ coverage

---

### Component 5: Opportunity Ranker

**Files**:
- `src/layers/layer4_x20/opportunity_ranker.py` (new)
- `tests/unit/test_opportunity_ranker.py` (new)

**Tasks**:
1. Implement multi-factor scoring
2. Weight components: Fundamental (35%), Narrative (25%), Quant (25%), Risk (15%)
3. Create opportunity objects with full metadata
4. Generate ranked opportunity lists
5. Document scoring rationale per opportunity

**Success Criteria**:
- ✅ Final X20 score 0-100
- ✅ Component weights justified
- ✅ Top 10-20 opportunities identified
- ✅ Unit tests 90%+ coverage

---

### Component 6: Integration Layer

**Files**:
- `src/layers/layer4_x20/integration.py` (new)
- `tests/integration/test_x20_integration.py` (new)

**Tasks**:
1. Implement BCE + X20 signal matching
2. Priority entry candidates (high BCE + high X20)
3. Watch list management (waiting for confirmation)
4. Quality filtering and constraints
5. Signal output formatting

**Success Criteria**:
- ✅ Integration with Layer 3 (BCE signals)
- ✅ Candidate ranking and filtering
- ✅ Multi-asset support (top 50-100)
- ✅ Integration tests all pass

---

## Testing Strategy

### Unit Tests (85%+ coverage)

- Fundamental scoring logic
- Narrative detection algorithms
- Quantitative metric calculations
- Risk assessment computations
- Ranking weighting logic

### Integration Tests

- End-to-end X20 scoring on real data
- Multi-asset opportunity identification
- Layer 3 + Layer 4 integration
- Signal quality validation
- Ranking consistency

### Validation Tests

- Historical opportunity performance (backtest)
- False positive rate (< 20%)
- Win rate correlation with score
- Multi-sector consistency
- No lookahead bias

---

## Success Criteria

### Phase 4 Gate

**Must have**:
- ✅ Fundamental analyzer component
- ✅ Narrative detection engine
- ✅ Quantitative scorer
- ✅ Risk assessment module
- ✅ Opportunity ranker
- ✅ Layer 3 + Layer 4 integration
- ✅ Unit tests 85%+ coverage
- ✅ Integration tests all pass

**Should have**:
- ✅ Top 10 opportunity identification
- ✅ Sector breakdown analysis
- ✅ Historical backtest results
- ✅ Risk-adjusted scoring
- ✅ Catalyst timeline tracking

**Nice to have**:
- ✅ Portfolio concentration alerts
- ✅ Correlation matrix visualization
- ✅ Narrative momentum charts
- ✅ Fundamental quality rankings
- ✅ Real-time opportunity streaming

---

## Timeline

| Milestone | Duration | Owner |
|-----------|----------|-------|
| Fundamental Analyzer | 2d | Claude Code |
| Narrative Detection | 2d | Claude Code |
| Quantitative Scorer | 2d | Claude Code |
| Risk Assessment | 1.5d | Claude Code |
| Opportunity Ranker | 1.5d | Claude Code |
| Integration Layer | 1d | Claude Code |
| Testing & Validation | 2d | Claude Code |
| Documentation | 1d | Claude Code |
| **Total** | **~13d** | |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Over-weighting narrative trends | Backtest historical narratives, validate with fundamentals |
| Liquidity assumptions change | Use dynamic liquidity checks, require minimum volume |
| Team quality hard to assess | Use public data (GitHub, Twitter), investor network analysis |
| Survivorship bias in backtests | Include failed projects, track delisting events |
| Concentration risk | Enforce portfolio limits, monitor correlation |
| Fake narratives/hype | Cross-reference multiple data sources, track trend duration |

---

## Dependencies

### External
- Feature Store (Layer 1) ✅
- DuckDB >= 1.0
- Pandas >= 2.0
- NumPy >= 1.24

### Internal
- Phase 1: Layer 1 Data Intelligence ✅
- Phase 2: Feature Store + Backtesting ✅
- Phase 3: Layer 3 BCE Engine ✅

---

## Governance

### Code Review
- All PRs require 1 human review minimum
- X20 scoring logic reviewed for bias
- Component weighting justified

### Testing Gates
- Unit tests 85%+ coverage
- Integration tests all pass
- No regression in Phase 1-3 components
- Backtests validated (no lookahead bias)

### Documentation
- Component scoring rationale documented
- Multi-factor weighting explained
- Opportunity examples with analysis
- Risk assumptions clearly stated

---

## Next Phase

**Phase 5**: NARM-P+ Engine (Narrative + Adoption + Rotation Model)

---

## Appendix A: Opportunity Score Calculation

```
X20_Score = (
  Fundamental_Score * 0.35 +
  Narrative_Score * 0.25 +
  Quantitative_Score * 0.25 +
  (100 - Risk_Score) * 0.15
)

Final Score = X20_Score (0-100)

Thresholds:
  High Confidence: >= 75
  Medium Confidence: 65-75
  Watch List: 55-65
  Rejected: < 55
```

### Fundamental Score Components:
- Team Quality (30%): Track record, experience, founder quality
- Investor Quality (25%): VC tier, angel involvement, funding rounds
- Tokenomics (20%): Supply, unlock schedule, distribution health
- Adoption (15%): User growth, TVL, transaction volume
- Differentiation (10%): Competitive advantage, market positioning

### Narrative Score Components:
- Sector Strength (35%): How hot is this narrative/sector?
- Adoption Trend (30%): Is adoption accelerating?
- Social Momentum (20%): Mention volume, sentiment
- Capital Rotation (15%): Is capital flowing into this narrative?

### Quantitative Score Components:
- Momentum (40%): RSI, price structure, breakout readiness
- Volatility (25%): Recent volatility, opportunity for gains
- Relative Strength (20%): Performance vs sector
- Liquidity (15%): Trading volume, bid-ask spread

### Risk Score (0-100, lower = safer):
- Drawdown Risk (40%): Estimated max loss from peak
- Concentration (30%): Position size risk
- Execution Risk (20%): Slippage, market impact
- Timeline Risk (10%): Upcoming events, unlock risks

---

**Document Version**: 1.0  
**Status**: READY FOR PHASE 4 IMPLEMENTATION  
**Approval**: Pending human review
