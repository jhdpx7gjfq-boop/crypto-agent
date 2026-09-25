# IGWT-PF26 Layers Specification

All layers are **modular**, **independently testable**, and **walk-forward validated**.

---

## Layer 1: Data Intelligence

**Module**: `src/layers/layer1_data/`

**Responsibility**: Raw data collection, validation, and feature engineering.

### Components

- **DataCollector** (`collector.py`)
  - Fetches OHLCV from: CoinGecko, Binance, local Parquet
  - Normalizes to `OHLCV` dataclass
  - Supports mock data for testing

- **DataValidator** (`validator.py`)
  - Checks: chronological order, OHLC integrity, duplicates
  - Detects: price jumps, volume spikes, temporal gaps
  - Returns: validation report + warnings

- **FeatureEngineer** (`validator.py`)
  - Computes: returns, volatility, SMA, RSI, MACD
  - All features are pandas-free (pure Python)
  - Rolling window support

### Input

- Ticker/asset ID
- Time period (days)

### Output

```python
List[OHLCV]:
  - timestamp
  - open, high, low, close
  - volume
```

### Validation Rules

- Minimum 100 candles for analysis
- No chronological inversions
- L ≤ O, C ≤ H (always)
- No more than 50% price jumps
- Volume must be positive

---

## Layer 2: Market Regime Engine

**Module**: `src/layers/layer2_regime/`

**Responsibility**: Detect market context (bull, bear, sideways, transition).

### Components

- **MarketRegimeDetector** (`regime_engine.py`)
  - Fetches: BTC price, funding rates, open interest, BTC dominance
  - Classifies regime based on signals
  - Computes macro score (DXY, US10Y)

### Input

- BTC price (optional — fetches if not provided)
- Funding rate (optional)
- Open interest change (optional)
- BTC dominance (optional)
- Macro indicators: DXY, US10Y (optional)

### Output

```python
MarketRegime:
  - regime: RegimeType (BULL | BEAR | SIDEWAYS | TRANSITION)
  - btc_dominance: 0-100%
  - funding_rate: float
  - open_interest_change: %
  - macro_score: 0-100
```

### Regime Logic

| Funding Rate | OI Change | BTC Dom | → Regime |
|---|---|---|---|
| > +0.05% | > +20% | - | BULL |
| < -0.05% | < -20% | - | BEAR |
| Between | Low | - | SIDEWAYS |
| Mixed | - | > 55% | TRANSITION |

---

## Layer 3: Wyckoff Intelligence (BCE)

**Module**: `src/layers/layer3_wyckoff/`

**Responsibility**: Bottom Confirmation Engine (BCE) scoring.

### Components

- **BottomConfirmationEngine** (`bce_engine.py`)
  - Scores 6 components (each 0-1)
  - Validates accumulation structure

### Input

```python
List[OHLCV]: 20+ candles (daily or higher timeframe)
```

### Components Scored

1. **Wyckoff Structure** (0-1)
   - Multiple tests of low = double/triple bottom
   - Score 0.8+ → Multiple lows within 2%

2. **Volume Analysis** (0-1)
   - High volume on bounces, low volume on declines
   - Score 0.9+ → 2+ high-vol bounces + declining vol

3. **Selling Exhaustion** (0-1)
   - Volume tapering + bounces from low
   - Score 0.9+ → Vol declining AND price bouncing

4. **Smart Money Accumulation** (0-1)
   - Tight range + balanced closes + consistent volume
   - Score 0.95+ → Range < 3% + balanced + consistent

5. **Market Structure** (0-1)
   - Higher lows pattern (bullish structure)
   - Score 0.9+ → Rising lows

6. **Momentum Confirmation** (0-1)
   - RSI rising from oversold (30-50)
   - Score 0.8+ → RSI 30-50 and rising

### Output

```python
WyckoffSignal:
  - bce_score: 0-6 (sum of components)
  - valid: bool (bce_score >= 5.0)
  - individual component scores (0-1 each)
```

### Validation Rule

**BCE ≥ 5.0 required** for entry signal validation.
Score < 5.0 → **NO ENTRY**.

---

## Layer 4: X20 Engine

**Module**: `src/layers/layer4_x20/`

**Responsibility**: Identify asymmetric opportunities (10-20x potential).

### Components

- **X20Scanner** (`x20_engine.py`)
  - Analyzes: fundamentals, narrative, quantitative signals
  - Combines scores (0-100 each)

### Analysis Dimensions

1. **Fundamental** (0-100)
   - Team quality
   - Investor backing
   - Tokenomics risk
   - Revenue/adoption

2. **Narrative** (0-100)
   - Sector momentum
   - Story strength
   - Cultural fit

