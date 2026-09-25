# Phase 9: AI Research Copilot Specification
**IGWT-PF26 Quant Intelligence Operating System**

**Phase:** 9 of 9  
**Timeline:** Jan 2027 - Mar 2027 (parallel with Phase 8)  
**Predecessor:** All Layers 1-8 ✅ OPERATIONAL  
**Successor:** None (final layer)  
**Input:** Dashboard state, user queries, market data, portfolio context  
**Output:** Research reports, anomaly alerts, hypothesis challenges, scenario comparisons  
**Authority:** Human (research assistant, not executor)  

---

## Executive Summary

Phase 9 adds autonomous AI research capability to complement human decision-making.

**Purpose:** Augmented analyst (not replacement) — identifies blind spots, challenges assumptions, surfaces anomalies  
**Scope:** Read-only research + analysis (zero execution, zero orders)  
**Format:** Conversational (Claude-based) + structured outputs (dashboard integration)  
**Users:** Portfolio managers, quantitative researchers  

---

## 1. Copilot Architecture

### 1.1 Core Components

```
AI Research Copilot (Phase 9)
├─ Input Processors
│  ├─ Portfolio State Reader
│  │  ├─ Current holdings (coin, size, entry price)
│  │  ├─ P&L metrics (realized, unrealized, max DD)
│  │  ├─ Allocation (% by coin, sector, narrative)
│  │  └─ Risk profile (Sharpe, Sortino, correlation)
│  │
│  ├─ Market Context Parser
│  │  ├─ Current regime (BULL/BEAR/NEUTRAL, confidence)
│  │  ├─ Sector rotation (money flow in/out)
│  │  ├─ Narrative strength (adoption curve, sentiment)
│  │  ├─ Capital flow vectors (which assets, which sizes?)
│  │  └─ Volatility regime
│  │
│  ├─ Signal Aggregator
│  │  ├─ BCE scores + zones (accumulation areas)
│  │  ├─ RRP scores + rankings (resurrection candidates)
│  │  ├─ X20 rankings (opportunity pipeline)
│  │  ├─ RPM signals (rotation confirmation)
│  │  └─ Alert status (active, dismissed, resolved)
│  │
│  └─ User Context Tracker
│     ├─ Decision history (what did user do before?)
│     ├─ Risk tolerance (observed from choices)
│     ├─ Conviction level (how strong were past bets?)
│     ├─ Blind spots (patterns in errors?)
│     └─ Interests (which narratives, coin types?)
│
├─ Analysis Engines (4 core capabilities)
│  ├─ ENGINE 1: Anomaly Detection & Reporting
│  │  Input: Market data, portfolio, alerts
│  │  Output: "X unusual activity on Y, probable reason Z"
│  │  Frequency: Daily (automated) + on-demand
│  │  Examples:
│  │  - "Volume spike 100x on [Coin] (airdrop announced?)"
│  │  - "Capital flow reversal into DeFi (rotation turning?)"
│  │  - "Your position hit max DD (stop-loss recommended?)"
│  │
│  ├─ ENGINE 2: Comparative Scenario Analysis
│  │  Input: Two opportunities, historical context
│  │  Output: "Compare X vs Y: why choose one over other?"
│  │  Frequency: On-demand (human asks)
│  │  Examples:
│  │  - "Is Solana stronger than Ethereum now? (adoption, narrative)"
│  │  - "Compare 2021 cycle peak to 2024 peak phases"
│  │  - "If capital rotation plays out as [scenario], portfolio gains X%"
│  │
│  ├─ ENGINE 3: Hypothesis Challenge & Bias Detection
│  │  Input: User decision + rationale, market data
│  │  Output: "You think X, but data shows Y — consider Z"
│  │  Frequency: Passive (daily) + on-demand
│  │  Examples:
│  │  - "You favor [Narrative], but adoption curve flattening"
│  │  - "Conviction bias: similar to decision in [date] (which failed)"
│  │  - "Recency bias: last 3 wins all during bull phase"
│  │
│  └─ ENGINE 4: Background Research & Intelligence
│     Input: Portfolio, regime, interests
│     Output: "Weekly digest of developments + risk warnings"
│     Frequency: Daily automated + on-demand
│     Examples:
│     - "Bitcoin ETF inflows: +$200M (supportive for price)"
│     - "[Coin] unlock event: 50M tokens in 7 days (dump risk?)"
│     - "Regulatory: SEC ruling on [category] (portfolio impact?)"
│
└─ Output Managers
   ├─ Dashboard Integration
   │  ├─ Anomaly alerts (card view on dashboard)
   │  ├─ Research updates (weekly digest)
   │  ├─ Comparison results (expandable card)
   │  └─ Hypothesis challenges (notification + detailed report)
   │
   ├─ Conversational Interface
   │  ├─ Chat with copilot (ask follow-up questions)
   │  ├─ Explain your reasoning (copilot challenges assumptions)
   │  ├─ "What if" scenarios (interactive exploration)
   │  └─ Historical context (how similar was past event?)
   │
   ├─ Report Generation
   │  ├─ Weekly market report (digest form)
   │  ├─ Monthly performance analysis (vs baseline)
   │  ├─ Quarterly decision audit (pattern analysis)
   │  └─ Annual strategy review (roadmap refinement)
   │
   └─ Decision Trail Logging
      ├─ Every analysis logged (timestamp + reasoning)
      ├─ User response logged (accepted/dismissed/debated)
      ├─ Outcome tracked (was copilot right? wrong? neutral?)
      └─ Continuous learning (improve suggestions over time)
```

