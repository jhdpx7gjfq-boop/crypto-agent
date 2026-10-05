"""H-005: BTC Exchange Flows Hypothesis

Development scope: BTC-USD 1D only
Signal horizon: 5D forward returns
Data provider: Glassnode (snapshot-versioned, PIT-safe)
WFV protocol: 19-window expanding (180D fixed train, 30D test, 30D slide)
Gate criteria: ΔIC > 0.005 AND HR > 0.50 AND Stability > 0.65 (ALL must pass)
Production status: BLOCKED indefinitely (no deployment)
"""
