# Phase 4 — Decision Engines (BCE, X20, NARM-P+, RPM/RCM, RRP)

**Version**: 1.0  
**Status**: Planning  
**Start Date**: 2026-09-25

---

## Overview

Phase 4 implements the decision engines that consume validated features from Phase 3 and produce investment signals.

**Primary Goals**:
1. Implement Bottom Confirmation Engine (BCE) — main validation gate
2. Implement X20 Engine — asymmetric opportunity detection
3. Implement NARM-P+ — narrative adoption rotation model
4. Implement RPM/RCM — capital flow and rotation models
5. Implement RRP — revival radar for dead coins
6. Validate all with walk-forward backtesting

**Dependencies**: Phase 3 complete ✅

---

## Architecture

```
Phase 3 (Validated Features)
    ↓
Layer 7: Decision Support Engines
    ├── BCE (Bottom Confirmation Engine)
    │   └── Score: 0-6 (Gate: >= 5)
    ├── X20 Engine
    │   └── Score: 0-100 (Multi-factor)
    ├── NARM-P+
    │   └── Score: 0-100 (Narrative + Adoption)
    ├── RPM / RCM
    │   └── Score: 0-100 (Capital Flow)
    └── RRP (Revival Radar)
        └── Score: 0-100 (Dead Coin Revival)
    ↓
Layer 8: Signal Aggregation
    ├── Regime Filter
    ├── FOMO Circuit Breaker
    ├── Risk Breaker
    └── Final Signal (BUY / HOLD / SELL)
    ↓
Alert System
```

---

## Phase 4A: Bottom Confirmation Engine (Priority 1)

### Deliverables

#### A.1 BCE Engine
**File**: `src/layers/layer7_decision/bce.py`

```python
@dataclass
class WyckoffStructure:
    """Wyckoff accumulation/distribution structure."""
    phase: str  # "accumulation" | "distribution" | "unknown"
    strength: float  # 0-1
    confidence: float  # 0-1

class BCEEngine:
    def analyze_wyckoff(self, closes, highs, lows, volumes, period=20) 
        → WyckoffStructure
    
    def analyze_volume_profile(self, closes, volumes, period=20) 
        → Dict[str, float]
    
    def detect_selling_exhaustion(self, closes, volumes, period=20) 
        → float
    
    def detect_smart_money_accumulation(self, closes, volumes, period=20) 
        → float
    
    def analyze_market_structure(self, closes, highs, lows, period=20) 
        → Dict[str, float]
    
    def calculate_bce_score(self, 
                           wyckoff_score,
                           volume_score,
                           exhaustion_score,
                           smart_money_score,
                           structure_score) → int  # 0-6
    
    def validate_signal(self, bce_score) → bool  # >= 5/6
```

#### A.2 BCE Scoring

Components (each 0-1):
1. Wyckoff structure (30%)
2. Volume profile (20%)
3. Selling exhaustion (20%)
4. Smart money accumulation (20%)
5. Market structure (10%)

**Gate Rule**: BCE_SCORE >= 5/6 required for entry

#### A.3 Tests
**File**: `tests/unit/test_bce_engine.py`

- ✅ Wyckoff detection (accumulation vs distribution)
- ✅ Volume profile analysis
- ✅ Selling exhaustion detection
- ✅ Smart money tracking
- ✅ Market structure analysis
- ✅ Score aggregation (0-6)
- ✅ Gate validation (>= 5/6)
- ✅ Edge case handling
- ✅ No look-ahead verification

### Estimated Effort
- BCE implementation: 8 hours
- Tests: 5 hours
- Validation: 2 hours
- **Total**: ~15 hours

---

## Phase 4B: X20 Engine (Priority 2)

### Deliverables

#### B.1 X20 Engine
**File**: `src/layers/layer7_decision/x20_engine.py`

```python
@dataclass
class X20Score:
    fundamental: float  # 0-30
    narrative: float    # 0-30
    quantitative: float # 0-40
    total: float        # 0-100

class X20Engine:
    def score_fundamentals(self, symbol, team_quality, investor_quality,
                          tokenomics, unlocks, revenue, adoption) 
        → float
    
    def score_narrative(self, symbol, sector, rotation_momentum,
                       attention_growth, adoption_narrative) 
        → float
    
    def score_quantitative(self, momentum, volatility, relative_strength,
                          liquidity, risk_reward) 
        → float
    
    def detect_x20_opportunities(self, symbol, timeframe, data) 
        → X20Score
```