### 1.2 Knowledge Base & Data Sources

```
Copilot Reasoning Sources:
├─ IGWT-PF26 Layers 1-8 (internal)
│  ├─ Market Regime Engine (Layer 2 output)
│  ├─ BCE Accumulation Zones (Layer 3 output)
│  ├─ X20 Opportunity Rankings (Layer 5 output)
│  ├─ NARM-P+ Narrative Scores (Layer 6 output)
│  ├─ RPM/RCM Rotation Signals (Layer 7 output)
│  ├─ RRP Resurrection Scores (Layer 7, Phase 7 alpha)
│  └─ Dashboard Alerts & Views (Layer 8 output)
│
├─ External Market Intelligence
│  ├─ CoinGecko (prices, market data, news)
│  ├─ Glassnode (on-chain metrics)
│  ├─ Nansen (smart money tracking)
│  ├─ Arkham (entity identification)
│  ├─ Polymarket (prediction markets)
│  ├─ Governance forums (Discord, Discourse)
│  └─ Social sentiment (LunarCrush, Santiment)
│
├─ Historical Context Library
│  ├─ 2017 bull/bear cycle (patterns, outcomes)
│  ├─ 2020-2021 DeFi summer (adoption curve)
│  ├─ 2022 bear market (survivors vs casualties)
│  ├─ 2023 recovery phase (rotation patterns)
│  ├─ 2024+ current cycle (live analysis)
│  └─ Comparative narratives (which have played out? which failed?)
│
└─ User Context
   ├─ Portfolio history (what user owns, owned)
   ├─ Decision log (choices + timing + rationale)
   ├─ Performance metrics (Sharpe, Sortino, wins/losses)
   ├─ Risk profile (observed risk tolerance)
   ├─ Blind spots (patterns in errors)
   └─ Interests (which narratives, coin types fascinate?)
```

---

## 2. Core Capabilities

### 2.1 Capability 1: Anomaly Detection & Reporting

**Purpose:** Identify unusual patterns user might miss

**Input:**
```python
anomaly_input = {
    "market_data": market_state,           # Real-time prices, volume
    "portfolio": portfolio_state,          # Current holdings
    "alerts_active": [triggered_alerts],   # What's unusual?
    "narrative_strength": narrative_scores, # What narratives are hot?
    "capital_flows": flow_data,            # Where is money going?
}
```

