# P0: Real Binance Data Ingestion & Validation

**Status**: ⏸️ **AWAITING USER ACTION**  
**Phase**: 3 Real-Data WFV  
**Date**: 2026-10-01

---

## Overview

Phase 3 validation requires **real Binance OHLCV data** only. Synthetic data has been archived.

This document guides:
1. **Data acquisition** (user responsibility)
2. **File structure** (how to organize downloaded data)
3. **Provenance validation** (automated audit)
4. **WFV execution** (pipeline runs automatically after audit passes)

---

## 1. Data Acquisition

### Source
- **Binance Data Portal**: https://www.binance.vision/

### Assets & Time Range
| Asset | Period | Notes |
|-------|--------|-------|
| BTCUSDT | 2020-01-01 onwards | Daily candles (1d) |
| ETHUSDT | 2020-01-01 onwards | Daily candles (1d) |
| SOLUSDT | 2020-03-20 onwards | NO pre-launch data (launch: 2020-03-20) |

### Download Steps
1. Visit https://www.binance.vision/
2. Select **Download Center**
3. For each asset:
   - Asset: Select (e.g., BTCUSDT)
   - Interval: **1d** (daily)
   - Date Range: 2020-01-01 to 2026-10-01
   - Format: **CSV or JSON**
4. Record download metadata:
   - URL / Download path
   - Download timestamp
   - File hash (sha256)
   - First/last candle timestamps
   - Row count

---

## 2. File Organization

Place downloaded files in `data/real_binance/{SYMBOL}/`:

```
data/
└── real_binance/
    ├── BTCUSDT/
    │   └── BTCUSDT_1d.json          # Downloaded real Binance data
    ├── ETHUSDT/
    │   └── ETHUSDT_1d.json
    └── SOLUSDT/
        └── SOLUSDT_1d.json

# Synthetic data archived:
data/raw/synthetic_invalid/
├── BTCUSDT_2020-2025.json          # INVALID - DO NOT USE
├── ETHUSDT_2020-2025.json
└── SOLUSDT_2020-2025.json
```

### Expected File Format

**JSON OHLCV structure**:
```json
[
  {
    "timestamp": 1577836800,
    "open": 9287.33,
    "high": 9340.11,
    "low": 9256.77,
    "close": 9312.42,
    "volume": 48345.67
  },
  ...
]
```

**CSV format** (if downloaded as CSV, convert to JSON):
```csv
timestamp,open,high,low,close,volume
1577836800,9287.33,9340.11,9256.77,9312.42,48345.67
...
```

---

## 3. Provenance Validation

### Automated Audit

Once files are in place, run:

```bash
python -m src.layers.layer3_wyckoff.data_provenance_audit
```

### Audit Checks

| Check | Requirement | Fail Condition |
|-------|-------------|-----------------|
| **File Exists** | Each symbol file present | File missing → BLOCK |
| **SHA-256** | Recorded for integrity | Mismatch → WARN |
| **OHLCV Format** | Valid JSON with timestamp, open, high, low, close, volume | Missing fields → BLOCK |
| **Row Count** | Non-empty | Empty → BLOCK |
| **First Candle** | >= 2020-01-01 00:00:00 UTC | Earlier date → BLOCK |
| **Duplicates** | Zero duplicate timestamps | Duplicates found → WARN |
| **Gaps** | No missing daily candles (expected gap = 86400s) | Gaps detected → REPORT |
| **Asset Coverage** | SOL must NOT include pre-2020-03-20 | Pre-launch data → BLOCK |
| **Timestamp Order** | Strictly ascending | Out of order → BLOCK |

### Expected Audit Output

```json
{
  "BTCUSDT": {
    "symbol": "BTC",
    "metadata": {
      "exists": true,
      "file_size_bytes": 1024576,
      "sha256": "abc123...",
      "file_mtime": "2026-10-01T19:30:00"
    },
    "content": {
      "row_count": 2436,
      "first_candle_datetime": "2020-01-01T00:00:00",
      "last_candle_datetime": "2026-10-01T00:00:00",
      "unique_timestamp_count": 2436,
      "duplicate_count": 0,
      "gap_count": 0
    },
    "coverage": {
      "coverage_valid": true,
      "symbol": "BTC"
    }
  },
  ...
}
```

