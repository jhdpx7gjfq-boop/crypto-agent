# Phase 8: Dashboard Layer Specification
**IGWT-PF26 Quant Intelligence Operating System**

**Phase:** 8 of 9  
**Timeline:** Jan 2027 - Mar 2027 (12 weeks, upon RRP VALIDATED_ALPHA)  
**Predecessor:** RRP Alpha Validation (Phase 7) ✅ VALIDATED_ALPHA  
**Successor:** Phase 9 Agent IA Research Assistant  
**Input:** All Layers 1-7 outputs, RRP alpha model  
**Output:** Production-ready iPhone-native dashboard  
**Authority:** Human (read-only, research tool)  

---

## Executive Summary

Phase 8 integrates all prior IGWT-PF26 layers into a unified research dashboard for human decision-makers.

**Purpose:** Single pane of glass for quant intelligence + RRP signals + narrative analysis + risk assessment  
**Format:** iPhone-native, mobile-first  
**Scope:** Read-only research interface (no execution)  
**Users:** Crypto quant researchers, portfolio managers  

---

## 1. Dashboard Architecture

### 1.1 Core Principles

✅ **Mobile-first:** iPad/iPhone native (React Native or native iOS)  
✅ **Read-only:** Zero execution capability, zero order placement  
✅ **Real-time:** 15-minute update cadence (market data) + daily (RRP scores)  
✅ **Human-gated:** All alerts require human review before action  
✅ **Traceable:** Every decision logged with timestamp + rationale  
✅ **Accessible:** Offline mode for essential views  

### 1.2 Information Architecture

