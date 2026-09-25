# IGWT-PF26 — Claude Code Operating Contract

**Version**: 1.0  
**Last Audit**: 2026-09-25  
**Status**: Architecture Phase 1 — Initialization

---

## 1. Mission

IGWT-PF26 is a crypto-only Quant Intelligence OS.

**Primary objective:**
Build a reproducible, auditable and research-first quantitative decision system for crypto markets.

**Constraints:**
- The system is **RESEARCH_ONLY**
- It does not execute trades, place orders, cancel orders, manage leverage or custody assets
- Execution/custody is outside the system
- No autonomous trading whatsoever

---

## 2. Core Principles

1. Never invent data, metrics, test results or sources
2. Never promote an unvalidated research idea directly into production
3. Preserve provenance and timestamps for every external dataset
4. Prevent look-ahead bias and data leakage
5. Separate: RAW DATA → FEATURES → RESEARCH → VALIDATED ALPHA → PRODUCTION LOGIC
6. Every quantitative change must be testable and reproducible
7. Prefer small isolated modules over large coupled modules
8. Do not modify production scoring engines without explicit approval
9. No autonomous trading or transaction execution
10. Documentation and governance changes must remain auditable through Git

---

## 3. System Architecture

**Target structure:**

```
src/
├── layers/
│   ├── layer1_data/          # Data ingestion, normalization, validation
│   ├── layer2_features/      # Feature calculation & validation
│   ├── layer3_alpha/         # Alpha research candidates
│   ├── layer4_regime/        # Market regime detection
│   ├── layer5_risk/          # Risk measurement & breakers
│   ├── layer6_validation/    # PIT/OOS/WFV testing
│   ├── layer7_decision/      # BCE, X20, NARM-P+, RPM, RRP
│   └── layer8_monitoring/    # Data quality, drift detection, alerting
│
├── data/
│   ├── adapters/             # Datasource implementations
│   ├── schemas/              # Data structure definitions
│   ├── validation/           # Schema & data quality validators
│   └── storage/              # DuckDB, Parquet, metadata
│
├── features/
│   ├── technical/            # OHLCV-based features
│   ├── market/               # Market structure, funding, OI
│   ├── derivatives/          # Liquidation, spreads, basis
│   ├── onchain/              # Transfer, holder metrics
│   └── alternative/          # Social sentiment, narrative
│
├── config/                   # YAML configs, env templates
├── common/                   # Shared utilities, logging, types
└── __init__.py

tests/
├── unit/                     # Module-level tests
├── integration/              # Pipeline tests (data → features → validation)
├── regression/               # Protect validated behaviour
├── research/                 # Backtests, experiments
└── validation/               # PIT/OOS/WFV leakage tests

research/                     # Experimental work, isolated from production
experiments/
docs/
```

**Layer boundaries are explicit and must remain maintainable.**

---

## 4. Layer Contracts

### Layer 1 — Data Ingestion & Normalization

**Responsibilities:**
- Datasource adapters
- Ingestion and retry logic
- Schema normalization
- Timestamp handling & timezone consistency
- Data quality validation
- Provenance tracking (source, timestamp, version)
- Historical storage

**Current datasources (planned):**
- CoinGecko (public API)
- Binance (public API, OHLCV only)
- Glassnode (if available)

**No datasource should leak provider-specific implementation into higher layers.**

**Storage contract:**
```
data/raw/
└── {provider}/{symbol}/{timeframe}/
    └── YYYY-MM-DD.parquet (with metadata)
```

---

### Layer 2 — Feature Engineering

**Responsibilities:**
- Deterministic feature calculation
- Feature validation and schema compliance
- Missing-data handling policies
- Feature versioning

**Every feature must declare:**
```yaml
name: "feature_name"
version: "1.0"
source: "layer1.datasource_name"
timestamp_semantics: "point-in-time or bar-close"
lookback: 20  # bars / days
calculation: "mathematical description"
missing_data_policy: "forward-fill | interpolate | null"
validation_status: "ready | experimental"
```

**No future information in features.**

---

### Layer 3 — Alpha Discovery (Research)

**Responsibilities:**
- Research signal candidates
- Independent alpha testing
- Robustness & sensitivity analysis
- Ablation studies

**Constraint:** Research candidates are NOT production signals until validated.

**Must reside in:** `research/` or `experiments/` directory initially.

---

### Layer 4 — Market Regime

**Responsibilities:**
- Market regime detection (trending, ranging, volatile, quiet)
- Liquidity regime classification
- Volatility regime bucketing
- Regime-conditioned filtering

**No future information in regime features.**

---

### Layer 5 — Risk Measurement

**Responsibilities:**
- Drawdown calculation
- Exposure sizing
- Liquidity risk assessment
- Risk breakers (FOMO circuit)
- Crowding detection

**Risk logic must remain independent from alpha generation.**

---

### Layer 6 — Validation (Gate-keeping)