**Analysis Process:**
1. **Pattern Matching**: Compare current state to historical norms
2. **Anomaly Scoring**: Rate severity (1-10)
3. **Causal Analysis**: "Why might this be happening?"
4. **Impact Assessment**: "How does this affect user's portfolio?"
5. **Action Recommendation**: "Should user do something?"

**Output Examples:**

```markdown
# 🔴 CRITICAL ANOMALY: Volume Spike on [Coin X]

**Severity:** 9/10 (extreme)

**What:** Volume increased 50x on [Coin X] in last 2 hours (2M → 100M in 24h)
**Why:** Most likely — Airdrop announcement + listing on major exchange
**When:** Started 14:23 UTC (2 hours ago)
**Confidence:** 85% (announcement confirmed, exchange listing pending)

**Impact on your portfolio:**
- You don't hold [Coin X] (no direct impact)
- Capital flowing into [Coin X] may flow OUT of similar coins (rotation risk)
- Narrative shift: [X narrative] gaining attention (bullish signal?)

**What to do:**
- ✅ WATCH for breakout above $X (potential X10 opportunity)
- ⚠️ MONITOR holdings in [similar coins] for outflow pressure
- 🎯 IF interested: Pilot 0.5-1% if position established on second surge

**Historical context:**
- Similar spike in 2021 on [Coin Y] → led to 400% 3-month rally
- Similar spike in 2022 on [Coin Z] → was dump & disappeared
- Pattern: 60% of such spikes continue, 40% are dead cat bounces
```

```markdown
# 🟡 WATCH: Capital Flow Reversal into DeFi

**Severity:** 6/10 (moderate)

**What:** Capital flowing OUT of large-cap stocks INTO DeFi protocols (Uniswap, Aave, Compound)
**Trend:** +$2.3B inflow to DeFi in last 7 days (highest since Dec 2021)
**Confidence:** 72% (Glassnode data + on-chain analysis)

**Interpretation:**
- Risk-on sentiment: Investors rotating into higher-risk, higher-yield strategies
- Market regime implication: BULL phase strengthening (risk appetite increasing)
- Narrative rotation: DeFi regaining attention (after 2 years of dormancy)

**Impact on your portfolio:**
- You hold [Aave: 5% allocation] → directly benefits from DeFi rotation
- You hold [Bitcoin: 40% allocation] → typically outperforms during risk-on (supportive)
- You hold [Stablecoin: 10% allocation] → rotation may reduce stablecoin demand

**Expected duration:** 2-4 weeks (if pattern holds)

**What to do:**
- ✅ HOLD current DeFi exposure (tailwinds)
- ✅ CONSIDER increasing Aave allocation (1-2% more?) if conviction high
- ⚠️ WATCH for reversal signal (if capital flows back to large-cap)

**Historical analogs:**
- Similar capital flow pattern preceded 2021 DeFi summer (+12x overall)
- Similar pattern preceded 2022 DeFi collapse (-80%)
- Key differentiator: Adoption curve level (now mid-growth vs peak)
```

```markdown
# ℹ️ INFO: Your Position Hit Max Drawdown Threshold

**Severity:** 7/10 (decision point)

**What:** [Coin X] position unrealized P&L = -12.3% (your max DD threshold)
**Trigger:** Price dropped from $50 (entry) to $44 (current)
**Duration:** 8 days in drawdown

**Portfolio impact:**
- Overall portfolio DD: -3.8% (diversification helping)
- Max exposure at risk: [Coin X] only
- Cascade risk: None detected (other holdings stable)

**What to do:**
1. **Re-evaluate conviction:**
   - Original thesis (resonance → $150 mcap): Still valid?
   - New information since entry: Any changes?
   - Risk/reward still 1:10? Or deteriorated?

2. **Decision options:**
   - **HOLD:** If conviction unchanged, ignore noise
   - **ADD:** If thesis strengthened (double down)
   - **REDUCE:** If conviction weakened (50% exit)
   - **EXIT:** If thesis broken (cut loss)

**Copilot assessment:**
- Reason for drop: Sector rotation (money out of [narrative])
- Resolution timeline: 2-4 weeks typical for such rotations
- Probability of recovery: 65% (if thesis still valid)

**Your history on similar situations:**
- Last 3 times: You held through, avg recovery +80%
- Last 1 time: You sold at -12%, missed +200% rally
- Pattern: Your thesis is usually right (conviction is a strength)

**Recommendation:** HOLD unless new information changed thesis
```

