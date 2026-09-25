# IGWT-PF26 — Quant Intelligence OS

**Version**: v0.1.0  
**Status**: Phase 1 — Repository Structure & Data Layer  
**Last Updated**: 2026-09-25

---

## Mission

IGWT-PF26 is a personal quantitative research infrastructure for **decision intelligence** in crypto investment (medium/long term).

**NOT a trading bot.**  
**IS a Cabal Brain**: collect → analyze → detect asymmetries → measure risk → validate → alert.  
Decision remains human. No auto-execution.

---

## Architecture

8 distinct layers, each with clear responsibilities:

| Layer | Module | Purpose | Status |
|-------|--------|---------|--------|
| 1 | DATA INTELLIGENCE | Raw data → clean features | IN PROGRESS |
| 2 | MARKET REGIME ENGINE | Regime detection (BTC, liquidity, macro) | IN PROGRESS |
| 3 | WYCKOFF INTELLIGENCE | BCE (Bottom Confirmation Engine) ≥5/6 | IN PROGRESS |
| 4 | X20 ENGINE | Asymmetric opportunity detection | IN PROGRESS |
| 5 | NARM-P+ | Narrative + Adoption + Rotation scoring | IN PROGRESS |
| 6 | RCM/RPM ENGINE | Capital rotation detection (walk-forward validated) | IN PROGRESS |
| 7 | RRP REVIVAL RADAR | Dead token resurrection detection | IN PROGRESS |
| 8 | RPM X20 OPTIMIZER | Backtest + optimization + validation | TODO |

---

## Directory Structure

```
crypto-agent/
├── src/
│   ├── __init__.py
│   ├── layers/
│   │   ├── __init__.py
│   │   ├── layer1_data/          # Data collection & validation
│   │   ├── layer2_regime/        # Market regime detection
│   │   ├── layer3_wyckoff/       # BCE engine
│   │   ├── layer4_x20/           # X20 opportunity scanner
│   │   ├── layer5_narm/          # NARM-P+ scoring
│   │   ├── layer6_rcm/           # RCM/RPM engine
│   │   ├── layer7_rrp/           # RRP detection
│   │   └── layer8_optimizer/     # Backtest & optimization
│   ├── core/
│   │   ├── __init__.py
│   │   ├── pipeline.py           # Decision pipeline orchestration
│   │   ├── models.py             # Core data models
│   │   └── config.py             # Configuration management
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── data_validators.py    # Data validation routines
│   │   ├── feature_engine.py     # Feature engineering
│   │   └── logging.py            # Centralized logging
│   └── api/
│       ├── __init__.py
│       ├── app.py                # FastAPI app
│       └── routes.py             # API endpoints
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
│   ├── architecture.md           # System design
│   ├── api.md                    # API documentation
│   ├── layers.md                 # Each layer spec
│   └── governance.md             # Validation rules
├── data/
│   ├── raw/                      # Raw market data
│   ├── processed/                # Clean features
│   └── validation_reports/       # Backtests + reports
├── notebooks/
│   └── research/                 # Analysis notebooks
├── .github/
│   └── workflows/                # CI/CD pipelines
├── pyproject.toml                # Python project config
├── requirements.txt              # Dependencies
├── pytest.ini                    # Test config
└── README.md                     # User-facing doc

```

---

## Development Philosophy

- **Exactitude > speed**. Validate before shipping.
- **Research > speculation**. Data-driven decisions only.
- **Robustness > complexity**. Simple, testable modules.
- **No premature abstractions**. 3 lines → helper; no half-finished code.
- **Defensive data handling**. Validate at system boundaries.
- **Walk-forward validation mandatory** for all models. No lookahead bias.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+ |
| Web Framework | FastAPI |
| Data Storage | Parquet + DuckDB |
| Streaming | Kafka / Redis Streams |
| ML/Optimization | MLFlow + Optuna |
| Frontend | Next.js + React |
| Visualization | Recharts (mobile-first) |

---

## Data Sources (No API Trading)

✅ **Public data only** (no CEX API access):
- CoinGecko (prices, market data)
- Binance public OHLCV
- Glassnode (on-chain metrics)
- CryptoQuant (derivatives, funding rates)
- DefiLlama (TVL, yield)
- Nansen (smart money flows)
- Arkham (fund movements)

❌ **No automatic trading**:
- No CEX API credentials
- No order execution
- Wallet: Tangem (cold storage)
- Execution: Manual only

---

## Core Rules

### Signal Validation

**BCE ≥ 5/6 mandatory** before any entry signal.

```
BCE = Sum([
  wyckoff_structure,
  volume_analysis,
  selling_exhaustion,
  smart_money_accumulation,
  market_structure,
  momentum_confirmation
]) / 6
```

### FOMO Circuit Breaker

If price discovery + euphoria + extension → **reduce score**.  
System must prevent emotional buys.

### Walk-Forward Testing

Every backtest must:
1. Use ≥200 trades minimum
2. Show Profit Factor > 1.3
3. Max drawdown < 25%
4. Pass walk-forward validation
5. **No lookahead bias**

---

## Governance

Each feature requires:
1. Specification document
2. Implementation
3. Unit tests (≥80% coverage)
4. Integration tests
5. Walk-forward validation (models)
6. Version freeze before merge

---

## Phase Implementation Order

**Phase 1** (NOW): Repository structure + Data layer  
**Phase 2**: Feature Store + Backtesting framework  
**Phase 3**: BCE Engine (production-ready)  
**Phase 4**: X20 Engine  
**Phase 5**: NARM-P+  
**Phase 6**: RCM/RPM  
**Phase 7**: RRP  
**Phase 8**: Dashboard (Next.js)  
**Phase 9**: Agent IA (autonomous research assistant)

---

## CI/CD & Testing

- Pre-commit hooks: format, lint, type-check
- Unit tests: pytest + coverage
- Integration tests: real data validation
- Walk-forward backtests: MLFlow tracking
- Dashboard: Chromatic for visual regression

---

## Key Files

| File | Purpose |
|------|---------|
| `src/core/pipeline.py` | Decision orchestration |
| `src/layers/layer1_data/collector.py` | Data ingestion |
| `src/layers/layer3_wyckoff/bce.py` | Bottom Confirmation |
| `tests/fixtures/market_data.py` | Test data |
| `docs/layers.md` | Layer specifications |

---

## Git Workflow

- **Branch**: `claude/gracious-pascal-mcg5bl` (development)
- **Commits**: Descriptive, atomic, with Co-Authored-By footer
- **PRs**: Mirror `.github/pull_request_template.md` structure
- **Merge**: Squash to main after approval

---

## Memory / Preferences

**Token economy**: Concise responses, no verbiage, direct answers.  
**Code style**: Minimal comments, well-named identifiers only.  
**No hardcoding**: Config externalized, environment variables enforced.

---

## Next Steps (Auto-Driven)

1. ✅ CLAUDE.md created (now)
2. → Restructure src/ directories
3. → Move existing engines to src/layers/
4. → Create layer1_data module (collector + validator)
5. → Write layer specs (docs/layers.md)
6. → Add pyproject.toml + modern Python packaging
7. → Set up pytest fixtures
8. → Begin Phase 2

---

**Status**: Ready for Phase 1 restructuring. No user input needed. Proceeding autonomously.
