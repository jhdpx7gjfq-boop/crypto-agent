# ADR-035: Data Source Architecture & Immutability Contract

**Status:** ACCEPTED  
**Date:** 2026-09-29  
**Deciders:** Technical Authority + Data Governance  
**Affected Component:** Layer 1 Data Intelligence  

---

## 1. Context

### Problem Statement

IGWT-PF26 walk-forward validation requires proving that:
1. Historical data used in backtests was available at the time of decision (Point-in-Time)
2. Retroactive corrections (revisions) are traceable and auditable
3. Intraday market regime shifts are observable
4. Data provenance is immutable and reproducible

**Current State:** CoinGecko daily OHLCV API provides accessible price data but:
- Daily candles only (no intraday detection)
- Unknown revision policy (retroactive OHLC changes undocumented)
- No native timestamp versioning
- No immutable snapshot mechanism

### Gate 3 Requirement

C1.4 (Revision Traceability) and C1.5 (Point-in-Time Reconstruction) **MUST PASS** or Gate 3 is **BLOCKED**.

---

## 2. Decision: Dual-Layer Data Architecture

### 2.1 Core Data Layers

#### **Layer 1A: Primary Market Data (OHLCV)**

**Source:** CoinGecko Public API  
**Endpoint:** `/coins/{id}/market_chart`  
**Resolution:** Daily (UNIX timestamp UTC)  
**Coverage:** 3,500+ coins, 7 years history  
**API Tier:** Free (no authentication)  
**SLA:** Best-effort; no uptime guarantee  

**Contract:**
- Close price: Last execution price (UTC midnight)
- High/Low: Daily range (synthetic from order books, may vary ±0.5%)
- Volume: 24h trading volume (USDT)
- Timestamp: UNIX milliseconds (UTC)

**Limitations:**
- No intraday granularity (daily candles only)
- Revision policy undefined (retroactive corrections possible)
- No native versioning

**Mitigation:** Implement immutable snapshot layer (Layer 1B).

---

#### **Layer 1B: Intraday Regime Detection (Optional Secondary)**

**Sources (Priority Order):**
1. **Binance Public API** (`/api/v3/klines`)
   - Resolution: 15m, 1h, 4h
   - Coverage: ~500 major pairs (BTC, ETH, SOL, etc.)
   - Cost: Free
   - Latency: Real-time + 90-day lookback

2. **Kraken Public REST API** (`/0/public/Trades`)
   - Resolution: Real-time tick-level
   - Coverage: ~250 pairs
   - Cost: Free
   - Latency: 24-month lookback

3. **LunarCrush Data API** (if connector available)
   - Resolution: 4h, 1d aggregates
   - Coverage: 5,000+ coins
   - Cost: Requires API key
   - Latency: Real-time + 2-year lookback

**Decision:** Use Binance 15m/4h candles for BTC/ETH/major alts. Accept daily-only for long-tail coins.

**Rationale:** Enables intraday regime detection (C1.6 ≥15m alignment) while maintaining coverage.

---

### 2.2 Immutability & Snapshot Architecture

#### **Snapshot Store Design**

```
data/
├── snapshots/
│   ├── YYYYMMDD_HHMMSS/
│   │   ├── manifest.json         # Provenance record
│   │   ├── coingecko_BTC_raw.parquet
│   │   ├── coingecko_ETH_raw.parquet
│   │   ├── binance_BTC_15m.parquet
│   │   └── checksums.json        # SHA256 hashes
│   └── latest_snapshot -> YYYYMMDD_HHMMSS/
├── raw/
│   ├── coingecko/                # Primary daily data
│   └── binance/                  # Intraday regime data
└── processed/
    ├── features_layer1.parquet
    └── validation_pits/          # Frozen PIT snapshots
```

#### **Manifest Format (immutable)**

```json
{
  "snapshot_id": "20260929_153000",
  "snapshot_timestamp": "2026-09-29T15:30:00Z",
  "data_as_of": "2026-09-29T00:00:00Z",
  "sources": [
    {
      "source": "coingecko",
      "endpoint": "/coins/{id}/market_chart",
      "fetch_timestamp": "2026-09-29T15:30:00Z",
      "date_range": ["2019-01-01", "2026-09-29"],
      "coins": ["bitcoin", "ethereum", "..."],
      "candle_resolution": "daily",
      "rows_fetched": 45230,
      "checksums": {
        "file": "coingecko_raw.parquet",
        "sha256": "abc123def456...",
        "row_count": 45230
      }
    },
    {
      "source": "binance",
      "endpoint": "/api/v3/klines",
      "fetch_timestamp": "2026-09-29T15:30:00Z",
      "date_range": ["2024-09-29", "2026-09-29"],
      "symbols": ["BTCUSDT", "ETHUSDT"],
      "candle_resolution": "15m",
      "rows_fetched": 89760,
      "checksums": {
        "file": "binance_15m.parquet",
        "sha256": "xyz789abc123...",
        "row_count": 89760
      }
    }
  ],
  "immutable_hash": "sha256:root_merkle_hash",
  "frozen_at": "2026-09-29T15:30:00Z",
  "retention_policy": "permanent",
  "versioned": true
}
```

