# Phase 1: Architecture & Data Layer

**Status**: In Progress  
**Date**: 2026-09-25

## Overview

Phase 1 establishes the foundational architecture and data ingestion pipeline for IGWT-PF26.

**Out of scope for Phase 1:**
- Feature engineering (Layer 2+)
- Alpha research engines
- Risk measurement
- Validation framework
- Backtesting
- Monitoring and drift detection

**In scope:**
- Modular directory structure
- Datasource abstraction and adapter pattern
- OHLCV normalization with provenance tracking
- Schema and type definitions
- Structured logging
- Configuration management
- Unit tests for adapters
- Integration tests for data pipeline

---

## Architecture

### Directory Structure

```
src/
├── layers/              # Layer-specific logic (mostly empty Phase 1)
├── data/                # Data ingestion, schemas, validation
│   ├── adapters/        # Datasource implementations
│   ├── schemas/         # Type definitions, provenance
│   ├── validation/      # Data quality validators
│   └── storage/         # DuckDB, Parquet utilities (Phase 1 stub)
├── features/            # Feature definitions (Phase 2+)
├── config/              # Runtime configuration (YAML)
└── common/              # Logging, utilities
```

### Data Flow (Phase 1)

```
Configuration (YAML)
    ↓
Datasource Adapter (CoinGecko, Binance stubs)
    ↓
Normalization → OHLCV + Provenance
    ↓
Validation (OHLC ordering, no gaps, etc.)
    ↓
Storage (Parquet files with metadata)
```

---

## Key Contracts

### Datasource Adapters

All adapters implement `DatasourceAdapter` base class:

```python
class DatasourceAdapter(ABC):
    def fetch_ohlcv(symbol, timeframe, start_date, end_date) -> List[OHLCV]
    def validate_data(ohlcv_list) -> bool
```

**Current adapters:**
- `CoinGeckoAdapter` — Free tier, daily data only
- `BinanceAdapter` — Stub (Phase 1)

### Provenance Tracking

Every OHLCV candle carries:

```python
@dataclass
class Provenance:
    source: str              # "coingecko", "binance"
    provider: str            # "CoinGecko", "Binance"
    endpoint: str            # API path
    retrieval_timestamp      # When we fetched it
    event_timestamp          # When the bar closed
    symbol, timeframe        # What asset/timeframe
    schema_version           # For compatibility
    data_version             # YYYY-MM-DD
    caveats: Optional[str]   # Known issues
```

Immutable, auditable, point-in-time preserving.

### Structured Logging

All pipeline events use structured JSON logging:

```json
{
  "timestamp": "2026-09-25T14:32:00Z",
  "component": "layer1.coingecko_adapter",
  "event": "fetch_complete",
  "status": "success",
  "symbol": "BTC",
  "record_count": 500
}
```

---

## Configuration

**File:** `src/config/default.yaml`

Controls:
- Datasource endpoints and timeouts
- Storage directories
- DuckDB configuration
- Symbols and timeframes to collect
- Logging level and format
- Validation settings

**Runtime override:** Environment variables

**Secrets:** Never in YAML. Use `.env` (git-ignored).

---

## Testing Strategy (Phase 1)

### Unit Tests

- **Adapter behavior**: Symbol mapping, error handling
- **Data validation**: OHLC ordering, timestamp monotonicity, negative volumes
- **Provenance**: Fields present and correct

**Location:** `tests/unit/`

### Integration Tests

- Datasource → Normalization → Validation → Storage pipeline
- End-to-end candle ingestion
- Schema compliance

**Location:** `tests/integration/` (stub)

### Regression Tests

- Protect existing working behavior
- Prevent accidental breakage

**Location:** `tests/regression/`

---

## Implementation Checklist

### Completed ✅
- [x] Directory structure
- [x] CLAUDE.md (governance contract)
- [x] Configuration YAML template
- [x] Type definitions (OHLCV, Provenance, Feature, Validation)
- [x] Structured logging module
- [x] Datasource adapter base class
- [x] CoinGecko adapter (basic implementation)
- [x] Unit tests for adapter validation
- [x] Requirements.txt (Phase 1 deps)

### In Progress 🔄
- [ ] Integration tests (data pipeline)
- [ ] Binance adapter stub
- [ ] Parquet storage utilities
- [ ] DuckDB schema + basic queries
- [ ] Data quality validator module
- [ ] Run and verify CoinGecko adapter against live API

### Upcoming (Phase 2)
- [ ] Feature store abstraction
- [ ] Feature pipeline (technical, market, derivatives, onchain)
- [ ] Backtesting framework
- [ ] Walk-forward validation
- [ ] Leakage detection

---

## Verification

**To verify Phase 1 is working:**

```bash
# Install dependencies
pip install -r requirements.txt

# Run unit tests
pytest tests/unit/ -v

# Test adapter manually (requires internet)
python -c "
from src.data.adapters.coingecko import CoinGeckoAdapter
from datetime import datetime, timezone
adapter = CoinGeckoAdapter()
data = adapter.fetch_ohlcv('bitcoin', '1d', 
                           datetime(2025, 1, 1, tzinfo=timezone.utc),
                           datetime(2025, 1, 31, tzinfo=timezone.utc))
print(f'Fetched {len(data)} candles')
print(data[0].to_dict())
"
```

---

## Known Limitations

- **CoinGecko free tier**: Daily data only, not true OHLC (all prices are closes)
- **Binance adapter**: Stub, not implemented
- **No local caching**: Every fetch hits the API
- **No rate limiting**: Not enforced client-side yet
- **No retry logic**: Basic API errors not retried

These will be addressed in subsequent phases or when needed.

---

## Next Steps

1. **Verify adapter works** against live CoinGecko API
2. **Create integration tests** (full data pipeline)
3. **Implement Parquet storage** (write raw data)
4. **Implement DuckDB schema** (query raw data)
5. **Document data quality expectations** (Phase 2 dependencies)

---

## References

- CLAUDE.md: Governance and validation gates
- src/config/default.yaml: Runtime configuration
- src/data/schemas/types.py: Type definitions
- src/data/adapters/base.py: Adapter interface contract

