# BCE Engine v1: Bottom Confirmation Engine

**Status**: SPECIFICATION  
**Date**: 2026-09-25  
**Registry ID**: BCE-ENGINE-001  
**Kind**: contract  

---

## 1. Purpose

Identify accumulation zones through Wyckoff analysis. The BCE scores market
structure across six independent factors to detect when smart money is buying
into panic selling.

A single numeric output: **0–6 score**. Entry forbidden below 5/6.

---

## 2. Scoring Framework

Six factors, each contributes 0 or 1 point:

| # | Factor | How it Passes (1 point) | How it Fails (0 points) |
|---|---|---|---|
| 1 | **Wyckoff Structure** | Five-wave down, capitulation, low holds | Ambiguous or uptrend waves |
| 2 | **Volume Profile** | Volume spike at lows, decline on recovery | No volume confirmation at lows |
| 3 | **Selling Exhaustion** | High volume at lows, thin offers above | Volume uniform, no exhaustion signal |
| 4 | **Smart Money Accumulation** | Distribution stops, absorption detected | Distribution ongoing |
| 5 | **Market Structure** | Lower lows hold, higher lows form | New lows, no support forming |
| 6 | **Momentum Confirmation** | Stochastic, RSI, or MACD bullish divergence | No momentum divergence at lows |

**Validation Rule**: Score ≥ 5/6 required. A 4/6 is a near-miss, not a setup.

---

## 3. Input Contract

### Time Series Required

- **OHLCV**: Open, High, Low, Close, Volume (daily or intraday, implementation-defined)
- **Lookback**: 252 bars minimum (1 year of daily data, ~50 bars for hourly)
- **Current Date**: The date on which the score is computed

### Point-in-Time Constraint

The score at date `t` uses only data from `t-252` to `t` inclusive.
**No forward-looking data** (violates embargo).

---

## 4. Implementation Notes

### 4.1 Wyckoff Structure Detection

Identify five waves:

1. **Impulse Down** (W1): Initial selling, high volume
2. **Rally** (W2): Partial recovery (typically 30–50% of W1 loss)
3. **Secondary Decline** (W3): Lower low, moderate volume
4. **Recovery** (W4): Consolidation, lower volume
5. **Capitulation** (W5): Thrust to new low, often on declining volume or sudden increase

Score 1 if all five waves are present and low after W5 holds (no lower lows in next `n` bars).

### 4.2 Volume Analysis

- **At Lows**: Highest volume spike within the lookback
- **On Recovery**: Volume declines as price rises
- **Distribution Check**: If volume stays elevated on up moves, score 0

### 4.3 Selling Exhaustion

- Count bars with volume > 50th percentile at lows
- Count bars with volume < 50th percentile on recovery
- If exhaustion ratio > 0.7, score 1

### 4.4 Smart Money Accumulation

- Check for absorption pattern: net selling volume declines, bid-ask imbalance reverses
- Fallback: If distribution stops, score 1 (conservative measure)

### 4.5 Market Structure

- **Support Hold**: No new lows for `n` bars after the main capitulation bar
- **Higher Lows**: At least one recovery attempt reaches higher than the previous low
- Score 1 if both conditions met

### 4.6 Momentum Confirmation

- **Stochastic**: %K < 20 at lows; signal line crossed above %K
- **RSI**: < 30 at lows, divergence if price makes new low but RSI does not
- **MACD**: Histogram reversal (negative to positive) near lows

Score 1 if any one indicator confirms.

---

## 5. Output Contract

```python
@dataclass
class BCEScore:
    score: int  # 0-6
    date: date
    components: dict[str, bool]  # {
        #     "wyckoff_structure": bool,
        #     "volume_profile": bool,
        #     "selling_exhaustion": bool,
        #     "smart_money_accumulation": bool,
        #     "market_structure": bool,
        #     "momentum_confirmation": bool,
        # }
    details: dict[str, Any]  # rich diagnostic info for each component
    signal: str  # "BUY", "WAIT", or "MONITOR"
```

**Signal Rules**:
- `BUY` if score ≥ 5/6
- `WAIT` if score = 4/6 (near confirmation, needs one more)
- `MONITOR` if score ≤ 3/6 (not a setup)

---

## 6. Rejection Rules

Reject the computation and return score 0 if:

- Lookback < 252 bars
- OHLCV data contains NaN or non-positive Close
- Current price is more than 2% above the session high (gap up, not a real bottom)
- Volume is uniformly distributed (no spikes — likely low-liquidity or synthetic data)

---

## 7. Determinism and Reproducibility

- No external APIs or real-time ticks
- Use only committed OHLCV data
- All thresholds (e.g., 50th percentile, 20% Stochastic) hardcoded, no tuning parameters
- Rebuild from identical lookback always yields identical score

---

## 8. Integration Points

### Consumers

- `RPM-ENGINE` (next layer) reads BCE scores
- Alert system shows WAIT vs BUY vs MONITOR
- WFV v2 can stratify by BCE score if needed

### Dependencies

- `REAL-DATA-FIXTURE-001` or `REAL-DATA-FULL-001` for OHLCV
- `WFV-V2-CONTRACT` ensures embargo (no forward labels)

---

## 9. Validation Criteria (CI)

- All six factors tested independently
- Synthetic OHLCV test cases (known bottoms, known false signals) verified
- Determinism test: score(data) == score(data) on rebuild
- No lookahead: score at t=N uses no data after t=N
- Edge cases: gaps, limit moves, liquidity dries, outlier volume all handled

---

## 10. Success Metrics

- [ ] 100% test coverage on each factor
- [ ] Manual annotation of 50 crypto bottoms: BCE ≥ 5/6 on at least 80% of true bottoms
- [ ] False positive rate < 10% on non-bottoms
- [ ] Rebuild determinism verified
- [ ] Embargo compliance certified

---

## References

- Wyckoff, R. D. (1910–1930). Stock Market Technique
- Faller, A. (2016). The Wyckoff Trading Method for Digital Assets
- IGWT-PF26 context: Bottom confirmation as mandatory entry gate
