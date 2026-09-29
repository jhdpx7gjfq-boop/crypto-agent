# DATA-SRC-003C: Control Specification — GATE 3 Validation

**Classification:** CONTROL SPECIFICATION  
**Revision:** 3C (Final for Gate 3)  
**Effective Date:** 2026-09-29  
**Authority:** Data Infrastructure Governance  
**Scope:** Layer 1 Data Intelligence — Source Validation  

---

## Executive Summary

DATA-SRC-003C defines seven mandatory controls (C1.1–C1.7) for validating data source architecture before Gate 3 passage. Each control has:
- **Definition:** What must be true
- **Measurement:** How to verify
- **Threshold:** Acceptance criteria
- **Evidence Artifact:** What proves compliance
- **Gate Impact:** Blocks Gate 3 if FAIL/UNVERIFIED

**Gate 3 Blocking Rules:**
- **C1.4 FAIL** → Gate 3 BLOCKED (revision traceability mandatory)
- **C1.5 FAIL** → Gate 3 BLOCKED (PIT reconstruction mandatory)
- **C1.6 = NO-GO:** Daily-only data for H2 prohibited (≥15m required for BTC/ETH)
- **C1.x UNVERIFIED** → Not PASS (unverified ≠ pass)

---

## Control Definitions & Validation Procedures

### C1.1: Historical Availability

#### Definition
All required market data assets have continuous historical coverage without gaps exceeding acceptable limits.

#### Measurement
```
Availability % = (actual_trading_days / expected_trading_days) × 100
                where expected_trading_days = calendar_days - exchange_holidays
```

#### Thresholds

| Asset Class | Source | Period | Minimum Coverage | Gap Limit |
|-------------|--------|--------|------------------|-----------|
| BTC, ETH | CoinGecko daily | 2019-01-01 to now | ≥98% | Max 2 consecutive days |
| Major alts (SOL, AVAX, etc.) | CoinGecko daily | Inception to now | ≥97% | Max 3 consecutive days |
| Long-tail (Top 1000 coins) | CoinGecko daily | Listing date to now | ≥95% | Max 7 consecutive days |
| BTC, ETH intraday | Binance 15m | Last 90 days | ≥99% | Max 1 candle missed |
| Regime data (Funding, OI) | CryptoQuant | 2020 to now | ≥90% | Max 1 day |

#### Validation Query

```python
def validate_c1_1():
    """Verify historical availability meets thresholds."""
    for asset in ['BTC', 'ETH', ...]:
        manifest = load_manifest(f'snapshot_{YYYYMMDD}')
        expected_days = calculate_trading_days(
            asset,
            inception_date(asset),
            manifest.snapshot_date
        )
        actual_days = manifest.sources['coingecko'][asset]['rows_fetched']
        availability = (actual_days / expected_days) * 100
        
        assert availability >= THRESHOLDS[asset], \
            f"{asset} availability {availability}% < {THRESHOLDS[asset]}%"
        
        # Check max gap
        gaps = find_gaps(manifest, asset)
        assert all(gap <= MAX_GAP[asset] for gap in gaps), \
            f"{asset} gap {max(gaps)} exceeds {MAX_GAP[asset]}"
```

#### Evidence Artifact
- **Location:** `{snapshot_id}/manifest.json` → `sources[].checksums.row_count`
- **Format:** JSON manifest with row counts per source per asset
- **Timestamp:** Snapshot creation time (data_as_of)

#### Acceptance Criteria
```
Status: PASS if:
  - CoinGecko daily coverage ≥ thresholds for all required assets
  - No gap exceeds maximum days allowed
  - Manifest attestation signed (SHA256 checksum verified)
  
Status: FAIL if:
  - Any asset < minimum coverage threshold
  - Gap > maximum consecutive days
  - Manifest not found or corrupted
  
Status: UNVERIFIED if:
  - Snapshot not frozen
  - Manifest incomplete (missing row counts)
```