```
Dashboard Root
├─ Market Regime Monitor (Layer 2)
│  ├─ Bitcoin dominance (real-time)
│  ├─ DXY index (real-time)
│  ├─ US10Y yield (daily)
│  ├─ Funding rates (hourly)
│  ├─ ETF flows (daily)
│  └─ Regime score (bear/neutral/bull)
│
├─ Revival Radar Pipeline (RRP - Layer 7 Integration)
│  ├─ Top 20 resurrection candidates (daily)
│  │  ├─ Coin name + RRP score (0-100)
│  │  ├─ Component breakdown (volume, narrative, capital, momentum)
│  │  ├─ Validation performance (AUC ± CI)
│  │  ├─ Historical context (dormancy start, duration)
│  │  └─ Go/no-go decision support
│  │
│  ├─ RRP Score Distribution (histogram)
│  │  ├─ By coin size (large/mid/small)
│  │  ├─ By market regime
│  │  ├─ By resurrection type (quick/slow)
│  │  └─ Statistical overview
│  │
│  └─ Monitoring Dashboard
│     ├─ Monthly AUC vs baseline
│     ├─ Component health (data availability)
│     ├─ Alert thresholds (red/yellow/green)
│     └─ Governance gates (validation phase)
│
├─ Feature Store Dashboard (Layer 4)
│  ├─ Top coins by narrative momentum
│  ├─ Sector rotation heatmap
│  ├─ Capital flow analysis (inflow/outflow)
│  ├─ Adoption metrics (addresses, transactions)
│  └─ Volatility regime (VIX-like)
│
├─ Wyckoff BCE Engine (Layer 3)
│  ├─ Active accumulation zones (bottom confirmation ≥5/6)
│  │  ├─ Coin name + BCE score
│  │  ├─ Wyckoff structure breakdown
│  │  ├─ Volume analysis
│  │  ├─ Smart money accumulation signals
│  │  └─ Risk/reward estimate (target, stop)
│  │
│  └─ Pending zones (BCE 3-4, watch list)
│
├─ X20 Opportunity Engine (Layer 5)
│  ├─ High-conviction candidates (X20+ potential)
│  │  ├─ Coin name + X20 score (0-100)
│  │  ├─ Narrative strength (sector, adoption, AI)
│  │  ├─ Fundamental score (team, tokenomics, revenue)
│  │  ├─ Quantitative strength (momentum, volatility, LIQ)
│  │  ├─ Risk/reward (target mcap, stop loss)
│  │  └─ Decision checklist (ready to buy?)
│  │
│  └─ Ranked pipeline (top 20 by score)
│
├─ NARM-P+ Narrative Adoption (Layer 6)
│  ├─ Hot narratives (BTC, ETH, RWA, DeFi, Infrastructure, AI)
│  │  ├─ Narrative strength score (0-100)
│  │  ├─ Adoption curve (early/growth/mature)
│  │  ├─ Capital rotation (% AUM moving in)
│  │  ├─ Key drivers (news, events, hype)
│  │  └─ Risk assessment (bubble risk, momentum exhaustion)
│  │
│  └─ Narrative rotation timeline (Gartner-like hype cycle)
│
├─ RPM/RCM Rotation Confirmation (Layer 7)
│  ├─ Capital flow heatmap (which sectors, which sizes?)
│  ├─ Relative strength rankings
│  │  ├─ By narrative (Bitcoin vs Ethereum vs Solana vs etc)
│  │  ├─ By size (large cap vs mid vs small)
│  │  └─ By sector (DeFi vs Layer 1 vs Infrastructure)
│  │
│  ├─ Rotation signals (high confidence)
│  │  ├─ "Capital flowing INTO X, out of Y" (rationale)
│  │  ├─ Strength (confidence 0-100)
│  │  ├─ Expected duration (weeks/months)
│  │  └─ Entry/exit guidance
│  │
│  └─ Walk-forward performance (30/60/90-day lookback)
│
├─ Portfolio Cockpit
│  ├─ Holdings overview
│  │  ├─ Current positions (coin, size, entry price)
│  │  ├─ P&L (unrealized, realized)
│  │  ├─ Allocation (% per coin, sector, narrative)
│  │  └─ Risk metrics (max DD, Sharpe, sortino)
│  │
│  ├─ Scenario analyzer (read-only)
│  │  ├─ "If Bitcoin goes to $X, portfolio becomes Y"
│  │  ├─ "If this rotation plays out, expected gain Z%"
│  │  └─ Sensitivity analysis (price, regime, vol)
│  │
│  └─ Alerts + decisions
│     ├─ Position in bottom confirmation zone (BCE ≥5/6)?
│     ├─ Rotation signal triggered (RPM strength >75)?
│     ├─ X20 opportunity appeared (target mcap <$500M)?
│     └─ Risk threshold crossed (max DD, allocation limit)?
│
├─ Research Assistant (Phase 9 Integration)
│  ├─ Anomaly reports (auto-generated)
│  │  ├─ Unusual volume spike on X (catalyst?)
│  │  ├─ Capital flow reversal into Y
│  │  ├─ Sentiment surge on Z (real or bot-driven?)
│  │  └─ Governance update on W (roadmap?)
│  │
│  ├─ Comparison scenarios (human-requested)
│  │  ├─ "Compare 2017 vs 2021 vs 2024 cycle phases"
│  │  ├─ "Is this narrative stronger than that one?"
│  │  └─ "What happened last time capital flowed like this?"
│  │
│  ├─ Hypothesis challenges
│  │  ├─ "You think X, but data shows Y — reconsider?"
│  │  └─ "Confirmation bias risk on Z narrative?"
│  │
│  └─ Auto-research (background)
│     ├─ Market updates (daily digest)
│     ├─ Governance changes (weekly)
│     ├─ Tokenomics events (unlock calendars)
│     └─ Risk warnings (regulatory, technical)
│
└─ Settings & Governance
   ├─ Alerts configuration (thresholds, channels)
   ├─ View preferences (day/night mode, refresh rate)
   ├─ Data source configuration (CoinGecko, Glassnode, etc)
   ├─ Monitoring status (RRP health, Layer data freshness)
   └─ Audit trail (decision log, export)
```

---

## 2. UI/UX Specifications

### 2.1 Core Views (iPhone-native)

#### View 1: Market Regime + Opportunity Dashboard
**Default/Home View**

```
┌─────────────────────────────────┐
│ IGWT-PF26 QUANT INTELLIGENCE    │ [Settings]
├─────────────────────────────────┤
│ 📊 MARKET REGIME                │
│ Status: BULL (DXY↓, BTC.D↑)      │
│ Confidence: 78/100              │
│ Last update: 2 min ago          │
├─────────────────────────────────┤
│ 🎯 TOP 3 OPPORTUNITIES          │
│                                  │
│ 1. [Coin A]  RRP: 87  BUY?     │
│    Volume↑ Narrative↑ Flow↑     │
│    Target: $50M  Risk: Medium   │
│    ✅ Go (if positions freed)   │
│                                  │
│ 2. [Coin B]  BCE: 6/6  ACQ     │
│    Bottom conf. 92/100          │
│    Accumulated 2.3M usd         │
│    ⚠️ Wait for breakout         │
│                                  │
│ 3. [Coin C]  X20: 84  UPR      │
│    Market cap: $45M → $1B pot   │
│    Team: A+ Narrative: Strong   │
│    ⚠️ Early stage, high risk    │
│                                  │
├─────────────────────────────────┤
│ ⚡ ALERTS (3 new)               │
│ • Capital flowing into DeFi     │
│ • Solana narrative accelerating │
│ • [Coin D] hit max DD threshold │
└─────────────────────────────────┘
```

