# Checkpoint 4: Reference Dataset Collection (Research Framework)

**Status**: RESEARCH_READY  
**Gate**: C4 — Reference Dataset Validation  
**Blocked Until**: C3 PASS + API key  
**Framework Created**: 2026-10-06  

---

## Objective

Build immutable, audited reference dataset of CoinDesk volume metrics for 12 months across 3 assets (BTC, ETH, SOL).

```
Input:  C3 findings (revision patterns, PIT semantics)
        ↓
Process: Fetch 365 days × 3 assets × 3 volume types
        ↓
Output: data/coindesk/
        ├── btc_volume_metrics_2025_2026.parquet
        ├── eth_volume_metrics_2025_2026.parquet
        └── sol_volume_metrics_2025_2026.parquet
```

---

## Dataset Specification

### Scope
| Property | Value |
|----------|-------|
| **Assets** | BTC, ETH, SOL |
| **Duration** | 365 days (12 months) |
| **Volume Types** | aggregate, top_tier, direct |
| **Format** | Parquet (columnar, compressed) |
| **Location** | `data/coindesk/` |
| **Naming** | `{asset_lower}_volume_metrics_2025_2026.parquet` |

### Schema (per Parquet file)

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | datetime | UTC date (daily) |
| `volume_aggregate` | float64 | Total venue aggregate |
| `volume_top_tier` | float64 | Top-tier venues only |
| `volume_direct` | float64 | Direct (non-aggregated) |
| `ttcr` | float64 | Top-tier ratio (top_tier / aggregate) |
| `data_source` | string | "coindesk_data_api" |
| `fetch_date` | date | When this snapshot was collected |
| `api_version` | string | CoinDesk API version |

### Storage Estimate

```
Per asset (365 rows):
  - 8 columns × 365 rows × 8 bytes/value ≈ 23 KB (uncompressed)
  - Parquet compression ≈ 3-5 KB per asset
  - Metadata overhead ≈ 5 KB per file

Total: 3 assets × 10 KB ≈ 30 KB (compressed)
```

---

## Collection Workflow

### Phase 1: Fetch Volume Data

**For each asset (BTC, ETH, SOL)**:

```python
# Fetch 365 days of volume metrics
data = fetch_volume_metrics(
    asset="bitcoin",
    start_date="2025-10-06",
    end_date="2026-10-05",
    interval="daily",
    volume_types=["aggregate", "top_tier", "direct"]
)
# Returns 365 rows × 3 columns
```

**Constraints**:
- All fetches must use SAME API key (for audit trail)
- Fetch all 3 assets on SAME day (ensures PIT consistency)
- Record fetch timestamp for each snapshot
- Tag with C3 audit version (which PIT revision snapshot?)

### Phase 2: Data Validation

**Completeness Check**:
- Expected: 365 rows (one per day)
- Threshold: ≥95% (347+ rows)
- Fail if: <95% completeness

**Integrity Check**:
```python
assert df.shape[0] >= 365 * 0.95  # Completeness
assert df['timestamp'].is_monotonic_increasing  # Ordered
assert df['timestamp'].nunique() == len(df)  # No duplicates
assert df[['volume_aggregate', 'volume_top_tier', 'volume_direct']].notna().all()  # No nulls
assert (df['volume_aggregate'] > 0).all()  # Valid ranges
```

**Gap Detection**:
```python
# Detect missing dates
expected_dates = pd.date_range(start_date, end_date, freq='D')
actual_dates = set(df['timestamp'].dt.date)
gaps = expected_dates[~expected_dates.isin(actual_dates)]
assert len(gaps) == 0  # Zero gaps
```

### Phase 3: Storage

**Parquet Format**:
- Compression: snappy (fast, small)
- Index: timestamp (enables fast range queries)
- Partitioning: None (single file per asset)

```python
df.to_parquet(
    "data/coindesk/btc_volume_metrics_2025_2026.parquet",
    compression="snappy",
    index=False,
    engine="pyarrow"
)
```

**Metadata File** (JSON):
```json
{
  "checkpoint": "C4_REFERENCE_DATASET",
  "asset": "BTC",
  "collection_date": "2026-10-06T00:00:00Z",
  "date_range": {
    "start": "2025-10-06",
    "end": "2026-10-05"
  },
  "records": 365,
  "completeness": 1.0,
  "quality_passed": true,
  "c3_audit_version": "c3_snapshot_20261006",
  "api_version": "v1",
  "auth_key_hash": "sha256_hash_of_api_key"
}
```

### Phase 4: Audit Trail

