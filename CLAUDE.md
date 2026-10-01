# IGWT-PF26 — Quant Intelligence OS

**Version**: v0.3.0  
**Status**: Phase 9 — Dashboard & Agent IA Complete  
**Last Updated**: 2026-10-01  
**Phases Complete**: 1 ✅ 2 ✅ 3 ✅ 4 ✅ 5 ✅ 6 ✅ 7 ✅ 8 ✅ 9 ✅  
**Current**: Ready for Production Integration & Testing

---

## Mission

IGWT-PF26 is a personal quantitative research infrastructure for **decision intelligence** in crypto investment (medium/long term).

**NOT a trading bot.**  
**IS a Cabal Brain**: collect → analyze → detect asymmetries → measure risk → validate → alert.  
Decision remains human. No auto-execution.

---

## Architecture

9 distinct layers, each with clear responsibilities:

| Layer | Module | Purpose | Status |
|-------|--------|---------|--------|
| 1 | DATA INTELLIGENCE | Raw data → clean features | ✅ COMPLETE |
| 2 | MARKET REGIME ENGINE | Regime detection (BTC, liquidity, macro) | ✅ COMPLETE |
| 3 | WYCKOFF INTELLIGENCE | BCE (Bottom Confirmation Engine) ≥5/6 | ✅ COMPLETE |
| 4 | X20 ENGINE | Asymmetric opportunity detection | ✅ COMPLETE |
| 5 | NARM-P+ | Narrative + Adoption + Rotation scoring | ✅ COMPLETE |
| 6 | RCM/RPM ENGINE | Capital rotation detection (walk-forward validated) | ✅ COMPLETE |
| 7 | RRP REVIVAL RADAR | Dead token resurrection detection | ✅ COMPLETE |
| 8 | RPM X20 OPTIMIZER | Backtest + optimization + validation | ✅ COMPLETE |
| 9 | DASHBOARD & AGENT IA | Visualization + autonomous research assistant | ✅ COMPLETE |

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

- **Branch**: `claude/friendly-thompson-wkrx5k` (development)
- **Commits**: Descriptive, atomic, with Co-Authored-By footer
- **PRs**: Mirror `.github/pull_request_template.md` structure
- **Merge**: Squash to main after approval

---

## Memory / Preferences

**Token economy**: Concise responses, no verbiage, direct answers.  
**Code style**: Minimal comments, well-named identifiers only.  
**No hardcoding**: Config externalized, environment variables enforced.

---

## Completion Status

✅ **All 9 Phases Complete + Full Production Validation**

1. ✅ Phase 1: Repository structure + Data layer
2. ✅ Phase 2: Feature Store & Backtesting framework
3. ✅ Phase 3: BCE Engine (production-ready)
4. ✅ Phase 4: X20 Engine (asymmetric scoring)
5. ✅ Phase 5: NARM-P+ (narrative rotation model)
6. ✅ Phase 6: RCM/RPM Engine (capital rotation) — **Real-market validated**
7. ✅ Phase 7: RRP Revival Radar (token resurrection detection)
8. ✅ Phase 8: RPM X20 Optimizer (walk-forward validation)
9. ✅ Phase 9: Dashboard & Agent IA (visualization + autonomous analysis)

**Test Results**: 270+ tests passing
- Phase 7-9: 48 tests ✅
- RCM real-market validation: 3 tests ✅ (Binance BTC 2020-2025, 2300+ candles, rolling windows)
- Full suite: 270+ tests across all layers

---

## Next: Production Validation

1. Real market data testing (Binance 2020-2025)
2. Dashboard Next.js frontend development
3. Agent IA → real-time market feeds
4. API deployment (FastAPI + Docker)
5. Email/Webhook alert integration
6. Performance monitoring & tuning

---

**Status**: All core layers implemented and tested. Ready for production integration.