#### View 2: Revival Radar Pipeline (RRP)
**Dedicated RRP Monitoring**

```
┌─────────────────────────────────┐
│ 🔮 REVIVAL RADAR PIPELINE       │
├─────────────────────────────────┤
│ Model: RRP Alpha 1.0.0          │
│ Validation: ✅ VALIDATED_ALPHA  │
│ Last update: 1h ago             │
│                                  │
│ MONTHLY PERFORMANCE             │
│ AUC: 0.82 (baseline: 0.72)      │
│ Status: ✅ HEALTHY              │
│ Confidence: [●●●●●○] 95% CI    │
│                                  │
├─ TOP 20 RESURRECTIONS ──────────┤
│                                  │
│ Rank │ Coin      │ Score │ Action
│ ────┼───────────┼───────┼───────
│  1  │ [Coin X]  │  92   │ → BUY?
│  2  │ [Coin Y]  │  88   │ → WATCH
│  3  │ [Coin Z]  │  85   │ → RESEARCH
│  ... │ ...      │ ...   │ ...
│
├─ COMPONENT HEALTH ──────────────┤
│ ✅ Volume Trend: online          │
│ ✅ Narrative Score: online       │
│ ✅ Capital Flow: online          │
│ ✅ Momentum: online              │
│                                  │
└─ Next rebalance: 2024-12-20    │
└─────────────────────────────────┘
```

#### View 3: Portfolio Cockpit
**Position Management + Scenario Analysis**

```
┌─────────────────────────────────┐
│ 💼 PORTFOLIO COCKPIT            │
├─────────────────────────────────┤
│ Holdings: 3 positions           │
│ Total AUM: $850K (est)          │
│ P&L YTD: +47% (realized)        │
│ Max DD: -12% (acceptable)       │
│                                  │
│ POSITIONS:                       │
│ • Bitcoin: 0.25 BTC → $12.5K    │
│   Entry: $45K, current: $50K    │
│   Conviction: Hold (BCE 5/6)    │
│                                  │
│ • Solana: 100 SOL → $8K         │
│   Entry: $80, current: $80      │
│   Conviction: Hold (narrative)  │
│   Risk: Break below $75?        │
│                                  │
│ • [Alt]: 100K coin → $2.5K      │
│   Entry: $0.025, current: $0.025
│   Conviction: Monitor (X20 pot) │
│                                  │
├─ SCENARIO ANALYSIS ─────────────┤
│ "If BTC → $60K: portfolio +15%" │
│ "If rotation out: -8%"          │
│ "If X20 hits target: +120%"    │
│                                  │
└─────────────────────────────────┘
```

#### View 4: Research Anomalies
**Auto-generated Insights (Phase 9)**

```
┌─────────────────────────────────┐
│ 🔬 RESEARCH INSIGHTS            │
├─────────────────────────────────┤
│ Generated: 24h ago (by AI Copilot
│                                  │
│ 🔴 CRITICAL ANOMALY              │
│ [Coin X] volume spike 50x        │
│ Reason: Airdrop announcement     │
│ Action: Monitor for breakout     │
│                                  │
│ 🟡 WATCH PATTERN                 │
│ Capital flowing OUT of DeFi      │
│ Into: Layer 1s (SOL, SUI)       │
│ Strength: 72/100                 │
│ Expected duration: 2-4 weeks    │
│                                  │
│ ℹ️  INFO UPDATE                  │
│ [Coin Y] unlock event tomorrow  │
│ Risk: Post-unlock dumping        │
│ Mitigation: Reduce position 25%  │
│                                  │
│ 🎯 HYPOTHESIS CHALLENGE          │
│ You think [Narrative] is strong  │
│ But: Adoption curve plateauing   │
│ Reconsider: Is peak approaching? │
│                                  │
└─────────────────────────────────┘
```

