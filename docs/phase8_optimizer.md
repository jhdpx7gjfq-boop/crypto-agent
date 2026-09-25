# Phase 8 — RPM X20 Optimizer Engine

**Status**: ✅ Complete  
**Last Updated**: 2026-09-25  
**Tests**: 13 integration tests (all passing)  
**LOC**: ~400 production code

---

## Overview

The **Optimizer Engine** (Layer 8) implements parameter optimization with mandatory constraint enforcement. It enables systematic tuning of strategy parameters while preventing overfitting through walk-forward validation.

Key features:
- Parameter sweep with exhaustive search
- Hard constraint enforcement (200+ trades, PF ≥ 1.3, DD < 25%)
- Walk-forward validation on each candidate
- Composite scoring (PF × Sharpe × (1 - DD/100))
- Ranked result reporting

---

## Architecture

### Core Classes

#### `OptimizerConstraints`
Hard constraints that must be satisfied:
- `min_trades`: Minimum 200 trades (prevents noise)
- `min_profit_factor`: ≥ 1.3 (profit/loss ratio)
- `max_drawdown`: ≤ 25% (capital preservation)
- `min_sharpe`: ≥ 0.5 (risk-adjusted returns)

#### `OptimizerParameters`
Tunable strategy parameters:
- `ma_fast`: Fast MA period (default 20)
- `ma_slow`: Slow MA period (default 50)
- `rsi_period`: RSI period (default 14)
- `rsi_oversold`: RSI entry threshold (default 30)
- `rsi_overbought`: RSI exit threshold (default 70)
- `volatility_threshold`: Min volatility for entry (default 2.0)
- `position_size`: Fraction of capital (default 1.0)
- `stop_loss_pct`: Stop loss % (default 2.0)
- `take_profit_pct`: Take profit % (default 5.0)

#### `OptimizationResult`
Single evaluation outcome:
- `parameters`: The tested parameter set
- `backtest_result`: BacktestResult with metrics
- `walk_forward_valid`: Out-of-sample validation status
- `passes_constraints`: All constraints met?
- `constraint_failures`: List of failed constraints
- `score`: Composite ranking score

#### `OptimizationReport`
Complete sweep summary:
- `total_combinations`: Number of parameter sets tested
- `results_passing`: Combinations that passed constraints
- `results_failing`: Combinations that failed
- `best_result`: Top-ranked parameter set
- `top_results`: Top 5 candidates
- `optimization_time_seconds`: Computation time

#### `OptimizerEngine`
Main optimization orchestrator:
- `optimize()`: Run full parameter sweep
- `_generate_combinations()`: Create all parameter sets
- `_evaluate_parameters()`: Test one parameter set
- `_validate_walkforward()`: Out-of-sample test
- `generate_report_text()`: Human-readable output

---

## Scoring Formula

Composite score for ranking passing candidates:

```
score = profit_factor × max(1.0, sharpe_ratio) × (1 - max_drawdown/100)
```

This formula favors:
- Higher profit factors (profitable strategies)
- Better risk-adjusted returns (sharpe)
- Lower drawdowns (capital preservation)

---

## Constraint Enforcement

**All constraints must pass simultaneously** — no exceptions.

### Constraint 1: Minimum Trades
```
total_trades >= 200
```
Prevents strategies that win occasionally due to luck.

### Constraint 2: Profit Factor
```
profit_factor >= 1.3
```
At least 30% more gross profit than gross loss.

### Constraint 3: Maximum Drawdown
```
max_drawdown <= 25%
```
Capital preservation threshold.

### Constraint 4: Walk-Forward Validation
Run on 5 out-of-sample windows (rolling 70/30 train/test):
- Must generate ≥200 trades on each test window
- Must maintain PF ≥ 1.3 on each test window
- Must keep DD ≤ 25% on each test window

**Purpose**: Detect overfitting and ensure robustness to unseen data.

---

## Usage Example

```python
from src.layers.layer8_optimizer.optimizer_engine import OptimizerEngine
from src.core.backtest import Trade, TradeType

# Strategy function (required)
def my_strategy(ohlcv, params):
    trades = []
    for i in range(len(ohlcv)):
        # Use params.ma_fast, params.ma_slow, etc.
        pass
    return trades

# Initialize optimizer
engine = OptimizerEngine()

# Define parameter ranges (min, max, step)
param_ranges = {
    "ma_fast": (10, 30, 5),
    "ma_slow": (40, 100, 20),
    "take_profit_pct": (3, 10, 1),
}

# Run optimization
report = engine.optimize(
    asset="BTC",
    ohlcv_data=historical_data,
    strategy_func=my_strategy,
    param_ranges=param_ranges
)

# Access results
if report.best_result:
    print(f"Best PF: {report.best_result.backtest_result.profit_factor:.2f}")
    print(f"Best params: {report.best_result.parameters.to_dict()}")
```

---

## Output Format