#### **Revision Audit Log**

Every data update creates a revision record:

```json
{
  "revision_id": "coingecko_BTC_rev_20260930",
  "asset": "BTC",
  "source": "coingecko",
  "revision_type": "retroactive_correction",
  "detected_at": "2026-09-30T08:00:00Z",
  "affected_dates": ["2026-09-28"],
  "changes": [
    {
      "date": "2026-09-28",
      "field": "close",
      "old_value": 65432.50,
      "new_value": 65445.25,
      "reason": "exchange_adjustment"
    }
  ],
  "data_quality_impact": "low",
  "pit_sensitivity": "requires_snapshot_refresh"
}
```

---

## 3. Control Specifications

### C1.1: Historical Availability

**Definition:** Data completeness for all required assets and lookback periods.

**Thresholds:**
- Daily OHLCV (CoinGecko): ≥98% trading days since coin inception (allow ≤2% gaps for delisted pairs)
- Intraday 15m (Binance): ≥99% candles for BTC/ETH, 90+ day rolling window
- Long-tail coins (CoinGecko daily): ≥95% coverage from listing date

**Measurement:** `(actual_rows / expected_rows) × 100`

**Acceptance:** All assets ≥ threshold

---

### C1.2: Timestamp Precision & Stability

**Definition:** Timestamp format, resolution, and consistency across snapshots.

**Requirements:**
- Format: UNIX milliseconds (UTC, ISO 8601 for human-readable)
- Precision: Millisecond (ms) for daily, nanosecond (ns) for intraday
- Timezone: All times stored as UTC; no local time assumptions
- Boundary Behavior: Daily candle timestamp = UTC midnight (00:00:00.000Z)
- Stability: Identical timestamp across identical snapshots (idempotent fetches)

**Validation:**
- Timestamps strictly increasing within asset
- No future dates
- Gaps match documented exchange holidays or maintenance windows

---

### C1.3: Forecast + Actual Availability

**Definition:** Data collection lag and forward-looking data availability.

**SLA:**
- Daily OHLCV: Available by 01:00 UTC next day (24h + 1h lag)
- Intraday 15m: Available by 15:05 UTC (5m lag, updated every 15m)
- Historical lookback: 90+ days guaranteed available without gaps

**Forecast Data:** None (no forward-looking prices). All data is historical spot prices.

**Revision Lag:** Retroactive corrections must be detected within 7 days (1 week window).

---

### C1.4: Revision Traceability

**Definition:** Audit trail for all retroactive data corrections.

**Requirements:**
- Every retroactive change logged in immutable revision log
- Change timestamp, field, old value, new value, reason
- Impact assessment: Does it affect Point-in-Time reconstruction?
- Retention: Permanent (never delete revision logs)

**Implementation:**
```python
class RevisionAudit:
    revision_id: str          # "source_asset_rev_YYYYMMDD"
    asset: str               # "BTC", "ETH"
    source: str              # "coingecko", "binance"
    detected_at: datetime    # When change detected
    affected_dates: List[date]
    changes: List[FieldChange]
    pit_sensitive: bool      # Affects walk-forward tests?
```

**Gate 3 Rule:** C1.4 FAIL → Gate 3 BLOCKED. All revisions must be documented.

---

### C1.5: Point-in-Time Reconstruction

**Definition:** Ability to recreate exact market data state at any historical date.

**Requirement:** For every walk-forward window, prove data used was available at decision point.

**Implementation:**
- Snapshot frequency: Daily (post-market, ~01:00 UTC)
- Immutable store: Parquet + SHA256 checksums
- Version tagging: `snapshot_{YYYYMMDD}_{HHMMSS}_{checksum_8chars}`
- Query API: `get_data_as_of(asset, query_date, snapshot_date)` returns locked view

**Validation:**
```
For WFV window [2026-01-01 to 2026-03-31]:
  Proof: "On 2026-04-01 00:00 UTC, we fetched data snapshot."
  Data state: {BTC: [OHLCV from 2019-01-01 to 2026-03-31]}
  Immutable: YES (hash-locked)
  → Walk-forward decision made with THIS data only
```

**Gate 3 Rule:** C1.5 FAIL → Gate 3 BLOCKED. PIT reconstruction is mandatory for experimental dataset.

---

### C1.6: BTC/ETH Intraday Alignment ≥15m

**Definition:** Ability to detect intraday market regimes (liquidations, funding spikes, euphoria).

**Requirement:** ≥15-minute candle resolution for BTC and ETH.

**Sources:**
- Primary: Binance 15m klines API
- Fallback: Kraken 4h (if Binance unavailable)
- Limitation: CoinGecko daily only (insufficient for intraday)

**Coverage:**
- BTC/ETH: ≥99% 15m candles (90-day rolling)
- Major alts (SOL, AVAX, etc.): 4h minimum
- Long-tail: Daily only (documented limitation)