### 2.2 Capability 2: Comparative Scenario Analysis

**Purpose:** Compare opportunities, understand trade-offs

**Input:**
```python
comparison_input = {
    "candidate_a": {"coin": "Solana", "rrp_score": 87, "market_cap": "$45B"},
    "candidate_b": {"coin": "Ethereum", "rrp_score": 72, "market_cap": "$280B"},
    "user_context": portfolio_state,
    "time_horizon": "6-12 months",
}
```

**Analysis Process:**
1. **Multi-dimensional comparison** (narrative, adoption, technicals, risk)
2. **Historical precedent analysis** (when did similar scenarios occur?)
3. **Portfolio impact modeling** (which adds more value to holdings?)
4. **Risk/reward quantification** (expected return vs drawdown)
5. **Decision recommendation** (choose one? both? neither?)

**Output Example:**

```markdown
# 🎯 COMPARISON: Solana vs Ethereum (6-month horizon)

## Executive Summary
**Better opportunity:** Solana (higher risk/reward, RRP stronger)  
**Safer choice:** Ethereum (larger, more stable, proven narrative)  
**Recommendation:** 70% Solana / 30% Ethereum (if forced to choose both)

---

## Detailed Comparison

| Dimension | Solana | Ethereum | Winner |
|-----------|--------|----------|--------|
| **Narrative Strength** | 8.5/10 (AI+gaming) | 8/10 (staking) | Solana (+0.5) |
| **Adoption Curve** | Growth (early) | Mature (high) | Ethereum (scale) |
| **RRP Resurrection** | 87/100 | 72/100 | Solana (+15) |
| **On-chain Activity** | ↑25% (YoY) | ↑8% (YoY) | Solana (growth) |
| **Risk (max DD)** | 35% (high) | 18% (moderate) | Ethereum (safer) |
| **X20 Potential** | 8/10 (real) | 3/10 (too big) | Solana (upside) |
| **Market Cap Risk** | <$50B (room) | $280B (heavy) | Solana (lighter) |

**Winner by dimension:** Solana (5/7) vs Ethereum (2/7)

---

## Historical Analog Analysis

**Similar scenario #1: 2020-2021 cycle**
- Solana-like coin: Polkadot ($20B → $250B, 12.5x)
- Ethereum-like coin: Bitcoin ($10B → $60B, 6x)
- Outcome: Smaller cap won (Polkadot)
- Lesson: Growth narratives outperform in bull phase

**Similar scenario #2: 2022 bear market**
- Solana-like coin: Crashed -95% (capital destruction)
- Ethereum-like coin: Crashed -65% (better recovery)
- Outcome: Larger cap better downside protection
- Lesson: Risk matters in reversals

**Overall pattern:** In risk-on phases (current), growth narratives win. In risk-off, larger caps win.
Current regime: BULL → suggests Solana > Ethereum

---

## Risk/Reward Modeling

**Scenario A: Bull continues (60% probability)**
- Solana: +200% likely (to $300B mcap)
- Ethereum: +80% likely (to $500B mcap)
- Better: Solana (3x upside edge)

**Scenario B: Rotation happens (30% probability)**
- Solana: -40% likely (to $20B mcap, narrative wanes)
- Ethereum: -25% likely (to $210B mcap, stays stable)
- Better: Ethereum (safer)

**Scenario C: Bear market (10% probability)**
- Solana: -75% likely (to $11B mcap, capitulation)
- Ethereum: -50% likely (to $140B mcap, narrative survives)
- Better: Ethereum (capital preservation)

**Weighted expected return:**
- Solana: (200% × 0.6) + (-40% × 0.3) + (-75% × 0.1) = +85%
- Ethereum: (80% × 0.6) + (-25% × 0.3) + (-50% × 0.1) = +38%
- Advantage: Solana (but higher risk)

---

## Portfolio Impact

**If you allocate $10K:**
- To Solana: Expected gain $8,500 (best case), loss $4,000 (worst case)
- To Ethereum: Expected gain $3,800 (best case), loss $2,500 (worst case)
- Sharpe ratio: Solana 0.85, Ethereum 0.72

**If you hold both ($5K each):**
- Portfolio expected return: +6.2%
- Correlation: 0.78 (moderate diversification)
- Max portfolio DD: -3.8% (better than single bets)

---

## Decision Framework

**Choose SOLANA if:**
- ✅ You have 6-12 month time horizon
- ✅ You can tolerate 40% drawdown
- ✅ You believe AI/gaming narrative is real
- ✅ You want maximum upside (growth phase)

**Choose ETHEREUM if:**
- ✅ You want capital preservation
- ✅ You're uncertain about narratives
- ✅ You need stability for psyche
- ✅ You want proven track record

**Choose BOTH if:**
- ✅ You can allocate to both
- ✅ You want growth + safety combo
- ✅ Suggested: 70% Solana / 30% Ethereum

---

## Copilot Recommendation

**My assessment:** Solana > Ethereum (6-month view)

**Why?** RRP score higher (87 vs 72), narrative momentum stronger (AI), adoption curve steeper, market regime supportive (bull).

**BUT:** Ethereum is safer if surprised by bear market.

**Your history:** You typically win on growth narratives (past 3 bets avg +150%). Your Sharpe improves when you pick the "riskier" option that pans out.

**Final recommendation:** Go 70% Solana if your conviction is high. 50/50 if uncertain.
```

