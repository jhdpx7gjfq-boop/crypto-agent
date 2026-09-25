"""Layer 8 — RPM X20 Optimizer.

Backtesting, optimization, and parameter tuning.
Walk-forward validation mandatory.

Constraints:
- Min 200 trades
- Profit factor > 1.3
- Max drawdown < 25%
"""

from .optimizer_engine import BacktestOptimizer

__all__ = ["BacktestOptimizer"]
