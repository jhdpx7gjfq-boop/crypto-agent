# Phase 9: Dashboard & Agent IA Specification

**Version**: 1.0  
**Status**: Implementation  
**Target Completion**: 2026-10-15

---

## Overview

Phase 9 delivers two integrated components:

1. **Dashboard**: Mobile-first visualization of IGWT-PF26 analysis results
2. **Agent IA**: Autonomous research assistant for market surveillance & hypothesis testing

Neither component executes trades. Both support human decision-making.

---

## Part A: Dashboard Layer (layer9_dashboard)

### Purpose

Real-time visualization of:
- Market regime detection
- BCE (Bottom Confirmation) signals
- X20 opportunity scores
- RRP revival candidates
- RCM capital rotation alerts
- NARM-P+ narrative rotation

### Architecture

```
src/layers/layer9_dashboard/
├── __init__.py
├── api_models.py          # FastAPI response schemas
├── dashboard_service.py   # Core dashboard logic
├── data_formatters.py     # Convert layer output → UI format
└── alert_engine.py        # Real-time alert generation
```

### API Endpoints (FastAPI)

```
GET  /api/v1/dashboard/summary
     → Overall market regime + top signals

GET  /api/v1/dashboard/bce/{asset}
     → BCE analysis for specific asset

GET  /api/v1/dashboard/x20
     → Top X20 opportunities ranked

GET  /api/v1/dashboard/rrp
     → RRP revival candidates by stage

GET  /api/v1/dashboard/rcm/rotation
     → Capital rotation signals

GET  /api/v1/dashboard/alerts
     → Real-time alerts
```

### Data Models

```python
@dataclass
class DashboardSummary:
  timestamp: datetime
  market_regime: str           # bullish|bearish|ranging|volatile
  regime_confidence: float     # 0-1
  top_signals: List[SignalAlert]
  critical_alerts: int
  assets_under_watch: int

@dataclass
class SignalAlert:
  asset: str
  signal_type: str             # bce|x20|rrp|rcm
  score: float                 # 0-100
  confidence: float            # 0-1
  reasoning: str
  action: str                  # entry_ready|hold|research|avoid
  timestamp: datetime
  severity: str                # critical|high|medium|low
```

---

## Part B: Agent IA Framework (core/agent_ia)

### Purpose

Autonomous analyst:
- Monitors signals across all layers
- Generates research reports
- Detects anomalies & breakouts
- Compares scenarios
- Challenges assumptions
- Escalates to user

### Core Functions

```python
class MarketAnalyzer:
  async def scan_signals(self) -> Dict
  async def detect_regime_shift(self) -> Optional[RegimeAlert]
  async def identify_breakouts(self) -> List[BreakoutSignal]

class ReportGenerator:
  async def daily_summary(self) -> MarketReport
  async def asset_deep_dive(self, asset: str) -> AssetReport
  async def scenario_analysis(self, asset: str, scenarios) -> ScenarioReport

class AnomalyDetector:
  async def detect_anomalies(self) -> List[Anomaly]
  async def find_divergences(self) -> List[Divergence]

class ScenarioSimulator:
  async def backtest_hypothesis(self, asset, thesis, lookback_days) -> HypothesisResult
  async def monte_carlo_analysis(self, asset, entry_price, simulations) -> MonteCarloResult

class AgentOrchestrator:
  async def run_continuous(self)
  async def on_signal(self, signal: Signal)
  async def challenge_hypothesis(self, hypothesis: str) -> Rebuttal
```

### Integration Points

Agent IA reads from all layers 1-8 and outputs to:
- Dashboard API (alert stream, reports)
- Email/Webhook (critical alerts)
- Agent memory (context)

---

## Testing Strategy

- API schema validation
- Data formatter accuracy
- Alert generation thresholds
- Signal detection accuracy
- Report completeness
- Anomaly detection precision
- End-to-end layer integration

**Target**: 50+ tests, 80%+ coverage

---

## Non-Goals

❌ Order execution  
❌ CEX API integration  
❌ Automated trading  
❌ Price prediction  

---

## Success Criteria

✅ Dashboard real-time display  
✅ Mobile responsive (320px+)  
✅ Daily reports auto-generated  
✅ 80%+ anomaly detection  
✅ Hypothesis validation matches walk-forward  
✅ Zero false positives on critical alerts  
✅ 50+ tests @ 80%+ coverage