### 2.3 Capability 3: Hypothesis Challenge & Bias Detection

**Purpose:** Challenge assumptions, reduce overconfidence, catch blind spots

**Triggering Logic:**
```python
challenge_triggers = [
    "User holding same narrative 3+ positions",
    "User conviction score very high (>90%)",
    "User made similar decision before (how'd it go?)",
    "User ignoring contradictory signals",
    "User in drawdown (emotional decision risk?)",
]
```

**Output Example:**

```markdown
# 🤔 Hypothesis Challenge: Your Bitcoin Conviction

**What you believe:** "Bitcoin dominance will increase to 60% (from current 45%)"

**Your conviction:** Very high (marked as 95/100)

**Supporting evidence you cite:**
- ✅ ETF inflows accelerating
- ✅ Regulatory clarity improving
- ✅ Macro conditions supportive (DXY↓)

**But data also shows:**
- ❌ Altcoin adoption accelerating (Solana, Sui, Base)
- ❌ Narrative rotation happening (DeFi, AI coins getting attention)
- ❌ Dominance actually declining (from 48% → 45% in 2 weeks)
- ❌ You underestimate adoption curve effects

---

## Copilot Challenge

**Question:** If Bitcoin dominance was DECLINING, what would that look like?
→ Answer: Exactly what we're seeing right now

**Question:** How confident would you be if you saw this data *before* forming conviction?
→ Honest answer: Maybe 65%, not 95%

**Question:** What evidence would change your mind?
→ Your answer: "If dominance dropped below 40%"
→ BUT: Dominance is already declining (trend against you)

---

## Pattern Recognition: Your Past Decisions

| Date | Conviction | Outcome | Bias? |
|------|-----------|---------|-------|
| 2024-03 | BTC → $100K | Wrong (-30%) | Overconfidence |
| 2024-06 | ETH → $5K | Right (+80%) | ✅ Good call |
| 2024-09 | SOL flip to #1 | Right (+150%) | ✅ Good call |
| 2024-11 | DeFi summer 2.0 | TBD (current bet) | Overconfidence? |

**Pattern:** When conviction > 90%, you're right ~50% of the time. When conviction 70-80%, you're right ~80% of the time.

**Lesson:** Your sweet spot is 70-80% conviction, not 95%.

---

## Recency Bias Alert

Your last 2 bets won big (ETH, SOL). You're now more confident than usual.

**Historical precedent:** After 2-3 wins, traders often get overconfident and take larger risks. Sometimes works (runs continue), often fails (regression to mean).

**Your previous hot streaks:**
- 2021 Q3-Q4: Won 4x in a row, then lost on 5th (cumulative loss)
- 2024 Q2-Q3: Won 3x in a row, then flat for 2 months

**Pattern:** After 3-win streaks, expect regression (this is normal, not personal failure).

---

## Revised Recommendation

**Original conviction: 95% → Revised conviction: 70%**

**Why?** Evidence is mixed. Dominance *might* increase IF ETF flows overwhelm altcoin adoption. But current trend is *against* you.

**Suggested action:**
- ✅ HOLD existing Bitcoin (conviction still positive)
- ⚠️ DON'T add more (reduce conviction from 95% to 70%)
- 🎯 SET trigger: If dominance drops <42%, re-evaluate thesis

**What would restore confidence?**
- Bitcoin dominance reverses + starts climbing (trend becomes clear)
- Altcoin narrative weakens (rotation pauses)
- Macro supports risk-off (DXY↑, yields↑)

**Until then:** Acknowledge uncertainty. Reduce position sizing. Diversify bets.
```

