"""Phase 8 — Optimizer Engine Example: Parameter tuning end-to-end."""

from src.layers.layer8_optimizer.optimizer_engine import OptimizerEngine, OptimizerParameters
from src.core.backtest import Trade, TradeType
from src.layers.layer1_data.collector import DataCollector
from tests.fixtures.market_data import generate_bull_ohlcv


def simple_ma_strategy(ohlcv, params: OptimizerParameters):
    """Simple moving average strategy for optimization."""
    if len(ohlcv) < params.ma_slow:
        return []

    trades = []
    in_trade = False
    entry_price = 0

    for i in range(params.ma_slow, len(ohlcv)):
        close = ohlcv[i].close
        
        # Simple MA computation
        sma_fast = sum(c.close for c in ohlcv[i-params.ma_fast:i]) / params.ma_fast
        sma_slow = sum(c.close for c in ohlcv[i-params.ma_slow:i]) / params.ma_slow

        # Entry: fast MA crosses above slow MA
        if not in_trade and sma_fast > sma_slow:
            entry_price = close
            in_trade = True

        # Exit: take profit or loss
        if in_trade:
            pnl_pct = ((close - entry_price) / entry_price) * 100

            # Take profit exit
            if pnl_pct >= params.take_profit_pct:
                trades.append(
                    Trade(
                        entry_time=ohlcv[i-1].timestamp,
                        entry_price=entry_price,
                        exit_time=ohlcv[i].timestamp,
                        exit_price=close,
                        trade_type=TradeType.LONG,
                    )
                )
                in_trade = False

            # Stop loss exit
            elif pnl_pct <= -params.stop_loss_pct:
                trades.append(
                    Trade(
                        entry_time=ohlcv[i-1].timestamp,
                        entry_price=entry_price,
                        exit_time=ohlcv[i].timestamp,
                        exit_price=close,
                        trade_type=TradeType.LONG,
                    )
                )
                in_trade = False

    return trades


def main():
    """Run Phase 8 optimizer example."""
    print("\n" + "="*70)
    print("PHASE 8 — OPTIMIZER ENGINE EXAMPLE")
    print("="*70)

    # Generate sample market data
    print("\n1. Generating market data...")
    ohlcv_data = generate_bull_ohlcv(200)
    print(f"   ✓ Generated {len(ohlcv_data)} OHLCV candles")

    # Initialize optimizer
    print("\n2. Initializing optimizer...")
    optimizer = OptimizerEngine()
    print(f"   ✓ Constraints: min_trades={optimizer.constraints.min_trades}, "
          f"min_pf={optimizer.constraints.min_profit_factor}, "
          f"max_dd={optimizer.constraints.max_drawdown}%")

    # Define parameter ranges
    print("\n3. Defining parameter ranges...")
    param_ranges = {
        "ma_fast": (10, 25, 5),
        "ma_slow": (40, 100, 20),
        "rsi_period": (12, 16, 2),
        "rsi_oversold": (25, 35, 5),
        "take_profit_pct": (3, 8, 1),
    }
    print(f"   ✓ Parameter ranges defined")

    # Run optimization
    print("\n4. Running optimization sweep...")
    report = optimizer.optimize(
        "BTC",
        ohlcv_data,
        simple_ma_strategy,
        param_ranges
    )

    # Display results
    print(optimizer.generate_report_text(report))

    # Best parameters
    if report.best_result:
        print("\n5. Best parameters found:")
        best = report.best_result
        params = best.parameters.to_dict()
        for key, val in params.items():
            print(f"   {key}: {val}")

        print(f"\n6. Performance metrics:")
        print(f"   Total Trades: {best.backtest_result.total_trades}")
        print(f"   Win Rate: {best.backtest_result.win_rate:.2f}%")
        print(f"   Profit Factor: {best.backtest_result.profit_factor:.2f}")
        print(f"   Max Drawdown: {best.backtest_result.max_drawdown:.2f}%")
        print(f"   Sharpe Ratio: {best.backtest_result.sharpe_ratio or 'N/A'}")
        print(f"   Walk-Forward Valid: {'✓' if best.walk_forward_valid else '✗'}")

    else:
        print("\n✗ No parameter combinations passed all constraints.")

    print("\n" + "="*70)
    print("Optimizer example complete.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
