# Path A: Phase 2 Integration Setup Guide

**Status**: 🟡 SCAFFOLDING READY (awaiting API credentials)  
**Date**: 2026-09-25  
**Phase**: 2 — API Integration Framework  

---

## Overview

Phase 2 integration scaffolding is complete and ready to accept CryptoQuant and Glassnode API credentials. Once credentials are provided, the framework will:

1. **Validate credentials** (real-time check)
2. **Collect liquidation ground truth** (CryptoQuant)
3. **Collect exchange flows** (Glassnode)
4. **Cross-validate data sources** (timestamp alignment, price consistency, flow-event correlation)
5. **Unblock Phase 3 walk-forward validation**

---

## What's Ready

### Credential Management
- ✅ `src/research/phase2_credentials.py` — Credential loader + validator
- ✅ `.env.example` — Environment variable template
- ✅ Status reporting tool

### Integration Framework
- ✅ `src/research/phase2_integration.py` — CryptoQuantCollector, GlassnodeCollector, SourceValidator
- ✅ `Phase2IntegrationPipeline` — 4-stage orchestrator
- ✅ Data classes: `LiquidationEvent`, `ExchangeFlowRecord`

### Testing Scaffolding
- ✅ `tests/integration/test_phase2_integration.py` — Test stubs (ready for real API tests)
- ✅ Acceptance criteria validation hooks

---

## Setup Steps

### 1. Request CryptoQuant API Key

Visit: **https://www.cryptoquant.com**

- Sign up / Log in
- Navigate to **API Settings**
- Request API access (free or paid tier)
- You need: **Liquidation Events API** endpoint
- Required data: Liquidation events by exchange, asset, side (BTC, ETH recommended)
- Copy your API key

### 2. Request Glassnode API Key

Visit: **https://glassnode.com**

- Sign up / Log in
- Navigate to **API Settings**
- Request API access (free tier: 1000 requests/month)
- You need: **On-Chain Metrics API** 
- Required data: CEX inflows/outflows (BTC, ETH)
- Copy your API key

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
# Copy from .env.example
cp .env.example .env

# Edit .env with your actual keys
export CRYPTOQUANT_API_KEY="<your_cryptoquant_key>"
export GLASSNODE_API_KEY="<your_glassnode_key>"

# Verify credentials are loaded
python src/research/phase2_credentials.py
```

Expected output if credentials are valid:
```
======================================================================
PHASE 2 CREDENTIAL STATUS
======================================================================
  ✓ CryptoQuant............................ valid
  ✓ Glassnode.............................. valid
======================================================================

Overall Status: READY ✓
```

---

## Activate Phase 2

Once credentials are configured:

```python
from src.research.phase2_integration import Phase2IntegrationPipeline

pipeline = Phase2IntegrationPipeline(
    cryptoquant_key=os.getenv("CRYPTOQUANT_API_KEY"),
    glassnode_key=os.getenv("GLASSNODE_API_KEY"),
)

# Run full integration (collect + validate)
results = pipeline.run_full_integration(
    assets=["BTC", "ETH"],
    days=180,  # 180-day lookback window
)

# Results contain:
# - liquidation_events: List[LiquidationEvent]
# - exchange_flows: List[ExchangeFlowRecord]
# - validation_report: Dict with timestamp alignment, price consistency, etc.
```

---

## Expected Data Volume

### Liquidation Events (CryptoQuant)
- **BTC**: ~630 events (180 days @ ~3.5/day average)
- **ETH**: ~630 events
- **Total**: ~1,260 liquidation records

### Exchange Flows (Glassnode)
- **BTC**: ~180 daily records (one per day)
- **ETH**: ~180 daily records
- **Total**: ~360 flow records

### Combined Phase 2 Volume
**~1,620 total ground truth data points**

---

## Validation Checkpoints

Phase 2 completes successfully when:

| Criterion | Target | Status |
|-----------|--------|--------|
| CryptoQuant credentials valid | ✓ | ⏳ Awaiting |
| Glassnode credentials valid | ✓ | ⏳ Awaiting |
| Liquidation events collected | ≥500 | ⏳ Awaiting |
| Exchange flow records collected | ≥180 | ⏳ Awaiting |
| Timestamp alignment | >80% | ⏳ Awaiting |
| Price consistency | Validated | ⏳ Awaiting |
| Flow-event correlation | Analyzed | ⏳ Awaiting |
| No data quality issues | Verified | ⏳ Awaiting |

---

## Files Structure

```
crypto-agent/
├── .env.example                          ← Environment variable template
├── .env                                  ← Your credentials (gitignored)
├── src/research/
│   ├── phase2_credentials.py             ← Credential manager
│   ├── phase2_integration.py             ← API collectors + validators
│   └── phase1_*.py                       ← Phase 1 (completed)
├── tests/integration/
│   └── test_phase2_integration.py        ← Test scaffolding (ready for real tests)
└── docs/
    ├── PATH_A_PHASE2_SETUP.md            ← This document
    ├── PATH_A_PHASE2_STATUS.md           ← Status tracking
    └── PATH_A_PHASE1_COMPLETION.md       ← Phase 1 results
```

---

## Testing

### Pre-Integration Test (Credentials Only)
```bash
# Verify credentials without calling APIs
python src/research/phase2_credentials.py
```

### Integration Tests
```bash
# Run tests (skips real API calls if credentials missing)
pytest tests/integration/test_phase2_integration.py -v

# Run with real API calls (requires credentials)
CRYPTOQUANT_API_KEY="..." GLASSNODE_API_KEY="..." pytest tests/integration/ -v
```

---

## Troubleshooting

### "Missing CRYPTOQUANT_API_KEY"
→ Visit https://www.cryptoquant.com, request API access, then:
```bash
export CRYPTOQUANT_API_KEY="<your_key>"
```

### "Missing GLASSNODE_API_KEY"
→ Visit https://glassnode.com, request API access, then:
```bash
export GLASSNODE_API_KEY="<your_key>"
```

### "API Rate Limited"
→ Check API subscription tier. Free tiers have request limits. Upgrade if needed.

### "Timestamp Alignment < 80%"
→ Data sources may have gaps. Verify both APIs return data for the requested period.

---

## Timeline

```
✅ Phase 1 (Sept 25):        Data collection complete (1,460 points)
⏳ Phase 2 (Oct 2-15):       API integration (scaffolding ready, awaiting credentials)
  └─ Step 1: Request keys   (~2-3 business days)
  └─ Step 2: Configure env  (~1 hour)
  └─ Step 3: Run pipeline   (~1 day)
⏳ Phase 3 (Oct 16-22):      Walk-forward validation (ready, blocked on Phase 2)
⏳ Phase 4 (Oct 23-Nov 19):  Research paper & findings
```

---

## Next Action

1. **Request API credentials** from CryptoQuant and Glassnode
2. **Configure environment variables** in `.env`
3. **Verify credentials** with: `python src/research/phase2_credentials.py`
4. **Activate Phase 2** integration when ready

**Status**: All scaffolding complete. Ready to accept credentials.

---

**Generated**: 2026-09-25  
**Phase**: 2 (Integration Framework)  
**Governance**: Research-only, no training/optimization, walk-forward validation mandatory