#### Gate 3 Impact
- PASS: C1.1 satisfied ✓
- FAIL/UNVERIFIED: C1.1 fails; requires snapshot remediation

---

### C1.2: Timestamp Precision & Stability

#### Definition
All timestamps are consistent in format, resolution, and timezone, enabling temporal reproducibility.

#### Measurement

**Format Check:**
- UNIX milliseconds (integer, UTC)
- ISO 8601 human-readable (YYYY-MM-DDTHH:MM:SS.sssZ)
- No mixed formats within snapshot

**Precision Check:**
```
Daily OHLCV:   Milliseconds (3 decimal places)
Intraday 15m:  Milliseconds (3 decimal places)
Event log:     Milliseconds (3 decimal places)
```

**Stability Check:**
- Identical snapshots → identical timestamps
- Idempotent API calls → same result
- No clock drift between fetch attempts

#### Validation Query

```python
def validate_c1_2():
    """Verify timestamp consistency across snapshots."""
    for snapshot_date in snapshots:
        manifest = load_manifest(snapshot_date)
        
        # Format check
        for source in manifest.sources:
            for record in load_parquet(source.file):
                ts = record['timestamp']
                assert isinstance(ts, int), f"Non-integer timestamp: {ts}"
                assert 0 < ts < 2**53, f"Out-of-range timestamp: {ts}"
                
                # Timezone check: all UTC
                dt = datetime.fromtimestamp(ts/1000, tz=UTC)
                assert dt.tzinfo == UTC, f"Non-UTC timezone: {dt.tzinfo}"
        
        # Stability check: compare with previous snapshot
        if prev_snapshot_exists:
            prev_manifest = load_manifest(prev_snapshot_date)
            overlap_data = get_overlap(manifest, prev_manifest)
            for record in overlap_data:
                curr_ts = record['curr_snapshot_ts']
                prev_ts = record['prev_snapshot_ts']
                assert curr_ts == prev_ts, \
                    f"Timestamp divergence: {curr_ts} vs {prev_ts}"
```

#### Evidence Artifact
- **Location:** `{snapshot_id}/manifest.json` → `sources[].file` parquet headers
- **Format:** Sample of 10 timestamp records + format description
- **Test:** Idempotent API call (fetch same asset twice, verify identical timestamps)

#### Acceptance Criteria
```
Status: PASS if:
  - All timestamps UNIX milliseconds (UTC)
  - All timestamps in valid range [1e12, 2e12)
  - Idempotent calls produce identical timestamps
  - No timezone drift detected
  
Status: FAIL if:
  - Mixed timestamp formats detected
  - Timezone ambiguity (local time assumed)
  - Clock drift > 1s between snapshots
  - Timestamps out of logical range
  
Status: UNVERIFIED if:
  - Timestamp sample not provided
  - No idempotency test results
```

#### Gate 3 Impact
- PASS: Reproducibility guaranteed ✓
- FAIL/UNVERIFIED: Cannot use data for walk-forward (temporal integrity uncertain)

---

### C1.3: Forecast + Actual Availability

#### Definition
Forward-looking data availability and lag are within SLA; no leakage of future information into historical datasets.

#### Measurement

**Data Collection Lag:**
```
Lag = fetch_timestamp - data_as_of_timestamp
  where:
    fetch_timestamp = when we actually retrieved data (UTC now)
    data_as_of_timestamp = date the data represents (market close UTC)
```

**SLA Thresholds:**
| Metric | SLA | Measurement |
|--------|-----|-------------|
| Daily OHLCV (CoinGecko) | ≤24h + 1h lag | Last candle available by 01:00 UTC next day |
| Intraday 15m (Binance) | ≤15m + 5m lag | Latest 15m candle available within 5m |
| Forecast data | None | No forward-looking prices in dataset |
| Revision window | ≤7 days | Retroactive corrections detected within 1 week |

#### Validation Query

