# Spring Detector Specification — SPRING-DETECTOR-001

**Version:** 1.0 RESEARCH_CANDIDATE  
**Date:** 2026-09-24  
**Status:** Not validated. Research only. No predictive guarantee.

---

## ⚠️ DISCLAIMER

This specification is **RESEARCH_CANDIDATE** status. It:
- Does NOT predict profitable entries
- Is NOT statistically validated
- Is NOT validated Out-of-Sample or Walk-Forward
- Identifies structures **compatible with** Wyckoff Spring patterns
- Makes no performance guarantees

Use only to identify candidates for further analysis and manual confirmation.

---

## 1. Overview

The Spring Detector identifies price structures on **Daily timeframe** compatible with a Wyckoff Spring pattern. It classifies into 5 mutually exclusive states without claiming predictive power.

**What it does:**
- Detects identifiable range structures
- Identifies liquidity sweeps (penetration below support)
- Detects reactions and reclaim patterns
- Classifies into 5 states (NO_SPRING, RANGE, SWEEP, SPRING_CANDIDATE, BREAKDOWN)

**What it doesn't do:**
- Predict price movement
- Score "likelihood" of success
- Guarantee reliability
- Validate on historical data
- Use external indicators (RSI, MACD, etc.)

---

## 2. Concepts & Definitions

### 2.1 Range

**Definition:** A price band where price oscillates between identifiable high and low over a lookback period.

**Characteristics:**
- `range_high`: Highest close or high in lookback window
- `range_low`: Lowest close or low in lookback window
- `range_width`: (range_high - range_low) / range_low * 100 (percent)
- `range_lookback`: Number of candles analyzed (research: 20-40 days, default 30)

**Method (Research):**
```
recent = df.tail(range_lookback)
range_high = recent["high"].max()
range_low = recent["low"].min()
range_width_pct = (range_high - range_low) / range_low * 100
```

**Constraint:** Range must be identifiable (width > 2%, width < 25%)

---

### 2.2 Support Level

**Definition:** The range low; level where liquidity is presumed to exist.

**Reference:** 
```
support_level = range_low
```

**Usage:**
- Benchmark for sweep detection
- Target for reclaim confirmation
- May be adjusted by 0.5% tolerance for wicks

---

### 2.3 Sweep

**Definition:** Price penetration below support level, triggering stop-loss orders and accumulation.

**Metric:**
```
candle.low < support_level (no tolerance)
```

**Tracking:**
- `sweep_low`: Lowest price during sweep
- `sweep_depth`: (support_level - sweep_low) / support_level * 100 (percent)
- `sweep_candles`: Number of consecutive candles below support

**Constraint:** Sweep depth should be 0.5% to 3% (research guess, not optimized)

---

### 2.4 Reaction

**Definition:** Price movement after sweep, indicating potential recovery.

**Metrics (Research):**
- `close_above_support`: First candle close > support_level after sweep
- `recovery_pct`: (close_after_sweep - sweep_low) / sweep_low * 100
- `candles_to_recovery`: Number of candles from sweep to close above support

**Constraint:** Recovery must occur within 1-5 candles (research)

---

### 2.5 Reclaim

**Definition:** Return above a reference level, confirming the Spring pattern.

**Reference Level:** Support level (range_low)

**Reclaim Condition:**
```
close > support_level (no tolerance, must close above)
```

**Timestamp:** Signal timestamp is the candle where reclaim is confirmed (first close > support)

**Constraint:** Reclaim must occur within 3-10 candles of sweep (research)

---

### 2.6 Breakdown

**Definition:** Failure to reclaim; sustained weakness below support.

**Criteria (Research):**
- No close > support within reclaim window (3-10 candles)
- Price continues lower after sweep
- Establishes new lows below sweep_low

**Classification:**
```
If sweep occurs but no reclaim within window:
  → BREAKDOWN (not SPRING_CANDIDATE)
```

---

## 3. State Machine

Tokens are classified into one of **5 mutually exclusive states**:

