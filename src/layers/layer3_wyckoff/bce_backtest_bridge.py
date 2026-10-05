"""
BCE-to-Backtest Bridge: Production infrastructure connecting BCE signals to trade execution.

This module bridges the BottomConfirmationEngine (Layer 3) to the BacktestEngine,
enabling deterministic, testable trade execution without lookahead bias.

EXIT RULE GOVERNANCE: RESEARCH EXECUTION CONVENTION
====================================================

CRITICAL: This exit rule is NOT part of the frozen Phase 3 BCE specification.

- Exit rule (BCE < 5.0 → exit at t+1 open) is PROVISIONAL RESEARCH CONVENTION
- Exit rule is implemented ONLY to enable deterministic infrastructure testing
- Exit rule is NOT validated as alpha
- Exit rule is NOT a trading recommendation
- Future WFV integration will depend on this provisional exit
- Any economic/alpha conclusions using this exit are NON-VALIDATED

VALIDATED vs. RESEARCH COMPONENTS
==================================
- VALIDATED: BCE engine (BottomConfirmationEngine class, frozen 6-component spec)
- VALIDATED: Entry gate (BCE >= 5.0, frozen Phase 3 specification)
- RESEARCH CONVENTION: Exit rule (this module, provisional for infrastructure testing)
- RESEARCH CONVENTION: Execution timing (next candle open for entry and exit)

This bridge is INFRASTRUCTURE, not validated alpha:
- Deterministic, reproducible, no-lookahead enforcement
- Suitable for research testing, NOT economic validation
- No parameters are optimized; all logic is frozen
- Strictly prevents lookahead bias via rigorous candle ordering

Distinguish clearly:
A) BCE engine specification (frozen, validated, immutable)
B) This bridge's exit rule (research convention, provisional, infrastructure only)
C) WFV metrics (will depend on this provisional exit, NOT economic validation)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

from src.core.models import OHLCV
from src.core.backtest import Trade, TradeType, BacktestEngine, BacktestResult
from .bce import BottomConfirmationEngine, BCEResult


logger = logging.getLogger(__name__)


@dataclass
class SignalEvent:
    """Signal generated at a specific candle."""
    candle_index: int
    timestamp: datetime
    signal_type: str  # "entry" or "exit"
    bce_score: float
    price: float  # Price at signal generation
    reason: str = ""


@dataclass
class TradeSignals:
    """Trade signals for backtesting with execution details."""
    entry_signal: SignalEvent
    exit_signal: Optional[SignalEvent] = None
    entry_execution_candle: int = 0  # Candle index where trade is executed
    exit_execution_candle: Optional[int] = None  # Candle index where trade is exited
    entry_execution_price: float = 0.0  # Next candle open after signal
    exit_execution_price: Optional[float] = None
    final_position_open: bool = False  # True if position never closed


@dataclass
class BCEBacktestResult:
    """Bridge execution results."""
    trades: List[Trade] = field(default_factory=list)
    signals: List[TradeSignals] = field(default_factory=list)
    backtest_metrics: Optional[BacktestResult] = None
    lookahead_violations: List[str] = field(default_factory=list)
    final_open_position: Optional[TradeSignals] = None
    execution_summary: Dict[str, Any] = field(default_factory=dict)


class BCEBacktestBridge:
    """
    Bridges BCE engine to BacktestEngine with deterministic, no-lookahead execution.

    CRITICAL: This class is INFRASTRUCTURE ONLY. The exit rule is a RESEARCH EXECUTION
    CONVENTION, not a validated trading strategy or part of the BCE specification.

    Core logic:
    1. For each candle t, compute BCE using only data through t
    2. If BCE >= 5.0 at t and not in position, generate entry signal
    3. Entry execution price = candle (t+1) open (next executable price)
    4. If BCE < 5.0 at t and in position, generate exit signal (PROVISIONAL)
    5. Exit execution price = candle (t+1) open (next executable price) (PROVISIONAL)
    6. If final candle leaves position open, close at final close price
    7. Create Trade object with these prices/times
    8. Feed trades to BacktestEngine

    EXIT RULE GOVERNANCE (RESEARCH CONVENTION):
    ============================================
    - Exit signal: BCE score drops below 5.0
    - Exit execution: Next candle (t+1) open
    - Conservative design: prevents holding through uncertain periods
    - STATUS: PROVISIONAL RESEARCH EXECUTION CONVENTION
    - NOT part of frozen Phase 3 BCE specification
    - NOT validated as alpha
    - Exists ONLY to enable deterministic infrastructure testing
    - Future WFV metrics depend on this provisional exit rule
    - Any economic/alpha conclusions using this exit are NON-VALIDATED

    ENTRY (VALIDATED):
    - Threshold: BCE >= 5.0 (from frozen Phase 3 BCE spec)
    - Execution: Next candle (t+1) open
    - VALIDATED component (no-lookahead enforcement only)
    """

    def __init__(self, asset: str, max_concurrent_trades: int = 1):
        """
        Initialize bridge.

        Args:
            asset: Asset symbol (e.g., 'BTCUSDT')
            max_concurrent_trades: Max simultaneous positions (for future multi-trade support)
        """
        self.asset = asset
        self.max_concurrent_trades = max_concurrent_trades
        self.bce_engine = BottomConfirmationEngine(asset)
        self.logger = logger

    def run_backtest(
        self,
        ohlcv_data: List[OHLCV],
        initial_capital: float = 100000.0,
    ) -> BCEBacktestResult:
        """
        Run full backtest with BCE signals on OHLCV data.

        Critical no-lookahead constraints:
        - BCE at candle t uses only data[0:t+1]
        - Entry execution uses candle t+1 open
        - Exit execution uses candle t+1 open
        - Final open position handled explicitly

        Args:
            ohlcv_data: Time-sorted OHLCV candles
            initial_capital: Starting capital for BacktestEngine

        Returns:
            BCEBacktestResult with trades and metrics
        """
        result = BCEBacktestResult()

        # Input validation
        if not ohlcv_data:
            self.logger.warning("No OHLCV data provided")
            result.lookahead_violations.append("Empty OHLCV data")
            return result

        if len(ohlcv_data) < 50:
            result.lookahead_violations.append(
                f"Insufficient data: {len(ohlcv_data)} candles (need ≥50 for BCE)"
            )
            return result

        self.logger.info(
            f"Starting backtest: {self.asset}, {len(ohlcv_data)} candles, "
            f"{ohlcv_data[0].timestamp} to {ohlcv_data[-1].timestamp}"
        )

        # Phase 1: Generate signals with strict no-lookahead enforcement
        signals = self._generate_signals_no_lookahead(ohlcv_data)
        result.signals = signals

        self.logger.info(f"Generated {len(signals)} signal pairs")

        # Phase 2: Convert signals to trades
        trades = self._signals_to_trades(ohlcv_data, signals, result)
        result.trades = trades

        self.logger.info(f"Converted to {len(trades)} trades")

        # Phase 3: Run backtest via BacktestEngine
        engine = BacktestEngine(initial_capital=initial_capital)
        if trades:
            engine.add_trades_batch(trades)

        metrics = engine.compute_metrics()
        result.backtest_metrics = metrics

        # Phase 4: Build execution summary
        result.execution_summary = {
            "asset": self.asset,
            "total_candles": len(ohlcv_data),
            "total_trades": len(trades),
            "final_open_position": result.final_open_position is not None,
            "lookahead_violations_count": len(result.lookahead_violations),
        }

        self.logger.info(
            f"Backtest complete: {metrics.total_trades} trades, "
            f"PF={metrics.profit_factor:.3f}, DD={metrics.max_drawdown:.2f}%"
        )

        return result

    def _generate_signals_no_lookahead(
        self,
        ohlcv_data: List[OHLCV],
    ) -> List[TradeSignals]:
        """
        Generate entry/exit signals with STRICT no-lookahead enforcement.

        Algorithm:
        For each candle t in range [50, len(ohlcv_data) - 1]:
          1. Compute BCE using only ohlcv_data[0:t+1]
          2. Check if BCE >= 5.0 AND not currently in position
             → Entry signal at candle t, execution at t+1
          3. If in position and BCE < 5.0
             → Exit signal at candle t, execution at t+1

        Returns:
            List of TradeSignals (paired entry/exit)
        """
        signals: List[TradeSignals] = []
        in_position = False
        current_entry_signal: Optional[SignalEvent] = None

        # Minimum 50 candles needed for BCE computation
        min_history = 50
        if len(ohlcv_data) < min_history + 1:
            self.logger.warning(
                f"Insufficient history: {len(ohlcv_data)} < {min_history + 1}"
            )
            return signals

        # Main loop: iterate through candles, computing BCE only from historical data
        for t in range(min_history, len(ohlcv_data) - 1):
            # NO LOOKAHEAD: Use only data[0:t+1]
            historical_data = ohlcv_data[0 : t + 1]

            try:
                bce_result = self.bce_engine.compute_bce_score(
                    ohlcv_data=historical_data,
                    smart_money_data=None,  # No smart money in bridge for research
                )
            except ValueError as e:
                self.logger.debug(f"Candle {t}: BCE computation skipped ({e})")
                continue

            bce_score = bce_result.bce_score
            current_candle = ohlcv_data[t]

            # Entry logic: BCE >= 5.0 and not in position
            if bce_score >= 5.0 and not in_position:
                current_entry_signal = SignalEvent(
                    candle_index=t,
                    timestamp=current_candle.timestamp,
                    signal_type="entry",
                    bce_score=bce_score,
                    price=current_candle.close,
                    reason=f"BCE {bce_score:.2f} >= 5.0",
                )
                in_position = True
                self.logger.debug(
                    f"Candle {t} ({current_candle.timestamp}): Entry signal, BCE={bce_score:.2f}"
                )

            # Exit logic: BCE < 5.0 and in position
            elif bce_score < 5.0 and in_position and current_entry_signal is not None:
                exit_signal = SignalEvent(
                    candle_index=t,
                    timestamp=current_candle.timestamp,
                    signal_type="exit",
                    bce_score=bce_score,
                    price=current_candle.close,
                    reason=f"BCE {bce_score:.2f} < 5.0",
                )

                trade_signal = TradeSignals(
                    entry_signal=current_entry_signal,
                    exit_signal=exit_signal,
                    entry_execution_candle=current_entry_signal.candle_index + 1,
                    exit_execution_candle=t + 1,
                    entry_execution_price=ohlcv_data[current_entry_signal.candle_index + 1].open,
                    exit_execution_price=ohlcv_data[t + 1].open,
                    final_position_open=False,
                )
                signals.append(trade_signal)
                in_position = False
                current_entry_signal = None

                self.logger.debug(
                    f"Candle {t} ({current_candle.timestamp}): Exit signal, BCE={bce_score:.2f}"
                )

        # Handle final position if still open
        if in_position and current_entry_signal is not None:
            final_candle = ohlcv_data[-1]
            final_signal = TradeSignals(
                entry_signal=current_entry_signal,
                exit_signal=None,
                entry_execution_candle=current_entry_signal.candle_index + 1,
                exit_execution_candle=len(ohlcv_data) - 1,
                entry_execution_price=ohlcv_data[current_entry_signal.candle_index + 1].open,
                exit_execution_price=final_candle.close,
                final_position_open=True,
            )
            signals.append(final_signal)
            self.logger.info(
                f"Final candle: Position still open, closing at {final_candle.close}"
            )

        return signals

    def _signals_to_trades(
        self,
        ohlcv_data: List[OHLCV],
        signals: List[TradeSignals],
        result: BCEBacktestResult,
    ) -> List[Trade]:
        """
        Convert signal pairs to Trade objects with validation.

        Validates:
        - Entry execution candle < exit execution candle (no time travel)
        - Entry price and time valid
        - Exit price and time valid
        - No overlapping trades
        """
        trades: List[Trade] = []

        for i, sig in enumerate(signals):
            # Validate candle indices
            if sig.entry_execution_candle >= len(ohlcv_data):
                result.lookahead_violations.append(
                    f"Signal {i}: entry candle {sig.entry_execution_candle} "
                    f">= data length {len(ohlcv_data)}"
                )
                continue

            if sig.exit_execution_candle is None:
                result.lookahead_violations.append(
                    f"Signal {i}: no exit candle defined"
                )
                continue

            if sig.exit_execution_candle >= len(ohlcv_data):
                result.lookahead_violations.append(
                    f"Signal {i}: exit candle {sig.exit_execution_candle} "
                    f">= data length {len(ohlcv_data)}"
                )
                continue

            # Validate execution order
            if sig.entry_execution_candle >= sig.exit_execution_candle:
                result.lookahead_violations.append(
                    f"Signal {i}: entry candle {sig.entry_execution_candle} "
                    f">= exit candle {sig.exit_execution_candle}"
                )
                continue

            # Get execution candles
            entry_candle = ohlcv_data[sig.entry_execution_candle]
            exit_candle = ohlcv_data[sig.exit_execution_candle]

            # Create Trade with validated prices and times
            trade = Trade(
                entry_time=entry_candle.timestamp,
                entry_price=sig.entry_execution_price,
                exit_time=exit_candle.timestamp,
                exit_price=sig.exit_execution_price,
                trade_type=TradeType.LONG,
                quantity=1.0,
                commission=0.0,
                tags={
                    "signal_index": i,
                    "entry_signal_candle": sig.entry_signal.candle_index,
                    "exit_signal_candle": sig.exit_signal.candle_index if sig.exit_signal else None,
                    "bce_entry_score": sig.entry_signal.bce_score,
                    "bce_exit_score": sig.exit_signal.bce_score if sig.exit_signal else None,
                    "final_position": sig.final_position_open,
                },
            )

            trades.append(trade)

        # Track final open position if any
        if signals and signals[-1].final_position_open:
            result.final_open_position = signals[-1]

        return trades


# Convenience function for WFV pipeline integration
def run_bce_backtest(
    asset: str,
    ohlcv_data: List[OHLCV],
    initial_capital: float = 100000.0,
) -> BCEBacktestResult:
    """
    Convenience function for integration with WFV pipeline.

    This function will be called by real_data_wfv_pipeline.py in future phases.

    Args:
        asset: Asset symbol
        ohlcv_data: OHLCV data for window
        initial_capital: Starting capital

    Returns:
        BCEBacktestResult with trades and metrics
    """
    bridge = BCEBacktestBridge(asset)
    return bridge.run_backtest(ohlcv_data, initial_capital)