**Audit PASS** = All three symbols pass all checks (no "error" in metadata/content/coverage)

---

## 4. WFV Execution

### Prerequisites
- ✅ Real Binance data downloaded
- ✅ Files organized in `data/real_binance/{SYMBOL}/`
- ✅ Provenance audit PASS
- ✅ No synthetic data leakage

### Execute WFV Pipeline

```bash
python -m src.layers.layer3_wyckoff.real_data_wfv_pipeline
```

### Pipeline Stages

| Stage | Description |
|-------|-------------|
| **1. Load & Audit** | Provenance validation on each file |
| **2. Window Gen** | Generate 71 WFV windows (60d train, 30d test, 30d step) |
| **2.5 Window Validation** | Verify: windows_computed ≥ 71. If NO → BLOCKED |
| **3. PIT Validation** | No lookahead bias checks on train/test splits |
| **4. BCE Backtest** | Run BCE scoring on each test window |
| **5. OOS Metrics** | Calculate Profit Factor, Max DD, Consistency |
| **6. Immutable Gates** | Apply frozen thresholds (OOS >= 200, PF >= 1.30, etc.) |
| **7. Phase 3 Verdict** | PASS / FAIL / INCONCLUSIVE |

### 71 Windows Requirement

**Calculation** (rolling windows with 30-day step):
```
Days needed = train_days + test_days + (windows - 1) × step_days
            = 60 + 30 + (71 - 1) × 30
            = 2,190 days
            ≈ 6.0 years
```

**2020–2025 scope**: ~2,068 calendar days (≈5.67 years)
→ **At the limit**: May be insufficient depending on exact dates and gaps
→ **Validation**: Pipeline computes actual windows; if < 71 → BLOCKED

### Immutable Gates (Cannot Change)

```
✓ OOS Trade Count >= 200
✓ Profit Factor >= 1.30
✓ Max Drawdown < 25%
✓ Degradation < 30%
✓ Consistency >= 50%
```

---

## 5. Expected Outcomes

### Success Path (PASS)
- All audits clear
- All WFV windows execute
- All immutable gates satisfied
- **Phase 3 VERDICT: ✅ PASS**
- Phase 4 X20 Engine unblocked

### Failure Path (FAIL)
- Real data metrics do NOT satisfy immutable gates
- **Phase 3 VERDICT: ❌ FAIL**
- Phase 4 remains blocked
- Adjust BCE or governance, document decision
- Re-run real-data WFV

### Inconclusive Path (INCONCLUSIVE)
- Data quality issues prevent clean execution
- **Phase 3 VERDICT: ⚠️ INCONCLUSIVE**
- Investigate data gaps, duplicates, or gaps
- Acquire alternate data source or extend coverage
- Re-audit and re-run

---

## 6. Validation Reports

Reports generated after WFV:

```
data/validation_reports/
├── phase3_real_data_wfv_2026-10-01.json       # Full pipeline output
├── provenance_audit_2026-10-01.json           # Audit details
└── PHASE3_REAL_DATA_VERDICT_2026-10-01.txt    # Human-readable verdict
```

---

## 7. Governance Checkpoints

✅ **Completed**:
- Phase 3 BCE engine (57/57 tests)
- Synthetic data archived
- Validation pipeline implemented
- Governance rules frozen

⏸️ **Awaiting**:
- Real Binance data download (user)
- Provenance audit (automated)
- WFV execution (automated)
- Phase 3 verdict (automated)

❌ **Blocked**:
- Phase 4 X20 Engine (until Phase 3 PASS)

---

## 8. Next Steps

1. **User Action**: Download BTCUSDT, ETHUSDT, SOLUSDT from Binance Data Portal
2. **User Action**: Organize in `data/real_binance/{SYMBOL}/`
3. **Automated**: Run provenance audit
4. **Automated**: Execute WFV pipeline
5. **Automated**: Generate Phase 3 verdict
6. **Conditional**: Unblock Phase 4 if verdict = PASS

---

**Reference**: Phase 3 Specification (commit f20c7fb)  
**Authority**: IGWT-PF26 Governance (commit 6d194fa)  
**Status**: Ready for data ingestion