### 2.4 Capability 4: Background Research & Intelligence

**Purpose:** Keep user informed of developments affecting portfolio

**Automated Daily Digest Example:**

```markdown
# 📰 IGWT Market Intelligence Digest — 2024-12-20

## Key Developments

### 1. 🔴 REGULATORY: SEC Clarifies Altcoin Classification

**What:** SEC issued guidance that 80% of altcoins may be securities (not commodities)
**When:** Yesterday, 18:00 UTC
**Impact:** Potential regulatory crackdown on unregistered tokens
**Your exposure:**
- High risk: [Coin X] (80% likely security)
- Medium risk: [Coin Y] (30% likely security)
- Low risk: [Coin Z] (5% likely security)

**Action:** Monitor for legal developments. Consider reducing [Coin X] exposure if lawsuit filed.

---

### 2. 🟢 POSITIVE: Bitcoin ETF Inflows Hit Record

**What:** BlackRock iShares BTC ETF added $500M inflow (daily record)
**When:** Today, markets open
**Confidence:** 95% (official filing)
**Implication:** Institutional demand accelerating (bullish signal)
**Your holdings:** Bitcoin +2% today on this news

**Action:** No action needed (tailwind for holdings).

---

### 3. ⚠️ EVENT: Solana Validator Outage (Resolved)

**What:** 30% of Solana validators went offline for 2 hours
**When:** 3 hours ago
**Resolved:** ✅ All validators back online
**Impact:** Minor (network stayed functional)
**Implication:** Centralization concerns remain topic

**Your holdings:** Solana -3% on news (but recovered partially)

**Action:** Not a selling signal (such outages happen occasionally). Monitor for pattern.

---

### 4. 📊 CAPITAL FLOWS: $1.2B Moved OUT of Stablecoins

**What:** USDC, USDT outflows combined $1.2B in last 24h
**Why:** Capital rotating INTO risk assets (risk-on signal)
**Implication:** Bullish for crypto prices (money flowing back in)
**Your portfolio:** Supportive (you're ~80% risk assets)

**Action:** No action needed (favorable macro environment).

---

### 5. 📅 UPCOMING EVENTS (Next 7 days)

- **2024-12-21:** Spot ETH ETF news expected (potential catalyst)
- **2024-12-23:** Holiday market low liquidity (may cause volatility)
- **2024-12-25:** Christmas (markets quiet)
- **2024-12-27:** [Coin X] token unlock event (50M tokens, potential dump)

**Your holdings affected by [Coin X] unlock:** Consider reducing 25% before event.

---

## Risk Warnings

⚠️ **Holiday volatility:** Next 5 days are low-liquidity period. Expect wider spreads + sudden moves.
⚠️ **Regulatory uncertainty:** SEC guidance may cause altcoin selloff. Stay alert for trends.
⚠️ **Macro:** If equities crash on earnings (next week), crypto may follow.

---

## Market Regime Status

**Current:** BULL (confidence 78/100)
**Likely to continue:** 2-4 more weeks (based on capital flow trends)
**Risk:** Regime reversal if macro data disappoints

**Your portfolio positioning:** Well-aligned to bull regime. No urgent changes needed.

---

## What Copilot Recommends Today

1. ✅ HOLD all positions (tailwinds present)
2. ⚠️ REDUCE [Coin X] before Dec 27 unlock (token dilution risk)
3. 🎯 WATCH spot ETH ETF news (catalyst for Ethereum)
4. 📊 MONITOR holiday volatility (may create entry opportunities)

**Confidence in recommendations:** 72/100
```

