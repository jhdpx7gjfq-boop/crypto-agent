# Phase 2: Feature Store & Backtesting Framework

**Status**: Complete  
**Date**: 2026-09-25

---

## Deliverables

### Feature Store (`src/utils/feature_store.py`)

Centralized feature management with:

- **FeatureVector**: Dataclass holding all computed features for a candle
- **FeatureStore**: Engine for computing, caching, and persisting features

#### Features Computed

| Feature | Params | Use |
|---------|--------|-----|
| SMA | 20, 50 | Trend direction |
| Volatility | 20-period | Regime assessment |
| RSI | 14-period | Momentum/oversold |
| MACD | 12/26/9 | Trend confirmation |
| Momentum | 14-period | Directional strength |
| Volume MA | 20-period | Liquidity check |

#### Methods

```python
fs = FeatureStore()

# Compute features (returns List[FeatureVector])
features = fs.compute_features("BTC", ohlcv_data)

# Persist to disk
fs.save_features_parquet("BTC", features)
fs.save_features_json("BTC", features)

# Load from disk
features = fs.load_features_parquet("BTC")
```

**Design**: No external dependencies except pandas (optional for Parquet).

---

### Backtesting Framework (`src/core/backtest.py`)

Complete backtesting + walk-forward validation:

#### Trade Class

```python
@dataclass
class Trade:
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    trade_type: TradeType  # LONG | SHORT
    quantity: float = 1.0
    
    @property
    def pnl(self) -> float: ...      # Absolute P&L
    @property
    def pnl_pct(self) -> float: ...  # Percentage return
    @property
    def is_winning(self) -> bool: ...
```

#### BacktestEngine

```python
engine = BacktestEngine(initial_capital=100000.0)

# Add trades
engine.add_trade(trade)
engine.add_trades_batch(trades)

# Compute metrics
metrics = engine.compute_metrics()
# → BacktestResult with:
#   - total_trades, winning_trades, losing_trades
#   - win_rate (%)
#   - profit_factor (gross_profit / gross_loss)
#   - max_drawdown (%)
#   - sharpe_ratio, sortino_ratio
```

#### WalkForwardValidator

Prevents lookahead bias:

```python
validator = WalkForwardValidator(total_periods=5)

# Generate train/test splits
splits = validator.get_train_test_splits(len(ohlcv_data))
# → [(train_start, train_end, test_start, test_end), ...]

# Validate strategy
passed = validator.validate(
    strategy_func=my_strategy,
    ohlcv_data=ohlcv_data,
    min_profit_factor=1.3,
    min_trades=200,
)
```

**Key Property**: Training data always ends BEFORE test data starts (no lookahead).

---

## Tests

### Feature Store Tests (`tests/unit/test_feature_store.py`)

- ✓ FeatureVector creation & serialization
- ✓ Feature computation (SMA, RSI, MACD)
- ✓ Padding/alignment of features
- ✓ Insufficient data handling
- ✓ Bounds checking (RSI 0-100, etc.)

### Backtest Tests (`tests/unit/test_backtest.py`)

- ✓ Trade P&L computation (long & short)
- ✓ Backtest metrics (win rate, profit factor, drawdown)
- ✓ Sharpe/Sortino ratios
- ✓ Walk-forward split generation
- ✓ No lookahead bias in splits

---

## Constraints Enforced

### Feature Store

- Minimum 50 candles required for feature computation
- Features padded to match OHLCV length
- None values for insufficient history

### Backtest

- **Absolute minimum**:
  - 200+ trades for statistical significance
  - Profit Factor ≥ 1.3
  - Max Drawdown < 25%

- **Walk-forward**:
  - 5 periods minimum
  - Training/test non-overlapping
  - Must train on past data only

---

## Integration with Layers

### Layer 1 → Feature Store

```python
from src.layers.layer1_data.collector import DataCollector
from src.utils.feature_store import FeatureStore

collector = DataCollector()
ohlcv = collector.fetch_coingecko("bitcoin")

fs = FeatureStore()
features = fs.compute_features("BTC", ohlcv)
fs.save_features_parquet("BTC", features)
```

### Layer 3-8 → Backtest

```python
from src.core.backtest import BacktestEngine, Trade, TradeType

# Strategy generates trades
trades = [...]

# Backtest
engine = BacktestEngine(initial_capital=100000)
engine.add_trades_batch(trades)
metrics = engine.compute_metrics()

if metrics.profit_factor >= 1.3 and metrics.max_drawdown < 25:
    print("✓ Strategy passes minimum constraints")
```

---

## Next: Phase 3

- **BCE Production Hardening**: Add robustness tests
- **X20 Engine**: Implement fundamental scoring
- **Pipeline Integration**: Connect all layers

---

## Implementation Notes

### Feature Store

- All features computed in pure Python (no numpy required)
- EMA approximation used for MACD (good enough for analysis)
- Volatility = rolling std dev of closes
- RSI uses standard formula (smooth average gains/losses)

### Backtest

- Equity tracking: equity = initial_capital + cumulative_pnl
- Drawdown: peak-to-trough from highest equity
- Sharpe: assumes 250 trading days/year, 2% risk-free rate
- Sortino: downside deviation (only negative returns)

### Walk-Forward

- Data split automatically based on total_periods
- Step size = data_length / periods
- Training/test windows non-overlapping (mandatory)
- Designed to prevent lookahead bias

---

## Files Changed

```
src/
├── core/
│   └── backtest.py          (NEW: 400+ lines)
└── utils/
    └── feature_store.py     (NEW: 450+ lines)

tests/
├── unit/
│   ├── test_feature_store.py (NEW: 150+ lines)
│   └── test_backtest.py      (NEW: 200+ lines)
```

---

## Running Tests

```bash
# Feature store tests
pytest tests/unit/test_feature_store.py -v

# Backtest tests
pytest tests/unit/test_backtest.py -v

# All Phase 2 tests
pytest tests/unit/test_*.py -v

# With coverage
pytest tests/unit/test_feature_store.py tests/unit/test_backtest.py --cov=src
```

---

**Phase 2 complete. Ready for Phase 3: BCE production hardening.**
