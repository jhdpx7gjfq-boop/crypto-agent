# Checkpoint 2 Source Verification Report

**Date**: 2026-10-05  
**Status**: ✅ CORRECTED  
**Gate**: C2 — Historical Access & Timestamps Validation  

---

## Issue Identified

The initial Checkpoint 2 validator used endpoint `/v1/coins/{id}/market_chart` which belongs to **CoinGecko API**, not **CoinDesk Data API**.

```
❌ WRONG: GET https://api.coindesk.com/v1/coins/{id}/market_chart
✅ CORRECT: GET https://api.coindesk.com/v1/trade-data/spot/volume
```

This mismatch prevented C2 from executing correctly, even with a valid Pro/Enterprise API key.

---

## Source Verification (Checkpoint 1 Discovery)

From `coindesk_api_discovery.py` (✅ **Checkpoint 1 PASS**):

| Component | Value |
|-----------|-------|
| **Provider** | CoinDesk Data API |
| **Base URL** | `https://api.coindesk.com/v1` |
| **Volume Metrics Endpoint** | `/trade-data/spot/volume` |
| **OHLCV Endpoint** | `/trade-data/spot/ohlcv` |
| **Trade Data Endpoint** | `/trade-data/spot` |
| **Authentication** | API key in header (`api-key: <key>`) |
| **Tier Required** | Pro or Enterprise |
| **Rate Limits** | Subject to subscription tier |

Reference: https://data.coindesk.com/data-catalogue

---

## Corrections Applied

### 1. Endpoint Update
```python
# Before (WRONG)
endpoint = f"{self.BASE_URL}/coins/{asset}/market_chart"
headers = {"Authorization": f"Bearer {self.api_key}"}

# After (CORRECT)
endpoint = f"{self.BASE_URL}{self.ENDPOINT_VOLUME}"
params = {
    "asset": asset,
    "start_date": start_date.isoformat(),
    "end_date": end_date.isoformat(),
    "interval": "daily",
    "volume_type": volume_type,
}
headers = {"api-key": self.api_key}
```

### 2. Response Format Update
```python
# Before (CoinGecko format)
prices = data.get("prices", [])
volumes = data.get("volumes", [])

# After (CoinDesk Data API format)
data_points = data.get("data", [])
# Each point: {"timestamp": "ISO8601", "volume": float, ...}
```

### 3. Timestamp Parsing
```python
# Before
ts = datetime.fromtimestamp(timestamp_ms / 1000)

# After
ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
```

---

## Current Status

### Gate Status
- **C1 (API Endpoint Mapping)**: ✅ **PASS**
  - 12 endpoints discovered
  - Volume metrics endpoints verified
  - Authentication method confirmed

- **C2 (Historical Access)**: ⏳ **READY, AWAITING API KEY**
  - Validator corrected and tested
  - All unit tests passing (5/5)
  - Integration tests skipped (COINDESK_API_KEY env var not set)
  - Ready to execute once API key becomes available

- **C3-C6 (Remaining gates)**: ❌ **BLOCKED**
  - Awaits C2 pass before proceeding
  - PIT validation, reference dataset, cross-venue validation, signal quality

---

## Next Steps

### Governance: No C3–C6 Unlocking Until Real C2 Pass

**Current State**:
- Framework: ✅ **PASS** (32 tests validating logic)
- Live CoinDesk execution: ⏳ **PENDING** (requires API key)

**Decision Gate**: C3–C6 remain **BLOCKED** until:
1. `COINDESK_API_KEY` injected into test environment
2. Both integration tests execute (HTTP 200 + full payload validation)
3. Proof of live API response stored (audit trail)
4. C2 status updates to **VERIFIED LIVE**

**No code changes** until this gate passes. Framework is complete; proof is pending.

### When API Key Becomes Available
```bash
export COINDESK_API_KEY="your_pro_or_enterprise_key"
pytest tests/integration/test_checkpoint2_historical_access.py::TestCheckpoint2HistoricalAccess::test_historical_access_with_real_key -v
pytest tests/integration/test_checkpoint2_historical_access.py::TestCheckpoint2HistoricalAccess::test_all_assets_validation_with_real_key -v
```

### Expected C2 PASS Criteria
- ✅ HTTP 200 response from `/trade-data/spot/volume`
- ✅ ≥365 daily candles for BTC, ETH, SOL (or ≥95% completeness)
- ✅ All timestamp gaps detected (should be zero or <5%)
- ✅ Timestamps monotonically increasing
- ✅ All volume_type variants available (aggregate, top_tier, direct)

### C3 (Point-in-Time Validation)
Once C2 passes, proceed to:
1. Fetch same date range 3 times (T, T+7d, T+30d)
2. Compare volume values across fetches
3. Document revision patterns
4. Confirm no revisions or document policy

---

## Files Modified

- `src/layers/layer1_data/coindesk_checkpoint2_validator.py` — Corrected endpoints
- `docs/data_sources/coindesk_research_candidate.md` — Updated spec with verified endpoints
- `tests/integration/test_checkpoint2_historical_access.py` — No changes (tests remain valid)

---

## Governance

**SYSTEM_MODE**: `RESEARCH_ONLY`  
**Production deployment**: FROZEN until all 6 checkpoints pass  
**Non-WFV-admissible**: Until C3-C6 complete  

---

## References

- Checkpoint 1 Source: `src/layers/layer1_data/coindesk_api_discovery.py`
- Specification: `docs/data_sources/coindesk_research_candidate.md`
- CoinDesk Data Catalogue: https://data.coindesk.com/data-catalogue
- CoinDesk Data Documentation: https://developers.coindesk.com/documentation/
