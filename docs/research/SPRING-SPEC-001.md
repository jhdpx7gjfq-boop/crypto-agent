# Wyckoff Spring Detection Specification — SPRING-SPEC-001

**Version:** 1.0 RESEARCH_CANDIDATE  
**Date:** 2026-09-24  
**Status:** Not validated. For research only. No production usage.  
**Author:** Claude Code (IGWT-AIOS)

---

## ⚠️ DISCLAIMER

This specification is **RESEARCH_CANDIDATE** status. It is:
- Not backtested
- Not statistically validated
- Not validated Out-of-Sample
- Not validated through Walk-Forward
- Not production-ready

Use only for exploratory analysis and hypothesis testing. Any decisions based on SPRING_CANDIDATE signals must be manually reviewed.

---

## 1. Overview

A **Spring** (Wyckoff Spring) is a market structure pattern in which price briefly violates a key support level, triggering stops, and then reverses sharply above the support level. Springs are hypothesized to indicate **accumulation** by sophisticated participants (smart money).

This specification defines a testable state machine to identify Spring candidates.

---

## 2. Definitions

### 2.1 Support / Range

A **support zone** is a price level or range where price has stalled or bounced multiple times, indicating institutional interest.

**Detection Method (Research Candidate):**
- Identify the **lowest low** over a lookback window (default: 100 daily candles)
- Identify the **second-lowest low** or a horizontal resistance to that lowest low
- Support is the range formed by these levels
- Minimum support "width": price must test the support at least 2–3 times without breaking below

**Example:**
```
Price:  50, 49, 51, 49, 50, [support zone = 48–50]
```

### 2.2 Liquidity Sweep / Spring Trigger

A **liquidity sweep** occurs when price briefly drops below the support level, triggering long-stop orders.

**Detection Method:**
- Price closes **below** the support low by at least 0.5–1% (configurable)
- The low extends below support but the **close may return above or stay below**
- Volume often increases during the sweep (optional confirmation)

**Example:**
```
Support: 48
Sweep Candle: low = 47.5, close = 47.8 (below support)
```

### 2.3 Reclaim

A **reclaim** is when price rapidly re-enters and establishes above the support level.

**Detection Method:**
- After the sweep candle, price closes **above** the support level
- Ideally within 1–3 candles after the sweep
- The reclaim candle typically has lower volume than the sweep (as buying pressure slows stops)

**Example (after sweep):**
```
Candle 1: low = 47.5, close = 47.8 (sweep)
Candle 2: open = 47.9, close = 49.5 (reclaim)
```

### 2.4 Breakdown

A **breakdown** occurs when price closes **below** the support and continues lower without reclaim.

**Detection Method:**
- Consecutive closes below the support level
- No reclaim within 3–5 candles
- Price extends lower (new lows)

This is the **invalidation** of a Spring candidate.

---

## 3. State Machine

Tokens can be classified into one of the following mutually exclusive states:

```
┌─────────────────────────────────────┐
│         START / NO_SETUP            │
│   (No identifiable support found)   │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│      RANGE_CANDIDATE                │
│  (Support identified, no sweep yet) │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│      SPRING_CANDIDATE               │
│ (Sweep detected, awaiting reclaim)  │
└─────────────────────────────────────┘
         ↙         ↘
        ↓           ↓
    BREAKDOWN   SPRING_RECLAIM
  (Invalidated) (Reclaim triggered)
```

### 3.1 State: NO_SETUP

**Condition:**
- No identifiable support level found
- Insufficient data or no clear support zone
- Token is in uptrend or unstructured

**Exit To:**
- `RANGE_CANDIDATE` when support is identified

---

### 3.2 State: RANGE_CANDIDATE

**Condition:**
- Support/range level is identified
- Price has tested support 2–3 times without breaking
- No sweep has been triggered yet

**Requirements:**
- Minimum 2 tests of the support level
- Support holds (no closes below support in the last N candles)
- Price is near or above support

**Exit To:**
- `SPRING_CANDIDATE` when sweep is triggered
- `NO_SETUP` if support is invalidated (e.g., continuous breakdown)

---

### 3.3 State: SPRING_CANDIDATE

**Condition:**
- Sweep has occurred (price briefly below support)
- Reclaim is awaited

**Requirements:**
- Liquidity sweep candle: low < support_low - threshold
- Reclaim has not yet occurred
- Time elapsed since sweep < 5 candles

**Exit To:**
- `SPRING_RECLAIM` when reclaim occurs
- `BREAKDOWN` when breakdown occurs (invalidation)
- `RANGE_CANDIDATE` if neither occurs within 5 candles (reset)

---

### 3.4 State: SPRING_RECLAIM

**Condition:**
- Reclaim has occurred
- Price is back above support and holding

**Requirements:**
- Close > support_high (ideally)
- Occurred within 3–5 candles of sweep

**Implications:**
- **Potential accumulation zone identified**
- Does not guarantee future upside
- Requires further confirmation (relative strength, market regime, etc.)

---

### 3.5 State: BREAKDOWN

**Condition:**
- Support has been violated decisively
- No reclaim
- Invalidation of the Spring hypothesis

**Requirements:**
- Consecutive closes below support
- New lows are being made
- Time since sweep > 5 candles without reclaim

**Implications:**
- Support was false or structural break occurred
- Spring candidate is invalidated

---

## 4. Detection Algorithm (Pseudocode)

