# Layer 2: Market Regime Engine Specification

**Status:** SPECIFICATION (awaiting implementation)  
**Phase:** Architecture + TDD design  
**Dependency:** Layer 1 (snapshot/PIT infrastructure) COMPLETE  
**Data Dependency:** P0.1 Binance BTCUSDT (real data) PENDING; mock data sufficient for development

---

## Objective

Identify global market context to detect regime shifts, liquidity conditions, and risk appetite changes. Enables **dynamic parameter optimization** and **opportunistic signal filtering** in downstream layers.

**Principle:** "Understand the market before entering a position."

---

## Architecture Overview

```
Layer 2: Market Regime Engine
├── C2.1: Bitcoin Dominance Regime
├── C2.2: Liquidity Regime (Funding Rates)
├── C2.3: Risk-On / Risk-Off Detection
├── C2.4: Macro Conditions (DXY, US10Y, CPI, M2)
├── C2.5: ETF Flow Analysis
├── C2.6: Open Interest Regime
└── C2.7: Regime Composite Score

Outputs:
├── regime_state: "BULL" | "BEAR" | "SIDEWAYS" | "TRANSITION"
├── liquidity_regime: "TIGHT" | "NORMAL" | "ABUNDANT"
├── risk_appetite: 0.0–1.0 (0=risk-off, 1=risk-on)
├── macro_regime: "EASING" | "NEUTRAL" | "TIGHTENING"
└── composite_score: 0–100 (weighted regime strength)
```

---

## Control Specifications

### C2.1: Bitcoin Dominance Regime

**Purpose:** Detect capital rotation between BTC and altcoins.

**Variables:**
- `btc_dominance` (%)
- `btc_dominance_sma_20d`
- `btc_dominance_sma_60d`

**Rules:**

```python
def bitcoin_regime(btc_dom: float, sma20: float, sma60: float) -> str:
    if btc_dom > sma60 and sma60 > sma20:
        return "BTC_ACCUMULATION"  # BTC gaining dominance
    elif btc_dom < sma60 and sma60 < sma20:
        return "ALT_ROTATION"       # Alts gaining
    else:
        return "BALANCED"           # Transition or consolidation
```

**Proof Level:** C (API historical, no retroactive revisions expected)  
**Data Source:** CoinGecko `get_global_market()` (BTC dominance)  
**Update Frequency:** Daily  

---

### C2.2: Liquidity Regime (Funding Rates)

**Purpose:** Detect overleverage and liquidation risk.

**Variables:**
- `funding_rate_8h` (%)
- `funding_rate_moving_avg_7d` (%)
- `open_interest_change_24h` (%)

**Rules:**

```python
def liquidity_regime(funding: float, funding_avg: float, oi_change: float) -> str:
    if funding > 0.10 and funding > funding_avg:
        return "TIGHT"              # Longs overleveraged
    elif funding < -0.10 and funding < funding_avg:
        return "ABUNDANT"           # Shorts overleveraged
    else:
        return "NORMAL"             # Balanced leverage
```

**Proof Level:** C (real-time API, no historical archive)  
**Data Source:** Binance `exchangeInfo` → funding rates API  
**Update Frequency:** 8-hourly  
**Backtest Challenge:** Historical funding rates difficult to obtain; use proxy (volatility ≈ liquidation risk)  

---

### C2.3: Risk-On / Risk-Off Detection

**Purpose:** Detect investor sentiment shift (equity/crypto correlation).

**Variables:**
- `btc_spy_correlation_7d` (correlation coefficient)
- `vtix_implied_volatility` (%)
- `eth_btc_ratio` (ETH price / BTC price)

**Rules:**

```python
def risk_appetite(corr: float, vix: float, eth_btc: float) -> float:
    """
    Returns risk_appetite score [0, 1].
    0 = risk-off (BTC down, VIX up)
    1 = risk-on (BTC up, VIX low)
    """
    correlation_score = max(0, min(1, (corr + 1) / 2))  # [-1,1] → [0,1]
    volatility_score = max(0, 1 - (vix / 100))          # VIX inverted
    eth_score = max(0, min(1, eth_btc / 0.1))           # ETH/BTC ratio
    
    return (0.4 * correlation_score + 
            0.3 * volatility_score + 
            0.3 * eth_score)
```

