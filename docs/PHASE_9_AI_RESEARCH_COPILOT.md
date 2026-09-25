# Phase 9: AI Research Copilot
**IGWT-PF26 Final Layer - Read-Only Human-Gated Research Assistant**

**Status:** ✓ Production (Research Phase)  
**Version:** 1.0.0  
**Test Coverage:** 18/18 ✓  
**Governance:** ✅ Read-Only, ✅ Human-Gated, ✅ No Auto-Execution  

---

## Architecture

### Overview

Phase 9 is a **read-only AI research copilot** that augments human decision-making by:
- Analyzing all available data (Layers 1-8)
- Generating structured hypotheses
- Detecting statistical anomalies
- Proposing experiments for validation
- Challenging assumptions
- Comparing scenarios side-by-side

### Governance Constraints

```
✅ CAN DO                          ❌ CANNOT DO
────────────────────────────────────────────────────
✅ Read all data                   ❌ Modify parameters
✅ Run analyses                    ❌ Execute trades
✅ Propose hypotheses              ❌ Approve signals
✅ Report findings                 ❌ Bypass validation
✅ Generate experiments            ❌ Override human decisions
✅ Challenge assumptions           ❌ Store credentials
```

### Pipeline Architecture

```
Human Query
    ↓
AI Research Copilot (READ-ONLY)
    ├─ Read data from all layers
    ├─ Run analyses
    ├─ Compare scenarios
    └─ Detect anomalies
    ↓
Research Proposal / Hypothesis
    ├─ Structured format
    ├─ Confidence levels
    ├─ Data sources tracked
    ├─ Assumptions listed
    └─ Risk factors documented
    ↓
Human Review & Approval
    ├─ Accept proposal
    ├─ Reject proposal
    └─ Request clarification
    ↓
Experimental Validation (PIT/OOS/WFV)
    ├─ In-sample backtest
    ├─ Out-of-sample test
    └─ Walk-forward confirmation
    ↓
Human Decision
    └─ Manual execution (if approved)
```

---

## Core Components

### 1. ResearchProposal

Structured hypothesis for human review.

```python
@dataclass
class ResearchProposal:
    proposal_id: str
    timestamp: datetime
    coin_id: str
    hypothesis: str                          # English description
    confidence: float                        # 0-1 confidence level
    supporting_metrics: Dict[str, Any]      # Evidence FOR
    conflicting_metrics: Dict[str, Any]     # Evidence AGAINST
    data_sources_used: List[str]            # Data sources
    assumptions: List[str]                   # Underlying assumptions
    risk_factors: List[str]                  # Failure modes
    approval_status: ApprovalGate            # PENDING | APPROVED | REJECTED
    is_backed_by_walk_forward: bool         # WFV validation?
    pit_oos_wfv_status: str                 # research_phase | pit_validated | oos_tested | wfv_confirmed
```

### 2. AnomalyReport

Statistical anomaly detection.

```python
@dataclass
class AnomalyReport:
    report_id: str
    timestamp: datetime
    coin_id: str
    anomaly_type: str                       # volume_surge, narrative_reversal, etc.
    severity: str                           # low, medium, high, critical
    baseline_value: float                   # Normal/expected value
    current_value: float                    # Observed value
    deviation_sigma: float                  # Standard deviations from mean
    affected_layers: List[str]              # Which analysis layers detected this
    likely_causes: List[str]                # Hypothesized root causes
    human_verified: bool                    # Human confirmed?
    approval_gate: ApprovalGate             # PENDING | APPROVED
```

### 3. ComparisonScenario

Side-by-side coin/scenario analysis.

```python
@dataclass
class ComparisonScenario:
    scenario_id: str
    timestamp: datetime
    coins_analyzed: List[str]
    dimensions: Dict[str, Dict[str, float]]     # {metric: {coin: value}}
    divergences: Dict[str, List[str]]           # Metrics where coins differ (>30%)
    convergence_signals: List[str]              # Metrics where coins align (<10%)
    approval_required: bool
    analysis_depth: str                         # research | validated
```

---

## API Reference

### Initialize Copilot

```python
from src.agent.ai_research_copilot import AIResearchCopilot

# Must operate in read-only mode (mandatory)
copilot = AIResearchCopilot(read_only=True)
```