```python
def validate_c1_3():
    """Verify data collection SLA and forecast leakage."""
    manifest = load_manifest(current_snapshot)
    
    # Check lag for daily data
    for source in manifest.sources:
        if source.candle_resolution == 'daily':
            data_as_of = manifest.data_as_of
            fetch_time = source.fetch_timestamp
            lag = (fetch_time - data_as_of).total_seconds() / 3600  # hours
            assert lag <= 25, f"Daily OHLCV lag {lag}h exceeds SLA"
        
        # Check lag for intraday
        elif source.candle_resolution == '15m':
            lag = (source.fetch_timestamp - manifest.data_as_of).total_seconds() / 60
            assert lag <= 20, f"Intraday lag {lag}m exceeds SLA"
    
    # Check for forecast leakage: no data beyond snapshot_date
    for source in manifest.sources:
        data = load_parquet(source.file)
        max_ts = data['timestamp'].max()
        snapshot_ts = manifest.snapshot_timestamp
        assert max_ts <= snapshot_ts, \
            f"Forecast leakage detected: data_max_ts {max_ts} > snapshot {snapshot_ts}"
    
    # Check revision window
    revisions = load_revision_log()
    for rev in revisions:
        days_since_detected = (now - rev.detected_at).days
        assert days_since_detected <= 7, \
            f"Revision {rev.id} undetected for {days_since_detected}d"
```

#### Evidence Artifact
- **Location:** `{snapshot_id}/manifest.json` → `sources[].fetch_timestamp` and `data_as_of`
- **Format:** JSON with lag calculation for each source
- **Revision Log:** `revisions/revision_audit.json` with detection dates

#### Acceptance Criteria
```
Status: PASS if:
  - Daily OHLCV lag ≤ 25 hours
  - Intraday 15m lag ≤ 20 minutes
  - No forecast data (max timestamp ≤ snapshot_timestamp)
  - All revisions detected within 7 days
  
Status: FAIL if:
  - Lag > SLA thresholds
  - Future data detected in snapshot
  - Revisions undetected > 7 days
  
Status: UNVERIFIED if:
  - Fetch timestamps not recorded
  - No revision log present
  - Lag SLA not defined for source
```

#### Gate 3 Impact
- PASS: Data availability predictable; no future leakage ✓
- FAIL/UNVERIFIED: Backtest validity uncertain (possible lookahead bias)

---

### C1.4: Revision Traceability

#### Definition
All retroactive corrections to historical data are logged, timestamped, and auditable. No silent data changes.

#### Measurement

**Revision Audit Requirements:**
- Every correction logged in immutable audit log
- Log entry: timestamp, source, asset, field, old value, new value, reason
- Retention: Permanent (never delete)
- Detection: Automated or manual, recorded within 7 days

**Audit Log Schema:**
```python
class RevisionAuditEntry:
    revision_id: str                        # "coingecko_BTC_rev_20260930_001"
    asset: str                              # "BTC"
    source: str                             # "coingecko"
    detected_at: datetime                   # When we noticed the change
    affected_dates: List[date]              # Which rows changed
    affected_snapshots: List[str]           # Which snapshots impacted
    changes: List[FieldChange]
        - date: date
        - field: str                        # "close", "high", "low", "volume"
        - old_value: float
        - new_value: float
        - change_pct: float
    reason: str                             # "exchange_adjustment", "delisting", etc.
    data_quality_impact: str                # "none", "low", "medium", "high"
    pit_sensitive: bool                     # Affects walk-forward tests?
    corrective_snapshot_id: str             # New immutable snapshot created
```

#### Validation Query

