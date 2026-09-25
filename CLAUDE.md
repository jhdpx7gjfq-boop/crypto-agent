# IGWT-PF26 Quant Research Infrastructure

## Contexte

IGWT-PF26 est une infrastructure personnelle de recherche quantitative destinée à construire un système d'intelligence décisionnelle pour l'investissement crypto moyen/long terme.

**Pas un trading bot. Un "Cabal Brain" : analyste quant augmenté.**

## Architecture Cible : 8 Layers

1. **Data Intelligence** : Multi-source, contracted, versioned
2. **Market Regime Engine** : Global context detection (DXY, risk-on/off, macro)
3. **Wyckoff / BCE** : Bottom Confirmation Engine (≥5/6 required)
4. **X20 Engine** : Asymmetric opportunity detection (Fundamental + Narrative + Quant)
5. **NARM-P+** : Narrative Adoption Rotation Model (100-point scoring)
6. **RCM/RPM** : Capital Rotation + Rotation Confirmation Model
7. **RRP** : Revival Radar Pipeline (dead token renaissance detection)
8. **Dashboard** : Next.js, iPhone-responsive, live data

## Current State (Phase 1 Foundation)

**Implemented** :
- Layer 1 skeleton : Data abstraction + persistence
- Test infrastructure : Fixtures, contracts validation
- Config external : YAML + Pydantic

**Placeholders** :
- Layers 2-7 : Module structure ready, implementation deferred

## Mandatory Constraints

- ✅ **RESEARCH_ONLY** : No autonomous trade execution, decision remains human
- ✅ **No data invention** : Zero synthetic data, zero forecasting
- ✅ **No alpha promotion** : Quantitative validation PIT/OOS/WFV required
- ✅ **Look-ahead prevention** : Explicit timestamps, strict train/test separation
- ✅ **Provenance tracking** : Source + timestamp + version for every datapoint
- ✅ **Type safety** : All inputs validated (Pydantic)
- ✅ **No mixing** : Research and production strictly separated
- ✅ **Statistical rigor** : Walk Forward mandatory for all quantitative modules
- ✅ **Audit trail** : What, who, when for every data modification
- ✅ **Zero hardcoding** : Config external (YAML)

## Tech Stack

**Core** : Python 3.11+
**Backend** : FastAPI (future API)
**Data** : DuckDB (queries) + Parquet (storage) + Turso (metadata)
**ML/Validation** : MLFlow (experiment tracking)
**Testing** : pytest + fixtures
**Linting** : ruff + mypy (strict)
**Docs** : Markdown

## Module Structure

```
src/
  __init__.py
  config.py                # External config (YAML → Pydantic)
  
  data/                    # Layer 1 : Data Intelligence
    __init__.py
    sources.py             # Datasource ABC + CoinGecko impl
    contracts.py           # Pydantic schemas (DataPoint, etc.)
    persistence.py         # DuckDB + Parquet operations
  
  models/                  # Layers 2-7 (placeholders)
    regime/
      __init__.py
    wyckoff/
      __init__.py
    x20/
      __init__.py
    narm_p/
      __init__.py
    rcm_rpm/
      __init__.py
    rrp/
      __init__.py
  
  pipeline/                # Feature engineering
    __init__.py
    raw.py                 # Raw data ingestion
    validation.py          # Data contract checking
    features.py            # Feature computation
  
  utils/
    __init__.py
    logging.py             # Structured logs + MLFlow
    types.py               # Common types, Pydantic base models
    validation.py          # Input validation utilities

tests/
  conftest.py              # Fixtures (mock DB, datasources)
  test_data_sources.py
  test_contracts.py
  test_persistence.py
  test_pipeline.py
  test_main.py             # Original tests (preserved)

config.yaml                # Config template
config.local.yaml          # Local overrides (gitignored)
pyproject.toml             # Project metadata
```

## Key Principles

1. **Exactitude > Rapidité**
2. **Validation > Intuition**
3. **Données > Opinions**
4. **Recherche > Spéculation**
5. **Robustesse > Complexité**

## Governance

- Each module : Spec + Impl + Tests + Version freeze
- No module considered "done" without proof of validation
- Walk Forward required for all quantitative work
- Changelog per release
- Type hints mandatory on all new code

## Phase 1 Checklist

- [x] CLAUDE.md
- [x] `src/` directory structure + `__init__.py`
- [x] `config.yaml` template + `config.py` (Pydantic)
- [x] `data/sources.py` : Datasource ABC + timestamp/provenance
- [x] `data/contracts.py` : DataPoint + schemas
- [x] `data/persistence.py` : DuckDB + Parquet CRUD
- [x] `utils/logging.py` : Structured logs
- [x] Tests refactor : Fixtures + new test structure
- [x] Type hints on all new code
- [x] GH Actions : lint + mypy + pytest
- [ ] Architecture.md (follow-up)
- [ ] README per layer (follow-up)

## Next Phases

**Phase 2** : Feature Store implementation + Backtester ABC
**Phase 3** : Layer 2 (Market Regime Engine) implementation
**Phase 4** : Layer 3 (Wyckoff / BCE) implementation
**Phases 5-7** : Layers 4-6 implementations
**Phase 8** : Dashboard (Next.js + iPhone)
**Phase 9** : Research IA Assistant Agent

---

**Status** : Phase 1 - Foundation (In Progress)
**Last Updated** : 2026-09-25
**Version** : 0.1.0-alpha
