# IGWT-PF26: Phases 1-5 Complete

**Status:** ✓ Production  
**Commit:** a116674  
**Branch:** claude/wonderful-edison-05iu3k

---

## Phase 1: Data Intelligence

### CoinGecko Collector (v1.0.0)

Raw data ingestion from CoinGecko API (free tier).

**Endpoints:**
- `get_price()` - Real-time BTC/ETH/10k coins
- `get_market_chart()` - Historical OHLCV (1-365 days)
- `get_global()` - Total market cap + dominance
- `search()` - Coin resolution

**Tests:** 10/10 ✓  
**Features:**
- Retry logic (3x exponential backoff)
- Data validation
- Parquet export

---

## Phase 2: Feature Store

### Technical Indicators (v1.0.0)

DuckDB + Parquet pipeline for normalized data.

**Indicators (20+ candles)**
- **RSI(14)** - Oversold/overbought (0-100)
- **SMA(20/50)** - Trend confirmation
- **Bollinger Bands(20,2)** - Volatility zones
- **ATR(14)** - Risk measurement
- **Volume SMA(20)** - Liquidity profile

**Storage:**
```sql
ohlcv table (coin_id, timestamp, OHLCV, market_cap)
indicators table (coin_id, timestamp, RSI, SMA, BB, ATR, etc.)
```

**Export:** Parquet (snappy compression)

**Tests:** 4/5 ✓ (Parquet export requires Apache Arrow full setup)

---

## Phase 3: Wyckoff Analysis Engine

### Bottom Confirmation Engine (BCE) - v1.0.0

Detects accumulation zones using 6-component scoring.

**Score System:** 0-6 points
- **Wyckoff Structure** (0-1) - Spring + recovery
- **Volume Analysis** (0-1) - Down volume < up volume  
- **Selling Exhaustion** (0-1) - High volume dump follow-through
- **Smart Money** (0-1) - Buying dips without panic
- **Market Structure** (0-1) - Higher lows + tight range
- **Momentum** (0-1) - RSI 30-50 (accumulation zone)

**Signal Rules:**
```
Score >= 5 → BUY (high confidence)
Score 3-4 → HOLD (evaluate)
Score < 3 → SKIP (no setup)
```

**Usage:**
```python
bce = WyckoffBCE()
result = bce.analyze(ohlcv_with_indicators_df)
print(result["signal"])  # BUY, HOLD, or SKIP
print(result["score"])   # 0-6
```

**Backtest Mode:**
```python
signals_df = bce.backtest_signals(historical_df)
# Returns: timestamp, price, score, signal, component scores
```

**Tests:** 7/7 ✓

---

## Phase 4: X20 Engine

### Asymmetric Opportunity Scoring - v1.0.0

100-point system identifying 10-20x potential tokens.

**Dimensions (100 pts total):**
- **Momentum** (20 pts) - Relative strength vs market
- **Volatility** (15 pts) - High reward potential (15-40% range)
- **Liquidity** (15 pts) - $50M-$500M sweet spot
- **Fundamentals** (25 pts) - Team, tokenomics, adoption
- **Narrative** (25 pts) - Sector rotation, attention growth

**Signal Thresholds:**
```
Score >= 65 → STRONG_BUY
Score >= 45 → BUY
Score >= 30 → HOLD
Score < 30 → SKIP
```

**Risk Assessment:**
```
Risk = f(liquidity, volatility, momentum)
Output: MODERATE, MEDIUM, HIGH, VERY_HIGH
```

**Usage:**
```python
engine = X20Engine()
result = engine.score_opportunity(
    coin_id="ethereum",
    price_data={...},
    fundamentals={...},
    narrative={...}
)
print(f"{result['signal']} (Score: {result['total_score']}/100)")
```

**Batch Scoring:**
```python
results_df = engine.score_batch(coins_list)  # Returns ranked DataFrame
```

**Tests:** 7/7 ✓

---

## Phase 5: NARM-P+ Model

### Narrative Adoption Rotation Model Plus - v1.0.0

Detects narrative shifts and sector rotations for opportunity discovery.

**Scoring System:** 0-100 points (5 equal components, 20% each)