```
┌─────────────────────────────────────┐
│         NO_SPRING                   │
│  (No identifiable range or trend)   │
└─────────────────────────────────────┘
              ↓ (range detected)
┌─────────────────────────────────────┐
│         RANGE                       │
│  (Consolidation, no sweep yet)      │
└─────────────────────────────────────┘
              ↓ (sweep below support)
┌─────────────────────────────────────┐
│         SWEEP                       │
│  (Below support, awaiting reclaim)  │
└─────────────────────────────────────┘
         ↙         ↘
        ↓           ↓
   SPRING_      BREAKDOWN
   CANDIDATE   (no reclaim)
```

### 3.1 State: NO_SPRING

**Condition:**
- No identifiable range detected
- Price in strong trend (no consolidation)
- Insufficient data (< 50 candles)

**Evidence:**
- Reason for rejection
- Data points available
- Range metrics (if attempted)

**Exit To:**
- `RANGE` when price consolidates into identifiable band

---

### 3.2 State: RANGE

**Condition:**
- Identifiable range (2% < width < 25%)
- Price oscillating between high and low
- Support level defined (range_low)
- No active sweep below support

**Metrics:**
- `range_high`, `range_low`, `range_width_pct`
- `range_lookback` candles
- Time in range
- Oscillation count (touches to low/high)

**Exit To:**
- `SWEEP` when price low < support_level
- `NO_SPRING` if range breaks down and dissipates

---

### 3.3 State: SWEEP

**Condition:**
- At least one candle with low < support_level
- No reclaim yet (close ≤ support_level or still in sweep sequence)
- Active potential for reclaim

**Metrics:**
- `sweep_low`: Lowest point during sweep
- `sweep_depth_pct`: Distance below support
- `sweep_candles`: Number of candles below support
- `recovery_pct`: Recovery from sweep_low to current close
- `candles_since_sweep`: Duration since sweep occurred

**Exit To:**
- `SPRING_CANDIDATE` if reclaim occurs (close > support within window)
- `BREAKDOWN` if sweep is not reclaimed within window and continues lower
- `RANGE` if price recovers back into range without formal reclaim confirmation

---

### 3.4 State: SPRING_CANDIDATE

**Condition:**
- Sweep confirmed (price did go below support)
- Reclaim confirmed (close > support_level)
- Reaction occurred between sweep and reclaim
- Pattern consistent with Wyckoff Spring definition

**Metrics:**
- All SWEEP metrics + reclaim timestamp
- `reclaim_timestamp`: Candle where close > support
- `reclaim_close`: Close price at reclaim
- `reclaim_candles`: Number of candles from sweep to reclaim

**Evidence:**
- Complete Spring structure with all components
- No future confirmation (signal locked at reclaim timestamp)

**Status:** RESEARCH_CANDIDATE (not guaranteed to lead to upside)

---

### 3.5 State: BREAKDOWN

**Condition:**
- Sweep occurred (price below support)
- Reclaim window closed without reclaim
- Sustained weakness or new lows

**Metrics:**
- `sweep_low`: Lowest point of failed sweep
- `breakdown_low`: New low (if applicable)
- `reclaim_window_candles`: How long was waited (default 10)
- `reason`: Why pattern failed (no reclaim, continued weakness, etc.)

**Evidence:**
- Why this is NOT a Spring
- Support breakdown vs. Spring confirmation

---

## 4. Detection Algorithm (Pseudocode)