#### View 5: Settings & Audit Trail
**Configuration + Governance**

```
┌─────────────────────────────────┐
│ ⚙️  SETTINGS & GOVERNANCE        │
├─────────────────────────────────┤
│ ALERTS CONFIGURATION            │
│ ☑ RRP score >80: enabled        │
│ ☑ BCE score ≥5/6: enabled       │
│ ☑ Rotation signal >75: enabled  │
│ ☑ Position risk: enabled        │
│ ☑ Narrative shift: enabled      │
│                                  │
│ DATA SOURCES                    │
│ • CoinGecko: ✅ online (now)    │
│ • Glassnode: ✅ online (5m)     │
│ • Crypto.com: ✅ online (1m)    │
│ • Sentiment: ✅ online (1h)     │
│                                  │
│ AUDIT TRAIL (last 10)            │
│ 2024-12-19 14:30: Viewed RRP 87  │
│ 2024-12-19 13:15: Marked bought  │
│ 2024-12-19 12:00: Reviewed scenario
│ 2024-12-18 22:30: Set alert thresh
│ ...                              │
│                                  │
│ 📊 Model Status: VALIDATED_ALPHA │
│ Last audit: 2026-12-20          │
│ Next audit: 2027-03-20          │
│                                  │
└─────────────────────────────────┘
```

---

## 3. Data Integration Layer

### 3.1 Data Sources & Refresh Rates

| Layer | Data Source | Update | Latency | Quality |
|-------|-------------|--------|---------|---------|
| **1: Regime** | Binance, CoinGecko, macro APIs | 15m | <2m | ≥99% |
| **2: Market** | Glassnode, Nansen, Arkham | Daily | <2h | ≥95% |
| **3: BCE** | OHLCV, on-chain | 1h | <5m | ≥99% |
| **4: X20** | Fundamental + quant | Daily | <2h | ≥90% |
| **5: NARM-P+** | Sentiment, adoption, capital | Daily | <4h | ≥85% |
| **6: RPM/RCM** | Capital flows, relative strength | Daily | <2h | ≥90% |
| **7: RRP** | Component scores (locked) | Daily | <6h | ≥95% |
| **9: Anomalies** | AI-generated | Daily | <4h | Context-dependent |

### 3.2 Real-Time Data Pipeline

```
Market Data Sources
├─ CoinGecko API (public)
│  ├─ Price (15m)
│  ├─ Volume (15m)
│  ├─ Market cap (15m)
│  └─ Sentiment (daily)
│
├─ Binance (public)
│  ├─ Funding rates (real-time)
│  ├─ Open interest (real-time)
│  └─ Liquidations (real-time)
│
├─ Glassnode (subscribed)
│  ├─ On-chain metrics (daily)
│  ├─ Exchange flows (daily)
│  └─ Holder distribution (daily)
│
└─ Custom Layers 1-7 (internal)
   ├─ BCE scores (1h)
   ├─ X20 scores (daily)
   ├─ NARM scores (daily)
   ├─ RPM signals (daily)
   └─ RRP scores (daily, locked model)

Pipeline Architecture:
- Kafka (streaming): Price, volume, funding (15m cadence)
- DuckDB (analytical): Daily snapshots (NARM, RPM, X20, RRP)
- Cache (Redis): Real-time views (<1s refresh)
- Archive (Parquet): Historical for backtest/audit
```

---

## 4. Feature Specifications

### 4.1 Go/No-Go Decision Support (Critical)

**For every opportunity shown:**

```python
decision_framework = {
    "coin_id": "solana",
    "opportunity_type": "RRP_resurrection",
    
    "go_criteria": [
        {
            "name": "RRP Score",
            "threshold": "≥80",
            "actual": "87",
            "status": "✅ PASS"
        },
        {
            "name": "Market Regime",
            "threshold": "BULL or NEUTRAL",
            "actual": "BULL",
            "status": "✅ PASS"
        },
        {
            "name": "BCE Accumulation",
            "threshold": "≥4/6 (supportive)",
            "actual": "3/6",
            "status": "⚠️ WEAK"
        },
        {
            "name": "Capital Flow Trend",
            "threshold": "Positive or stable",
            "actual": "Positive",
            "status": "✅ PASS"
        }
    ],
    
    "decision": "GO (3/4 criteria met, 1 weak)",
    "risk_level": "MEDIUM",
    "suggested_position": "1-2% of AUM (pilot)",
    "stop_loss": "$24 (if entry $30)",
    "target": "$150 (500% gain)",
    "expected_holding": "6-12 months",
    
    "rationale": "RRP alpha validated (AUC 0.82). Resurrection signal strong. Market regime supportive. Minor weakness: no strong accumulation yet. Recommendation: pilot position, scale if breakout confirmed.",
    
    "decision_trail": [
        "2024-12-19 14:30 — Reviewed RRP score 87",
        "2024-12-19 14:35 — Checked market regime (BULL)",
        "2024-12-19 14:40 — Noted weak BCE (3/6)",
        "2024-12-19 14:45 — DECISION: GO with 1% pilot"
    ]
}
```