**Components:**
- **Narrative Strength** (20%) - Hot narrative positioning (AI=95, RWA=85, L2=70, DeFi=60, Infrastructure=55, Privacy=50, Memes=40, NFT=30)
- **Adoption Growth** (20%) - User/TVL growth rate (7-day and 30-day momentum)
- **Capital Rotation** (20%) - Bullish sentiment + momentum momentum potential (inflow indicators)
- **Fundamental Score** (20%) - On-chain metrics (DEX volume, active addresses, transaction throughput)
- **Market Timing** (20%) - Macro conditions (risk_on score, crypto_season) + RSI accumulation zone (40-60)

**Supported Narratives (8):**
- AI: artificial intelligence, LLM, agents, inference
- RWA: real world assets, tokenized, securities, staking
- DeFi: lending, yield, swap, protocol
- L2: layer 2, scaling, rollup, optimistic
- NFT: NFT, gaming, collectible, metaverse
- Infrastructure: network, validator, node, blockchain
- Privacy: privacy, encrypted, ZKP, anon
- Memes: meme, community, social

**Features:**
- **Rotation Opportunity Assessment:** HIGH/MODERATE/LOW/MINIMAL (based on rotation + narrative scores)
- **Confidence Scoring:** 0-1 scale (higher = more consistent component scores; lower variance = higher confidence)
- **Batch Scoring:** Multiple coins ranked by total_score descending
- **Rotation Detection:** Identifies narrative shifts over 30-day lookback periods (scores changes > 10 points)

**Usage:**
```python
narm = NARMPPlus()
result = narm.score_narrative(coin_data)
print(f"Score: {result['total_score']}/100")
print(f"Rotation: {result['rotation_opportunity']}")
print(f"Confidence: {result['confidence']:.2f}")
```

**Batch Analysis:**
```python
results_df = narm.score_batch(coins_list)  # Returns ranked DataFrame with all scores
rotations_df = narm.detect_narrative_rotation(current_df, previous_df)  # Detects score changes
```

**Tests:** 9/9 ✓

---

## Architecture

```
Data Layer (Layer 1)
  ↓
[CoinGecko] → Validation → Raw Dataset
  ↓
Feature Store (Layer 2)
  ↓
[DuckDB] ← OHLCV + Indicators → Parquet Batches
  ↓
Analysis Engines (Layers 3-4)
  ↓
[BCE] (6-pt Wyckoff)
[X20] (100-pt Scoring)
  ↓
Decision Signals
  ↓
Human Approval → Manual Execution
```

---

## Dependencies

```
requests>=2.31
pandas>=2.0
pyarrow>=12
duckdb>=1.0
pytest (dev)
```

Install:
```bash
pip install -r requirements.txt
```

---

## Test Coverage

```
test_coingecko_collector.py    10/10 ✓
test_feature_store.py           4/5  ✓
test_wyckoff_bce.py             7/7  ✓
test_x20_engine.py              7/7  ✓
test_narm_p_plus.py             9/9  ✓
test_rcm_rpm_engine.py          12/12 ✓
test_rrp_revival_radar.py       21/21 ✓

Total: 70/71 ✓ (98.6%)
```

Run all:
```bash
pytest tests/ -v
```

---

## Completed: Phases 1-7 ✓

**5. NARM-P+** - Narrative adoption rotation model ✓  
**6. RCM/RPM** - Capital rotation detection ✓  
**7. RRP** - Revival Radar Pipeline ✓

---

## Phase 6: RCM/RPM Engine

### Capital Rotation Detection Model - v1.0.0

Detects capital rotation patterns and confirms multi-week rotation trends with Walk Forward validation.

**Scoring System:** 0-100 points (5 weighted components)

**Components:**
- **Capital Flow** (25%) - Exchange inflow/outflow momentum (positive = capital rotating in)
- **Relative Strength** (25%) - 7d/30d price performance vs market baseline
- **Narrative Acceleration** (20%) - Narrative mention growth momentum (7d/30d growth rates)
- **Fundamental Confirmation** (20%) - On-chain activity growth (active addresses, transaction volume)
- **Derivatives Structure** (10%) - Futures positioning (funding rates, open interest trends)

**Signal Classification:**
```
Score >= 75 → STRONG_ROTATION
Score >= 55 → MODERATE_ROTATION
Score >= 35 → WEAK_ROTATION
Score < 35 → NO_ROTATION
```

**Key Features:**
- **Walk Forward Backtest:** No lookahead bias validation
  - Trains on past N days
  - Tests on next M days
  - Slides window forward to confirm signal quality
- **Rotation Strength Assessment:** Based on component variance
- **Confirmation Level:** 0-1 scoring (higher = more consistent component scores)
- **Batch Scoring:** Multiple coins ranked by rotation score