```python
def classify_spring_state(df, symbol):
    """
    Classify token into one of: 
    NO_SETUP, RANGE_CANDIDATE, SPRING_CANDIDATE, SPRING_RECLAIM, BREAKDOWN
    """
    
    # Step 1: Identify support
    support_low, support_high = find_support_zone(df, lookback=100)
    if support_low is None:
        return {symbol: "NO_SETUP", reason: "No support found"}
    
    # Step 2: Count recent tests of support (2+ required)
    tests = count_support_tests(df, support_low, support_high, lookback=50)
    if tests < 2:
        return {symbol: "NO_SETUP", reason: f"Only {tests} support test(s)"}
    
    # Step 3: Check for recent sweep
    recent_low = df.iloc[-1:]["low"].min()
    sweep_threshold = support_low * 0.995  # 0.5% below support
    
    if recent_low < sweep_threshold:
        # Sweep detected, check for reclaim
        sweep_candle_idx = df[df["low"] < sweep_threshold].index[-1]
        candles_since_sweep = len(df) - sweep_candle_idx - 1
        
        if candles_since_sweep > 5:
            # Too long, assume breakdown
            if df.iloc[-1]["close"] < support_high:
                return {symbol: "BREAKDOWN", reason: "No reclaim >5 candles"}
        
        # Check for reclaim
        if df.iloc[-1]["close"] > support_high:
            return {
                symbol: "SPRING_RECLAIM",
                support_low: support_low,
                reclaim_price: df.iloc[-1]["close"],
                candles_to_reclaim: candles_since_sweep,
            }
        else:
            return {
                symbol: "SPRING_CANDIDATE",
                support_low: support_low,
                sweep_price: recent_low,
                candles_since_sweep: candles_since_sweep,
            }
    
    # No recent sweep, check if range is intact
    recent_close = df.iloc[-1]["close"]
    if recent_close >= support_low * 0.99:  # Within 1% of support
        return {
            symbol: "RANGE_CANDIDATE",
            support_low: support_low,
            current_price: recent_close,
            distance_to_support_pct: (recent_close - support_low) / support_low * 100,
        }
    else:
        return {symbol: "NO_SETUP", reason: "Price too far below support"}
```

---

## 5. Parameters (Research, Not Optimized)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `lookback_support` | 100 daily candles | Sufficient to identify structural support |
| `lookback_tests` | 50 daily candles | Count recent tests of support |
| `min_support_tests` | 2–3 | Minimum evidence of institutional interest |
| `sweep_threshold` | support_low × 0.995 (−0.5%) | Small penetration to trigger stops |
| `max_sweep_duration` | 5 candles | Max time to reclaim before invalidation |
| `reclaim_threshold` | support_high | Close above support indicates reclaim |
| `support_width` | 1–2% | Range from lowest low to previous high |

**⚠️ These are research guesses, not validated.**

---

## 6. Limitations & Known Issues

1. **Support Detection:** Method is simple (just lowest low); does not account for volatility, broken structure, or multiple support zones.

2. **Volatility:** In highly volatile markets, micro-sweeps may be noisy; no filter for market regime.

3. **Timeframe Bias:** Specification applies to daily candles. Behavior on 4H or 1H may differ.

4. **False Positives:** Many sweeps fail to reclaim (breakdown). High false positive rate expected until filtering improves.

5. **Volume Confirmation:** Algorithm does not currently use volume; may be added in refinement.

6. **Gaps:** Does not handle missing candles (e.g., delisted pairs). Assumes continuous data.

7. **Liquidity:** Does not filter by liquidity; may produce signals for illiquid tokens.

---

## 7. Validation Plan

Before any production use, this spec must pass:

1. **Backtesting:** Historical replay on Top 500, measure false positive rate
2. **PIT (Parameter In-Sample Test):** Optimize parameters on historical data
3. **OOS (Out-of-Sample Test):** Validate on held-out date range
4. **WFV (Walk-Forward Validation):** Rolling validation to prevent overfitting
5. **Robustness:** Test on different market regimes (bull, bear, sideways)
6. **Ablation:** Remove parameters one-by-one; measure impact

**No signal is production-ready until WFV passes.**

---

## 8. Integration

- **P0.3:** Bottom detector (prerequisite for Spring)
- **P0.4:** Spring detector (uses this spec)
- **P0.5:** Reclaim / BOS detector (extends this spec)
- **P0.8:** Watchlist output (includes Spring candidates)

---

## 9. Example Output

```json
{
  "symbol": "BNBUSDT",
  "state": "SPRING_CANDIDATE",
  "support_low": 620.00,
  "support_high": 630.00,
  "support_tests": 3,
  "current_price": 618.50,
  "sweep_price": 618.20,
  "candles_since_sweep": 2,
  "max_sweep_duration": 5,
  "invalidation_level": 618.00,
  "reason": "Sweep detected, awaiting reclaim",
  "confidence": "LOW",
  "status": "RESEARCH_CANDIDATE"
}
```

---

## 10. References

- **Wyckoff:** "The Wyckoff Methodology" (public domain)
- **Smart Money:** Various market structure educators
- **Note:** This implementation is simplified; real Wyckoff analysis includes volume, time, and risk/reward analysis not present here.

---

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1.0 RESEARCH_CANDIDATE | 2026-09-24 | Initial spec. Ready for exploratory backtesting. |

---

**Status:** RESEARCH_CANDIDATE  
**Do Not Use for Production Decisions Without Validation**
