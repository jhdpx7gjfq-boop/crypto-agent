# Phase 3 — Feature Engineering & Validation Framework

**Version**: 1.0  
**Status**: Planning  
**Start Date**: 2026-09-25

---

## Overview

Phase 3 builds the feature engineering layer and validation framework on top of Phase 2's immutable raw data.

**Primary Goals**:
1. Define reproducible feature contracts (versioning, semantics, validation)
2. Implement basic technical features (RSI, MA, MACD, Bollinger Bands)
3. Create PIT replay engine for backtesting
4. Detect look-ahead bias and data leakage

**Dependencies**: Phase 2 complete ✅

---

## Architecture

```
Phase 2 (Raw Data)
    ↓ immutable, provenance-tracked
Layer 2: Feature Store
    ├── feature_definitions/ (versioned contracts)
    ├── feature_calculations/ (deterministic, no look-ahead)
    └── feature_validation/ (schema, range, drift checks)
    ↓
Layer 6: Validation Framework
    ├── pit_replay/ (point-in-time reconstruction)
    ├── walk_forward/ (training/test splits)
    └── leakage_detection/ (future information checks)
    ↓
Layer 7: Decision Engines (Phase 4+)
    └── (BCE, X20, NARM-P+, etc.)
```

---

## Phase 3A: Feature Store (Priority 1)

### Deliverables

#### 1.1 Feature Contract Definition
**File**: `src/data/features/contract.py`

```python
@dataclass
class FeatureContract:
    name: str                    # e.g., "rsi_14"
    version: str                 # "1.0"
    source: str                  # "layer2.technical"
    timestamp_semantics: str     # "point-in-time" or "bar-close"
    lookback_bars: int           # historical bars needed
    parameters: Dict[str, Any]   # {"period": 14}
    dtype: str                   # "float", "int", "bool"
    valid_range: Tuple[float, float]  # (0, 100) for RSI
    missing_policy: str          # "forward_fill" | "interpolate" | "drop"
    calculation: str             # description of how it's calculated
    
    def validate(self, value: float) -> bool:
        """Check if value is within valid_range."""
```

#### 1.2 Feature Calculations
**Directory**: `src/layers/layer2_features/technical/`

Implement:
- `rsi.py` — Relative Strength Index (14, 7)
- `ma.py` — Moving Averages (SMA, EMA, WMA)
- `macd.py` — MACD (12, 26, 9)
- `bb.py` — Bollinger Bands (20, 2.0)
- `volatility.py` — Volatility metrics (HV, Parkinson)

**Constraints**:
- ❌ No future price information
- ❌ No look-ahead
- ✅ Deterministic (same input → same output)
- ✅ Reproducible (no random state)

#### 1.3 Feature Store Class
**File**: `src/data/features/store.py`

```python
class FeatureStore:
    def __init__(self, duckdb_store: DuckDBStore):
        self.ohlcv_data = duckdb_store
        self.contracts = {}  # Feature contract registry
    
    def calculate_feature(self, symbol: str, timeframe: str, 
                         feature_name: str, 
                         as_of_timestamp: datetime) -> List[float]:
        """Calculate feature for symbol up to as_of_timestamp (PIT)."""
        # 1. Fetch OHLCV data with availability_timestamp <= as_of_timestamp
        # 2. Calculate feature value
        # 3. Validate against contract
        # 4. Return time series
    
    def register_contract(self, contract: FeatureContract):
        """Register a feature contract."""
        self.contracts[contract.name] = contract
    
    def validate_feature(self, name: str, values: List[float]) -> bool:
        """Validate feature values against contract."""
        contract = self.contracts[name]
        for val in values:
            if not contract.valid_range[0] <= val <= contract.valid_range[1]:
                raise ValueError(f"Value {val} outside range {contract.valid_range}")
        return True
```

#### 1.4 Tests
**File**: `tests/unit/test_feature_calculations.py`