```python
def classify_spring_state(symbol, df_daily, config):
    """
    Classify token into one of 5 Spring states based on daily OHLCV.
    
    Args:
        symbol: Token symbol (e.g., "BTC")
        df_daily: DataFrame with columns [timestamp, open, high, low, close, volume]
                  sorted by timestamp, closed candles only
        config: Configuration dict with parameters
    
    Returns:
        state, evidence (dict of raw values), signal_timestamp
    """
    
    if len(df_daily) < 50:
        return "NO_SPRING", {"reason": "insufficient_data"}, None
    
    # Step 1: Detect range
    range_lookback = config.get("range_lookback", 30)
    recent = df_daily.tail(range_lookback)
    range_high = recent["high"].max()
    range_low = recent["low"].min()
    range_width_pct = (range_high - range_low) / range_low * 100
    
    if range_width_pct < 2 or range_width_pct > 25:
        return "NO_SPRING", {
            "reason": "range_not_identifiable",
            "range_width": range_width_pct
        }, None
    
    # Step 2: Check current position
    current_close = df_daily["close"].iloc[-1]
    current_low = df_daily["low"].iloc[-1]
    
    if current_close > range_high:
        # Price above range; breakout, not Spring setup
        return "NO_SPRING", {
            "reason": "price_above_range",
            "current_close": current_close,
            "range_high": range_high
        }, None
    
    # Step 3: Detect sweep
    sweep_idx = None
    for i in range(len(recent) - 1, -1, -1):
        if recent["low"].iloc[i] < range_low:
            sweep_idx = i
            break
    
    if sweep_idx is None:
        # No sweep; price within range
        return "RANGE", {
            "range_high": range_high,
            "range_low": range_low,
            "range_width": range_width_pct,
            "range_lookback": range_lookback
        }, None
    
    # Step 4: Analyze sweep
    sweep_low = recent.iloc[sweep_idx:]["low"].min()
    sweep_depth_pct = (range_low - sweep_low) / range_low * 100
    
    # Step 5: Look for reclaim after sweep
    reclaim_window = config.get("reclaim_window_candles", 10)
    reclaim_idx = None
    
    for i in range(sweep_idx + 1, min(sweep_idx + reclaim_window + 1, len(recent))):
        if recent["close"].iloc[i] > range_low:
            reclaim_idx = i
            break
    
    if reclaim_idx is not None:
        # Reclaim found; SPRING_CANDIDATE
        reclaim_timestamp = recent["timestamp"].iloc[reclaim_idx]
        reclaim_close = recent["close"].iloc[reclaim_idx]
        
        # Calculate recovery
        recovery_pct = (reclaim_close - sweep_low) / sweep_low * 100
        candles_to_reclaim = reclaim_idx - sweep_idx
        
        return "SPRING_CANDIDATE", {
            "range_high": range_high,
            "range_low": range_low,
            "range_width": range_width_pct,
            "sweep_low": sweep_low,
            "sweep_depth": sweep_depth_pct,
            "recovery_pct": recovery_pct,
            "reclaim_timestamp": reclaim_timestamp,
            "reclaim_close": reclaim_close,
            "candles_to_reclaim": candles_to_reclaim,
            "volume": recent["volume"].iloc[reclaim_idx] if "volume" in recent else None
        }, reclaim_timestamp
    
    # Check if window closed without reclaim
    if sweep_idx + reclaim_window < len(recent):
        # Window has closed; check for BREAKDOWN
        post_window = recent.iloc[sweep_idx + reclaim_window:]
        new_low = post_window["low"].min()
        
        if new_low < sweep_low:
            # Continued weakness → BREAKDOWN
            return "BREAKDOWN", {
                "reason": "continued_weakness",
                "sweep_low": sweep_low,
                "breakdown_low": new_low,
                "reclaim_window_candles": reclaim_window
            }, None
    
    # Still in sweep, waiting for reclaim or breakdown
    return "SWEEP", {
        "range_low": range_low,
        "sweep_low": sweep_low,
        "sweep_depth": sweep_depth_pct,
        "candles_since_sweep": len(recent) - sweep_idx,
        "recovery_pct": (current_close - sweep_low) / sweep_low * 100 if sweep_low > 0 else 0
    }, None
```

---

## 5. Parameters (Research, Not Optimized)

| Parameter | Value | Note |
|-----------|-------|------|
| `range_lookback` | 30 days | Capture consolidation (RESEARCH_CANDIDATE) |
| `range_width_min` | 2% | Minimum identifiable width (RESEARCH_CANDIDATE) |
| `range_width_max` | 25% | Maximum width for consolidation (RESEARCH_CANDIDATE) |
| `sweep_tolerance` | 0% | No tolerance; must penetrate support (firm) |
| `reclaim_threshold` | Support level | Reclaim = close > range_low (firm) |
| `reclaim_window_candles` | 10 | Max candles to reclaim after sweep (RESEARCH_CANDIDATE) |
| `breakdown_threshold` | -0.5% | New lows below sweep_low (RESEARCH_CANDIDATE) |

