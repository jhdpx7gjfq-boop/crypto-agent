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

## 5. Control Separation & Integrity Model (AMENDMENT: 2026-09-29)

### 5.1 Source-Level Controls

#### C1.4-SOURCE: Upstream Revision Exposure

**Definition:** Source exposes sufficient version/vintage history to prove what changes were made to historical data and when.

**Implementation-Agnostic Criteria:**
- Source provides API, audit log, or documentation showing retroactive corrections
- Changes timestamped (when correction detected/applied)
- Old and new values traceable
- Reason for correction documented or inferrable

**Status:** ⚠️ UNVERIFIED
- CoinGecko: No revision API; revision policy undocumented → FAIL
- Binance: Transparent kline fetch; retroactive corrections rare → PARTIAL
- TradingView: OAuth not accessible in this session → UNVERIFIED

---

#### C1.5-SOURCE: Upstream Point-in-Time API

**Definition:** Source exposes an API or mechanism allowing queries to deterministically reconstruct the data state at a specific historical timestamp or version reference.

**Implementation-Agnostic Criteria:**
- A query specifying the same historical timestamp/version deterministically reconstructs the same data state
- Results are idempotent (same query parameters = same data)
- Available for lookback period (≥90 days minimum)

**Status:** ⚠️ UNVERIFIED
- CoinGecko: `get-coin-history(date=YYYY-MM-DD)` does NOT support `as_of_timestamp` or vintage selection → FAIL
- Binance: No versioned snapshots endpoint → FAIL
- TradingView: OAuth required; not tested → UNVERIFIED

---

### 5.2 IGWT-Level Controls

#### C1.4-IGWT: Capture-Layer Revision Audit

**Definition:** IGWT responsibility to detect and log changes between consecutive daily snapshots, proving that capture layer has audited provider data changes.

**Key Constraint:** Does NOT prove native provider revision history. Proves capture integrity only.

**Implementation:**
- Daily snapshot fetch with full OHLCV history (e.g., BTC: 2019-01-01 to today)
- Diff detection: Compare current snapshot with previous snapshot
- Revision log entry for each detected change (date, field, old value, new value)
- Permanent retention of revision audit log

**Status:** ✅ AUTHORIZED
- Scope: C1.4-IGWT infrastructure build as implementation Step 3
- Non-PIT work; no lookahead-bias implications

**Example:**
```
Snapshot 2026-09-29 vs. 2026-09-28:
  BTC 2026-09-27:
    close: 64500 → 64512 (provider corrected)
    → Revision log entry: "coingecko_BTC_20260928_corrected_20260929"
```

---

#### C1.5-IGWT: Capture-Layer Point-in-Time Freezing

**Definition:** IGWT responsibility to freeze daily snapshots with cryptographic hash verification, enabling deterministic reconstruction of captured data.

**Key Constraint:** Does NOT prove provider PIT availability. Proves reproducibility of captured snapshots only.

**Implementation:**
- Daily snapshot fetch stored in tamper-evident, hash-verified snapshot store with versioned manifests
- Manifest includes: snapshot_id, snapshot_timestamp, data_as_of, sources metadata, immutable hash
- Hash verification on reconstruction: Verify snapshot integrity before use
- Query API: `get_data_as_of(asset, query_date, snapshot_date)` returns frozen view

**Status:** ✅ AUTHORIZED
- Scope: C1.5-IGWT infrastructure build as implementation Step 4
- Non-PIT work; proves reproducibility only

**Example:**
```
Manifest for snapshot 20260929_150000:
  immutable_hash: sha256:abc123def456...
  BTC_2026_03_31_close: 68420.50
  Reconstructed on 2026-10-15: Same hash, same data
  → Proof: We captured this state deterministically
```

---

### 5.3 Validation-Level Control: C1.5-PIT

#### C1.5-PIT: Hard Gate for Walk-Forward Validation

**Definition:** Independent proof that data used in walk-forward window was available at the upstream provider at the decision timestamp.

**Acceptance Criteria (Dual-Path):**

**Option A: Source-Native PIT API**
- Source exposes native versioned query API (C1.5-SOURCE)
- Query with `as_of_date` or equivalent returns deterministic historical state
- No local transformation required

**Option B: Independently Verifiable Signed Attestation**
- Provider publishes signed statement of historical availability
- Third-party verification service (e.g., blockchain timestamp, notary)
- Covers decision window lookback period

**Key Constraint:** Local snapshots (C1.5-IGWT) do NOT satisfy C1.5-PIT.
- C1.5-IGWT proves: "We captured this data on date X"
- C1.5-PIT requires: "Provider had this data available on date X"
- These are independent gates.

**Status:** 🔴 BLOCKED
- No tested source meets Option A criteria
- No Option B attestation discovered
- Gate 3 progression BLOCKED until C1.5-PIT verified

---

### 5.4 Gate 3 Implications

#### Mandatory Unblocking Decisions

**Decision 1:** Approve ADR-035 §5 amendment (governance clarification)?
- ✅ APPROVED (2026-09-29)

**Decision 2:** Authorize Capture Layer (C1.4-IGWT + C1.5-IGWT) implementation?
- ✅ AUTHORIZED (2026-09-29)

**Decision 3: Unblock Gate 3 (requires C1.5-PIT verification)**
- Status: PENDING
- Requirement: Discover source exposing C1.5-SOURCE or obtain Option B attestation
- Timeline: Before WFV/PIT-dependent work (Phase 3+)

---

### 5.5 Governance Rule: Control Separation & Integrity Invariant

**CRITICAL INVARIANT:** Every artifact produced by Layer 1 must carry explicit provenance state:

```
PIT_STATUS = UNVERIFIED
```

**Rationale:** Prevents accidental conflation of C1.5-IGWT (capture reproducibility) with C1.5-PIT (upstream availability) in future research or LLM analysis.

**Enforcement:**
- Snapshots: `PIT_STATUS = UNVERIFIED` in manifest
- Feature store: `PIT_STATUS = UNVERIFIED` in column metadata
- Backtest results: `PIT_STATUS = UNVERIFIED` in validation report
- Any research using Layer 1 data: Explicit disclaimer before PIT gate confirmed

**Consequence:** Any Layer 3+ work (BCE, X20, RPM, WFV) referencing Layer 1 data must fail fast if `PIT_STATUS ≠ VERIFIED`.

---

## 6. Governance Invariants

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

## 7. Data Quality Acceptance Criteria

| Metric | Minimum | Evidence |
|--------|---------|----------|
| Daily OHLCV Completeness (CoinGecko) | ≥98% | Manifest row counts vs. expected |
| Intraday 15m Completeness (Binance BTC/ETH) | ≥99% | Binance klines API audit |
| Timestamp Precision | Milliseconds (daily), Nanoseconds (intraday) | Snapshot format verification |
| Revision Audit Coverage | 100% | All retroactive changes logged |
| PIT Reconstruction Proof | Pass test on 5 random snapshots | Query API validation |
| Event Inventory Currency | ≥95% coverage 2019-2026 | Spot check vs. historical sources |

---

## 8. Rationale

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

## 9. Future Extensions

- [ ] Add on-chain metrics (Glassnode snapshots) for Layer 2 regime detection
- [ ] Implement automated PIT validation (monthly regression test)
- [ ] Add liquidity snapshots (order book depth, funding rates)
- [ ] Support multi-timeframe aggregation (1m → 5m → 15m)

---

**Decision:** ACCEPTED  
**Date:** 2026-09-29  
**Authority:** Data Governance Review  
**Amendment:** §5 Control Separation approved 2026-09-29  
**Status:** Canonical branch incorporation (2026-09-29)