**Responsibilities:**
- Point-in-time (PIT) validation
- Out-of-sample (OOS) validation
- Walk-forward validation (WFV)
- Leakage detection
- Sensitivity analysis
- Robustness testing

**Gate rule:** No alpha becomes production-ready without validation evidence.

---

### Layer 7 — Decision Support

**Target engines:**
- BCE (Bottom Confirmation Engine)
- X20 Engine
- NARM-P+
- RPM / RCM (Rotation/Capital Flow Models)
- RRP (Revival Radar Pipeline)

**Constraint:** Decision engines consume validated upstream outputs only.

**These engines must not create new research logic silently.**

---

### Layer 8 — Monitoring & Drift Detection

**Responsibilities:**
- Data quality monitoring
- Feature drift detection
- Signal drift detection
- Model degradation tracking
- Pipeline failure alerting
- Provenance monitoring

---

## 5. Research → Production Lifecycle

```
IDEA
  ↓ (explicit proposal)
RESEARCH_CANDIDATE
  ↓ (specification written)
SPECIFIED
  ↓ (backtested on historical data)
BACKTESTED
  ↓ (validated PIT)
PIT_VALIDATED
  ↓ (validated OOS)
OOS_VALIDATED
  ↓ (walk-forward tested)
WFV_VALIDATED
  ↓ (robustness confirmed)
ROBUST
  ↓ (ablation complete)
ABLATION_COMPLETE
  ↓ (explicit approval required)
PRODUCTION_APPROVED
```

**Rule:** A research idea must never skip validation stages.

---

## 6. Quantitative Validation Reporting

When validation metrics are reported, include:

```
Sample size
Time period covered
Universe / symbols
Timeframe (1h, 1d, 1w)
Train / test split
Walk-forward methodology
Transaction assumptions (fees, slippage)
Metrics:
  - Sharpe ratio
  - Profit Factor
  - Max Drawdown
  - Hit rate
  - Expectancy
  - Turnover
  - Trade count
  - Exposure
Confidence intervals / uncertainty
Limitations
```

**Never report a metric without calculation context.**

---

## 7. Data Requirements & Provenance

Every dataset must preserve:

```yaml
source: "coingecko | binance | glassnode | ..."
provider: "vendor name"
endpoint: "API path or feed name"
retrieval_timestamp: "2026-09-25T14:32:00Z"
event_timestamp: "2026-09-25T14:30:00Z (bar close time)"
symbol: "BTC | ETH | ..."
timeframe: "1h | 1d | 4h"
schema_version: "1.0"
data_version: "2026-09-25"
caveats: "any known issues | data gaps"
```

**Priority:**
1. Machine-readable (Parquet with metadata)
2. Point-in-time compatible
3. Historically reproducible
4. Timestamped precisely
5. Auditable through Git/versioning

**Rule:** Current data must not be silently substituted for historical data in retrospective research.

---

## 8. Storage & Backup Strategy

**Preferred research storage:**
- Parquet for datasets (with metadata)
- DuckDB for analytical queries
- JSON/YAML for metadata and configurations

**Structure:**
```
data/
├── raw/                      # Untransformed, source-stamped
├── normalized/               # Schema-normalized, ready for features
├── features/                 # Calculated features
├── datasets/                 # Research datasets (PIT-stamped)
├── metadata/                 # Provenance and lineage tracking
└── validation/               # Validation results, leakage tests
```

**Rule:** Never overwrite raw historical data. Immutable raw storage.

---

## 9. Configuration Management

**Runtime configuration must not be hardcoded.**

Use:
- `config/*.yaml` for environment-specific settings
- `.env` (git-ignored) for secrets and local overrides
- Environment variables for runtime flags

**Secret handling:**
- API keys NEVER in source code
- API keys NEVER in tests
- API keys NEVER in logs
- API keys NEVER in documentation
- API keys NEVER committed to Git

Approved: `BOT_TOKEN`, `CHAT_ID`, `GLASSNODE_API_KEY` as env vars only.

---

## 10. Structured Logging

Every important pipeline event must expose:

```json
{
  "timestamp": "2026-09-25T14:32:00Z",
  "component": "layer1.coingecko_adapter",
  "event": "fetch_complete",
  "status": "success | error | warning",
  "symbol": "BTC",
  "timeframe": "1d",
  "version": "1.0",
  "duration_ms": 234,
  "record_count": 500,
  "error": null
}
```

**Logs must never expose secrets.**

---

## 11. Testing Requirements

Minimum coverage:

| Category | Purpose |
|----------|---------|
| **Unit** | Individual functions, adapters, validators |
| **Integration** | Datasource → normalization → storage → feature pipeline |
| **Regression** | Protect validated behaviour from accidental changes |
| **Research** | Backtests, walk-forward validation, ablation studies |
| **Validation** | PIT/OOS/WFV tests, leakage detection, robustness |

**Rule:** A code change is incomplete if it breaks existing tests.

---