**Gate 3 Rule:** "H2 with daily OHLCV only is NO-GO." BTC/ETH MUST have ≥15m.

---

### C1.7: Event Inventory Coverage

**Definition:** Structured log of market events affecting interpretation (chain splits, airdrops, delistings, rebrands).

**Required Events:**
- Exchange listings/delistings
- Coin burns, airdrops, unlocks
- Hard forks, chain migrations
- Name changes, ticker changes
- Major exchange support changes (e.g., Coinbase listing)

**Schema:**
```python
class MarketEvent:
    event_id: str                  # "BTC_fork_20170801"
    asset: str                     # "BTC"
    event_type: str                # "fork", "airdrop", "listing", etc.
    event_date: datetime
    description: str
    data_impact: str               # "none", "restart_ts", "duplicate_value", etc.
    sources: List[str]             # Where information came from
```

**Implementation:** Curated CSV + automated monitoring for delistings.

---

## 4. Implementation Roadmap

### Phase 1A: Snapshot Infrastructure (Week 1)
- [ ] Create snapshot schema + manifest format
- [ ] Implement daily snapshot fetch + hash verification
- [ ] Add revision audit log parser
- [ ] Version-tag snapshots in git (immutable, compressed)

### Phase 1B: Intraday Data Integration (Week 2)
- [ ] Add Binance 15m fetcher for BTC/ETH
- [ ] Validate against CoinGecko daily closes
- [ ] Document divergence policy (±1% acceptable)
- [ ] Store 90-day rolling window

### Phase 1C: Event Inventory (Week 2)
- [ ] Create market events CSV schema
- [ ] Populate BTC/ETH/SOL key events (2019-2026)
- [ ] Automate delisting detection (CoinGecko API monitoring)

### Phase 2: PIT Query API (Week 3)
- [ ] Implement `get_data_as_of(asset, query_date, snapshot_date)`
- [ ] Validate snapshot immutability (hash check)
- [ ] Add query logging for audit trail

### Phase 3: Gate 3 Verification (Week 4)
- [ ] Run C1.1–C1.7 controls against frozen snapshots
- [ ] Document any deviations or limitations
- [ ] Sign off on data architecture compliance

---

## 5. Governance Invariants

### Invariant 1: Immutability
- Once snapshot is frozen (timestamped), it cannot be modified
- Revisions create NEW snapshots, never alter existing ones
- All snapshots committed to git with immutable hash

### Invariant 2: Reproducibility
- All data fetches logged with timestamp + parameters
- Future re-runs should produce identical results (same source state)
- Cached datasets versioned; cache invalidation explicit

### Invariant 3: Traceability
- Every data point traceable to source, fetch timestamp, and snapshot version
- Revision audit log complete and permanent
- No anonymous or undocumented data changes

### Invariant 4: No Post-Hoc Modifications
- Once data enters immutable snapshot, no field-level edits
- Corrections require new snapshot + revision log
- Walk-forward windows locked to snapshot version used

---

## 6. Data Quality Acceptance Criteria

| Metric | Minimum | Evidence |
|--------|---------|----------|
| Daily OHLCV Completeness (CoinGecko) | ≥98% | Manifest row counts vs. expected |
| Intraday 15m Completeness (Binance BTC/ETH) | ≥99% | Binance klines API audit |
| Timestamp Precision | Milliseconds (daily), Nanoseconds (intraday) | Snapshot format verification |
| Revision Audit Coverage | 100% | All retroactive changes logged |
| PIT Reconstruction Proof | Pass test on 5 random snapshots | Query API validation |
| Event Inventory Currency | ≥95% coverage 2019-2026 | Spot check vs. historical sources |

---

## 7. Rationale

### Why Dual-Layer Architecture?

**CoinGecko daily OHLCV alone is insufficient** because:
1. Cannot detect intraday euphoria/liquidation cascades (C1.6 requirement)
2. Revision policy undocumented (C1.4 risk)
3. No native versioning (C1.5 gap)

**Binance intraday adds:**
1. True tick-level data for regime detection
2. Transparent revision policy (documented)
3. Native API versioning support

**Together:** BTC/ETH observable at ≥15m (intraday), daily fallback for long-tail.

### Why Immutable Snapshots?

Walk-forward validation requires **proof of data availability at decision point**. Without snapshots, we cannot prove:
- "On 2026-01-15, what data existed?" → Walk-forward invalid (lookahead bias risk)
- Retroactive OHLC correction → Invalidates backtest using old value

**Solution:** Hash-locked daily snapshots = temporal attestation.

---

## 8. Future Extensions

- [ ] Add on-chain metrics (Glassnode snapshots) for Layer 2 regime detection
- [ ] Implement automated PIT validation (monthly regression test)
- [ ] Add liquidity snapshots (order book depth, funding rates)
- [ ] Support multi-timeframe aggregation (1m → 5m → 15m)

---

**Decision:** ACCEPTED  
**Date:** 2026-09-29  
**Authority:** Data Governance Review  
**Next:** Implement ADR-035; proceed to DATA-SRC-003C controls.