**Versioning**:
- Keep all parquet snapshots (immutable)
- Tag each with collection date
- Example: `btc_volume_metrics_2025_2026_v20261006.parquet`

**Metadata Registry** (`data/coindesk/metadata/`):
- `btc_registry.json` — All BTC snapshots with timestamps
- `eth_registry.json` — All ETH snapshots
- `sol_registry.json` — All SOL snapshots

---

## Quality Gates (C4 PASS Criteria)

| Gate | Threshold | Check |
|------|-----------|-------|
| **Completeness** | ≥95% | Data points ≥ 347/365 |
| **No Gaps** | 100% | All dates present (daily freq) |
| **No Duplicates** | 100% | One row per date |
| **No Nulls** | 100% | All volume columns filled |
| **Monotonic** | 100% | Timestamps strictly increasing |
| **Value Range** | Valid | Volumes > 0 |
| **PIT Consistency** | ✓ | References C3 snapshot |

**Verdict Logic**:
- ✅ **PASS**: All gates met
- ⚠️ **WARNING**: 1-2 gates at edge (≥90% but <95%)
- ❌ **FAIL**: Any gate < threshold

---

## Use Cases (Post-C4)

### C5: Cross-Venue Validation
```python
# Compare CoinDesk aggregate vs Binance spot
coindesk_vol = load_dataset("btc")
binance_vol = load_binance_volume("btc")

# Calculate ratio
ratio = binance_vol / coindesk_vol
# Expected: 0.3 ~ 0.8 (Binance is subset)
```

### C6: Signal Quality
```python
# Use for feature engineering
df['ttcr_sma_7d'] = df['ttcr'].rolling(7).mean()
df['ttcr_zscore'] = (df['ttcr'] - df['ttcr_sma_7d']) / df['ttcr'].std()

# Forward-looking labels
df['fwd_volume_7d'] = df['volume_aggregate'].shift(-7) / df['volume_aggregate']
```

### Layer 10 (Liquidity Layer - Future)
```python
# Real-time liquidity confirmation
current_ttcr = get_latest_ttcr()
historical_mean = dataset['ttcr'].mean()
zscore = (current_ttcr - historical_mean) / dataset['ttcr'].std()

if zscore > 2.0:
    # Abnormal top-tier concentration
    liquidity_signal = "concentrated"
```

---

## Gate Dependencies

```
C2 (Historical Access)
    ↓
    MUST PASS ← Proves we can fetch raw data
    ↓
C3 (PIT Semantics)
    ↓
    MUST PASS ← Proves revision patterns understood
    ↓
C4 (Reference Dataset)
    ↓
    Collect dataset with C3 findings applied
    ↓
C5 (Cross-Venue Validation)
    ↓
    Compare CoinDesk vs Binance using C4 dataset
    ↓
C6 (Signal Quality)
    ↓
    Test correlation: TTCR zscore → volume expansion
```

---

## Implementation Status

### Code Ready
- `Checkpoint4ReferenceDataset` ✅
- `fetch_volume_metrics()` ✅
- `validate_dataset_quality()` ✅
- `estimate_dataset_size()` ✅
- Storage plan ✅

### Tests Ready
- 12 unit tests (research mode) ✅

### Live Execution (Blocked Until C3 PASS + API Key)
1. Fetch 365 days × 3 assets
2. Validate completeness & integrity
3. Store parquet files
4. Generate metadata registry
5. Compute dataset statistics
6. Advance to C5

---

## Timeline Estimate

| Phase | Duration | Dependency |
|-------|----------|------------|
| **C2 Execution** | 5 min | API key available |
| **C3 Audit** | 30 min | C2 PASS |
| **C4 Collection** | 10 min | C3 PASS |
| **C5 Cross-Venue** | 1-2 hrs | C4 dataset ready |
| **C6 Signal Quality** | 2-4 hrs | C5 validation complete |

**Total**: ~4-6 hours once API key available

---

## Success Indicators

✅ **C4 PASS** signals:
1. CoinDesk data is fetchable and consistent
2. Volumes follow expected patterns
3. No gaps or data quality issues
4. Ready for downstream analysis (C5-C6)
5. Foundation for Liquidity Layer (proposed Layer 10)

---

## Sign-Off

**C4 Framework Status**: ✅ COMPLETE  
**C4 Tests**: ✅ 12 PASS  
**C4 Gate**: 🔴 BLOCKED (awaiting C3 PASS + API key)  
**Next Review**: After C3 audit completes  

**Owner**: TBD  
**Created**: 2026-10-06  
**Last Updated**: 2026-10-06  
