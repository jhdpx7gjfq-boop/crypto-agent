# IGWT-PF26 — Quant Intelligence OS

Personal quantitative research infrastructure for **decision intelligence** in crypto investment (medium/long term).

**NOT** a trading bot. **IS** a Cabal Brain that collects data → analyzes markets → detects asymmetries → measures risk → validates → generates alerts.

Decision remains **human**. No auto-execution.

---

## Quick Start

```bash
# Clone repository
git clone https://github.com/jhdpx7gjfq-boop/crypto-agent.git
cd crypto-agent

# Install dependencies
pip install -e .

# Install dev dependencies (optional)
pip install -e ".[dev]"

# Run tests
pytest tests/
```

---

## Architecture

### 8-Layer Decision Pipeline

| Layer | Module | Purpose | Status |
|-------|--------|---------|--------|
| 1 | DATA INTELLIGENCE | Collection, validation, features | ✅ Complete |
| 2 | MARKET REGIME | Context detection (bull/bear/sideways) | ✅ Complete |
| 3 | WYCKOFF BCE | Bottom confirmation scoring (0-6) | ✅ Complete |
| 4 | X20 ENGINE | Asymmetric opportunity detection | 🔄 Stub |
| 5 | NARM-P+ | Narrative + adoption scoring | 🔄 Stub |
| 6 | RCM/RPM | Capital rotation detection | 🔄 Stub |
| 7 | RRP RADAR | Dead token revival detection | 🔄 Stub |
| 8 | OPTIMIZER | Backtest + walk-forward validation | 🔄 Stub |

**Signal Validation Rule**: **BCE ≥ 5.0 required** for entry. Score < 5.0 → NO ENTRY.

---

## Phase Status

- ✅ **Phase 1** (DONE): Repository structure + Data layer
- 🔄 **Phase 2**: Feature Store + Backtesting framework
- ⏳ **Phase 3-9**: Remaining engines + Dashboard + Agent

See `CLAUDE.md` for full project context.

---

## Key Modules

### Core (`src/core/`)

```python
from src.core.models import OHLCV, MarketRegime, WyckoffSignal, DecisionSignal
from src.core.pipeline import DecisionPipeline
from src.core.config import Config
```

- **models.py**: 15 dataclasses (validated, type-safe)
- **pipeline.py**: Decision orchestration + FOMO circuit breaker
- **config.py**: Centralized config management

### Layer 1 — Data Intelligence

```python
from src.layers.layer1_data.collector import DataCollector, DataStore
from src.layers.layer1_data.validator import DataValidator, FeatureEngineer

# Fetch OHLCV
collector = DataCollector()
ohlcv = collector.fetch_coingecko("bitcoin", days=365)

# Validate
validator = DataValidator()
is_valid, summary, warnings = validator.validate_ohlcv_list(ohlcv, "bitcoin")

# Features
fe = FeatureEngineer()
returns = fe.compute_returns(ohlcv)
volatility = fe.compute_volatility(ohlcv, window=20)
rsi = fe.compute_rsi(ohlcv, period=14)
```

### Layer 2 — Market Regime

```python
from src.layers.layer2_regime.regime_engine import MarketRegimeDetector

detector = MarketRegimeDetector()
regime = detector.detect_regime()  # Fetches live data automatically
# Or provide data manually
regime = detector.detect_regime(
    btc_price=100000.0,
    funding_rate=0.0005,
    btc_dominance=55.0,
)
```

### Layer 3 — Wyckoff BCE

```python
from src.layers.layer3_wyckoff.bce_engine import BottomConfirmationEngine

engine = BottomConfirmationEngine()
signal = engine.analyze("BTC", ohlcv_data)

if signal.valid:  # signal.bce_score >= 5.0
    print(f"✅ Valid BCE entry: {signal.bce_score:.2f}/6")
else:
    print(f"❌ Invalid BCE: {signal.bce_score:.2f}/6 (need >= 5.0)")
```

