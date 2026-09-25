# Path A: Liquidation Independent Alpha — Initial Status

**Date**: 2026-09-25  
**Phase**: Initialization (Week 1)  
**Status**: 🟢 PIPELINE READY — Awaiting Real Data

---

## Summary

Path A research is a governance-approved, independent alpha investigation into liquidation-based trading signals. It runs **parallel to**, not integrated with, Layers 1-7.

### Key Properties

- **Scope**: Research-only (no training/optimization)
- **Data**: Real-only (public APIs, no simulation)
- **Validation**: Walk-forward required (≥3 windows, ≥55% cascade accuracy)
- **Integration**: Only after validation (separate approval gate)
- **Timeline**: 6-8 weeks (data collection → validation → paper)

---

## Deliverables (Pipeline Created)

✅ **liquidation_pipeline.py** (690 lines)
- LiquidationDataCollector (4 data sources)
- LiquidationFeatureEngineer (5 pre-event, 3 post-event features)
- LiquidationValidationPipeline (walk-forward framework)
- LiquidationAlphaResearchFramework (orchestrator)

✅ **data_sources_config.py** (380 lines)
- DataSourceRegistry (11 data sources cataloged)
- DataCollectionPlan (3-phase phased approach)
- Availability tracking (API keys, rate limits, latency)

✅ **PATH_A_LIQUIDATION_ALPHA_SPEC.md** (470 lines)
- Research objective + hypothesis
- Feature definitions (frozen)
- Validation framework (no lookahead bias)
- Acceptance criteria (≥55% accuracy)

✅ **src/research/__init__.py**
- Module imports + governance note

---

## Current Status: Phase 1

### Ready Now ✅
```
binance_public      ✓ OHLCV (no key required)
coingecko_public    ✓ Price history (no key)
blockscout          ✓ On-chain transactions (no key)
deribit             ✓ Funding rates + options (public)
```

**Immediate Action**: Start Phase 1 data collection (BTC/ETH, 6 months)

### Blocked Until ⏳
```
cryptoquant         🔑 API key required (ground truth liquidations)
glassnode           🔑 API key required (exchange flows)
lunarcrush          🔑 API key required (optional)
```

**Next Step**: Request API credentials from data vendors

---

## Data Collection Checklist

### Phase 1 (Week 1 — READY)
- [ ] Download 6 months OHLCV from Binance (BTC/ETH)
- [ ] Collect Deribit funding rates + options skew
- [ ] Parse Blockscout whale transaction logs
- [ ] Compute feature vectors for all periods

### Phase 2 (Week 2-3 — BLOCKED)
- [ ] Obtain CryptoQuant API key
- [ ] Obtain Glassnode API key
- [ ] Collect liquidation event timelines
- [ ] Cross-validate sources (consistency check)

### Phase 3 (Week 4+ — OPTIONAL)
- [ ] Obtain LunarCrush API key
- [ ] Integrate sentiment correlation
- [ ] Finalize feature set

---

## Data Source Status

| Source | Type | Status | Latency | Access |
|--------|------|--------|---------|--------|
| **Binance** | OHLCV | ✅ Ready | Real-time | Public |
| **CoinGecko** | Prices | ✅ Ready | 1h | Public |
| **Blockscout** | On-chain | ✅ Ready | 1-5m | Public |
| **Deribit** | Derivatives | ✅ Ready | Real-time | Public |
| **CryptoQuant** | Liquidations | ⏳ Waiting | 1h | API Key |
| **Glassnode** | Flows | ⏳ Waiting | 1-2h | API Key |
| **LunarCrush** | Sentiment | 🟢 Optional | 1h | API Key |

---

## Feature Architecture

### Pre-Event Signals (1h lookback)
1. **Funding Pressure** (z-score of 8h funding rate)
2. **Derivative Stress** (funding + OI imbalance)
3. **Correlation Breakdown** (asset vs. BTC decoupling)
4. **Orderbook Fragility** (spread + depth collapse)
5. **Volatility Expansion** (recent vol / historical vol)

→ **Cascade Likelihood** (0-100)

### Post-Event Signals (24h window)
1. **Recovery Time** (minutes to 50% reversion)
2. **Mean Reversion %** (24h recovery strength)

→ **Recovery Window Quality** (0-100)