3. **Quantitative** (0-100)
   - Momentum
   - Volatility (for range)
   - Relative strength
   - Liquidity

### Output

```python
X20Opportunity:
  - combined_score: 0-100
  - component scores
  - risk assessment
```

### Validation

Score ≥ 70 recommended for multi-confirmation.

---

## Layer 5: NARM-P+ Engine

**Module**: `src/layers/layer5_narm/`

**Responsibility**: Narrative Adoption Rotation Model Plus.

### Components

- **NARPEngine** (`narm_engine.py`)
  - Tracks narrative strength, adoption, capital rotation
  - 100-point scoring system

### Scoring Breakdown

| Component | Weight | Max Points |
|---|---|---|
| Narrative Strength | 20% | 20 |
| Adoption | 25% | 25 |
| Capital Rotation | 25% | 25 |
| Fundamentals | 20% | 20 |
| Market Timing | 10% | 10 |
| **TOTAL** | | **100** |

### Validation

Score ≥ 60 for narrative confirmation.

---

## Layer 6: RCM/RPM Engine

**Module**: `src/layers/layer6_rcm/`

**Responsibility**: Rotation Confirmation Model (capital flow detection).

**REQUIRED**: Walk-forward validation for all signals.

### Components

- **RotationConfirmationModel** (`rcm_engine.py`)
  - Capital flow analysis (25%)
  - Relative strength (25%)
  - Narrative acceleration (20%)
  - Fundamental confirmation (20%)
  - Derivatives structure (10%)

### Output

```python
RCMSignal:
  - combined_score: 0-100
  - valid: bool (score >= 70)
```

### Constraints

- **Walk-forward mandatory** (no lookahead)
- Minimum 200 trades for validation
- Profit factor > 1.3

---

## Layer 7: RRP Revival Radar

**Module**: `src/layers/layer7_rrp/`

**Responsibility**: Detect dead tokens showing signs of renaissance.

### Components

- **RevivalRadar** (`rrp_engine.py`)
  - Snapshot health
  - Volume signature
  - Community activity
  - Technical confirmation

### Stages

| Stage | Revival Prob | Meaning |
|---|---|---|
| dead | < 30% | No activity |
| awakening | 30-60% | Initial signs |
| revival | 60-80% | Clear momentum |
| momentum | > 80% | Strong recovery |

### Output

```python
RRPSignal:
  - revival_probability: 0-100%
  - stage: str
  - component scores
```

---

## Layer 8: RPM X20 Optimizer

**Module**: `src/layers/layer8_optimizer/`

**Responsibility**: Backtesting, parameter optimization, validation.

### Components

- **BacktestOptimizer** (`optimizer_engine.py`)
  - Runs backtest on trades
  - Validates walk-forward (mandatory)
  - Detects lookahead bias

### Backtest Constraints

| Metric | Minimum | Enforcement |
|---|---|---|
| Trades | 200 | Absolute |
| Profit Factor | 1.3 | Required |
| Max Drawdown | < 25% | Hard stop |
| Walk-Forward | PASS | Mandatory |
| Lookahead Bias | None | Checked |

### Output

```python
BacktestResult:
  - total_trades: int
  - win_rate: float
  - profit_factor: float
  - max_drawdown: float
  - walk_forward_passed: bool
  - lookahead_bias_detected: bool
```

### Validation Failure

Any backtest failing constraints → **DO NOT USE** strategy.

---

## Decision Pipeline

```
DATA (L1)
    ↓
REGIME (L2)
    ↓
BCE (L3) [≥5.0 REQUIRED]
    ↓
X20 (L4) + NARM (L5)
    ↓
RCM (L6) [Walk-forward validated]
    ↓
RRP (L7) [Optional, for revivals]
    ↓
OPTIMIZER (L8) [Backtest if strategy]
    ↓
DECISION SIGNAL
    ↓
Human Decision
```

---

## Data Flow

- **Layer 1 → All**: Provides clean OHLCV + features
- **Layer 2 → Pipeline**: Provides regime context
- **Layer 3 → Pipeline**: Validates entry (BCE score)
- **Layer 4 → Pipeline**: Opportunity score
- **Layer 5 → Pipeline**: Narrative confirmation
- **Layer 6 → Pipeline**: Capital flow signal
- **Layer 7 → Pipeline**: Revival detection (bonus)
- **Layer 8 → Strategy Dev**: Backtest validation

---

## Testing Strategy

Each layer has:
- Unit tests (fixtures included)
- Integration tests (with real data when available)
- Validation tests (data quality checks)
- Walk-forward tests (for models)

See `tests/` directory for fixtures and test cases.