---

## 3. Integration with Dashboard (Phase 8)

### 3.1 Copilot Cards & Notifications

**On Dashboard Home View:**
- Anomaly alert card (collapsible, expandable)
- Research update card (weekly digest, on-demand detail)
- Hypothesis challenge card (if triggered, with rationale)
- Scenario comparison card (if requested, with deep dive)

**On Portfolio Cockpit View:**
- Copilot assessment of holdings
- Risk flags (if position near drawdown, etc)
- Opportunity indicators (if X20 candidate appears)

### 3.2 Conversational Interface

```
User: "Should I increase my Solana position?"

Copilot response: "Your conviction is high (87/100). Here's my analysis:
✅ Pros: RRP score 87, narrative momentum, market regime supportive
⚠️ Cons: Already at 15% allocation (concentrated), max DD 35%

Recommendation: Increase to 20% IF you add diversification elsewhere (reduce Bitcoin to 35%, add Ethereum to 20%).

Want me to model this portfolio change?"

[User clicks: "Model it"]

Copilot: "New portfolio (Solana 20%):
- Expected return: +7.2% (vs +6.2% current)
- Max DD: -4.8% (vs -3.8% current)
- Sharpe ratio: 0.88 (vs 0.82 current)
- Diversification: Improved (correlation spread better)

Net: +1% return for +1% risk. Acceptable trade-off IF your conviction high."
```

---

## 4. Guardrails & Safety

### 4.1 Core Constraints

✅ **Read-only only:** Copilot CANNOT execute trades, place orders, or move funds  
✅ **Research assistant:** Copilot ADVISES, human DECIDES  
✅ **Transparent reasoning:** Every recommendation includes "why"  
✅ **Uncertainty acknowledged:** Copilot always includes confidence levels  
✅ **Decision log:** Every analysis logged for audit trail  
✅ **Bias awareness:** Copilot self-corrects known biases  

### 4.2 Escalation Rules