#### B.2 Scoring Breakdown

**Fundamental (0-30)**:
- Team quality (5)
- Investor quality (5)
- Tokenomics health (5)
- Unlock schedule risk (5)
- Revenue/adoption (5)
- Competitive advantage (5)

**Narrative (0-30)**:
- Sector strength (10)
- Capital rotation (10)
- Attention growth (5)
- AI/RWA/DeFi adoption (5)

**Quantitative (0-40)**:
- Momentum (15)
- Relative strength (15)
- Volatility regime (5)
- Liquidity (5)

#### B.3 Tests
**File**: `tests/unit/test_x20_engine.py`

- ✅ Fundamental scoring
- ✅ Narrative momentum detection
- ✅ Quantitative analysis
- ✅ Score aggregation (0-100)
- ✅ Opportunity ranking
- ✅ False signal detection
- ✅ Edge cases

### Estimated Effort
- X20 implementation: 10 hours
- Tests: 5 hours
- Validation: 2 hours
- **Total**: ~17 hours

---

## Phase 4C: NARM-P+ & RPM/RCM (Priority 3)

### Deliverables

#### C.1 NARM-P+ (Narrative Adoption Rotation Model)
**File**: `src/layers/layer7_decision/narm_p_plus.py`

```python
class NARMPPlus:
    def score_narrative_strength(self, symbol, sector) → float
    
    def score_adoption(self, symbol, user_growth, transaction_volume) → float
    
    def score_capital_rotation(self, symbol, timeframe, prices, volumes) → float
    
    def score_fundamentals(self, symbol) → float
    
    def score_market_timing(self, symbol, market_regime) → float
    
    def calculate_narm_p_score(self, narrative, adoption, rotation,
                              fundamental, timing) → float  # 0-100
```

#### C.2 RPM/RCM (Rotation & Capital Flow Model)
**File**: `src/layers/layer7_decision/rpm_rcm.py`

```python
class RPMEngine:
    def calculate_capital_flow(self, prices, volumes, timeframe) → float
    
    def calculate_relative_strength(self, symbol, sector) → float
    
    def detect_narrative_acceleration(self, symbol) → float
    
    def confirm_fundamentals(self, symbol) → float
    
    def analyze_derivatives_structure(self, symbol) → float
    
    def calculate_rpm_score(self, capital_flow, relative_strength,
                           narrative, fundamental, derivatives) 
        → float  # 0-100
    
    def walk_forward_validate(self, symbol, timeframe, start_date, end_date)
        → BacktestResult
```

#### C.3 Tests
**File**: `tests/unit/test_narm_rpm.py`

- ✅ NARM-P+ scoring
- ✅ RPM capital flow
- ✅ Narrative acceleration
- ✅ Fundamental confirmation
- ✅ Walk-forward validation
- ✅ Parameter optimization

### Estimated Effort
- NARM-P+: 8 hours
- RPM/RCM: 10 hours
- Tests: 6 hours
- Validation: 2 hours
- **Total**: ~26 hours

---

## Phase 4D: RRP (Revival Radar Pipeline) (Priority 4)

### Deliverables

#### D.1 RRP Engine
**File**: `src/layers/layer7_decision/rrp.py`

```python
@dataclass
class RevivalCandidate:
    symbol: str
    dead_period: timedelta
    resurrection_signal: float  # 0-100
    fundamental_change: float
    narrative_emergence: float
    adoption_acceleration: float
    confidence: float

class RRPEngine:
    def identify_dead_coins(self, symbols, lookback_days=365) → List[str]
    
    def detect_resurrection_signals(self, symbol, timeframe) → float
    
    def track_fundamental_changes(self, symbol) → float
    
    def detect_narrative_emergence(self, symbol) → float
    
    def measure_adoption_acceleration(self, symbol) → float
    
    def rank_revival_candidates(self, symbols) → List[RevivalCandidate]
```

#### D.2 Tests
**File**: `tests/unit/test_rrp.py`

- ✅ Dead coin identification
- ✅ Resurrection signal detection
- ✅ Fundamental change tracking
- ✅ Narrative emergence
- ✅ Adoption acceleration
- ✅ Ranking algorithm

### Estimated Effort
- RRP implementation: 10 hours
- Tests: 4 hours
- Validation: 2 hours
- **Total**: ~16 hours

---

## Phase 4E: Signal Aggregation & Risk Controls

### Deliverables

#### E.1 Signal Aggregator
**File**: `src/layers/layer7_decision/signal_aggregator.py`