```python
def validate_c1_4():
    """Verify all retroactive corrections are logged."""
    # Load revision audit log
    revisions = load_revision_audit_log()
    assert len(revisions) > 0, "No revision log found"
    
    # For each revision, verify:
    for rev in revisions:
        # 1. Immutable record (cannot be edited)
        assert rev.is_read_only(), f"Revision {rev.id} is mutable!"
        
        # 2. Complete metadata
        assert rev.detected_at is not None
        assert len(rev.affected_dates) > 0
        assert len(rev.changes) > 0
        assert rev.reason is not None
        
        # 3. Timestamps valid
        assert rev.detected_at <= now, f"Future detection timestamp: {rev.detected_at}"
        assert all(d <= rev.detected_at for d in rev.affected_dates), \
            "Affected date > detection date"
        
        # 4. Impact assessment done
        assert rev.pit_sensitive in [True, False], "PIT sensitivity not specified"
        
        # 5. Corrective snapshot exists (if PIT-sensitive)
        if rev.pit_sensitive:
            assert snapshot_exists(rev.corrective_snapshot_id), \
                f"Corrective snapshot missing: {rev.corrective_snapshot_id}"
    
    # Check: no unlogged changes
    # (Compare current snapshot vs. previous source API, verify all changes logged)
```

#### Evidence Artifact
- **Location:** `revisions/revision_audit.json` (immutable)
- **Format:** JSON array of RevisionAuditEntry objects
- **Timestamp:** Detection dates within 7-day window
- **Signature:** Commit hash of revision log in git

#### Acceptance Criteria
```
Status: PASS if:
  - Revision audit log present and immutable
  - All retroactive changes logged with complete metadata
  - No undetected data divergences (sampling test)
  - Revisions detected within 7-day window
  
Status: FAIL if:
  - Revision log missing or editable
  - Unlogged changes detected
  - Revisions undetected > 7 days
  - Incomplete metadata on any revision
  
Status: UNVERIFIED if:
  - No revision audit log found
  - Detection procedure not documented
  - Sampling test not run
```

#### Gate 3 Impact
- **PASS:** All data changes traceable; walk-forward integrity valid ✓
- **FAIL/UNVERIFIED:** Gate 3 BLOCKED (mandatory control)
- **Rationale:** Cannot trust backtest results if data silently changes

---

### C1.5: Point-in-Time Reconstruction

#### Definition
Historical market data state can be reconstructed exactly as it existed on any past date. Enables walk-forward validation to use only data available at the time of decision.

#### Measurement

**PIT Snapshot Requirements:**
- Daily immutable snapshots (post-market, ~01:00 UTC)
- Hash-locked (SHA256 Merkle tree)
- Versioned (snapshot_YYYYMMDD_HHMMSS_checksum_8chars)
- Query API: `get_data_as_of(asset, data_date, snapshot_date)` returns frozen view

**PIT Query Test:**
```
For walk-forward window [2026-01-01 to 2026-03-31]:
  Test: Retrieve "market data as of 2026-04-01 00:00 UTC"
  Expected: Exact state of all OHLCV from 2019-01-01 to 2026-03-31
  Verify: Snapshot hash matches immutable registry
  Result: Historical data locked; cannot be changed retroactively
```

#### Validation Query