### 4.2 Alerts System

**Three-tier alert system:**

```
TIER 1: RESEARCH (passive notification)
- New RRP opportunity >80 score
- New BCE accumulation zone ≥5/6
- Capital rotation signal confirmed
- Narrative shift detected
→ Action: Human reviews, decides

TIER 2: DECISION (active notification + suggested action)
- Your position in bottom confirmation (BCE ≥5/6)
- Your holding crosses price target
- Rotation signal ends (exit guidance?)
- Narrative you're holding weakens
→ Action: Review rationale, confirm decision

TIER 3: CRITICAL (immediate escalation)
- Position P&L hits max drawdown threshold
- RRP monthly AUC drops >0.05 (model issues)
- Data source unavailable >24h (pipeline broken)
- Regulatory warning on position
→ Action: Immediate human review required
```

### 4.3 Offline Mode

**Essential views available without internet:**

- ✅ Current holdings (last synced)
- ✅ P&L calculations (last synced)
- ✅ Historical charts (7-day cache)
- ✅ Decision log (audit trail)
- ✅ Scenario calculator (static)
- ❌ Real-time data (disabled)
- ❌ Research anomalies (require AI)
- ❌ Alerts (require live data)

---

## 5. Performance Requirements

### 5.1 Speed Standards

| View | Load Time | Refresh Rate | Latency Target |
|------|-----------|--------------|-----------------|
| Market Regime | <500ms | 15m | <2m |
| RRP Scores | <1s | Daily | <6h |
| BCE Zones | <800ms | 1h | <5m |
| X20 Opportunities | <1.5s | Daily | <2h |
| Portfolio Cockpit | <400ms | 5m | <2m |
| Scenario Sim | <2s | On-demand | Instant |
| Anomalies | <1s | Daily | <4h |

### 5.2 Storage Requirements

- **Local cache:** 50 MB (daily snapshots)
- **Historical (1 year):** 500 MB (Parquet)
- **Model artifact:** 100 MB (RRP serialized)
- **Total device:** <1 GB

### 5.3 Connectivity

- **Minimum bandwidth:** 1 Mbps for sync
- **Fallback:** Offline mode if unavailable >30s
- **Sync strategy:** Differential updates (only changed data)

---

## 6. Security & Privacy

### 6.1 Data Handling

✅ **No sensitive data stored locally:** Portfolio positions encrypted at rest  
✅ **API keys:** Environment-based (never in client)  
✅ **Decision log:** Hashed user identifier (privacy)  
✅ **Audit trail:** Immutable (tamper-evident)  

### 6.2 Authentication

- Biometric (Face/Touch ID) for unlock
- OAuth for CoinGecko/Glassnode API (server-side)
- No passwords stored client-side

### 6.3 Compliance

✅ **Read-only enforcement:** No execution capability  
✅ **Audit trail:** Every view + decision logged  
✅ **Model governance:** VALIDATED_ALPHA status always visible  
✅ **Data freshness:** Timestamp on all views  

---

## 7. Implementation Timeline

### Phase 8a: MVP (Weeks 1-6)

**Weeks 1-2: Architecture & Setup**
- [ ] Design system (colors, typography, components)
- [ ] Data pipeline setup (DuckDB, Kafka, Redis)
- [ ] Authentication flow (OAuth, biometric)
- [ ] Model integration (RRP artifact loading)

**Weeks 3-4: Core Views**
- [ ] Market regime monitor (real-time)
- [ ] RRP dashboard (top 20 candidates)
- [ ] Portfolio cockpit (holdings + P&L)
- [ ] Alerts configuration

