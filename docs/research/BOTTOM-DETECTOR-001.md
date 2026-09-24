# Bottom Detector Specification — BOTTOM-DETECTOR-001

**Version:** 1.0 RESEARCH_CANDIDATE  
**Date:** 2026-09-24  
**Status:** Not validated. Research only. No predictive guarantee.

---

## ⚠️ DISCLAIMER

This specification is **RESEARCH_CANDIDATE** status. It:
- Does NOT predict bottoms
- Is NOT statistically validated
- Is NOT validated Out-of-Sample or Walk-Forward
- Identifies structures **compatible with** bottom phases
- Makes no performance guarantees

Use only to identify candidates for further analysis (Spring detection, manual review).

---

## 1. Overview

The Bottom Detector identifies price structures on **Daily timeframe** that are compatible with an accumulation or bottom phase. It classifies tokens into structural states without claiming predictive power.

**What it does:**
- Measures distance from recent high (drawdown)
- Detects consolidation/stabilization
- Classifies into 4 mutually exclusive states

**What it doesn't do:**
- Predict future price
- Score "likelihood" of bottom
- Guarantee reliability
- Validate on historical data

---

## 2. Definitions

### 2.1 Drawdown

**Definition:** Distance from price to a recent historical high.

```
drawdown_pct = (close - rolling_high) / rolling_high * 100
```

Where:
- `close` = current close price
- `rolling_high` = highest close in lookback window

**Lookback Window (Research):**
- Default: 100 daily candles (~5 months)
- Configurable in `config/scanner.yml`
- Why 100? Captures both trend highs and intermediate swings; avoids all-time highs for recent altcoins

**Example:**
```
rolling_high = 100
current_close = 60
drawdown = (60 - 100) / 100 * 100 = -40%
```

### 2.2 Base / Consolidation

**Definition:** Period where price oscillates within a bounded range after drawdown, indicating reduced selling pressure.

**Metrics (research candidates):**
- **Range Width:** `(base_high - base_low) / base_high`
- **Volatility:** Rolling standard deviation of returns
- **Price Density:** Proximity of closes to range mid-point

**Base Lookback Window (Research):**
- Default: 30 daily candles (~1 month recent)
- Rationale: Captures recent consolidation, not historical noise

**Example:**
```
base_high = 65
base_low = 58
range_width = (65 - 58) / 65 ≈ 10.8%
```

### 2.3 Stability Signal

**Definition:** Indication that price is not in free-fall.

**Simple measure (research):**
- Consecutive closes near range lows → LOW
- Consecutive closes near range mid → MEDIUM
- Closes oscillating above range mid → HIGH

No magic threshold; purely observational.

---

## 3. State Machine

Tokens are classified into one of **4 mutually exclusive states**:

```
┌─────────────────────────────────────┐
│     NO_BOTTOM_STRUCTURE             │
│  (Insufficient data or uptrend)     │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│      DRAWDOWN                       │
│  (Price down, no stabilization)     │
└─────────────────────────────────────┘
         ↙         ↘
        ↓           ↓
    ESCALATION  BASE_CANDIDATE
  (worse)       (stabilizing)
```

### 3.1 State: NO_BOTTOM_STRUCTURE

**Condition:**
- Insufficient data (< 50 daily candles)
- Price is in uptrend (above 200-day MA or equivalent)
- No detectable drawdown

**Evidence:**
- Data points available
- Rolling high proximity
- Trend direction

**Exit To:**
- `DRAWDOWN` when price falls and drawdown exceeds threshold

---

### 3.2 State: DRAWDOWN

**Condition:**
- Drawdown from rolling high ≥ threshold (research: 20%)
- Price has not stabilized yet
- High volatility or continued selling

**Requirements:**
- Drawdown ≥ 20% (configurable, RESEARCH_CANDIDATE)
- No clear consolidation range yet
- Or consolidation range too wide (>15% of close)

**Exit To:**
- `BASE_CANDIDATE` if consolidation detected
- `ESCALATION` (stays DRAWDOWN) if prices continue falling

---

### 3.3 State: BASE_CANDIDATE

**Condition:**
- Drawdown present (≥ 20%)
- Consolidation detected (range ~10% or narrower)
- Price stabilized (not cascading lower)

**Requirements:**
- Drawdown ≥ 20%
- Base range width ≤ 12% (configurable)
- Minimum 10 candles of consolidation
- Price not making new lows in recent candles

**Implications:**
- Selling pressure may be exhausted
- Potential accumulation starting
- NOT a signal to buy
- Candidate for Spring detection (P0.4)

---

### 3.4 Invalidation

A `BASE_CANDIDATE` is invalidated if:
- Price closes below the base low by >2% (escape downward)
- Volatility spikes (range doubles)
- Base breaks definitively

Once invalidated → `DRAWDOWN` or `NO_BOTTOM_STRUCTURE`.

---

## 4. Detection Algorithm (Pseudocode)