```python
def validate_c1_5():
    """Verify PIT reconstruction capability."""
    # 1. Snapshot infrastructure exists
    snapshots = load_snapshot_registry()
    assert len(snapshots) >= 30, "Insufficient snapshots (need ≥30 days)"
    
    # 2. Each snapshot is immutable
    for snap in snapshots:
        # Verify hash
        current_hash = compute_merkle_hash(snap.files)
        stored_hash = snap.manifest['immutable_hash']
        assert current_hash == stored_hash, \
            f"Snapshot {snap.id} hash mismatch! Data modified."
        
        # Verify read-only
        assert snap.is_read_only(), f"Snapshot {snap.id} is writable!"
        
        # Verify timestamp
        assert snap.manifest['frozen_at'] is not None
    
    # 3. Query API works correctly
    test_cases = [
        (BTC, '2026-01-15', '2026-01-20'),  # Query for historical date
        (ETH, '2026-02-28', '2026-03-05'),  # Query for different window
        (SOL, '2026-03-31', '2026-04-01'),  # Query at boundary
    ]
    
    for asset, data_date, snapshot_date in test_cases:
        # Get data using PIT query
        data_pit = query_data_as_of(asset, data_date, snapshot_date)
        
        # Verify: data goes back to inception
        assert data_pit.min_date <= data_date, \
            f"Data incomplete for {asset} at {data_date}"
        
        # Verify: no forward-looking data
        assert data_pit.max_date <= data_date, \
            f"Forward leakage in {asset} PIT query"
        
        # Verify: reproducible (same query → same hash)
        hash1 = sha256(data_pit.to_parquet())
        hash2 = sha256(query_data_as_of(asset, data_date, snapshot_date).to_parquet())
        assert hash1 == hash2, "PIT query not reproducible"
    
    # 4. Walk-forward test: prove data used was available
    for window_start, window_end in walk_forward_windows:
        pit_date = window_end + timedelta(days=1)
        pit_snapshot = find_snapshot_on_date(pit_date)
        
        # Retrieve data as it existed at PIT date
        data = query_data_as_of(window_end, pit_snapshot.id)
        
        # Run backtest on this frozen data
        results = backtest_on_frozen_data(data, window_start, window_end)
        
        # Record: "This result used snapshot_{pit_snapshot.id}"
        assert results.snapshot_id == pit_snapshot.id
```

#### Evidence Artifact
- **Location:** `data/snapshots/{snapshot_id}/manifest.json`
- **Format:** Immutable registry with snapshot IDs, timestamps, hashes, file checksums
- **Test Results:** `data/validation_pits/pit_reconstruction_test.json`
  - 5 random PIT queries with reproduce hashes
  - Walk-forward window validation
  - Snapshot immutability assertions

#### Acceptance Criteria
```
Status: PASS if:
  - ≥30 daily immutable snapshots exist and are hash-locked
  - Query API implemented and tested (5 queries reproduce identically)
  - Walk-forward windows tied to snapshot versions
  - No forward-leakage detected in PIT queries
  - Snapshots committed to git with immutable hash
  
Status: FAIL if:
  - Snapshots missing or mutable
  - PIT queries not reproducible (different hash)
  - Forward leakage detected (data beyond PIT date)
  - Query API not implemented
  - <30 snapshots available
  
Status: UNVERIFIED if:
  - PIT query test not run
  - Snapshot manifest incomplete
  - Walk-forward snapshot binding not documented
  - No immutability proof (hash verification)
```

#### Gate 3 Impact
- **PASS:** Walk-forward validation approved; experimental dataset authorized ✓
- **FAIL/UNVERIFIED:** Gate 3 BLOCKED (mandatory control)
- **Rationale:** Without PIT reconstruction, cannot prove no lookahead bias in backtest

---

### C1.6: BTC/ETH Intraday Alignment ≥15m

#### Definition
Bitcoin and Ethereum have intraday market data at ≥15-minute resolution, enabling detection of regime shifts (liquidations, euphoria, funding spikes).

#### Measurement

**Coverage Requirements:**
- BTC, ETH: ≥15m candles (Binance API, 99% completeness)
- Lookback: ≥90 days rolling window
- Alignment: BTC 15m close ≈ daily candle close (±1% tolerance)

**Validation:**
```
BTC_15m: [2026-09-29 00:15, 2026-09-29 00:30, ..., 2026-09-29 23:45]
BTC_daily: [2026-09-29]

Test: BTC_15m[-1] (23:45 close) ≈ BTC_daily (midnight-midnight close)
  Tolerance: ±1% price divergence acceptable
```

#### Validation Query

