# Phase 2: Feature Store & Backtesting Framework

**Version**: 1.0  
**Status**: Specification  
**Date**: 2026-09-30  
**Phase**: 2 of 9  
**Base Commit**: 702e977 (PR #20 merged)

---

## Executive Summary

Phase 2 builds on the Layer 1-7 validation completed in Phase 1. This phase establishes the **Feature Store** and **Backtesting Framework** necessary for:
1. Multi-asset feature engineering (ETH, SOL, top 10 market cap assets)
2. Walk-forward validated backtesting
3. Statistical validation and parameter optimization
4. Production-ready research outputs

**NOT included**: Auto-trading, execution, CEX API integration.

---

## Objectives

### Primary

1. **Feature Store**: Centralized storage and retrieval of engineered features across all 7 layers
2. **Backtesting Framework**: Walk-forward validated backtesting with out-of-sample validation
3. **Multi-Asset Expansion**: Extend Layer 1-7 engines to ETH, SOL, and top 10 assets
4. **Statistical Validation**: Profit factor, drawdown, Sharpe ratio, walk-forward testing

### Secondary

- Integration testing across Layer 1-7 with multi-asset data
- Feature engineering documentation
- Backtest reporting and visualization
- Performance tracking (MLFlow integration)

---

## Scope

### In Scope

| Component | Description | Priority |
|-----------|-------------|----------|
| Feature Store (relational) | DuckDB-backed feature storage | P0 |
| Backtesting Engine | Walk-forward validation framework | P0 |
| Multi-Asset Collectors | ETH, SOL, top 10 symbol collectors | P1 |
| Feature Enrichment | Layer 1-7 feature computation pipeline | P1 |
| Statistical Validators | Profit factor, drawdown, WFV checks | P1 |
| MLFlow Integration | Experiment tracking and logging | P2 |
| Backtest Reporting | HTML/JSON reports with charts | P2 |

### Out of Scope

- Layers 8-9 (indefinitely blocked per governance)
- Automatic execution or CEX API
- Real-time market data ingestion
- Portfolio optimization or allocation
- Neural networks or machine learning models

---

## Architecture

### Data Flow

```
Layer 1-7 Engines (Phase 1)
        ↓
Feature Engineering Pipeline
        ↓
Feature Store (DuckDB)
        ↓
Backtesting Framework
        ↓
Walk-Forward Validation
        ↓
Statistical Validation
        ↓
Research Reports
```

### Feature Store Design

**Storage**: DuckDB (columnar, efficient for time-series)

**Schema**:
```
features_layer1
├─ timestamp (ms)
├─ asset (symbol)
├─ open, high, low, close, volume (OHLCV)

features_layer3
├─ timestamp
├─ asset
├─ bce_score, wyckoff_structure, volume_analysis, etc.

features_layer4
├─ timestamp
├─ asset
├─ x20_score, fundamental, narrative, quantitative

... (layers 5-7 similar)

backtest_results
├─ test_id (UUID)
├─ asset
├─ start_date, end_date
├─ trade_count, profit_factor, max_drawdown, etc.
```

### Backtesting Framework

**Walk-Forward Window**:
- Training: 50% of data
- Out-of-sample: 50% of data
- No lookahead bias

**Validation Constraints** (hard requirements):
- Minimum 200 trades
- Profit factor > 1.3
- Max drawdown < 25%
- Walk-forward validation PASS

**Trade Representation**:
```python
Trade:
  entry_time: int (ms)
  entry_price: float
  exit_time: int (ms)
  exit_price: float
  trade_type: LONG | SHORT
  pnl: float (computed)
  roi: float (computed)
```

---

## Components & Deliverables

### Component 1: Feature Store

**Files**:
- `src/data/feature_store.py` (expand existing)
- `src/data/feature_schema.py` (new)
- `tests/unit/test_feature_store.py` (expand)

**Tasks**:
1. Define DuckDB schema for all 7 layers
2. Implement feature insertion/retrieval
3. Add schema versioning
4. Implement data validation
5. Write schema documentation

**Success Criteria**:
- ✅ All Layer 1-7 features store/retrieve correctly
- ✅ Schema handles null/missing values gracefully
- ✅ Query performance acceptable for backtests
- ✅ Data integrity validated on insert

---

### Component 2: Backtesting Engine

**Files**:
- `src/core/backtest.py` (expand existing)
- `src/core/backtest_validator.py` (new)
- `tests/unit/test_backtest.py` (expand)

**Tasks**:
1. Implement walk-forward split logic (50/50)
2. Build trade representation and P&L calculation
3. Add statistical validators (profit factor, drawdown, Sharpe)
4. Implement walk-forward validation checker
5. Add result serialization (JSON/Parquet)

**Success Criteria**:
- ✅ Walk-forward testing produces in-sample + out-of-sample metrics
- ✅ No lookahead bias detected
- ✅ Statistical validators work correctly
- ✅ Results reproducible

---

### Component 3: Multi-Asset Data Collectors

**Files**:
- `src/layers/layer1_data/multi_asset_collector.py` (new)
- `tests/integration/test_multi_asset_integration.py` (new)

**Assets**:
- BTC (phase 1, already complete)
- ETH (Ethereum)
- SOL (Solana)
- Top 7 by market cap (LINK, DOGE, ADA, etc.)

**Tasks**:
1. Extend BinanceDataPortalCollector to support multi-symbol
2. Implement rate limiting for Binance API
3. Add data consistency checks
4. Integrate with feature store

**Success Criteria**:
- ✅ ETH, SOL, top 7 data fetches correctly
- ✅ Data quality constraints met for all assets
- ✅ No data gaps or duplicates
- ✅ Integration tests pass

---

### Component 4: Feature Enrichment Pipeline

**Files**:
- `src/data/feature_pipeline.py` (new)
- `tests/integration/test_feature_pipeline.py` (new)

**Tasks**:
1. Create pipeline: raw OHLCV → Layer 1-7 features → feature store
2. Implement streaming/batch modes
3. Add error handling and retry logic
4. Document feature definitions
5. Add monitoring/logging

**Success Criteria**:
- ✅ Pipeline processes all assets correctly
- ✅ Features computed per Layer 1-7 specs
- ✅ Feature store populated correctly
- ✅ No data loss or corruption

---

### Component 5: Statistical Validators

**Files**:
- `src/core/statistical_validators.py` (new)
- `tests/unit/test_statistical_validators.py` (new)

**Validators**:
- Profit factor: total_gains / abs(total_losses)
- Maximum drawdown: peak-to-trough loss
- Sharpe ratio: return per unit volatility
- Win rate: percentage of winning trades
- Walk-forward validation: in-sample vs out-of-sample comparison

**Tasks**:
1. Implement each validator
2. Add edge case handling (no trades, all winners, etc.)
3. Define pass/fail criteria
4. Add documentation

**Success Criteria**:
- ✅ All validators work correctly
- ✅ Edge cases handled gracefully
- ✅ Results match external benchmarks (optional)

---

## Testing Strategy

### Unit Tests (80% coverage target)

- Feature store CRUD operations
- Backtest walk-forward splitting
- Statistical validator calculations
- Data schema validation

### Integration Tests

- Multi-asset data collection
- Feature pipeline end-to-end
- Backtest with real data (Layer 1-7)
- Feature store + backtest integration

### Validation Tests

- Walk-forward testing (no lookahead bias)
- Trade P&L calculations
- Statistical constraint validation
- Reproducibility checks

---

## Success Criteria

### Phase 2 Gate

**Must have**:
- ✅ Feature store operational for all 7 layers
- ✅ Backtesting framework with walk-forward validation
- ✅ Multi-asset support (BTC, ETH, SOL, top 5)
- ✅ All constraints validated
- ✅ Unit tests 80%+ coverage
- ✅ Integration tests all pass

**Should have**:
- ✅ MLFlow experiment tracking
- ✅ Backtest HTML reports
- ✅ Feature engineering documentation
- ✅ Performance benchmarks

**Nice to have**:
- ✅ Jupyter notebooks for analysis
- ✅ CLI tools for backtesting
- ✅ Visualization dashboard

---

## Timeline

| Milestone | Duration | Owner |
|-----------|----------|-------|
| Feature Store Design & Schema | 2d | Claude Code |
| Feature Store Implementation | 3d | Claude Code |
| Backtesting Framework | 3d | Claude Code |
| Multi-Asset Collectors | 2d | Claude Code |
| Feature Pipeline | 2d | Claude Code |
| Statistical Validators | 1d | Claude Code |
| Integration Testing | 2d | Claude Code |
| Documentation | 1d | Claude Code |
| **Total** | **~16d** | |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| DuckDB performance issues | Profile queries early, optimize schema |
| Data quality problems in multi-asset | Implement strict validation checks |
| Lookahead bias in backtests | Peer review walk-forward logic |
| Integration complexity | Incremental testing, clear interfaces |

---

## Dependencies

### External
- DuckDB >= 1.0
- Pandas >= 2.0
- NumPy >= 1.24
- Requests >= 2.31 (Binance API)

### Internal
- Layer 1-7 engines (Phase 1) ✅ Complete
- OHLCV model and validation ✅ Complete
- Core models and config ✅ Complete

---

## Governance

### Code Review
- All PRs require human review
- Walk-forward logic reviewed by 2 eyes minimum
- Feature schema reviewed for correctness

### Testing Gates
- Unit tests must pass (80%+ coverage)
- Integration tests must pass
- Walk-forward validation tests must pass
- No regression in Phase 1 components

### Documentation
- Feature definitions documented
- Backtest report format specified
- API documentation complete
- Validation logic documented

---

## Next Phase

**Phase 3**: BCE Production Engine (Layer 3 optimization, refinement)

---

## Appendix A: DuckDB Schema Details

### features_layer1
```sql
CREATE TABLE features_layer1 (
  timestamp BIGINT NOT NULL,
  asset VARCHAR NOT NULL,
  open DOUBLE NOT NULL,
  high DOUBLE NOT NULL,
  low DOUBLE NOT NULL,
  close DOUBLE NOT NULL,
  volume DOUBLE NOT NULL,
  PRIMARY KEY (timestamp, asset)
);
```

### features_layer3
```sql
CREATE TABLE features_layer3 (
  timestamp BIGINT NOT NULL,
  asset VARCHAR NOT NULL,
  bce_score DOUBLE NOT NULL,
  wyckoff_structure DOUBLE,
  volume_analysis DOUBLE,
  selling_exhaustion DOUBLE,
  smart_money_accumulation DOUBLE,
  market_structure DOUBLE,
  momentum_confirmation DOUBLE,
  valid BOOLEAN,
  PRIMARY KEY (timestamp, asset)
);
```

(Similar schemas for layers 4-7)

### backtest_results
```sql
CREATE TABLE backtest_results (
  test_id VARCHAR PRIMARY KEY,
  asset VARCHAR NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  total_trades BIGINT,
  winning_trades BIGINT,
  losing_trades BIGINT,
  profit_factor DOUBLE,
  max_drawdown DOUBLE,
  sharpe_ratio DOUBLE,
  wfv_pass BOOLEAN,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

**Document Version**: 1.0  
**Status**: READY FOR PHASE 2 IMPLEMENTATION  
**Approval**: Pending human review
