# Daily Data Requirement for RRP Validation

**Status:** Identified blocking constraint  
**Date:** 2026-09-25  

---

## Summary

RRP validation framework requires **daily OHLCV data** (730+ candles for 2 years). Public API sources return aggregated data:
- TipRanks: Returns monthly or weekly aggregates when request window >90 days
- CoinGecko: Free tier limited to recent data; Pro features unavailable in network environment
- Binance: API accessible but rate-limited for large historical ranges

**Barrier:** Data source granularity, not framework design.

---

## Why Daily Data Required

### Validation Window Calculation
- Stage 1 (PIT Audit): Analyzes signal correlations over 90+ day windows
- Stage 4 (Baseline): Computes Information Coefficient on 30-day forward returns
- Stage 6 (WFV): Daily walk-forward loop from day 90 to day 150

### With Monthly Data (25 candles / 2 years)
- Window size: 1 month = 1 candle (too small)
- Stage results: 0 samples, FAIL
- Analysis: Cannot construct 90-day analysis window with only monthly granularity

### With Weekly Data (27 candles / 6 months)
- Window size: 1 week = 1 candle (insufficient)
- Stage results: Limited samples, unreliable
- Analysis: Minimum 13 weeks required for 90-day window; have 27 weeks (marginal)

### With Daily Data (730 candles / 2 years)
- Window size: 90 days = 90 candles (correct)
- Stage results: Full distribution of results
- Analysis: Proper temporal analysis window

---

## Data Source Options

### Option 1: CoinGecko Daily Endpoint (Preferred)
```python
# URL: https://api.coingecko.com/api/v3/coins/{id}/market_chart
# Parameters: vs_currency=usd, days=730, interval=daily
# Returns: Daily OHLCV (no aggregation)
# Status: Blocked by network proxy (401 Unauthorized)
# Solution: Use authenticated CoinGecko Pro or VPN
```

### Option 2: Binance Public API Daily
```python
# Endpoint: GET /api/v3/klines
# Symbol: BTCUSDT, ETHUSDT, SOLUSDT, AVAXUSDT
# Interval: 1d (daily)
# Returns: True OHLCV + volume
# Status: Works (tested in real_data_collector.py)
# Note: Rate-limited; requires pagination for 2-year history
```

### Option 3: Alternative Crypto Data Providers
- Kraken REST API (daily OHLCV)
- Poloniex REST API (daily candles)
- Cryptocurrency data specialists (daily feeds)

### Option 4: Purchase/Subscribe
- Premium data vendors (Bloomberg, RefinitivIntelligence, Tiingo)
- Paid crypto data feeds (Messari, Glassnode)

---

## Recommended Path

### Short Term (Next Sprint)
**Implement Binance daily OHLCV fetcher:**
1. Modify `real_data_collector.py`: Add `fetch_binance_daily_ohlcv()` with pagination
2. Fetch 730 daily candles per symbol
3. Save to `./real_market_data/` with provenance
4. Rerun validation stages 1, 4, 6

**Effort:** 2-4 hours (API integration + testing)

### Medium Term
**Set up automated daily data pipeline:**
- Cron job to fetch daily updates from Binance
- Store in DuckDB or Parquet
- Snapshot immutability versioning
- Ready for continuous RRP monitoring (post-Layer 8)

### Long Term
**Evaluate premium data:**
- If Binance API proves insufficient (rate limits, reliability)
- Migrate to professional data provider
- Maintain cost tracking

---

## Current State

✅ **Framework:** Ready for daily data  
✅ **Architecture:** Designed for 730+ daily candles  
✅ **Test Data:** Monthly and weekly samples available  
⏳ **Blocking:** Data source granularity (public API limitations)  

### Next Actions
1. Implement Binance daily OHLCV fetcher
2. Fetch data for BTC, ETH, SOL, AVAX
3. Run validation stages 1, 4, 6
4. Publish VALIDATED ALPHA or NEEDS_ITERATION decision

---

## Governance Impact

- **Layer 8 Status:** BLOCKED (no change)
- **Invariants:** Maintained (immutability, no tuning, no Layer 8 consumption)
- **Validation Gate:** Awaiting executable real data
- **Decision Memo:** RESEARCH-CANDIDATE stands until real data validation complete

---

## Files Updated

- `real_data_collector.py` — Multi-source collector, Binance ready
- `real_data_rrp_validation.py` — Stages 1, 4, 6 implemented
- `run_real_data_validation.py` — Orchestrator
- Real market data directory — Monthly (25) + weekly (27) samples

---

## Quota Status

- TipRanks calls: 8 of 10 monthly calls used (2 remaining for period)
- Binance public API: No quota (unlimited)
- Recommendation: **Use Binance for daily data**

---

**Owner:** IGWT-PF26 Real Data Validation Pipeline  
**Blocker Type:** Technical (data source availability)  
**Severity:** Medium (blocks VALIDATED ALPHA decision, not architecture)  
**Resolution Path:** Clear (implement Binance daily fetcher)