```python
def validate_c1_6():
    """Verify BTC/ETH have ≥15m intraday data."""
    # Load manifest
    manifest = load_manifest(current_snapshot)
    
    # Check: Binance 15m source present
    binance_15m = find_source(manifest, 'binance', '15m')
    assert binance_15m is not None, "Binance 15m source not found"
    
    for asset in ['BTC', 'ETH']:
        # Load 15m and daily data
        data_15m = load_parquet(binance_15m.file)
        data_daily = load_parquet(find_source(manifest, 'coingecko', 'daily').file)
        
        # Check coverage (99% minimum)
        expected_candles = 90 * 24 * 4  # 90 days × 24h × 4 candles/hour
        actual_candles = len(data_15m[data_15m['asset'] == asset])
        coverage = (actual_candles / expected_candles) * 100
        assert coverage >= 99, f"{asset} coverage {coverage}% < 99%"
        
        # Check alignment: daily close ≈ 15m last candle
        last_15m_close = data_15m.groupby('date')['close'].last()
        daily_close = data_daily[data_daily['asset'] == asset]['close']
        
        for date in daily_close.index:
            if date in last_15m_close.index:
                daily_val = daily_close[date]
                intraday_val = last_15m_close[date]
                divergence = abs((intraday_val - daily_val) / daily_val)
                assert divergence <= 0.01, \
                    f"{asset} {date} divergence {divergence*100}% > 1%"
```

#### Evidence Artifact
- **Location:** `{snapshot_id}/manifest.json` → `sources[binance_15m]`
- **Format:** Binance source with ≥90-day data for BTC and ETH
- **Test:** Alignment validation (daily close ≈ 15m last candle)

#### Evidence of **Limitation** (if daily-only):
```
Status: NO-GO (Data Constraint) if:
  - Only CoinGecko daily available (no intraday)
  - Binance 15m unavailable or incomplete
  - BTC/ETH 15m coverage < 90% (significant gap)
  
Rule: "H2 with daily OHLCV only is NO-GO"
  → If BTC/ETH have daily only → H2 risk detection DISABLED
  → Cannot use RRP for intraday euphoria detection
  → Document as limitation in Gate 3 report
```

#### Acceptance Criteria
```
Status: PASS if:
  - BTC, ETH have ≥15m Binance candles
  - Coverage ≥99% (≥90 days rolling)
  - Daily close aligns with 15m last candle (±1%)
  
Status: PASS with Limitation if:
  - Long-tail coins (non-BTC/ETH) daily-only (acceptable)
  - Document: "H2 intraday regime detection unavailable for long-tail"
  
Status: NO-GO if:
  - BTC or ETH daily-only (≥15m required)
  - Cannot proceed with Gate 3 (design constraint violation)
  
Status: UNVERIFIED if:
  - Intraday data source not found
  - Alignment test not run
  - Coverage < 90% (gap too large)
```

#### Gate 3 Impact
- **PASS:** Intraday regime detection enabled ✓
- **PASS + Limitation:** Long-tail daily-only, BTC/ETH has 15m ✓
- **NO-GO:** BTC/ETH daily-only → Gate 3 cannot proceed (design violation)
- **UNVERIFIED:** Cannot assess; requires data source confirmation

---

### C1.7: Event Inventory Coverage

#### Definition
Structured log of market events (listings, delistings, forks, airdrops) that affect data interpretation and result validity.

#### Measurement

**Event Types Required:**
| Event Type | Required For | Examples |
|------------|-------------|----------|
| Listing | All coins | IPO on Binance, Kraken, Coinbase |
| Delisting | Exit signals | Removed from exchange |
| Hard fork | Data continuity | Bitcoin → BTC/BCH fork Aug 2017 |
| Airdrop | Token supply | Uniswap airdrop Sep 2020 |
| Burn | Tokenomics | Ethereum EIP-1559 burn |
| Unlock | Price impact | Vesting cliff, token unlock |
| Rebrand | Ticker change | Antshares → NEO rename |
| Exchange support change | Market access | Coinbase listing/delisting |

**Schema:**
```python
class MarketEvent:
    event_id: str                   # "BTC_fork_20170801"
    asset: str                      # "BTC"
    event_type: str                 # "fork", "airdrop", etc.
    event_date: date
    description: str
    data_impact: str                # "none", "restart_ts", "duplicate_rows", etc.
    sources: List[str]              # ["glassnode", "coinbase", "twitter"]
    verified: bool
```

