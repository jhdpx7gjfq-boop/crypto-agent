# H-005: BTC Exchange Flows Hypothesis

**Status**: 🔴 BLOCKED (Preflight 2A-C gates pending)

## Hypothesis

> Variations in BTC exchange inflows/outflows at signal generation time improve prediction of future BTC returns, net of transaction costs.

## Pre-Registered Contract (IMMUTABLE)

| Parameter | Value |
|-----------|-------|
| Experiment ID | H-005 |
| Asset | BTC-USD (1D candles) |
| Scope | BTC 1D only |
| Signal horizon | 5D forward returns (5 trading days ahead) |
| Features | Exchange flows (max 6) |
| Data provider | Glassnode (snapshot-versioned, PIT-safe) |
| Development period | 2021-01-01 → 2024-09-25 (frozen) |
| Hold-out period | 2024-09-26 → 2025-09-28 (LOCKED, untouched) |
| WFV protocol | 19-window expanding (180D train fixed, 30D test, 30D slide) |
| PIT rule | No lookahead; embargo ≥ 1 day |
| Embargo rule | 1 day minimum (per H-005 contract) |
| Gate criteria | ΔIC > 0.005 AND HR > 0.50 AND Stability > 0.65 (ALL must pass) |
| Production status | 🔴 BLOCKED indefinitely (no deployment) |

## Architecture

### Data Layer (`h005_data_layer.py`)

**GlassnodeSnapshotManager**: Archive exchange flows with immutable timestamps
- Fetch flows from Glassnode API
- Archive with PIT-safe snapshot versioning
- Location: `data/snapshots/glassnode/YYYY-MM-DD_HHmm_exchange_flows.json`

**H005DataLayer**: Unified prices + flows
- Binance OHLCV: frozen 2021-2024 (validated, SHA256 locked)
- Glassnode flows: snapshot-versioned, immutable
- PIT-safe accessor: `get_ohlcv(pit_idx)` and `get_flows(pit_idx, pit_timestamp)`

### Feature Engineering (`h005_feature_engineering.py`)

**ExchangeFlowFeatures**: 6 normalized signals from Glassnode data
1. `inflow_7d`: 7-day moving average inflow
2. `outflow_7d`: 7-day moving average outflow
3. `netflow_7d`: inflow - outflow (moving average)
4. `inflow_accum`: cumulative inflow (30-day window)
5. `outflow_accum`: cumulative outflow (30-day window)
6. `exchange_ratio`: inflow volume ratio (normalized)

All features normalized to [-1, 1].

**H005SignalGenerator**: Weighted average of 6 features
- Default: equal weights (1/6 each)
- Output: score in [-1, 1] (positive = bullish, negative = bearish)
- PIT-safe: uses only data[:idx+1]

### Walk-Forward Validation (`h005_runner.py`)

**H005WFVRunner**: 19-window expanding protocol
- Train: 180 days fixed (starting 2021-01-01)
- Test: 30 days sliding (no overlap)
- Windows: exactly 19 sequential windows
- PIT compliance: signal receives data[:idx+1] only
- Metrics: IC (information coefficient), HR (hit rate), Stability

**Gate Decision**:
```
ΔIC > 0.005  ✅ PASS → Continue
AND
HR > 0.50    ✅ PASS → Continue
AND
Stability > 0.65  ✅ PASS → Gate PASS
---
If any criterion fails → Gate FAIL (report findings, no iteration)
```

## Preflight 2: Three-Gate Sequence

### Gate 2A: PIT Verification (CRITICAL)

**Status**: ⏳ TBD (Glassnode API docs unreviewed)

**Action**: Fetch Glassnode API documentation and confirm:
- Snapshot versioning policy (immutable per timestamp)
- Data mutability (no historical backfills after snapshot)
- Revision schedule (if any; should be none)
- Embargo feasibility (1 day sufficient?)