---

## Data Models

All models are **validated at construction** (raise `ValueError` on invalid data):

```python
from datetime import datetime
from src.core.models import OHLCV

# OHLCV validation
candle = OHLCV(
    timestamp=datetime.utcnow(),
    open=100.0,
    high=110.0,    # Must be >= low
    low=90.0,      # Must be <= high
    close=105.0,   # Must be in [low, high]
    volume=1e9,    # Must be >= 0
)

# Raises ValueError if any constraint violated
```

---

## Configuration

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

Key settings:
- `COINGECKO_API_KEY`: Optional (free tier available)
- `BCE_THRESHOLD`: Minimum score for entry (default 5.0)
- `LOOKBACK_DAYS`: Historical data window (default 365)
- `LOG_LEVEL`: DEBUG | INFO | WARNING | ERROR

See `.env.example` for all options.

---

## Testing

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# With coverage
pytest tests/ --cov=src --cov-report=term-missing
```

**Test fixtures** in `tests/fixtures/market_data.py`:
- `generate_mock_ohlcv()`: Random walk
- `generate_bull_ohlcv()`: Uptrend
- `generate_bear_ohlcv()`: Downtrend
- `generate_accumulation_ohlcv()`: Tight range (bottom formation)

---

## Development

### Code Style

- Format: `black` (100 char line length)
- Lint: `flake8` + `pylint`
- Type check: `mypy`
- Sort imports: `isort`

```bash
# Format
black src/ tests/

# Check
flake8 src/
mypy src/
```

### Adding a Layer

1. Create `src/layers/layerN_name/` directory
2. Create `__init__.py` with docstring
3. Create `engine.py` with main class
4. Inherit from appropriate base model
5. Add tests in `tests/integration/`

---

## Philosophy

- **Exactitude > speed**: Validate before shipping
- **Research > speculation**: Data-driven decisions only
- **Robustness > complexity**: Simple, testable modules
- **No premature abstraction**: 3 lines → helper only
- **Defensive data handling**: Validate at boundaries
- **Walk-forward validation mandatory**: No lookahead bias

---

## Data Sources (No CEX API Access)

✅ **Public sources only**:
- CoinGecko (free OHLCV)
- Binance public API (no auth)
- Glassnode (on-chain)
- CryptoQuant (derivatives)
- DefiLlama (TVL, yield)

❌ **No CEX trading access**:
- No API keys stored
- No order execution
- Manual wallet only (Tangem)

---

## Decision Pipeline

```
Raw Data (Layer 1)
    ↓
Market Regime (Layer 2)
    ↓
BCE Validation (Layer 3) — REQUIRED: score ≥ 5.0
    ↓
X20 + NARM (Layers 4-5)
    ↓
RCM (Layer 6) — Walk-forward validated
    ↓
RRP (Layer 7) — Optional, for revivals
    ↓
Backtest (Layer 8) — Strategy only
    ↓
DECISION SIGNAL
    ↓
🧠 Human Decision
```

---

## Governance

Each feature requires:
1. Specification (what & why)
2. Implementation (code)
3. Unit tests (≥80% coverage)
4. Integration tests (real data)
5. Walk-forward validation (models)
6. Version freeze

No component ships until **all passes**.

---

## Next Steps

- **Phase 2**: Feature Store + Backtesting framework
- **Phase 3**: BCE production hardening
- **Phase 4**: X20 opportunity scanner
- ...
- **Phase 9**: Autonomous IA research assistant

See `CLAUDE.md` for full roadmap.

---

## Documentation

- **CLAUDE.md**: Project context + philosophy
- **docs/layers.md**: 8-layer specification
- **src/core/**: Inline docstrings
- **tests/**: Example usage

---

## License

MIT. See LICENSE file.

---

**Status**: Active development (Phase 1 complete, Phase 2 in progress)  
**Maintainer**: Claude Code (Anthropic)  
**Created**: 2026-09-25