## 12. No-Lookahead Rules (Critical)

**Forbidden patterns:**
- Future OHLCV candles in historical feature calculation
- Future funding rates / open interest in historical analysis
- Future token supply or unlock information
- Future price labels leaking into training features
- Universe selection using future price information
- Survivorship-biased historical universes
- Post-event information used before publication timestamp

**All research datasets must respect information availability at decision time.**

---

## 13. Git & Change Governance

**Before modifying production logic:**

1. Inspect existing implementation
2. Inspect tests and dependencies
3. Inspect relevant documentation
4. Identify breaking changes
5. Propose change explicitly
6. Obtain approval when required (see section 14)
7. Implement minimally
8. Run all tests
9. Report changed files and validation results

**No broad refactors without explicit approval.**
**No silent architectural replacements.**

---

## 14. Approval Gates

### Automatic Approval (Claude Code)
- Bug fixes in tests or non-production modules
- Documentation updates
- Config adjustments (within existing schemas)
- Small feature additions to data adapters

### Explicit Approval Required
- New layer logic or major refactors
- Changes to production decision engines (Layer 7)
- New validation gates or data requirements
- Changes to feature definitions affecting historical datasets
- Risk measurement modifications

**Request approval explicitly before implementation.**

---

## 15. Research Isolation

**Experimental work must remain isolated.**

Approved locations:
- `research/` directory
- `experiments/` directory
- `tests/research/` for backtests
- Git branches prefixed `research/` or `experiment/`

**Every research experiment must document:**
```yaml
experiment_id: "EXP-001-bce-sensitivity"
hypothesis: "BCE performance improves with adjusted smoothing"
dataset: "BTC 2022-2026 1D"
methodology: "walk-forward, 6mo train, 1mo test"
results: "Sharpe improved 0.15, but WFV failed"
status: "REJECTED"
date: "2026-09-25"
notes: "Over-optimized on training period"
```

**Rule:** Do not place experimental alpha directly into production modules.

---

## 16. Definition of Done

A component is complete only when:

- ✅ Implementation exists
- ✅ Tests exist (unit + integration)
- ✅ Interfaces are documented
- ✅ Data assumptions are documented (provenance, schema)
- ✅ Failure modes are known and handled
- ✅ Reproducibility is demonstrated (no hidden randomness)
- ✅ No-lookahead constraints are verified
- ✅ Git diff is reviewed (minimal, safe changes)
- ✅ Validation status is explicitly declared

**If any of these is missing → component is NOT complete.**

---

## 17. Claude Code Behaviour Contract

Claude Code **must:**
- Inspect before editing (read existing code first)
- Make the smallest safe change (don't refactor speculatively)
- Preserve existing working behaviour (regressions are bugs)
- Avoid speculative implementation (implement only what's asked)
- Ask for approval before major architectural changes
- Never invent missing APIs or test results
- Never claim validation that was not performed
- Clearly distinguish implementation from research
- Report uncertainty explicitly

**If information is unavailable:**
- State: "I don't know."
- Do not guess or invent
- Ask for clarification

---

## 18. Current Status Audit

**Verified against repo as of 2026-09-25:**

| Component | Status | Evidence |
|-----------|--------|----------|
| **ARCHITECTURE** | PHASE 1 IN PROGRESS | Structure dirs created, not populated |
| **DATA LAYER** | NOT STARTED | Only basic BTC polling exists |
| **FEATURE STORE** | NOT STARTED | No feature definitions |
| **BACKTESTING** | NOT STARTED | No framework |
| **BCE** | UNKNOWN | Not in current repo, verify research branch |
| **X20** | UNKNOWN | Not in current repo, verify research branch |
| **NARM-P+** | UNKNOWN | Not in current repo, verify research branch |
| **RPM/RCM** | UNKNOWN | Not in current repo, verify research branch |
| **RRP** | UNKNOWN | Not in current repo, verify research branch |
| **DASHBOARD** | NOT STARTED | No UI |

**Status is verified from Git, not assumed.**

---

## 19. Phase 1 Checklist (Now)

- [ ] Create directory structure (src/, tests/, research/, etc.)
- [ ] Initialize config/ with YAML templates
- [ ] Implement Layer 1: Datasource abstraction (CoinGecko adapter)
- [ ] Implement data/ storage (Parquet, DuckDB, metadata)
- [ ] Write data quality validators
- [ ] Document data schemas and provenance tracking
- [ ] Add structured logging
- [ ] Create integration tests (datasource → storage)
- [ ] Verify no-lookahead compliance
- [ ] Document current status in this file

---

## 20. Governance Updates

**This file is the durable contract.**

Updates to CLAUDE.md:
- Must be Git-committed
- Must justify why the rule is changing
- Must maintain backwards compatibility with existing layers
- Cannot remove validation gates
- Cannot weaken no-lookahead rules

---

**End of Contract**

Next: Execute Phase 1. Report progress in Git commits.