Tests per feature:
- ✅ Known values (RSI(14) on historical BTC data)
- ✅ Edge cases (NaN, zero volume, gaps)
- ✅ Contract validation
- ✅ Determinism (same input → same output)
- ❌ Look-ahead detection (should fail if using future data)

### Estimated Effort
- Feature contracts: 4 hours
- Technical features (5x): 6 hours
- Feature store class: 3 hours
- Tests: 5 hours
- **Total**: ~18 hours

---

## Phase 3B: Validation Framework (Priority 2)

### Deliverables

#### 2.1 PIT Replay Engine
**File**: `src/layers/layer6_validation/pit_replay.py`

```python
class PITReplayEngine:
    def __init__(self, feature_store: FeatureStore):
        self.feature_store = feature_store
    
    def replay_at_timestamp(self, symbol: str, timeframe: str, 
                           decision_timestamp: datetime) -> Dict[str, float]:
        """
        Return all feature values as they would be known at decision_timestamp.
        
        Only uses data with availability_timestamp <= decision_timestamp.
        """
        # 1. Query OHLCV with availability filter
        # 2. Calculate all features
        # 3. Return feature dict
    
    def walk_forward(self, symbol: str, timeframe: str,
                    start_date: datetime, end_date: datetime,
                    train_period: timedelta, test_period: timedelta):
        """
        Walk-forward iteration: train on historical, test on future.
        
        Yields (train_features, test_features, metrics) for each period.
        """
```

#### 2.2 Leakage Detection
**File**: `src/layers/layer6_validation/leakage_detector.py`

```python
class LeakageDetector:
    def check_feature(self, feature_name: str, feature_values: List[float],
                      timestamps: List[datetime],
                      decision_timestamps: List[datetime]) -> LeakageReport:
        """
        Detect if feature uses future information.
        
        Check correlation between feature_change and future_price_change
        at time=0. Suspicious correlation → leakage.
        """
    
    def check_forward_bias(self, prices: List[float],
                          timestamps: List[datetime]) -> float:
        """
        Check if price labels are properly time-ordered.
        
        Returns correlation of price_today vs price_tomorrow.
        High correlation at lag=1 → potential look-ahead bias.
        """
```

#### 2.3 Tests
**File**: `tests/unit/test_leakage_detection.py`

- ✅ Detect intentional look-ahead (feature uses future price)
- ✅ Reject survivorship bias
- ✅ Reject forward-looking labels
- ✅ Accept clean features (no leakage)

### Estimated Effort
- PIT replay: 5 hours
- Leakage detection: 4 hours
- Tests: 3 hours
- **Total**: ~12 hours

---

## Phase 3C: Walk-Forward Validator (Priority 3)

### Deliverables

#### 3.1 Walk-Forward Engine
**File**: `src/layers/layer6_validation/walk_forward_validator.py`

```python
class WalkForwardValidator:
    def run_backtest(self, symbol: str, timeframe: str,
                    start_date: datetime, end_date: datetime,
                    train_period: timedelta, test_period: timedelta,
                    signal_name: str) -> BacktestResult:
        """
        Execute walk-forward validation.
        
        1. Split data into train/test periods
        2. For each period:
           - Train on historical data
           - Test on future data (with PIT filter)
           - Record metrics
        3. Aggregate results
        
        Returns: Sharpe, Profit Factor, Max Drawdown, etc.
        """

@dataclass
class BacktestResult:
    symbol: str
    signal_name: str
    trade_count: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    start_date: datetime
    end_date: datetime
    validation_method: str  # "walk_forward"
    confidence_interval: Tuple[float, float]
```

#### 3.2 Tests
**File**: `tests/unit/test_walk_forward.py`

- ✅ Correct period splits (no data leakage between train/test)
- ✅ PIT reconstruction (no future data in test)
- ✅ Metrics calculation (Sharpe, profit factor, drawdown)
- ✅ Walk-forward pass (multiple periods with valid results)

