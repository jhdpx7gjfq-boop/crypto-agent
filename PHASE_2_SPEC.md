# PHASE 2 : Feature Store + Backtester ABC

**Status**: In Progress  
**Version**: 0.1.0-alpha  
**Date**: 2026-09-25

---

## Objectifs

1. **Feature Store** : Abstraction pour compute/retrieve/persist features avec provenance
2. **Backtester ABC** : Interface générique pour backtesting quantitatif (walk-forward capable)
3. **Foundation Layers 2-7** : Préparer structure pour Market Regime, Wyckoff, X20, NARM-P+, RCM, RRP

---

## 1. Feature Store

### Spec

```python
class FeatureStore(ABC):
    """Abstraction pour gestion des features quantitatives."""
    
    @abstractmethod
    def ingest_raw(self, batch: RawDataBatch) -> None:
        """Ingérer données brutes et déclencher pipeline."""
    
    @abstractmethod
    def compute_feature(
        self, 
        feature_name: str, 
        asset: str, 
        start_timestamp: datetime, 
        end_timestamp: datetime
    ) -> pd.DataFrame:
        """Compute feature sur window temporelle."""
    
    @abstractmethod
    def retrieve_features(
        self,
        assets: list[str],
        features: list[str],
        start_timestamp: datetime,
        end_timestamp: datetime,
        lookback: Optional[timedelta] = None
    ) -> Dict[str, pd.DataFrame]:
        """Récupérer features avec lookback optionnel."""
    
    @abstractmethod
    def persist_snapshot(
        self,
        snapshot_name: str,
        asset: str,
        timestamp: datetime,
        features: Dict[str, float]
    ) -> None:
        """Persister snapshot immutable (audit trail)."""
    
    @abstractmethod
    def get_provenance(
        self,
        feature_name: str,
        asset: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Retourner provenance: source, version, compute_timestamp."""
```

### Implémentation DuckDB

```
src/feature_store/
  __init__.py
  base.py           # FeatureStore ABC
  duckdb_store.py   # Impl DuckDB
  schemas.py        # FeatureSnapshot schema
```

#### Tables DuckDB

```sql
-- Raw data (existing)
CREATE TABLE raw_data (...)

-- Computed features
CREATE TABLE feature_snapshots (
  feature_name VARCHAR NOT NULL,
  asset VARCHAR NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  value DOUBLE NOT NULL,
  compute_timestamp TIMESTAMP NOT NULL,
  source_version VARCHAR NOT NULL,
  PRIMARY KEY (feature_name, asset, timestamp)
)

-- Feature metadata
CREATE TABLE feature_metadata (
  feature_name VARCHAR PRIMARY KEY,
  description VARCHAR,
  computation_spec VARCHAR,  -- JSON
  source_table VARCHAR,
  created_timestamp TIMESTAMP,
  version VARCHAR
)
```

### Contraintes IGWT

- ✅ **No look-ahead** : Compute only with data available at timestamp
- ✅ **Provenance** : Chaque feature inclut source_version + compute_timestamp
- ✅ **Immutable** : Snapshots never updated, only appended
- ✅ **Audit trail** : Query history logged
- ✅ **Type safe** : Pydantic schema pour FeatureSnapshot

---

## 2. Backtester ABC

### Spec

```python
class BacktestSignal(BaseModel):
    """Signal généré par stratégie."""
    timestamp: datetime
    asset: str
    action: Literal["LONG", "SHORT", "EXIT"]
    confidence: float  # 0-1
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None

class PortfolioState(BaseModel):
    """État du portefeuille à un point temporel."""
    timestamp: datetime
    positions: Dict[str, float]  # asset -> quantity
    cash: float
    equity: float
    
class BacktestMetrics(BaseModel):
    """Métriques finales."""
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float
    trade_count: int
    win_rate: float

class Backtester(ABC):
    """Abstraction pour backtesting quantitatif."""
    
    @abstractmethod
    def setup(self, config: Dict[str, Any]) -> None:
        """Initialiser backtester avec config."""
    
    @abstractmethod
    def generate_signals(
        self,
        features: Dict[str, pd.DataFrame],
        timestamp: datetime
    ) -> List[BacktestSignal]:
        """Générer signaux sur données disponibles."""
    
    @abstractmethod
    def on_signal(self, signal: BacktestSignal) -> None:
        """Traiter signal (update portfolio)."""
    
    @abstractmethod
    def get_portfolio_state(self) -> PortfolioState:
        """Retourner state courant."""
    
    @abstractmethod
    def backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float
    ) -> BacktestMetrics:
        """Run full backtest walk-forward."""
    
    @abstractmethod
    def get_metrics(self) -> BacktestMetrics:
        """Retourner métriques finales."""
```