**Proof Level:** C (daily/weekly aggregates)  
**Data Source:** CoinGecko (BTC, ETH), TradingView/TipRanks (VIX proxy)  
**Update Frequency:** Daily  

---

### C2.4: Macro Conditions

**Purpose:** Detect Fed policy regime, inflation, money supply growth.

**Variables:**
- `dxy_level` (US Dollar Index)
- `us10y_yield` (%)
- `cpi_yoy` (% year-over-year)
- `m2_growth_yoy` (%)

**Rules:**

```python
def macro_regime(dxy: float, us10y: float, cpi: float, m2: float) -> str:
    """
    Maps macro indicators to policy regime.
    """
    if us10y > 4.5 and dxy > 105:
        return "TIGHTENING"  # High rates, strong USD
    elif cpi > 4.0:
        return "EASING_PRESSURE"  # Still elevated
    elif m2 > 5.0:  # YoY growth
        return "ACCOMMODATIVE"
    else:
        return "NEUTRAL"
```

**Proof Level:** A (published by central banks, versioned releases)  
**Data Source:** FRED (Federal Reserve Economic Data), TradingView (macro indicators)  
**Update Frequency:** Monthly (CPI, M2), daily (DXY, US10Y)  
**Latency:** CPI lag ~10 days; M2 data typically 1 week old  

---

### C2.5: ETF Flow Analysis

**Purpose:** Detect institutional capital rotation.

**Variables:**
- `spy_etf_flow_daily` (net inflow, millions USD)
- `ivv_etf_flow_daily`
- `gld_etf_flow_daily`

**Rules:**

```python
def etf_regime(spy_flow: float, gld_flow: float) -> str:
    """
    Detect capital rotation between equities and gold (risk-on vs risk-off).
    """
    if spy_flow > 50 and gld_flow < -20:
        return "EQUITIES_INFLOW"
    elif spy_flow < -50 and gld_flow > 20:
        return "SAFE_HAVEN_INFLOW"
    else:
        return "NEUTRAL_FLOWS"
```

**Proof Level:** C (ETF flow data from providers, limited retroactive revisions)  
**Data Source:** Morningstar, ETF.com (if connector available)  
**Update Frequency:** Daily  
**Backtest Challenge:** Historical ETF flows not always available; estimate from price/volume  

---

### C2.6: Open Interest Regime

**Purpose:** Detect positioning changes in futures markets.

**Variables:**
- `btc_oi_total` (Bitcoin open interest, USD)
- `btc_oi_change_24h` (%)
- `oi_shorts_vs_longs` (ratio)

**Rules:**

```python
def oi_regime(oi_change: float, shorts_ratio: float) -> str:
    if oi_change > 10 and shorts_ratio > 0.6:
        return "SHORT_ACCUMULATION"
    elif oi_change > 10 and shorts_ratio < 0.4:
        return "LONG_ACCUMULATION"
    elif oi_change < -10:
        return "LIQUIDATION_CYCLE"
    else:
        return "STABLE_OI"
```

**Proof Level:** C (futures data real-time, some revision possible)  
**Data Source:** Binance Futures API, Bybit API  
**Update Frequency:** Real-time, aggregated 4h/daily  
**Latency:** Derivatives data typically 24h behind spot  

---

### C2.7: Regime Composite Score

**Purpose:** Unified regime signal combining all controls.

**Formula:**