```
======================================================================
OPTIMIZATION REPORT — BTC
======================================================================

Summary:
  Total combinations: 288
  Passing constraints: 12/288
  Optimization time: 24.5s

Best Parameters:
  Score: 1.2450
  MA Fast: 15
  MA Slow: 60
  RSI Period: 14
  RSI Oversold: 30.0
  Take Profit %: 5.0

Performance:
  Total Trades: 245
  Win Rate: 56.33%
  Profit Factor: 1.87
  Max Drawdown: 18.52%
  Sharpe Ratio: 1.23
  Walk-Forward Valid: ✓ Yes

Top 5 Results:
  1. Score: 1.2450 | PF: 1.87 | DD: 18.52%
  2. Score: 1.1895 | PF: 1.75 | DD: 19.10%
  3. Score: 1.1320 | PF: 1.68 | DD: 20.50%
  ...

Analysis:
  • Total combinations evaluated: 288
  • Passing constraints: 12
  • Failing constraints: 276
  • ✓ Best score: 1.25
    PF: 1.87
    DD: 18.52%
    Trades: 245

======================================================================
```

---

## Constraint Workflow

```
Parameter Set
    ↓
Backtest (generate trades)
    ↓
Compute Metrics (PF, DD, etc.)
    ↓
Check Hard Constraints
    ├─ trades >= 200? ──NO─→ FAIL
    ├─ PF >= 1.3?     ──NO─→ FAIL
    ├─ DD <= 25%?     ──NO─→ FAIL
    └─ YES on all
    ↓
Walk-Forward Validation (5 windows)
    ├─ All windows pass constraints? ──NO─→ FAIL
    └─ YES
    ↓
PASS ✓
    ↓
Compute Score & Rank
```

---

## Walk-Forward Validation Details

For each passing parameter set:

1. **Split data**: 70% train, 30% test (5 rolling windows)
2. **Run strategy** on test data (future unseen data)
3. **Check constraints** on each test window:
   - Must generate ≥200 trades
   - Profit factor ≥ 1.3
   - Max drawdown ≤ 25%
4. **All 5 windows must pass** (no partial credit)

---

## Performance Characteristics

- **Parameter combinations**: O(∏ ranges) — exponential
  - Example: 5 parameters with 10 values each = 100,000 combinations
- **Time per evaluation**: ~10-50ms
- **Walk-forward cost**: 5× backtest time (5 windows)
- **Total runtime**: combinations × (backtest + 5×WF validation)

### Optimization Tips
1. Start with coarse ranges (large steps)
2. Identify promising region
3. Refine ranges around best result
4. Run with finer steps for final tuning

---

## Integration with Decision Pipeline

```
Data → Features → Backtest Strategies → Optimize Parameters
                                              ↓
                                     Ranked Parameter Sets
                                              ↓
                                     Deploy Top Candidate
```

The optimizer provides validated parameter sets for:
- BCE Engine (Layer 3): Wyckoff entry thresholds
- X20 Engine (Layer 4): Fundamental score weights
- RCM Engine (Layer 6): Capital flow thresholds
- Strategy parameters for any trading algorithm

---

## Files

- `src/layers/layer8_optimizer/optimizer_engine.py` — Core engine
- `src/layers/layer8_optimizer/__init__.py` — Module exports
- `tests/integration/test_optimizer.py` — 13 integration tests
- `examples/optimizer_example.py` — Usage demo

---

## Test Coverage

| Test | Coverage |
|------|----------|
| Engine initialization | ✓ |
| Parameter generation | ✓ |
| Parameter validation | ✓ |
| Constraint checking | ✓ |
| Walk-forward validation | ✓ |
| Score computation | ✓ |
| Report generation | ✓ |
| Edge cases (insufficient data) | ✓ |
| Multiple combinations | ✓ |
| Error handling | ✓ |

---

## Design Decisions

### Why walk-forward on each candidate?
Prevents overfitting to historical data. Out-of-sample validation ensures discovered parameters work on future unseen periods.

### Why hard constraints?
Soft constraints create ambiguity. Hard constraints enforce discipline:
- 200+ trades: Eliminates noise
- PF ≥ 1.3: Ensures profitability
- DD ≤ 25%: Protects capital
- Walk-forward: Confirms robustness

### Why composite score?
Multiple objectives (PF, Sharpe, DD) are weighted equally into a single ranking metric. Score balances:
- Profitability (PF)
- Risk-adjusted returns (Sharpe)
- Drawdown control (1 - DD/100)

---

## Constraints vs. Thresholds

**Hard constraints** (must pass all):
- min_trades: 200
- min_profit_factor: 1.3
- max_drawdown: 25%

**Soft preferences** (ranked by score):
- Sharpe ratio (higher is better)
- Profit factor (higher is better)
- Drawdown (lower is better)

---

## Next Phase

**Phase 9: Dashboard + Agent**
- Real-time visualization of optimized strategies
- Autonomous research assistant
- Alert system integration
- Performance monitoring dashboard

---

## References

- Walk-Forward Testing: Pardo, R. "The Evaluation and Optimization of Trading Strategies"
- Profit Factor: Tharp, V. "Trade Your Way to Financial Freedom"
- Sharpe Ratio: Sharpe, W.F. "The Sharpe Ratio"