### Generate Hypothesis

```python
proposal = copilot.propose_hypothesis(
    coin_id="bitcoin",
    hypothesis="Bitcoin approaching accumulation zone",
    confidence=0.72,  # 0-1
    supporting_metrics={
        "wyckoff_score": 5.2,
        "rsi": 42,
        "volume_trend": "increasing"
    },
    conflicting_metrics={
        "momentum": 0.3,
        "sentiment": "neutral"
    },
    data_sources=["coingecko", "technical_indicators"],
    assumptions=[
        "CEX data reliable",
        "Historical patterns repeat"
    ],
    risk_factors=[
        "Macro shock",
        "Regulatory change"
    ]
)

# Returns: ResearchProposal (approval_status=PENDING)
```

### Detect Anomalies

```python
anomaly = copilot.detect_anomaly(
    coin_id="ethereum",
    anomaly_type="volume_surge",
    baseline=1e9,
    current=3.5e9,
    sigma=3.2,  # 3.2 standard deviations
    affected_layers=["feature_store", "wyckoff_bce"],
    likely_causes=["Institutional accumulation", "Exchange listing"],
    severity="high"
)

# Returns: AnomalyReport (human_verified=False)
```

### Compare Scenarios

```python
scenario = copilot.compare_scenarios(
    coins=["bitcoin", "ethereum", "solana"],
    metrics={
        "price_momentum": {
            "bitcoin": 0.45,
            "ethereum": 0.38,
            "solana": 0.52
        },
        "narrative_score": {
            "bitcoin": 60,
            "ethereum": 72,
            "solana": 65
        },
        "volume_trend": {
            "bitcoin": 0.2,
            "ethereum": 0.8,
            "solana": 0.75
        }
    }
)

# Returns: ComparisonScenario with:
# - divergences: {metric: [coins]} where >30% spread
# - convergence_signals: [metrics] where <10% spread
```

### Challenge Assumptions

```python
challenge = copilot.challenge_assumption(
    assumption="Bitcoin accumulation is institutional-driven",
    supporting_evidence=[
        "Large buy orders",
        "Decreased exchange outflows",
        "Whale wallet accumulation"
    ],
    contradicting_evidence=[
        "Funding rates neutral",
        "Open interest declining"
    ],
    alternative_hypotheses=[
        "Retail FOMO",
        "Algorithm-driven accumulation",
        "Market maker positioning"
    ]
)

# Returns: {
#   "assumption": "...",
#   "confidence_in_assumption": 0.6,
#   "recommendation": "INVESTIGATE" or "HOLDS"
# }
```

### Propose Experiment

```python
experiment = copilot.propose_experiment(
    hypothesis_id=proposal.proposal_id,
    experiment_type="walk_forward",  # pit_backtest | oos_validation | walk_forward | monte_carlo | sensitivity
    parameters={"train_days": 30, "test_days": 7, "retest_period": 5},
    success_criteria=[
        "Profit factor > 1.3",
        "Max drawdown < 25%",
        "Win rate > 45%"
    ],
    failure_modes=[
        "Market regime change",
        "Overfitting on training data"
    ]
)

# Returns: Experiment proposal (approval_status=PENDING)
```

### Format Report

```python
report = copilot.format_research_report(
    proposal_id=proposal.proposal_id,
    executive_summary="Strong narrative tailwinds with measured inflows.",
    detailed_findings="Analysis shows 3-month adoption acceleration...",
    data_quality_notes="All sources verified. No lookahead bias detected."
)

# Returns: Markdown-formatted report
# - Includes: hypothesis, evidence, assumptions, risks
# - Includes: BOLD disclaimer about research-only status
# - Includes: NO automatic execution warning
```

### Human Approval Workflow

```python
# Accept hypothesis
approved = copilot.mark_proposal_approved(
    proposal_id=proposal.proposal_id,
    approver_comment="Hypothesis well-supported. Recommend walk-forward validation."
)

# Reject hypothesis
rejected = copilot.mark_proposal_rejected(
    proposal_id=proposal.proposal_id,
    rejection_reason="Confidence too low (<50%). Insufficient supporting evidence."
)

# Verify anomaly
verified = copilot.mark_anomaly_verified(
    anomaly_id=anomaly.report_id,
    verification_notes="Verified: Confirmed institutional accumulation pattern."
)
```