```python
def composite_regime_score(
    btc_dom_regime: str,
    liquidity: str,
    risk_appetite: float,
    macro: str,
    etf_flows: str,
    oi_regime: str
) -> int:
    """
    Returns composite score [0, 100].
    0 = extreme bear regime
    50 = neutral
    100 = extreme bull regime
    """
    scores = {
        "BTC_ACCUMULATION": 70,
        "ALT_ROTATION": 30,
        "BALANCED": 50,
        "TIGHT": 20,  # Liquidation risk, bearish
        "NORMAL": 50,
        "ABUNDANT": 70,  # Easy money, bullish
        "TIGHTENING": 20,
        "NEUTRAL": 50,
        "EASING_PRESSURE": 30,
        "ACCOMMODATIVE": 70,
        "EQUITIES_INFLOW": 70,
        "SAFE_HAVEN_INFLOW": 30,
        "SHORT_ACCUMULATION": 30,
        "LONG_ACCUMULATION": 70,
        "LIQUIDATION_CYCLE": 40,
        "STABLE_OI": 50,
    }
    
    # Weighted average
    btc_dom_score = scores.get(btc_dom_regime, 50)
    liquidity_score = scores.get(liquidity, 50)
    macro_score = scores.get(macro, 50)
    etf_score = scores.get(etf_flows, 50)
    oi_score = scores.get(oi_regime, 50)
    
    # Risk appetite as direct score [0, 100]
    risk_score = int(risk_appetite * 100)
    
    composite = (
        0.20 * btc_dom_score +
        0.15 * liquidity_score +
        0.25 * risk_score +      # Highest weight
        0.20 * macro_score +
        0.10 * etf_score +
        0.10 * oi_score
    )
    
    return int(round(composite))
```

**Output:**

```python
{
    "timestamp": "2026-10-05T00:00:00Z",
    "btc_dominance_regime": "BTC_ACCUMULATION",
    "liquidity_regime": "NORMAL",
    "risk_appetite": 0.72,
    "macro_regime": "NEUTRAL",
    "etf_flows": "EQUITIES_INFLOW",
    "oi_regime": "LONG_ACCUMULATION",
    "composite_score": 63,
    "regime_state": "BULL",  # Derived from composite_score thresholds
}
```

---

## Data Requirements

### Real-Time / Daily

| Variable | Source | Frequency | Backtest Available? |
|----------|--------|-----------|-------------------|
| BTC Dominance | CoinGecko | Daily | ✅ Yes (2013+) |
| ETH Price | CoinGecko | Daily | ✅ Yes (2015+) |
| BTC/USD | Binance / CoinGecko | Daily | ✅ Yes (2013+) |
| Funding Rates | Binance Futures | 8h | ⚠️ Limited (90d lookback) |
| Open Interest | Binance / Bybit | Daily | ⚠️ Limited (varies) |
| DXY | TradingView / FRED | Daily | ✅ Yes (2011+) |
| US10Y Yield | FRED / TradingView | Daily | ✅ Yes (decades) |
| CPI YoY | FRED | Monthly | ✅ Yes (decades) |
| M2 Growth | FRED | Weekly | ✅ Yes (decades) |
| ETF Flows | Morningstar / ETF.com | Daily | ⚠️ Limited (recent years) |
| SPY / GLD Prices | TradingView / Twelve Data | Daily | ✅ Yes (2004+) |

---

## Testing Strategy (TDD)

### Test Categories

**T2.1: Bitcoin Dominance Regime Tests**
```
test_btc_dom_accumulation()  # BTC > SMA60 > SMA20
test_btc_dom_alt_rotation()  # BTC < SMA60 < SMA20
test_btc_dom_balanced()       # Mixed conditions
```

**T2.2: Liquidity Regime Tests**
```
test_tight_liquidity()       # Funding > 0.10%, avg positive
test_abundant_liquidity()    # Funding < -0.10%, avg negative
test_normal_liquidity()      # Funding near 0
```

**T2.3: Risk Appetite Tests**
```
test_risk_on()              # BTC-SPY corr > 0, VIX low
test_risk_off()             # BTC-SPY corr < 0, VIX high
test_transition()           # Mixed signals
```

**T2.4-T2.6: Remaining Controls (similar pattern)**

**T2.7: Composite Score Tests**
```
test_bull_composite()       # Score > 70
test_bear_composite()       # Score < 30
test_neutral_composite()    # 40-60 range
test_weighted_averaging()   # Verify formula
```

**T2.8: Integration Tests**
```
test_full_regime_calculation()      # All controls → composite
test_regime_state_derivation()      # Score → regime label
test_timestamp_propagation()         # Metadata preservation
```

### Test Data Strategy

Use **fixture-based mock data** (no P0.1 dependency):