#### Validation Query

```python
def validate_c1_7():
    """Verify event inventory coverage."""
    events = load_event_inventory()
    assert len(events) > 0, "Event inventory empty"
    
    # Required: BTC/ETH major forks
    btc_fork = find_event('BTC', 'fork', date='2017-08-01')
    eth_fork = find_event('ETH', 'fork', date='2015-10-18')  # Homestead
    assert btc_fork is not None and btc_fork.verified
    assert eth_fork is not None and eth_fork.verified
    
    # Required: Major airdrops (UNI, AEVO, etc.)
    major_airdrops = find_events(event_type='airdrop', verified=True)
    assert len(major_airdrops) >= 5, f"<5 airdrops recorded (found {len(major_airdrops)})"
    
    # Required: Delisting tracking
    delistings = find_events(event_type='delisting')
    assert len(delistings) >= 10, "Insufficient delisting records"
    
    # Verification: spot-check sources
    for event in events:
        assert len(event.sources) > 0, f"Event {event.id} has no sources"
        assert event.verified in [True, False], f"Event {event.id} verification status unclear"
    
    # Coverage: events span data range
    event_dates = [e.event_date for e in events]
    assert min(event_dates) <= date(2019, 1, 1), "Events don't cover full data range"
```

#### Evidence Artifact
- **Location:** `data/market_events.csv` or `data/events/events.json`
- **Format:** CSV/JSON with event ID, type, date, description, sources, verified flag
- **Coverage:** ≥20 events minimum (focus on BTC/ETH/major alts)

#### Acceptance Criteria
```
Status: PASS if:
  - Event inventory CSV/JSON present with ≥20 entries
  - All major forks logged (BTC, ETH)
  - Major airdrops documented (≥5)
  - Delistings tracked (≥10)
  - Events verified (sources cited)
  
Status: PARTIAL if:
  - Event inventory present but incomplete
  - <10 events or missing major forks
  - Unverified sources
  
Status: UNVERIFIED if:
  - No event inventory found
  - Event format not standardized
  - No verification metadata
  
Status: LIMITATION (if documented) if:
  - Event inventory future-updated
  - Real-time delisting monitoring not available
```

#### Gate 3 Impact
- **PASS:** Interpretation of data changes clear; results less ambiguous ✓
- **PARTIAL:** Known events logged; gaps accepted with documentation
- **UNVERIFIED:** Cannot assess event-driven confounds
- **Blocking Rule:** If UNVERIFIED and unexplained event occurs → backtest invalidated retroactively

---

## Summary: Control Validation Matrix

| Control | Definition | Threshold | Evidence | Gate 3 Blocking? |
|---------|-----------|-----------|----------|-----------------|
| **C1.1** | Historical completeness | ≥98% daily, ≥99% intraday | Manifest row counts | Fails if <95% |
| **C1.2** | Timestamp consistency | UNIX ms, UTC, idempotent | Snapshot format test | Fails if mixed tz |
| **C1.3** | Data lag & forecast | ≤25h daily, ≤20m intraday, no future | Fetch timestamp log | Fails if future data |
| **C1.4** | Revision traceability | All changes logged, immutable | Revision audit log | **YES — BLOCKS** |
| **C1.5** | PIT reconstruction | Daily snapshots, hash-locked, query API | Snapshot registry + test | **YES — BLOCKS** |
| **C1.6** | Intraday ≥15m | BTC/ETH ≥15m, ≥99% cover | Binance 15m source | **NO-GO if daily-only** |
| **C1.7** | Event inventory | ≥20 major events, verified | CSV/JSON + sources | Advisory (not blocking) |

---

## Gate 3 Final Decision Rules