### Get Pending Items

```python
pending_proposals, pending_anomalies = copilot.get_pending_approvals()

# Returns:
# - List of ResearchProposal with approval_status=PENDING
# - List of AnomalyReport with human_verified=False
```

### Read-Only Enforcement

```python
# These intentionally raise PermissionError:
copilot.cannot_modify_parameters()   # ❌ No parameter changes
copilot.cannot_execute_trade()       # ❌ No trade execution
copilot.cannot_approve_signal()      # ❌ No signal approval
```

---

## Usage Example

```python
from src.agent.ai_research_copilot import AIResearchCopilot

# Initialize (read-only mandatory)
copilot = AIResearchCopilot(read_only=True)

# Scenario: Bitcoin showing unusual volume spike
btc_data = fetch_latest_bitcoin_data()

# 1. Detect anomaly
anomaly = copilot.detect_anomaly(
    coin_id="bitcoin",
    anomaly_type="volume_surge",
    baseline=btc_data.avg_volume_30d,
    current=btc_data.current_volume,
    sigma=btc_data.sigma_deviation,
    affected_layers=["feature_store", "wyckoff_bce", "x20_engine"],
    likely_causes=["Institutional accumulation", "Whale activity"],
    severity="high"
)

# 2. Propose hypothesis
proposal = copilot.propose_hypothesis(
    coin_id="bitcoin",
    hypothesis="Bitcoin entering institutional accumulation phase",
    confidence=0.68,
    supporting_metrics={
        "wyckoff_score": 5.1,
        "volume_surge_sigma": 3.2,
        "rsi": 38,
        "capital_flow": 1.15
    },
    conflicting_metrics={
        "funding_rates": 0.005,
        "sentiment": "neutral"
    },
    data_sources=["coingecko", "glassnode", "technical_indicators"],
    assumptions=[
        "Volume data is accurate",
        "Current market regime continues",
        "No major regulatory news incoming"
    ],
    risk_factors=[
        "False signal (technical anomaly)",
        "Macro reversal",
        "Regulatory FUD"
    ]
)

# 3. Generate research report
report = copilot.format_research_report(
    proposal_id=proposal.proposal_id,
    executive_summary="Bitcoin showing signs of institutional accumulation with 3-sigma volume spike.",
    detailed_findings="Volume spike confirmed across multiple indicators. Wyckoff structure intact.",
    data_quality_notes="All sources verified. No lookahead bias. Data current as of now."
)

# 4. Human review
print(report)
# ... Human reads report ...
# ... Human decides: APPROVE or REJECT ...

approval_decision = input("Approve hypothesis? (yes/no): ")
if approval_decision == "yes":
    approved = copilot.mark_proposal_approved(
        proposal.proposal_id,
        "Approved for walk-forward validation testing."
    )
    
    # 5. Propose validation experiment
    experiment = copilot.propose_experiment(
        hypothesis_id=approved.proposal_id,
        experiment_type="walk_forward",
        parameters={
            "train_window_days": 30,
            "test_window_days": 7,
            "retest_periods": 5
        },
        success_criteria=[
            "Accuracy >= 60% on out-of-sample",
            "Profit factor >= 1.3",
            "Win rate >= 45%"
        ],
        failure_modes=[
            "Regime change",
            "Overfitting",
            "Data quality issues"
        ]
    )
    
    print("Experiment ready for execution by human analyst.")
else:
    rejected = copilot.mark_proposal_rejected(
        proposal_id,
        rejection_reason
    )
```

---

## Test Coverage

```
test_copilot_initialization              ✓
test_copilot_cannot_initialize_writable  ✓  (write mode blocked)
test_propose_hypothesis_valid            ✓
test_propose_hypothesis_invalid_confidence ✓
test_detect_anomaly                      ✓
test_detect_anomaly_low_sigma_warning    ✓
test_compare_scenarios                   ✓
test_challenge_assumption                ✓
test_propose_experiment                  ✓
test_format_research_report              ✓
test_approval_workflow                   ✓
test_rejection_workflow                  ✓
test_anomaly_verification                ✓
test_get_pending_approvals               ✓
test_read_only_constraints               ✓
test_hypothesis_data_sources_tracked     ✓
test_assumption_tracking                 ✓
test_risk_factor_documentation           ✓

Total: 18/18 ✓
```