```python
@pytest.fixture
def sample_btc_dominance():
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "btc_dom": 52.5,
        "sma20": 51.0,
        "sma60": 50.0,
    }

def test_btc_dom_accumulation(sample_btc_dominance):
    regime = bitcoin_regime(
        sample_btc_dominance["btc_dom"],
        sample_btc_dominance["sma20"],
        sample_btc_dominance["sma60"]
    )
    assert regime == "BTC_ACCUMULATION"
```

---

## Implementation Phases

### Phase 1: Core Engine (Week 1)

- [ ] Create `src/layers/layer2_regime/` directory
- [ ] Implement control classes (C2.1–C2.7)
- [ ] Write unit tests (T2.1–T2.7)
- [ ] Implement composite score calculation
- [ ] All tests PASS
- [ ] Commit: "Implement Layer 2 core regime engine"

### Phase 2: Data Connectors (Week 2)

- [ ] CoinGecko connector (BTC dominance, prices)
- [ ] TradingView / FRED connector (macro indicators)
- [ ] Binance Futures connector (funding rates, OI)
- [ ] Integration tests with real API calls
- [ ] Mock fallback for offline development
- [ ] Commit: "Add Layer 2 data connectors"

### Phase 3: Historical Regime Replay (Week 3)

- [ ] Load historical CoinGecko data → compute regimes
- [ ] Validate regimes against known market events (e.g., 2021 bull peak, 2022 bear bottom)
- [ ] Create regime timeline visualization
- [ ] Backtest regime changes vs price movements
- [ ] Document discovered regime patterns
- [ ] Commit: "Historical regime analysis and validation"

### Phase 4: Integration with Layer 1 & P0.1

- [ ] Wire Layer 2 outputs to Layer 1 snapshot manifests
- [ ] Combine with real P0.1 Binance data (once available)
- [ ] Validate PIT compliance (availability_time ≤ decision_time)
- [ ] Prepare for Layer 3 (BCE module) integration

---

## Success Criteria (P2 PASS)

- [x] All 8 control specifications documented
- [ ] 30+ unit tests written and PASSING
- [ ] Composite score formula implemented and tested
- [ ] Integration tests with mock data PASSING
- [ ] Data connectors created (with fallbacks)
- [ ] Historical regime replay working
- [ ] Regime patterns documented
- [ ] Ready for P0.1 integration

---

## Governance & Constraints

### Mandatory Rules

1. **TDD First:** Tests written before implementation
2. **No Hardcoded Assumptions:** Document every data assumption
3. **PIT Compliance:** All regime outputs include `timestamp` and `pit_status="UNVERIFIED"` (until P0.1 real data)
4. **Immutable Regime Records:** Once computed, regime_state values are logged immutably
5. **No Forward-Looking:** Regime must use only data available as-of decision_time

### No Forward-Looking Rule

**Invalid (uses future data):**
```python
# ❌ WRONG: Computing regime on 2026-10-10 using 2026-10-15 data
regime = compute_regime(
    timestamp="2026-10-10",
    dxy=current_dxy,  # Today's DXY (too fresh!)
    us10y=future_us10y  # ❌ Future data
)
```

**Valid (uses only past data):**
```python
# ✅ CORRECT: Computing regime on 2026-10-10 using ≤2026-10-09 data
regime = compute_regime(
    timestamp="2026-10-10",
    dxy=yesterday_dxy,     # 2026-10-09 close
    us10y=yesterday_us10y  # 2026-10-09 close
)
```

---

## References

- **Layer 1 Infrastructure:** `src/layers/layer1_data/`
- **ADR-035:** `docs/ADR-035_DATA_SOURCE_ARCHITECTURE.md`
- **CLAUDE.md:** Project governance rules
- **P0.1 Blueprint:** `docs/P0.1_BINANCE_DATA_COLLECTION_BLUEPRINT.md`

---

## Document Status

**Created:** 2026-10-05 (Post-gate decision, Layer 2 kickoff)  
**Status:** SPECIFICATION  
**Authorization:** GO Layer 2 (2026-10-05)  
**Implementation:** Ready to begin Phase 1