```python
def classify_bottom_state(df_daily):
    """
    Classify token into one of 4 states based on daily OHLCV.
    
    Args:
        df_daily: DataFrame with columns [timestamp, open, high, low, close, volume]
                  sorted by timestamp, closed candles only
    
    Returns:
        state, evidence (dict of raw values)
    """
    
    if len(df_daily) < 50:
        return "NO_BOTTOM_STRUCTURE", {"reason": "insufficient_data"}
    
    # Step 1: Calculate drawdown
    rolling_high = df_daily["high"].rolling(100, min_periods=1).max()
    current_close = df_daily["close"].iloc[-1]
    current_high = rolling_high.iloc[-1]
    drawdown_pct = (current_close - current_high) / current_high * 100
    
    if drawdown_pct > -5:  # Up or minimal drawdown
        return "NO_BOTTOM_STRUCTURE", {
            "drawdown": drawdown_pct,
            "reason": "uptrend or minimal drawdown"
        }
    
    if drawdown_pct < -20:
        # Significant drawdown; check for stabilization
        
        # Step 2: Measure recent consolidation (last 30 candles)
        recent = df_daily.tail(30)
        base_high = recent["high"].max()
        base_low = recent["low"].min()
        base_range_pct = (base_high - base_low) / base_close * 100
        
        if base_range_pct > 15:
            # Wide range, still volatile
            return "DRAWDOWN", {
                "drawdown": drawdown_pct,
                "base_range": base_range_pct,
                "reason": "wide_base_range"
            }
        
        # Step 3: Check for continued selling (new lows in last 5 candles)
        recent_5 = df_daily.tail(5)
        lowest_5 = recent_5["low"].min()
        
        if lowest_5 < base_low * 0.98:
            # Escaping downward
            return "DRAWDOWN", {
                "drawdown": drawdown_pct,
                "recent_new_low": True,
                "reason": "continuing_selloff"
            }
        
        # Step 4: Check stability (closes near mid-range, not at lows)
        mid_range = (base_high + base_low) / 2
        closes_above_mid = (recent["close"] > mid_range).sum()
        stability_pct = closes_above_mid / len(recent)
        
        if stability_pct < 0.3:
            # Most closes at lows
            return "DRAWDOWN", {
                "drawdown": drawdown_pct,
                "stability": stability_pct,
                "reason": "low_stability"
            }
        
        # All checks passed
        return "BASE_CANDIDATE", {
            "drawdown": drawdown_pct,
            "base_high": base_high,
            "base_low": base_low,
            "base_range": base_range_pct,
            "stability": stability_pct,
            "consolidation_candles": len(recent)
        }
    
    else:
        # -5% to -20% drawdown
        return "DRAWDOWN", {
            "drawdown": drawdown_pct,
            "reason": "moderate_drawdown"
        }
```

---

## 5. Parameters (Research, Not Optimized)

| Parameter | Value | Note |
|-----------|-------|------|
| `drawdown_lookback` | 100 days | Capture trend high |
| `drawdown_threshold` | -20% | Significant decline (RESEARCH_CANDIDATE) |
| `base_lookback` | 30 days | Recent consolidation |
| `base_range_threshold` | 12% | Range width max (RESEARCH_CANDIDATE) |
| `min_base_candles` | 10 | Minimum consolidation duration |
| `stability_threshold` | 30% | Min closes above mid-range |
| `escape_threshold` | -2% | Invalidation threshold below base low |

**⚠️ All thresholds are research guesses, not optimized.**

---

## 6. Outputs

### 6.1 State Classification

```
symbol: "BTC"
timestamp: "2024-09-24T00:00:00Z"
timeframe: "daily"
state: "BASE_CANDIDATE"
evidence: {
  "drawdown": -42.5,
  "rolling_high": 98500,
  "current_close": 56600,
  "base_high": 62000,
  "base_low": 55800,
  "base_range": 10.1,
  "stability": 65,
  "consolidation_candles": 28
}
status: "RESEARCH_CANDIDATE"
```

### 6.2 Rejection/Classification Reasoning

Every state includes **raw feature values**, not interpretations.

---

## 7. Limitations

1. **Single Timeframe:** Uses daily only; intraday volatility ignored
2. **No Volume:** Volume confirmation not included
3. **No Regime:** Ignores macro conditions, market structure
4. **Backward-looking:** Uses historical highs; doesn't detect new bottoms
5. **False Positives:** Many `BASE_CANDIDATE` will not lead to upside
6. **No Spring Logic:** This is purely structural, not Wyckoff Spring-specific
7. **Arbitrary Thresholds:** 20%, 12%, 30% are educated guesses

---

## 8. Validation Plan

**NOT YET VALIDATED:**
- ❌ Backtesting (PIT not run)
- ❌ Out-of-Sample (OOS not run)
- ❌ Walk-Forward (WFV not run)
- ❌ Statistical significance

Future P1+:
1. Historical replay on Top 500
2. Measure false positive rate of `BASE_CANDIDATE`
3. Filter by follow-up Spring confirmation
4. Calculate precision/recall
5. Optimize thresholds on PIT, validate OOS
6. Walk-Forward test

---

## 9. References

- Wyckoff: Spring (reversal from weakness)
- Price Action: Consolidation, drawdown, stabilization
- Note: This spec is simplified; real Wyckoff analysis is more nuanced

---

## 10. Status

**RESEARCH_CANDIDATE**  
Not production-ready. Use for research only.

---

**Date:** 2026-09-24  
**Version:** 1.0  
**Next Milestone:** P0.4 Spring Detector