```python
class SignalAggregator:
    def aggregate_signals(self, bce_score, x20_score, narm_score, 
                         rpm_score, rrp_score) → int  # 0-6
    
    def apply_regime_filter(self, signal, market_regime) → int
    
    def apply_fomo_circuit_breaker(self, signal, price_discovery, 
                                   euphoria_level) → int
    
    def apply_risk_breaker(self, signal, position_size, drawdown) → int
    
    def finalize_signal(self, aggregated_score) 
        → Tuple[str, float]  # ("BUY" | "HOLD" | "SELL", confidence)
```

#### E.2 Tests
**File**: `tests/unit/test_signal_aggregation.py`

- ✅ Signal combination
- ✅ Regime filtering
- ✅ FOMO circuit breaker
- ✅ Risk management
- ✅ Final signal generation

### Estimated Effort
- Signal aggregation: 5 hours
- Tests: 3 hours
- Validation: 1 hour
- **Total**: ~9 hours

---

## Implementation Order

### Week 1: Phase 4A (BCE)
1. Implement Wyckoff analysis
2. Implement volume profiling
3. Implement selling exhaustion
4. Implement smart money detection
5. Implement market structure
6. Write comprehensive tests
7. Validate with walk-forward

### Week 2: Phase 4B (X20)
1. Implement fundamental scoring
2. Implement narrative scoring
3. Implement quantitative scoring
4. Combine scores
5. Write tests
6. Validate with historical data

### Week 3: Phase 4C (NARM-P+ & RPM)
1. Implement NARM-P+
2. Implement RPM capital flow
3. Implement RCM rotations
4. Write tests
5. Walk-forward validation

### Week 4: Phase 4D & E
1. Implement RRP
2. Implement signal aggregation
3. Implement risk controls
4. End-to-end validation
5. Full system backtest

---

## Success Criteria

### Phase 4A (BCE)
- [ ] BCE scores 0-6 correctly
- [ ] Gate rule (>= 5/6) enforced
- [ ] No look-ahead bias
- [ ] All tests passing

### Phase 4B (X20)
- [ ] X20 scores 0-100
- [ ] Detects asymmetric opportunities
- [ ] Walk-forward validation pass
- [ ] All tests passing

### Phase 4C (NARM-P+ & RPM)
- [ ] NARM-P+ scores narrative shifts
- [ ] RPM detects capital flows
- [ ] Multi-period validation
- [ ] All tests passing

### Phase 4D (RRP)
- [ ] Identifies dead coins
- [ ] Detects resurrections
- [ ] Ranks candidates
- [ ] All tests passing

### Phase 4E (Aggregation)
- [ ] Combines signals correctly
- [ ] Applies all risk filters
- [ ] Final signal (BUY/HOLD/SELL)
- [ ] All tests passing

### Phase 4 Overall
- [ ] 100+ new tests
- [ ] All tests passing
- [ ] Full system backtest on BTC/ETH 2-year history
- [ ] Profit Factor >= 1.3
- [ ] Expectancy > 0
- [ ] Sharpe >= 1.0
- [ ] Max Drawdown <= 25%
- [ ] Documentation complete
- [ ] Ready for Phase 5 (Monitoring & Drift)

---

## Deliverables (by Phase)

| Item | 4A | 4B | 4C | 4D | 4E | Status |
|------|----|----|----|----|----|-|
| BCE engine | X | | | | | 📋 |
| X20 engine | | X | | | | 📋 |
| NARM-P+ engine | | | X | | | 📋 |
| RPM/RCM engine | | | X | | | 📋 |
| RRP engine | | | | X | | 📋 |
| Signal aggregator | | | | | X | 📋 |
| Tests (all engines) | X | X | X | X | X | 📋 |
| Walk-forward validation | X | X | X | X | X | 📋 |
| System integration | | | | | X | 📋 |

---

## Next Steps

1. **Start Phase 4A** — Implement BCE engine
2. **Validate with Phase 3 data** — Run BCE on BTC 1d
3. **Iterate** — Add X20, NARM-P+, RPM, RRP
4. **Test coverage** — Ensure 100% pass rate
5. **Backtest** — Full walk-forward validation
6. **Move to Phase 5** — Build monitoring layer

---

**Status**: 📋 READY TO IMPLEMENT  
**Estimated Duration**: 4-5 weeks (83 hours)  
**Test Target**: 100+ new tests + Phase 3 validation (200+ total)