### Estimated Effort
- Walk-forward engine: 6 hours
- Metrics calculation: 3 hours
- Tests: 3 hours
- **Total**: ~12 hours

---

## Implementation Order

### Week 1: Phase 3A (Feature Store)
1. Define FeatureContract dataclass
2. Implement technical features (RSI, MA, MACD, BB)
3. Create FeatureStore class
4. Write unit tests
5. Validate against Phase 2 data

### Week 2: Phase 3B (Validation Framework)
1. Implement PIT replay engine
2. Add leakage detection
3. Write leakage detection tests
4. Test with real BTC data

### Week 3: Phase 3C (Walk-Forward Validator)
1. Implement walk-forward engine
2. Add metrics calculation
3. Write validation tests
4. Run end-to-end backtest

---

## Success Criteria

### Phase 3A (Feature Store)
- [ ] 5 features implemented and tested
- [ ] Contract validation working
- [ ] PIT-compatible (no look-ahead)
- [ ] Reproducible on known BTC data
- [ ] All feature tests passing

### Phase 3B (Validation Framework)
- [ ] PIT replay engine working
- [ ] Leakage detection functional
- [ ] Can detect intentional look-ahead
- [ ] Rejects biased datasets
- [ ] All leakage tests passing

### Phase 3C (Walk-Forward Validator)
- [ ] Walk-forward backtesting working
- [ ] Metrics correctly calculated
- [ ] No data leakage between train/test
- [ ] Multiple periods working
- [ ] All walk-forward tests passing

### Phase 3 Overall
- [ ] 100% test pass rate (50+ tests)
- [ ] No look-ahead bias detected on Phase 2 data
- [ ] Backtest results reproducible
- [ ] Documentation complete
- [ ] Ready for Phase 4 (Decision Engines)

---

## Blocked By

**Blocker #4: Temporal Boundary Filtering** (from Phase 2)

**Current Status**: Workaround available
- Metadata contains availability_timestamp
- Application-level filtering can be implemented
- Schema change deferred to Phase 3.5 (optimization)

**Phase 3A Approach**:
1. Use availability_timestamp from metadata
2. Filter in Python layer (fetch → filter)
3. Later optimize with schema change

---

## Risks

### Risk 1: Look-Ahead Bias Creep
**Mitigation**:
- Automated leakage detection
- Code review of feature calculations
- Hypothesis testing against random signals

### Risk 2: Performance (Feature Calculation)
**Mitigation**:
- Vectorize with NumPy/Pandas
- Cache intermediate calculations
- Profile on real BTC data

### Risk 3: Walk-Forward Overfitting
**Mitigation**:
- Sufficient test periods (min 10)
- Out-of-sample validation
- Parameter stability checks

---

## Deliverables (by Phase)

| Item | 3A | 3B | 3C | Status |
|------|----|----|-----|--------|
| Feature contracts | X | | | 📋 |
| 5 technical features | X | | | 📋 |
| Feature store class | X | | | 📋 |
| Feature tests | X | | | 📋 |
| PIT replay engine | | X | | 📋 |
| Leakage detection | | X | | 📋 |
| Leakage tests | | X | | 📋 |
| Walk-forward engine | | | X | 📋 |
| Metrics calculation | | | X | 📋 |
| Walk-forward tests | | | X | 📋 |

---

## Next Steps

1. **Start Phase 3A** — Create FeatureContract and implement RSI
2. **Validate with Phase 2 data** — Run RSI(14) on BTC 1d
3. **Iterate** — Add remaining features (MA, MACD, BB)
4. **Test coverage** — Ensure 100% pass rate
5. **Move to Phase 3B** — Build validation framework

---

**Status**: 📋 READY TO IMPLEMENT  
**Estimated Duration**: 3-4 weeks (42 hours)  
**Test Target**: 50+ passing tests (Phase 3)
