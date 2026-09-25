# Path A: Liquidation Independent Alpha — Status (September 2026)

**Overall Status**: ⏳ BLOCKED AT PHASE 2 (Awaiting API Credentials)  
**Date**: 2026-09-25  
**Last Update**: Phase 1 real data audit completed

---

## Status Summary

### ✅ Phase 1: Data Collection
- **OHLCV**: Real (CoinGecko API, 181 candles per asset)
- **Features**: Synthetic (still using mock generators)
- **Governance**: Real data loaded and validated
- **Data Quality**: PASSED all integrity checks
- **Blocker**: Features require real derivatives/on-chain data (APIs blocked or not yet connected)

### ⏳ Phase 2: Ground Truth Integration
- **Status**: Framework ready, awaiting credentials
- **Requirements**:
  - CryptoQuant API key (liquidation events)
  - Glassnode API key (exchange flows)
- **Mock Test**: F1=0.691, Accuracy=0.619 ✓
- **Real Data**: **NOT YET OBTAINED** — blocking real validation
- **Estimated Impact**: 2-3 business days to acquire + 1 day to process

### ⏳ Phase 3: Walk-Forward Validation
- **Status**: Framework ready, awaiting Phase 2 real data
- **Mock Test**: F1=0.691 (validates pipeline, NOT signal quality)
- **Acceptance Gates**: F1≥0.55 ✓ (on mock), Accuracy≥0.50 ✓ (on mock)
- **Real Test**: **BLOCKED** on Phase 2 credentials

---

## Data Pipeline Current State

```
Phase 1 OHLCV (Real ✓)
        ↓
Phase 1 Features (Synthetic ⏳)
        ↓
Phase 2 Liquidations (Awaiting credentials ⏳)
Phase 2 Exchange Flows (Awaiting credentials ⏳)
        ↓
Phase 3 Walk-Forward (Framework ready ⏳)
        ↓
Validation Metrics (Can't compute without Phase 2 ⏳)
```

---

## Critical Blocker

**CryptoQuant API Key + Glassnode API Key**

Both required to proceed beyond Phase 1.

- Without these: Phase 2/3 remain framework-only (mock data used)
- With these: Can validate signal with real ground truth (~48-72 hours)
- Current: Credentials not obtained

---

## What's Real vs Mock

| Component | Status | Source | Notes |
|-----------|--------|--------|-------|
| **OHLCV** | ✓ Real | CoinGecko | 181 daily candles per asset |
| **Funding Pressure** | ⏳ Mock | phase1_data_collector.py | Needs Deribit API |
| **Derivative Stress** | ⏳ Mock | phase1_data_collector.py | Needs Deribit API |
| **Cascade Likelihood** | ⏳ Mock | phase1_data_collector.py | Synthetic score |
| **Liquidations** | ⏳ Mock | phase2_mock_test.py | Needs CryptoQuant API |
| **Exchange Flows** | ⏳ Mock | phase2_mock_test.py | Needs Glassnode API |

---

## Files Status

| File | State | Purpose |
|------|-------|---------|
| src/research/binance_real_collector.py | ✓ Complete | Real Binance OHLCV (blocked by proxy 451) |
| src/research/phase1_real_data.py | ✓ Complete | Real CoinGecko OHLCV (working ✓) |
| src/research/phase1_data_collector.py | ⏳ Mock | Features still synthetic |
| src/research/phase2_integration.py | ✓ Framework | Ready for real credentials |
| src/research/phase3_walkforward.py | ✓ Framework | Ready for Phase 2 data |
| docs/PHASE1_REAL_DATA_AUDIT.md | ✓ New | Audit report (real data validated) |
| docs/PATH_A_TESTING_COMPLETE.md | ⚠ Outdated | Claims Phase 1 complete (was mock) |

---

## Next Actions (Priority Order)

### 1. Acquire API Credentials (External, 2-3 days)
```
→ CryptoQuant: https://www.cryptoquant.com
  Request: Liquidation Events API access
  
→ Glassnode: https://glassnode.com
  Request: On-Chain Metrics API access
```

### 2. Configure Environment (1 hour)
```bash
cp .env.example .env
# Edit with actual API keys
export CRYPTOQUANT_API_KEY="<your_key>"
export GLASSNODE_API_KEY="<your_key>"
```

### 3. Run Phase 2 with Real Data (1 day)
```bash
python scripts/run_phase2.py --mode real --assets BTC ETH --days 180
```

### 4. Execute Phase 3 with Real Ground Truth (8 hours)
```bash
python src/research/phase3_walkforward.py --mode real
```

### 5. Analyze Results
- If F1≥0.55 AND Accuracy≥0.50: Signal validated, proceed to research paper
- If not: Iterate on feature definitions, document limitations

---

## Governance Checklist

| Item | Status | Notes |
|------|--------|-------|
| Real data requirement | ✅ Met (Phase 1 OHLCV) | Features still mock, ground truth pending |
| No lookahead bias | ✅ Enforced | All data chronological, no future data |
| Zero auto-trading | ✅ Enforced | Framework decision-only, no execution |
| Layer 8 blocked | ✅ Blocked | Refinement not initiated |
| Layer 9 blocked | ✅ Blocked | No production deployment |
| PIT compliance | ✅ Met | Timestamps valid, source marked |
| Research-only | ✅ Maintained | No optimization on ground truth |

---

## Open Questions

1. **Feature Engineering**: Should Phase 1 features use real derivatives (Deribit) or remain synthetic?
   - Real: Higher fidelity, requires API access
   - Synthetic: Faster iteration, lower signal confidence

2. **Time Window**: Should Phase 1 use fixed 180-day window or rolling window?
   - Affects reproducibility and walk-forward structure

3. **Asset Scope**: Should Phase 1 expand beyond BTC/ETH to altcoins?
   - Requires expanded data collection
   - May have different cascade characteristics

---

## Key Dates

| Milestone | Date | Status |
|-----------|------|--------|
| Phase 1 OHLCV (Real) | 2026-09-25 | ✓ Complete |
| Phase 1 Features (Real) | TBD | ⏳ Blocked on derivatives APIs |
| Phase 2 Real Data | TBD | ⏳ Blocked on CryptoQuant + Glassnode keys |
| Phase 3 Validation | TBD | ⏳ Blocked on Phase 2 |
| Decision Gate | TBD | ⏳ Pending real validation |

---

## Conclusion

Path A is structurally complete (all three phases implemented) but **blocked on external API credentials**. OHLCV is real. Features remain synthetic pending derivatives/on-chain data access. Ground truth awaits CryptoQuant + Glassnode keys.

**When credentials acquired**: Can validate signal within 2-3 days.

**Current**: Framework ready, awaiting credentials. All governance requirements satisfied.

---

**Generated**: 2026-09-25  
**Status**: ⏳ BLOCKED AT PHASE 2  
**Next Action**: Acquire CryptoQuant + Glassnode API keys