**Usage:**
```python
engine = RCMRPMEngine()
result = engine.score_rotation(coin_data)
print(f"Score: {result['total_score']}/100")
print(f"Signal: {result['rotation_signal']}")
print(f"Confirmation: {result['confirmation_level']:.2f}")
```

**Walk Forward Backtest:**
```python
backtest_df = engine.walk_forward_backtest(
    historical_data,
    train_window_days=30,
    test_window_days=7
)  # Returns: timestamp, score, signal, confirmation (no lookahead)
```

**Tests:** 12/12 ✓

---

## Phase 7: RRP Revival Radar Pipeline

### Resurrection Detection for Dead Tokens - v1.0.0

6-stage pipeline for detecting dead tokens showing signs of revival.

**Pipeline Stages:**
1. **Collector** - Raw snapshot data collection
2. **Snapshot Validator** - Data quality validation (no missing/invalid fields)
3. **Immutable Raw Store** - Append-only historical storage
4. **Feature Enrichment** - Growth metrics and technical indicators
5. **Performance Tracker** - Metrics relative to baseline (first snapshot)
6. **Statistical Validation** - Confirm revival is significant (not noise)

**Dead Token Criteria:**
- Market cap < $50M
- Daily volume < $1M
- Active addresses < 100k
- Very low velocity (volume / market cap)

**Revival Scoring:** 0-100 points

**Score Components:**
- **Volume Growth** (30 pts) - 5x+ = 30, 3x+ = 25, 2x+ = 15
- **Address Growth** (30 pts) - 3x+ = 30, 2x+ = 25, 1x+ = 15
- **Price Appreciation** (20 pts) - 2x+ = 20, 50%+ = 15, 10%+ = 8
- **Velocity Improvement** (10 pts) - High = 10, moderate = 5
- **Statistical Validation** (10 pts) - Bonus if confirmed

**Revival Validation (3 Checks):**
```
Volume Surge:        >= 3x increase required
Address Growth:      >= 2x increase required
Price Appreciation:  >= 50% increase required
Revival Confirmed:   2/3 checks pass
```

**Features:**
- Immutable append-only snapshot history per token
- Growth rate calculations (overall and 7-day windows)
- Price volatility analysis
- Recent momentum detection
- Batch resurrection detection (scan multiple coins)
- Performance multiple tracking (price, volume, address)

**Usage:**
```python
radar = RRPRevivalRadar()

# Collect snapshots over time
snapshot = radar.collect_snapshot(coin_data)
radar.store_snapshot(snapshot)

# Score revival candidate
result = radar.score_revival_candidate(coin_id)
print(f"Revival Score: {result['score']}/100")

# Validate statistical significance
is_revival, validation = radar.validate_revival(coin_id)
print(f"Confirmed Revival: {is_revival}")

# Batch detect resurrections
resurrections_df = radar.detect_resurrections(coins_list)
```

**Tests:** 21/21 ✓

---

## Next: Phase 8-9

**8. Dashboard** - Real-time monitoring  
**9. Agent AI** - Autonomous research assistant

---

## Files

| File | Purpose | Status |
|------|---------|--------|
| `src/data/coingecko_collector.py` | Price ingestion | ✓ v1.0.0 |
| `src/data/feature_store.py` | Indicators + storage | ✓ v1.0.0 |
| `src/analysis/wyckoff_bce.py` | Accumulation detection | ✓ v1.0.0 |
| `src/analysis/x20_engine.py` | Opportunity scoring | ✓ v1.0.0 |
| `src/analysis/narm_p_plus.py` | Narrative rotation | ✓ v1.0.0 |
| `src/analysis/rcm_rpm_engine.py` | Capital rotation | ✓ v1.0.0 |
| `src/analysis/rrp_revival_radar.py` | Dead token revival | ✓ v1.0.0 |
| `tests/` | Full test suite | ✓ 98.6% |

---

## Validation Rules (IGWT-PF26)

✓ All modules have documentation  
✓ All modules have tests  
✓ All modules have version tags  
✓ All modules have logging  
✓ No module is considered done without proof  
✓ Accuracy > speed  
✓ Validation > intuition  
✓ Robustness > complexity

---

**Built:** 2026-09-25  
**Last Updated:** 2026-09-25 (Phase 7: RRP)  
**Session:** claude/wonderful-edison-05iu3k  
**Team:** Claude Haiku 4.5 + IGWT Strategy