**Weeks 5-6: Testing & Refinement**
- [ ] Unit tests (business logic)
- [ ] Integration tests (data pipeline)
- [ ] E2E tests (user flows)
- [ ] Performance tuning (<500ms loads)
- [ ] Offline mode validation

### Phase 8b: Full Feature Set (Weeks 7-12)

**Weeks 7-8: Advanced Features**
- [ ] Scenario analyzer (what-if modeling)
- [ ] Phase 9 (Anomalies, research copilot)
- [ ] Deep dives (component breakdown, ablation view)
- [ ] Historical comparison (vs prior cycles)

**Weeks 9-10: Integration & Validation**
- [ ] Connect all Layer 1-7 data sources
- [ ] Validate data freshness SLAs
- [ ] End-to-end flow testing
- [ ] UAT with human authority

**Weeks 11-12: Launch Readiness**
- [ ] Security audit (penetration testing)
- [ ] Performance load testing
- [ ] Governance documentation
- [ ] Production deployment playbook

---

## 8. Governance & Monitoring

### 8.1 Phase 8 Success Criteria

✅ **All 7 core views deployed and functional**  
✅ **Data pipeline refreshes on schedule (<95% uptime)**  
✅ **RRP model scores match Phase 7 validation results**  
✅ **Alerts trigger within 2-minute SLA**  
✅ **Scenario modeling matches backtest results**  
✅ **All user decisions logged with rationale**  
✅ **Offline mode works seamlessly**  
✅ **Load times <500ms (95th percentile)**  

### 8.2 Phase 8 Monitoring

**Post-Launch SLA:**

| Metric | Target | Escalation |
|--------|--------|-----------|
| Uptime | 99.5% | Page if <99% |
| Data freshness | On schedule | Alert if >30m behind |
| Alert latency | <2 min | Investigate if >5 min |
| Load time (p95) | <500ms | Optimize if >1s |
| Model health | VALIDATED_ALPHA | Escalate if AUC drops |

### 8.3 User Feedback Loop

- Weekly usage analytics (which views most used)
- Monthly user interviews (UX feedback)
- Quarterly feature requests + prioritization
- Annual audit trail review (decision patterns)

---

## 9. Integration with Phase 9 (AI Research Copilot)

### 9.1 Copilot Inputs (from Dashboard)

```python
copilot_context = {
    "user_portfolio": portfolio_state,           # Current holdings
    "market_regime": regime_assessment,          # BULL/BEAR/NEUTRAL
    "alerts_triggered": [active_alerts],         # Current anomalies
    "opportunities_viewed": [viewed_coins],      # User research history
    "decisions_made": [logged_decisions],        # User's past choices
}

# Copilot autonomously generates:
anomaly_reports = copilot.analyze_market(copilot_context)
comparison_scenarios = copilot.compare_opportunities(viewed_coins)
hypothesis_challenges = copilot.challenge_assumptions(decisions_made)
research_updates = copilot.background_research(portfolio + regime)
```

### 9.2 Copilot Outputs (to Dashboard)

- Anomaly alerts (auto-generated, human-reviewed)
- Comparison analyses (on-demand or daily)
- Hypothesis challenges (passive notifications)
- Research updates (background, weekly digest)

---

## Deliverables (Phase 8 Completion)

1. **Production iOS App**
   - App Store ready (TestFlight beta)
   - All 7 core views + settings
   - Biometric auth + offline mode

2. **Data Integration Layer**
   - Real-time pipeline (Kafka + DuckDB)
   - API integrations (CoinGecko, Glassnode, etc)
   - SLA monitoring (freshness, latency)

3. **Model Integration**
   - RRP artifact loaded correctly
   - Component scores matching validation results
   - Monthly audits automated

4. **Documentation**
   - User guide (how to use each view)
   - Operator guide (data pipeline, alerts)
   - Governance documentation (audit trail, compliance)

5. **Monitoring & Alerts**
   - Uptime monitoring (99.5% SLA)
   - Data freshness checks
   - Performance metrics (load times, latency)

---

**Built:** 2026-09-25  
**Phase:** 8 of 9  
**Status:** Ready for Jan 2027 Execution (upon RRP VALIDATED_ALPHA)  
**Downstream:** Phase 9 AI Research Copilot (integrated into dashboard)  

**Phase 8 integrates all Layers 1-7 into production-ready research intelligence for human decision-makers. Read-only. Human-gated. Traceable. Mobile-first.**