### ✅ GATE 3 PASS
```
Status: PASS if:
  ✓ C1.1 PASS (historical availability ≥ thresholds)
  ✓ C1.2 PASS (timestamps consistent, UTC, idempotent)
  ✓ C1.3 PASS (lag within SLA, no forecast leakage)
  ✓ C1.4 PASS (revision audit log complete and immutable)
  ✓ C1.5 PASS (PIT snapshots created, hash-locked, query API working)
  ✓ C1.6 PASS (BTC/ETH ≥15m, or daily-only with documented limitation)
  ✓ C1.7 PASS or PARTIAL (event inventory present, major events logged)
```

### ❌ GATE 3 BLOCKED
```
Status: BLOCKED if:
  ✗ C1.4 FAIL or UNVERIFIED (revision traceability not implemented)
  ✗ C1.5 FAIL or UNVERIFIED (PIT reconstruction not available)
  ✗ C1.6 NO-GO (BTC/ETH daily-only without ≥15m alternative)
```

### ⚠️ GATE 3 CONDITIONAL PASS
```
Status: PASS + LIMITATION if:
  ✓ C1.1-C1.7 mostly PASS
  ⚠️ C1.6 partial (long-tail daily-only; BTC/ETH has ≥15m)
    → Document: "Intraday regime detection unavailable for long-tail coins"
  ⚠️ C1.7 partial (event inventory incomplete)
    → Document: "Some events not yet cataloged; to be updated monthly"
```

---

## Implementation Timeline

**Week 1 (2026-09-29 to 2026-10-05):**
- [ ] Implement snapshot infrastructure (schema + manifest)
- [ ] Create daily fetch → snapshot pipeline
- [ ] Test C1.1, C1.2, C1.3

**Week 2 (2026-10-06 to 2026-10-12):**
- [ ] Implement revision audit log
- [ ] Validate C1.4 (test retroactive correction handling)
- [ ] Create event inventory CSV
- [ ] Test C1.7

**Week 3 (2026-10-13 to 2026-10-19):**
- [ ] Implement PIT query API
- [ ] Create 30-day snapshot backlog
- [ ] Run PIT reconstruction tests
- [ ] Validate C1.5 (pass or fail)

**Week 4 (2026-10-20 to 2026-10-26):**
- [ ] Integrate Binance 15m (if available)
- [ ] Validate C1.6 (intraday alignment)
- [ ] Generate Gate 3 validation report
- [ ] Sign off C1.1–C1.7 final status

---

## Appendix: Expected Results

### If All Controls PASS

```
GATE 3 VERIFICATION REPORT — FINAL

Status: ✅ PASS

C1.1 Historical Availability:     PASS (≥98% completeness)
C1.2 Timestamp Precision:         PASS (UNIX ms, UTC, idempotent)
C1.3 Data Lag & Forecast:         PASS (≤SLA, no future leakage)
C1.4 Revision Traceability:       PASS (audit log immutable)
C1.5 PIT Reconstruction:          PASS (snapshots locked, API verified)
C1.6 Intraday ≥15m:              PASS (Binance 15m for BTC/ETH)
C1.7 Event Inventory:             PASS (20+ verified events)

Data Architecture Status: VALIDATED ✅
Layer 1 Infrastructure: APPROVED ✅
Gate 3: PROCEED TO GATE 4 ✅
```

### If C1.4 or C1.5 FAIL

```
GATE 3 VERIFICATION REPORT — BLOCKED

Status: ❌ BLOCKED

C1.5 Point-in-Time Reconstruction: FAIL (PIT snapshots not implemented)

Blocking Issue: Without PIT reconstruction, cannot prove walk-forward 
               validation avoided lookahead bias. Data architecture 
               invalid for scientific validation.

Required Remediation:
  1. Implement daily immutable snapshot infrastructure
  2. Create hash-locked snapshot registry
  3. Implement get_data_as_of() query API
  4. Run 5-query PIT reproducibility test
  5. Re-submit for C1.5 re-verification

Gate 3: BLOCKED UNTIL C1.5 PASS
```

---

**Specification Version:** 3C (Final)  
**Effective Date:** 2026-09-29  
**Authority:** Data Infrastructure Governance  
**Review Date:** 2026-10-26 (post-implementation validation)
