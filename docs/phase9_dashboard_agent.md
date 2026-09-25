# Phase 9: Dashboard + Autonomous Research Agent

**Status**: ✅ COMPLETE  
**Version**: v1.0  
**Tests**: 21/21 passing  
**Last Updated**: 2026-09-25

---

## Overview

Phase 9 implements the **Decision Orchestrator** and **Research Agent** — the unified intelligence layer that combines outputs from all 8 layers into actionable investment signals and autonomous portfolio analysis.

### Purpose

- **Not a dashboard UI** (that's future work)
- **Is a decision engine** that orchestrates 8 independent analysis layers
- **Is a research agent** that autonomously evaluates multiple assets and challenges hypotheses

---

## Architecture

### 1. Decision Orchestrator

**Class**: `DecisionOrchestrator`  
**Module**: `src/layers/layer9_dashboard/orchestrator.py`

#### Orchestration Flow

```
Market Data → Layer 2 (Regime)
         ↓
         ├→ Layer 3 (BCE Score)
         ├→ Layer 4 (X20 Opportunity)
         ├→ Layer 5 (NARM Adoption)
         ├→ Layer 6 (RCM Confirmation)
         └→ Layer 7 (RRP Revival)
         ↓
    Decision Logic
         ↓
    DecisionSignal (unified output)
```

#### Core Method: `analyze()`

```python
def analyze(
    asset: str,
    ohlcv_data: List[OHLCV],
    fundamental_data: Optional[Dict[str, Any]] = None,
    narrative_data: Optional[Dict[str, Any]] = None,
    macro_data: Optional[Dict[str, Any]] = None,
) -> DecisionSignal:
```

**Inputs**:
- `asset`: ticker (e.g., "BTC", "ETH")
- `ohlcv_data`: historical price candles
- `fundamental_data`: team, investors, tokenomics, adoption
- `narrative_data`: media, sentiment, adoption metrics
- `macro_data`: DXY, BTC dominance, funding rates, OI

**Output**: `DecisionSignal` with unified intelligence

#### Decision Signal

```python
@dataclass
class DecisionSignal:
    asset: str
    timestamp: datetime
    
    # Layer outputs
    market_regime: str              # "bull", "bear", "sideways"
    bce_score: float                # 0-6
    bce_confirmed: bool             # >= 5?
    x20_score: float                # 0-100
    narm_score: float               # 0-100
    rcm_score: float                # 0-100
    rrp_probability: float          # 0-100
    
    # Composite decision
    should_enter: bool
    confidence: str                 # "high", "medium", "low"
    risk_level: str                 # "low", "medium", "high"
    
    # Audit trail
    reasoning: List[str]
    warnings: List[str]
```

#### Decision Logic Rules

1. **Hard Gate (mandatory)**:
   - BCE ≥ 5/6 required for ANY entry signal
   - RRP stage "dead" blocks entry

2. **Soft Scoring (0-100 entry score)**:
   - BCE confirmed: +30 points
   - X20 ≥ 70: +30 points
   - RCM ≥ 70: +25 points
   - NARM early stage: +15 points
   - Bull regime: +10 points
   - Sideways regime: +5 points

3. **Confidence Levels**:
   - Entry Score ≥ 80 → HIGH confidence (low risk)
   - Entry Score 60-79 → MEDIUM confidence (medium risk)
   - Entry Score 40-59 → LOW confidence (no entry)
   - Entry Score < 40 → LOW confidence + high risk

4. **FOMO Circuit Breaker**:
   - If: should_enter=true AND market_regime="bear" AND bce_score < 5.5
   - Then: Disable entry, set confidence=low, warn "FOMO circuit breaker triggered"

#### Example Usage

```python
from src.layers.layer9_dashboard.orchestrator import DecisionOrchestrator
from tests.fixtures.market_data import generate_bull_ohlcv

orchestrator = DecisionOrchestrator()

# Analyze BTC
ohlcv = generate_bull_ohlcv(100)
signal = orchestrator.analyze(
    asset="BTC",
    ohlcv_data=ohlcv,
    macro_data={
        "funding_rate": 0.0006,
        "btc_dominance": 58.5,
        "oi_change": 15.0,
    }
)

print(orchestrator.generate_report_text(signal))
```

---

### 2. Research Agent

**Class**: `ResearchAgent`  
**Module**: `src/layers/layer9_dashboard/research_agent.py`

#### Purpose

Autonomous analysis of **multiple assets** across all layers, with:
- Portfolio-wide signal aggregation
- Hypothesis validation
- Alert generation
- Market summary
- Opportunity ranking

#### Core Methods

**`analyze_assets(assets_dict) → ResearchReport`**

```python
assets_data = {
    "BTC": {
        "ohlcv": [...],
        "fundamental": {...},
        "narrative": {...},
    },
    "ETH": {
        "ohlcv": [...],
        "fundamental": {...},
        "narrative": {...},
    },
    # ... more assets
}

report = agent.analyze_assets(assets_data)
```

**Output**: `ResearchReport`
```python
@dataclass
class ResearchReport:
    timestamp: datetime
    assets_analyzed: List[str]
    signals_generated: int
    strong_signals: List[DecisionSignal]    # confidence >= "high"
    weak_signals: List[DecisionSignal]      # confidence < "high"
    decisions: Dict[str, str]               # asset → "ENTER"/"WAIT"
    findings: List[str]
    alerts: List[str]
    market_summary: str
    top_opportunity: Optional[DecisionSignal]
```

**`challenge_hypothesis(hypothesis: str, signal: DecisionSignal) → bool`**

Validates a claim against decision data:
```python
result = agent.challenge_hypothesis(
    hypothesis="BTC is in bull regime with strong BCE",
    signal=btc_signal
)
# Returns: True if hypothesis matches data, False otherwise
```

#### Example Usage

```python
from src.layers.layer9_dashboard.research_agent import ResearchAgent

agent = ResearchAgent()

# Analyze portfolio
portfolio = {
    "BTC": {...},
    "ETH": {...},
    "SOL": {...},
}

report = agent.analyze_assets(portfolio)

print(report.market_summary)
print(f"Strong opportunities: {len(report.strong_signals)}")
print(f"Top pick: {report.top_opportunity.asset}")

# Validate hypothesis
is_valid = agent.challenge_hypothesis(
    "ETH is awakening (RRP stage)",
    report.signals_generated["ETH"]
)
```

---

## Data Structures

### DecisionSignal
```python
@dataclass
class DecisionSignal:
    # Core decision
    asset: str
    timestamp: datetime
    should_enter: bool
    confidence: str              # "high"/"medium"/"low"
    risk_level: str             # "low"/"medium"/"high"
    
    # Layer metrics (0-100 where applicable)
    market_regime: str          # "bull"/"bear"/"sideways"
    bce_score: float            # 0-6 (scaled to %)
    bce_confirmed: bool
    x20_score: float
    narm_score: float
    rcm_score: float
    rrp_probability: float
    
    # Audit trail
    reasoning: List[str]        # Decision steps
    warnings: List[str]         # Risk alerts
```

### ResearchReport
```python
@dataclass
class ResearchReport:
    timestamp: datetime
    assets_analyzed: List[str]      # e.g., ["BTC", "ETH", "SOL"]
    signals_generated: int
    
    # Segmented signals
    strong_signals: List[DecisionSignal]
    weak_signals: List[DecisionSignal]
    
    # Summary data
    decisions: Dict[str, str]       # {asset: "ENTER"/"WAIT"}
    findings: List[str]
    alerts: List[str]
    market_summary: str
    top_opportunity: Optional[DecisionSignal]
```

---

## Testing

**File**: `tests/integration/test_orchestrator.py`  
**Coverage**: 21 integration tests

### DecisionOrchestrator Tests (10)
- ✅ Engine initialization
- ✅ Minimal data analysis
- ✅ Reasoning audit trail
- ✅ BCE gate enforcement
- ✅ Confidence level assignment
- ✅ Risk assessment
- ✅ Warning generation
- ✅ Report text generation
- ✅ All layer scores presence
- ✅ FOMO circuit breaker

### ResearchAgent Tests (11)
- ✅ Agent initialization
- ✅ Single asset analysis
- ✅ Multiple asset analysis
- ✅ Signal counting
- ✅ Alert generation
- ✅ Market summary
- ✅ Top opportunity selection
- ✅ Hypothesis validation
- ✅ Report generation
- ✅ Analysis history tracking
- ✅ Insufficient data handling

**Run tests**:
```bash
pytest tests/integration/test_orchestrator.py -v
```

---

## Integration Points

### With Layer 2 (Market Regime)
```python
regime_signal = self.regime_engine.detect_regime(
    btc_price=btc_price,
    funding_rate=funding_rate,
    open_interest_change=oi_change,
    btc_dominance=btc_dom,
)
market_regime = regime_signal.regime.value  # "bull"/"bear"/"sideways"
```

### With Layer 3 (BCE)
```python
bce_report = self.bce_analyzer.analyze(asset, ohlcv_data)
bce_score = bce_report.bce_score               # 0-6
bce_confirmed = bce_report.is_valid            # >= 5?
```

### With Layer 4 (X20)
```python
x20_report = self.x20_scanner.scan(
    asset, ohlcv_data, fundamental_data, narrative_data
)
x20_score = x20_report.combined_score          # 0-100
```

### With Layers 5-7 (NARM, RCM, RRP)
```python
narm_signal = self.narm_engine.scan(asset, ohlcv_data, narrative_data)
rcm_signal = self.rcm_engine.scan(asset, ohlcv_data, narrative_data, fundamental_data)
rrp_signal = self.rrp_engine.scan(asset, ohlcv_data, {}, {})
```

---

## Key Characteristics

✅ **No hardcoding**: All thresholds configurable  
✅ **Audit trail**: Every decision has reasoning + warnings  
✅ **Multi-asset**: ResearchAgent handles portfolios  
✅ **Hypothesis validation**: Challenge claims with data  
✅ **Risk-aware**: Composite scoring prevents FOMO  
✅ **Modular**: Each layer is independent  
✅ **Testable**: 21 comprehensive integration tests  

---

## Next Steps

1. **Dashboard UI** (Phase 9B): Build Next.js frontend for visualization
2. **API endpoints**: FastAPI routes for orchestrator/agent queries
3. **Real-time monitoring**: WebSocket updates for streaming signals
4. **Portfolio tracking**: Store historical signals and outcomes
5. **Backtesting integration**: Feed orchestrator scores into optimizer

---

## Files

| File | Purpose |
|------|---------|
| `src/layers/layer9_dashboard/orchestrator.py` | DecisionOrchestrator class |
| `src/layers/layer9_dashboard/research_agent.py` | ResearchAgent class |
| `src/layers/layer9_dashboard/__init__.py` | Module exports |
| `tests/integration/test_orchestrator.py` | 21 integration tests |

---

**Phase 9 Status**: ✅ COMPLETE  
All 8 layers unified into decision intelligence.  
Ready for Phase 10 (Dashboard UI) or deployment.