**Outcome**:
- ✅ If Glassnode PIT-safe → proceed to Gate 2B
- ❌ If Glassnode fails PIT → H-005 closes (same as CryptoQuant)

### Gate 2B: Resource Provisioning

**Status**: ⏳ Awaiting owner authorization

**Action**: Owner to authorize Glassnode API access
- Cost: $588/yr (Advanced) or $999/yr (Professional)
- Obtain API key
- Store in local `.env` file (NEVER in git or chat)

**Outcome**:
- ✅ Key provisioned → proceed to Gate 2C

### Gate 2C: Parameter Freeze

**Status**: ⏳ Pending Gates 2A & 2B success

**Action**: Freeze all H-005 parameters:
- Embargo rule: 1 day minimum (per contract)
- Development period: 2021-01-01 → 2024-09-25
- Hold-out period: 2024-09-26 → 2025-09-28 (LOCKED, inaccessible)
- Snapshot archival policy confirmed
- Feature list finalized (6 max)
- Gate thresholds locked (ΔIC > 0.005, HR > 0.50, Stability > 0.65)

**Outcome**:
- ✅ All frozen → H-005 DEV PHASE begins

## Development Phase (After All 3 Gates Pass)

### Step 1: Initialize Environment

```bash
export GLASSNODE_API_KEY="<key_from_gate_2b>"
cd /home/user/crypto-agent
python -m src.research.h005.h005_data_layer  # Fetch & archive baseline
```

### Step 2: Build Windows

```python
from src.research.h005.h005_runner import H005WFVRunner
runner = H005WFVRunner(n_windows=19, train_days=180, test_days=30)
windows = runner.build_windows(df_len=1365, dev_end_idx=1364)
```

### Step 3: Execute WFV

```python
from src.research.h005.h005_data_layer import H005DataLayer
from src.research.h005.h005_feature_engineering import ExchangeFlowFeatures, H005SignalGenerator

data_layer = H005DataLayer("BTC-Daily-2021-2024.csv")
feature_gen = ExchangeFlowFeatures(lookback=30)
signal_gen = H005SignalGenerator()

# For each window, compute features and signals
# Compare against baseline (momentum-only predictor)
# Freeze results before any post-hoc analysis
```

### Step 4: Freeze Results

- Save to: `reports/research/h005_frozen_wfv.json`
- NO post-hoc tuning
- NO regime decomposition
- NO feature selection based on hold-out performance

### Step 5: Gate Evaluation

If gate passes (ΔIC > 0.005 AND HR > 0.50 AND Stability > 0.65):
- Document findings
- Hold-out evaluation on 2024-09-26 → 2025-09-28 (LOCKED period)
- Confirm alpha on unseen data

If gate fails:
- Report findings
- No iteration; Layer 8 remains blocked

## Key Constraints

1. **No future data**: Signals use data[:idx+1] only
2. **Frozen parameters**: Cannot modify dev period, hold-out, embargo, gate thresholds
3. **Immutable results**: Freeze WFV results before post-hoc analysis
4. **No deployment**: Production blocked indefinitely
5. **6 features max**: Exchange flows only; no supplementary signals during dev

## Testing

Run PIT compliance tests:
```bash
pytest tests/h005/test_h005_pit_compliance.py -v
```

## Files

- `h005_data_layer.py`: Binance + Glassnode integration
- `h005_feature_engineering.py`: Exchange flow signals (6 features)
- `h005_runner.py`: WFV orchestrator (19-window expanding)
- `tests/h005/test_h005_pit_compliance.py`: PIT validation
- `data/snapshots/glassnode/`: Timestamped snapshots (created on fetch)
- `reports/research/h005_frozen_wfv.json`: Immutable results (after dev)

## Next Steps

1. **Gate 2A**: Fetch Glassnode docs, confirm PIT safety
2. **Gate 2B**: Owner authorizes + provides API key
3. **Gate 2C**: Freeze parameters
4. **DEV**: Execute WFV, report findings
5. **EVAL**: Hold-out validation (if gate passes)