---

## Key Design Principles

### 1. Read-Only Enforcement
- No parameter modification capability
- No trade execution capability
- No signal approval capability
- PermissionError raised for violations

### 2. Structured Output
- All proposals are dataclass-based
- All reports are Markdown-formatted
- All findings include timestamp and ID
- All data sources are tracked

### 3. Human-Gated Pipeline
- Every proposal requires human review
- Every anomaly requires human verification
- Every experiment requires human approval
- No automatic execution at any step

### 4. Reproducibility
- All data sources documented
- All assumptions listed
- All risk factors identified
- All confidence levels quantified (0-1)

### 5. Governance Compliance
- Research/validation status tracked (PIT/OOS/WFV)
- Lookahead bias prevention considered
- No credentials stored
- Clear disclaimer on all outputs

---

## Integration with Layers 1-8

Phase 9 (AI Research Copilot) reads from:

| Layer | Purpose | Read Access |
|-------|---------|-------------|
| Layer 1 | Data (CoinGecko, CEX, on-chain) | ✅ YES |
| Layer 2 | Feature Store (OHLCV, indicators) | ✅ YES |
| Layer 3 | Wyckoff BCE (accumulation scoring) | ✅ YES |
| Layer 4 | X20 Engine (opportunity scoring) | ✅ YES |
| Layer 5 | NARM-P+ (narrative rotation) | ✅ YES |
| Layer 6 | RCM/RPM (capital rotation) | ✅ YES |
| Layer 7 | RRP (revival radar) | ✅ YES |
| Layer 8 | Dashboard (UI/visualization) | ✅ YES |

Phase 9 writes to:
- Internal proposal/anomaly/scenario storage (in-memory)
- Formatted reports (text output)
- No modifications to Layer 1-8 data

---

## Future Enhancements

### Post-Validation
- [ ] Add backtesting result storage
- [ ] Add experiment execution logging
- [ ] Add performance tracking per hypothesis
- [ ] Add confidence score refinement over time

### Integration
- [ ] CLI interface for hypothesis generation
- [ ] Dashboard widget for pending approvals
- [ ] Email notifications for high-confidence anomalies
- [ ] Slack integration for alerts

### Advanced Features
- [ ] Multi-dimensional hypothesis comparison
- [ ] Automated assumption validation
- [ ] Sensitivity analysis generation
- [ ] Monte Carlo experiment proposals

---

## Safety & Constraints

### What Phase 9 IS
✅ Research assistant augmenting human judgment  
✅ Hypothesis generator with confidence levels  
✅ Anomaly detector with statistical rigor  
✅ Scenario analyzer for comparison  

### What Phase 9 IS NOT
❌ Autonomous trading agent  
❌ Decision-maker  
❌ Validator (that's human's role)  
❌ Executor  

### Mandatory Human Review
- Every hypothesis requires human approval
- Every anomaly requires human verification
- Every experiment requires human greenlight
- No exceptions, no overrides

---

## Files

| File | Purpose | Status |
|------|---------|--------|
| `src/agent/ai_research_copilot.py` | Main copilot module | ✓ v1.0.0 |
| `src/agent/__init__.py` | Module exports | ✓ v1.0.0 |
| `tests/test_ai_research_copilot.py` | Test suite (18 tests) | ✓ 100% passing |

---

## Version History

**v1.0.0** (2026-09-25)
- Initial read-only copilot implementation
- Hypothesis generation with confidence tracking
- Anomaly detection with sigma-based severity
- Scenario comparison with divergence/convergence detection
- Assumption challenging with evidence-based confidence
- Experiment proposal framework (PIT/OOS/WFV)
- Human approval/rejection workflow
- Research report formatting with governance disclaimers
- 18 tests, 100% passing
- Full read-only constraint enforcement

---

**Built:** 2026-09-25  
**Version:** 1.0.0  
**Status:** ✅ Production (Research Phase)  
**Governance:** ✅ Read-Only, ✅ Human-Gated, ✅ No Auto-Execution