---

## Validation Framework

### Walk-Forward Structure
```
├── Train Window: 30 days (feature analysis, no model fitting)
├── Test Window: 5 days (evaluate cascade detection)
└── Repeat: 6+ rolling windows (no overlap, forward-only)
```

### Acceptance Gate
```
✅ PASS if ALL:
- Cascade detection accuracy ≥ 55%
- Mean reversion within 24h ≥ 50%
- False positive rate ≤ 25%
- Consistency across ≥3 windows
- No lookahead bias detected
```

---

## Next Actions (Priority Order)

### Immediate (This Week)
1. Load 6 months Binance OHLCV (BTC/ETH)
2. Execute Phase 1 data collection pipeline
3. Generate initial feature vectors
4. Run exploratory analysis

### Week 2-3
1. Request CryptoQuant + Glassnode API keys
2. Integrate Phase 2 liquidation ground truth
3. Cross-validate all data sources
4. Begin walk-forward splits

### Week 4+
1. Execute walk-forward validation
2. Measure cascade prediction accuracy
3. Generate statistical report
4. Write research paper (if validated)

---

## Success Criteria

| Metric | Threshold | Current |
|--------|-----------|---------|
| Liquidation events detected | ≥500 | Pending Phase 2 |
| Cascade accuracy | ≥55% | Pending validation |
| Recovery pattern detection | ≥50% of events | Pending validation |
| Walk-forward stability | F1 ≥0.5 | Pending validation |
| Lookahead bias | None detected | Pending audit |

---

## Governance Checkpoints

### ✅ Phase 1: Pipeline Initialization (TODAY)
- [x] Research framework created
- [x] Data sources cataloged
- [x] Feature definitions frozen
- [x] Validation plan documented
- [x] Governance constraints recorded

### ⏳ Phase 2: Data Collection (Week 1-3)
- [ ] Phase 1 data loaded (immediate)
- [ ] Phase 2 credentials acquired
- [ ] All sources integrated
- [ ] No data quality issues

### 🟡 Phase 3: Walk-Forward Validation (Week 4)
- [ ] ≥6 windows created
- [ ] Cascade accuracy ≥55%
- [ ] No lookahead bias
- [ ] Reproducible audit trail

### 🟡 Phase 4: Research Paper (Week 5-8)
- [ ] Findings documented
- [ ] Limitations disclosed
- [ ] Follow-up paths proposed
- [ ] Human review gate

### 🟡 Phase 5: Integration Decision (Post-Validation)
- [ ] If validated: Request Layer X spec approval
- [ ] If not validated: Archive Path A, return to authorized layers

---

## Constraints & Guardrails

### Mandatory
- **Real data only** (no simulated liquidations)
- **Walk-forward validation** (≥3 windows, forward-only)
- **No optimization** (feature engineering only)
- **No integration** (until validated + approved)
- **Transparent audit trail** (reproducible code + data)

### Forbidden
- No model training / parameter fitting
- No backtesting with lookahead
- No integration with Layers 1-7 (until validated)
- No production deployment (research only)
- No autonomous trading (never)

---

## Timeline

```
Week 1 (Sept 25-Oct 1):     Phase 1 data collection (public sources)
Week 2-3 (Oct 2-15):         Phase 2 integration (API keys)
Week 4 (Oct 16-22):          Walk-forward validation
Week 5-8 (Oct 23-Nov 19):    Research paper + findings
Post-validation:             Integration decision gate (human approval)
```

---

## Authority & Approval

**Specification Authority**: Governance Research Track  
**Approval Date**: 2026-09-25  
**Status**: 🟢 PIPELINE INITIALIZED

**Next Gate**: Phase 1 Data Collection Completion  
**Gate Criteria**: ≥100 liquidation events detected, features validated

---

## References

- `PATH_A_LIQUIDATION_ALPHA_SPEC.md` — Research specification (frozen)
- `src/research/liquidation_pipeline.py` — Data collection framework
- `src/research/data_sources_config.py` — Data source registry
- `CLAUDE.md` — Project governance + constraints
- `PROJECT_STATUS.md` — Layer authorization status

---

**Path A runs independently. Integration decisions made post-validation.**  
**Research-only: no training, no optimization, no integration until approved.**