**Copilot escalates to Human Authority if:**
- Recommendation confidence < 50% (uncertain)
- Contradictory signals present (can't resolve)
- Multiple red flags found (portfolio risk elevated)
- Market regime breaking (assumptions invalid)

**Example escalation:**
```
Copilot: "I cannot recommend action (50% confidence).

Reasons:
- Conflicting signals (RRP bullish, technical bearish)
- Regime uncertainty (is bull ending?)
- Portfolio stress (already at max DD)

ESCALATION: Recommend human review before major position changes.

Questions for you:
1. What changed since you entered this position?
2. Are you still convinced of the thesis?
3. Can you afford the -12% drawdown emotionally?

Awaiting your input before further analysis."
```

### 4.3 Feedback Loops

**Copilot learns from user decisions:**

```python
user_decision = {
    "date": "2024-12-20 14:30",
    "copilot_recommendation": "HOLD Solana (70% confidence)",
    "user_action": "SOLD Solana (panicked at -10% DD)",
    "outcome": "Missed +80% recovery (2 months later)"
}

# Copilot updates its understanding:
learning = {
    "insight": "User sells on -10% DD despite high conviction",
    "pattern": "Emotional decision-making under stress",
    "adjustment": "Future recommendations account for user's risk tolerance in drawdowns"
}
```

---

## 5. Implementation & Rollout

### 5.1 Integration Timeline

**Week 1-2:** Connect Copilot to all Layer data sources + test accuracy  
**Week 3-4:** Deploy anomaly detection + test on historical data  
**Week 5-6:** Deploy scenario analysis + validate modeling  
**Week 7-8:** Deploy hypothesis challenge + gather feedback  
**Week 9-10:** Deploy background research + finalize daily digest  
**Week 11-12:** Full integration with dashboard + UAT  

### 5.2 Testing & Validation

- **Accuracy:** Copilot recommendations validated against historical outcomes (aim: >70% success rate)
- **Latency:** Analysis completes <5 seconds (real-time feel)
- **Safety:** Guardrails tested (no order execution possible)
- **UX:** Dashboard integration feels natural (no jarring cards/notifications)

### 5.3 Launch Criteria

✅ **All 4 capabilities deployed** (anomaly, scenario, challenge, research)  
✅ **Integration seamless** (card-based, conversational, logged)  
✅ **Safety validated** (no execution possible)  
✅ **Accuracy acceptable** (>70% win rate on recommendations)  
✅ **User feedback positive** (UAT approval)  

---

## 6. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Anomaly accuracy** | >75% (correct diagnosis) | Validation against outcomes |
| **Scenario modeling** | >80% (realistic predictions) | Backtest on historical data |
| **Hypothesis challenges** | >70% (catch real biases) | User feedback + decision review |
| **Research quality** | >85% (relevant, actionable) | User engagement rate |
| **Recommendation success** | >65% (user profit when follows) | Decision log analysis |
| **Time to analysis** | <5 seconds | Latency measurements |
| **User satisfaction** | >4/5 stars | NPS surveys |

---

## Deliverables (Phase 9 Completion)

1. **Copilot Engine (Claude-based)**
   - 4 core capabilities (anomaly, scenario, challenge, research)
   - Integrated with all Layer 1-8 data sources
   - Real-time analysis (<5s latency)

2. **Dashboard Integration**
   - Anomaly alert cards
   - Scenario comparison cards
   - Hypothesis challenge notifications
   - Research digest cards

3. **Conversational Interface**
   - Chat with copilot
   - Follow-up questions
   - Debate recommendations
   - Decision logging

4. **Safety & Governance**
   - Guardrails (read-only only)
   - Escalation procedures
   - Audit trail logging
   - Bias detection

5. **Documentation**
   - User guide (how to use copilot)
   - Operator guide (monitoring, feedback)
   - Architecture documentation
   - Test results + validation

---

**Built:** 2026-09-25  
**Phase:** 9 of 9 (Final Phase)  
**Status:** Ready for Jan 2027 Execution (parallel with Phase 8)  

**Phase 9 completes IGWT-PF26 as full decision-support system: market intelligence (Layers 1-7) + RRP resurrection detection (Layer 7 alpha) + unified dashboard (Layer 8) + AI research copilot (Layer 9). Human-gated, read-only, research-only. Quant intelligence operating system COMPLETE.**