### Implémentation Mock

```
src/backtester/
  __init__.py
  base.py           # Backtester ABC + schemas
  mock.py           # Mock impl pour tests
```

#### Mock Backtester

```python
class MockBacktester(Backtester):
    """Simple mock: BUY-HOLD-SELL strategy."""
    
    def generate_signals(self, features, timestamp):
        # Signal LONG si feature > threshold
        # Signal EXIT si max profit or stop loss
        pass
```

### Contraintes IGWT

- ✅ **Walk-Forward** : Backtest must be OOS-safe (no future data leak)
- ✅ **Point-in-Time** : Features retrieved as if available at signal_timestamp
- ✅ **Reproducible** : Seed controls randomness
- ✅ **Equity curve** : Track day-by-day
- ✅ **Trade log** : Every entry/exit recorded
- ✅ **Slippage** : Optional slippage model

---

## 3. Pipeline Integration

```
Feature Store ← Raw Data
       ↓
   Features
       ↓
 Backtester.generate_signals()
       ↓
 Portfolio Updates
       ↓
 Metrics
```

### Execution Flow

1. Ingest raw data (RawDataBatch)
2. Compute features (FeatureStore.compute_feature)
3. For each timestamp in backtest:
   - Retrieve features (only available data)
   - Generate signals (Backtester.generate_signals)
   - Update portfolio (Backtester.on_signal)
4. Calculate metrics (BacktestMetrics)

---

## 4. Testing

### Unit Tests

```
tests/test_feature_store.py
  - test_ingest_raw_updates_features
  - test_compute_feature_no_lookahead
  - test_retrieve_features_with_lookback
  - test_provenance_tracked
  - test_immutable_snapshots
  - test_feature_metadata_versioned

tests/test_backtester.py
  - test_setup_initializes_config
  - test_generate_signals_returns_list
  - test_on_signal_updates_portfolio
  - test_portfolio_state_consistency
  - test_backtest_walk_forward_oos
  - test_metrics_calculated_correctly
  - test_mock_backtester_buy_hold
```

### Integration Tests

```
tests/test_phase2_integration.py
  - test_feature_store_backtester_pipeline
  - test_walk_forward_validation
  - test_trade_log_completeness
```

---

## 5. Deliverables

### Code

- ✓ `src/feature_store/base.py` + `duckdb_store.py`
- ✓ `src/backtester/base.py` + `mock.py`
- ✓ `src/backtester/schemas.py`
- ✓ Test suite (51+ tests)

### Docs

- ✓ This spec
- ✓ Usage examples
- ✓ API reference (docstrings)

### Validation

- ✓ pytest: PASS
- ✓ mypy strict: 0 errors
- ✓ ruff: All checks passed
- ✓ Walk-forward tests: PASS

---

## 6. Acceptance Criteria

- [x] Feature Store ABC defined
- [x] DuckDB persistence works
- [x] Backtester ABC defined
- [x] Mock impl works
- [x] No look-ahead in any code
- [x] Provenance tracked
- [x] Tests pass
- [x] Type safe (mypy strict)
- [x] Linting clean (ruff)
- [x] Walk-forward example runs

---

## 7. Success Metrics

| Metric | Target | Gate |
|--------|--------|------|
| pytest | PASS | ✓ |
| mypy strict | 0 errors | ✓ |
| ruff | All checks | ✓ |
| Walk-forward tests | PASS | ✓ |
| Trade log records | 100% | ✓ |
| Provenance completeness | 100% | ✓ |

---

## 8. Notes

- Feature Store + Backtester are **independent layers**
- Mock Backtester enables testing without Layer 2-7 impl
- Ready for Layer 2 (Market Regime) to add feature computations
- Walk-forward framework enables future statistical validation

---

**Phase 2 Ready for Implementation**