**⚠️ All thresholds are research guesses, not optimized.**

---

## 6. Outputs

### 6.1 State Classification

```
symbol: "BTC"
timestamp: "2024-09-24T00:00:00Z"
timeframe: "daily"
state: "SPRING_CANDIDATE"
signal_timestamp: "2024-09-26T00:00:00Z"
evidence: {
  "range_high": 62000,
  "range_low": 55800,
  "range_width": 11.1,
  "sweep_low": 54000,
  "sweep_depth": 3.2,
  "recovery_pct": 8.5,
  "reclaim_timestamp": "2024-09-26T00:00:00Z",
  "reclaim_close": 58600,
  "candles_to_reclaim": 3,
  "volume": 4500.0
}
status: "RESEARCH_CANDIDATE"
reason: null
```

### 6.2 State Transitions

Each state includes raw feature values, not interpretations.

---

## 7. State Transition Diagram

```
NO_SPRING
  ↓ (range detected)
RANGE
  ↓ (price < range_low)
SWEEP
  ├→ (close > range_low within window) SPRING_CANDIDATE
  └→ (no reclaim, continued weakness) BREAKDOWN

BREAKDOWN
  ↓ (recovery) could return to RANGE or NO_SPRING
```

---

## 8. Limitations

1. **Single Timeframe:** Uses daily only; 4H structure ignored
2. **No Volume Rules:** Volume exposed but not required
3. **No Indicators:** Pure structural (no RSI/MACD/Stochastic)
4. **No Regime:** Ignores macro conditions
5. **Range Definition:** Backward-looking; doesn't detect forming ranges
6. **Sweep Definition:** Simple penetration; no "smart money" accumulation patterns
7. **False Positives:** Many SPRING_CANDIDATE will not lead to upside
8. **No Statistics:** Not backtested, OOS/WFV not run
9. **Arbitrary Thresholds:** 2%, 25%, 10 candles are educated guesses
10. **No Smart Money:** Cannot distinguish smart money from retail capitulation

---

## 9. Validation Plan

**NOT YET VALIDATED:**
- ❌ Backtesting (PIT not run)
- ❌ Out-of-Sample (OOS not run)
- ❌ Walk-Forward (WFV not run)
- ❌ Statistical significance
- ❌ Win rate / profit factor calculation

Future P1+:
1. Historical replay on Top 500
2. Measure false positive rate of `SPRING_CANDIDATE`
3. Track outcomes: how many led to reversals?
4. Calculate true positive rate and precision/recall
5. Optimize thresholds on PIT, validate OOS
6. Walk-Forward test
7. Integrate with P0.5 Reclaim/BOS for cumulative validation

---

## 10. Key Design Rules

### Signal Timestamp
- Signal (SPRING_CANDIDATE) is locked at reclaim candle (first close > support)
- No future data influences signal generation
- Evidence can include post-signal data for evaluation only

### No Future Confirmation
- The state at timestamp T uses only data ≤ T
- Evaluation at T+N can use T+N data (for historical analysis)
- But signal cannot be retroactively changed

### Determinism
- Same OHLCV input → same state output, always
- Replay test: processing candle-by-candle must match batch processing

---

## 11. References

- Wyckoff: Spring pattern, support testing, smart money accumulation
- Price Action: Range, support/resistance, reaction
- Note: This spec is simplified; real Wyckoff analysis includes volume profile, accumulation/distribution, market structure

---

## 12. Status

**RESEARCH_CANDIDATE**  
Not production-ready. Use for research only.

---

**Date:** 2026-09-24  
**Version:** 1.0  
**Next Milestone:** P0.4 Spring Detector Implementation + Tests

