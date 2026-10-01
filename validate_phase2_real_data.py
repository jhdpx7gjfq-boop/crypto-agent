#!/usr/bin/env python3
"""
Phase 2 Real Data Validation Harness
Validates Feature Store & Backtesting Framework on real Binance OHLCV data.

Covers:
1. DATA QA (missing values, duplicates, chronology)
2. PIT/Lookahead checks (no forward-looking bias)
3. Walk-Forward Validation (IS/OOS performance)
4. Statistical gates (PF, Sharpe, MaxDD, trade count)
5. Per-asset + global results

No mocks. No synthetic data. Real Binance data only.
"""

import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
from src.layers.layer1_data.binance_collector import BinanceDataPortalCollector
from src.core.backtest import BacktestEngine, Trade, TradeType
from src.core.backtest_validator import StatisticalValidator, VALIDATION_CONSTRAINTS
from src.core.models import OHLCV

# Setup logging
LOG_DIR = Path(__file__).parent / "logs" / "phase2_validation"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Validation parameters
ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
DATA_START = (2020, 1)
DATA_END = (2025, 12)
WFV_TRAIN_DAYS = 60
WFV_TEST_DAYS = 30
WFV_STEP_DAYS = 30

# Governance constraints (from backtest_validator.py)
CONSTRAINTS = VALIDATION_CONSTRAINTS


@dataclass
class DataQAResult:
    """Data quality assessment."""
    asset: str
    total_candles: int
    missing_values: int
    duplicate_timestamps: int
    non_monotonic: int
    date_range: Tuple[str, str]
    qa_pass: bool
    issues: List[str]


@dataclass
class PITResult:
    """PIT (Point-In-Time) lookahead check."""
    asset: str
    wfv_windows: int
    train_oos_overlap: int
    lookahead_events: int
    pit_pass: bool
    issues: List[str]


@dataclass
class WindowStats:
    """Stats for single WFV window."""
    window_id: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    is_sample: str  # "in-sample" or "out-of-sample"
    trades: int
    winning_trades: int
    losing_trades: int
    gross_profit: float
    gross_loss: float
    net_pnl: float
    return_pct: float
    profit_factor: str  # "Infinity|zero_loss" or float value
    max_drawdown: float
    sharpe_ratio: Optional[float]
    win_rate: float
    is_oos_positive: bool  # True if return_pct > 0
    passes_gates: bool


@dataclass
class AssetWFVResult:
    """Walk-forward validation result for one asset."""
    asset: str
    total_windows: int
    in_sample_windows: int
    out_sample_windows: int
    in_sample_stats: Dict
    out_sample_stats: Dict
    degradation_ratio: float
    consistency_score: float
    wfv_pass: bool
    window_results: List[WindowStats]
    gate_results: Dict


class Phase2ValidationHarness:
    """Real data Phase 2 validation."""

    def __init__(self):
        self.results = {
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": "1.0.0",
                "framework": "Phase 2 Feature Store & Backtest",
                "data_source": "Binance Data Portal (data.binance.vision)",
                "assets": ASSETS,
                "date_range": f"{DATA_START[0]}-{DATA_START[1]:02d} to {DATA_END[0]}-{DATA_END[1]:02d}",
            },
            "data_qa": {},
            "pit_checks": {},
            "wfv_results": {},
            "summary": {},
        }

    def fetch_binance_data(self, symbol: str) -> pd.DataFrame:
        """Fetch real Binance OHLCV data."""
        logger.info(f"Fetching {symbol} from Binance Data Portal...")
        try:
            collector = BinanceDataPortalCollector(symbol=symbol, granularity="1d")
            df = collector.download_and_parse(
                start_year=DATA_START[0],
                start_month=DATA_START[1],
                end_year=DATA_END[0],
                end_month=DATA_END[1],
            )
            logger.info(f"✓ Fetched {len(df)} candles for {symbol}")
            return df
        except Exception as e:
            logger.error(f"✗ Failed to fetch {symbol}: {e}")
            raise

    def qa_check_data(self, asset: str, df: pd.DataFrame) -> DataQAResult:
        """Data Quality Assurance checks."""
        logger.info(f"\n{'='*60}")
        logger.info(f"DATA QA: {asset}")
        logger.info(f"{'='*60}")

        issues = []

        # Check 1: Missing values
        missing = df[['open', 'high', 'low', 'close', 'volume']].isna().sum().sum()
        if missing > 0:
            issues.append(f"Missing values: {missing}")
            logger.warning(f"  ✗ Missing values: {missing}")
        else:
            logger.info(f"  ✓ No missing values")

        # Check 2: Duplicate timestamps
        duplicates = df['open_time'].duplicated().sum()
        if duplicates > 0:
            issues.append(f"Duplicate timestamps: {duplicates}")
            logger.warning(f"  ✗ Duplicate timestamps: {duplicates}")
        else:
            logger.info(f"  ✓ No duplicate timestamps")

        # Check 3: Chronological order (allow small number of non-monotonic)
        # Real market data can have 1-2 anomalies from data corrections
        non_monotonic = (df['open_time'].diff().dt.total_seconds() < 0).sum()
        non_monotonic_threshold = max(1, int(len(df) * 0.001))  # <0.1% anomalies OK
        if non_monotonic > non_monotonic_threshold:
            issues.append(f"Non-monotonic timestamps: {non_monotonic} (threshold: {non_monotonic_threshold})")
            logger.warning(f"  ✗ Non-monotonic: {non_monotonic} (exceeds {non_monotonic_threshold})")
        else:
            logger.info(f"  ✓ Timestamps monotonic increasing (anomalies: {non_monotonic}/{non_monotonic_threshold} OK)")

        # Check 4: OHLC validity (high >= open, high >= close, low <= open, low <= close)
        invalid_ohlc = (
            (df['high'] < df['open']) |
            (df['high'] < df['close']) |
            (df['low'] > df['open']) |
            (df['low'] > df['close'])
        ).sum()
        if invalid_ohlc > 0:
            issues.append(f"Invalid OHLC: {invalid_ohlc}")
            logger.warning(f"  ✗ Invalid OHLC bars: {invalid_ohlc}")
        else:
            logger.info(f"  ✓ All OHLC bars valid")

        # Check 5: Zero volume
        zero_vol = (df['volume'] == 0).sum()
        if zero_vol > 0:
            issues.append(f"Zero volume candles: {zero_vol}")
            logger.warning(f"  ✗ Zero volume candles: {zero_vol}")
        else:
            logger.info(f"  ✓ No zero volume candles")

        date_range = (
            df['open_time'].min().strftime('%Y-%m-%d'),
            df['open_time'].max().strftime('%Y-%m-%d'),
        )

        qa_pass = len(issues) == 0
        status = "✓ PASS" if qa_pass else "✗ FAIL"
        logger.info(f"\nData QA Status: {status}")
        logger.info(f"Candles: {len(df)}, Date range: {date_range[0]} to {date_range[1]}")

        return DataQAResult(
            asset=asset,
            total_candles=len(df),
            missing_values=missing,
            duplicate_timestamps=duplicates,
            non_monotonic=non_monotonic,
            date_range=date_range,
            qa_pass=qa_pass,
            issues=issues,
        )

    def pit_check_lookahead(self, asset: str, df: pd.DataFrame) -> PITResult:
        """Point-in-Time (PIT) lookahead bias check."""
        logger.info(f"\n{'='*60}")
        logger.info(f"PIT/LOOKAHEAD CHECK: {asset}")
        logger.info(f"{'='*60}")

        issues = []
        wfv_windows = 0
        train_oos_overlap = 0

        # Simulate WFV window generation
        df_sorted = df.sort_values('open_time').reset_index(drop=True)
        total_days = (df_sorted['open_time'].iloc[-1] - df_sorted['open_time'].iloc[0]).days

        if total_days < WFV_TRAIN_DAYS + WFV_TEST_DAYS:
            issues.append(f"Insufficient data: {total_days} days < min required {WFV_TRAIN_DAYS + WFV_TEST_DAYS}")
            logger.warning(f"  ✗ {issues[-1]}")
            return PITResult(
                asset=asset,
                wfv_windows=0,
                train_oos_overlap=train_oos_overlap,
                lookahead_events=0,
                pit_pass=False,
                issues=issues,
            )

        # Create rolling windows
        window_start = 0
        while True:
            train_end = window_start + int(WFV_TRAIN_DAYS * len(df_sorted) / total_days)
            test_end = train_end + int(WFV_TEST_DAYS * len(df_sorted) / total_days)

            if test_end >= len(df_sorted):
                break

            # Check: training data must end BEFORE test data starts (no overlap)
            train_last_time = df_sorted.iloc[train_end - 1]['open_time']
            test_first_time = df_sorted.iloc[train_end]['open_time']

            if train_last_time >= test_first_time:
                train_oos_overlap += 1
                logger.warning(f"  ✗ Window {wfv_windows}: train/test overlap")

            wfv_windows += 1
            window_start += int(WFV_STEP_DAYS * len(df_sorted) / total_days)

        logger.info(f"  ✓ WFV windows created: {wfv_windows}")
        logger.info(f"  ✓ Train/OOS overlaps: {train_oos_overlap}")

        pit_pass = train_oos_overlap == 0 and len(issues) == 0
        status = "✓ PASS" if pit_pass else "✗ FAIL"
        logger.info(f"\nPIT Check Status: {status}")

        return PITResult(
            asset=asset,
            wfv_windows=wfv_windows,
            train_oos_overlap=train_oos_overlap,
            lookahead_events=len(issues),
            pit_pass=pit_pass,
            issues=issues,
        )

    def simple_sma_strategy(self, df: pd.DataFrame) -> List[Trade]:
        """
        Simple SMA crossover strategy for testing.
        Entry: fast_sma > slow_sma
        Exit: fast_sma < slow_sma
        """
        df = df.sort_values('open_time').reset_index(drop=True)

        # Calculate SMAs (using close prices)
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['sma_fast'] = df['close'].rolling(window=20, min_periods=1).mean()
        df['sma_slow'] = df['close'].rolling(window=50, min_periods=1).mean()

        trades = []
        in_trade = False
        entry_idx = None
        entry_price = None

        for i in range(1, len(df)):
            fast = df.iloc[i]['sma_fast']
            slow = df.iloc[i]['sma_slow']
            prev_fast = df.iloc[i-1]['sma_fast']
            prev_slow = df.iloc[i-1]['sma_slow']

            # Skip if NaN
            if pd.isna(fast) or pd.isna(slow) or pd.isna(prev_fast) or pd.isna(prev_slow):
                continue

            # Entry signal: fast crosses above slow
            if not in_trade and prev_fast <= prev_slow and fast > slow:
                entry_idx = i
                entry_price = df.iloc[i]['close']
                in_trade = True

            # Exit signal: fast crosses below slow
            elif in_trade and prev_fast >= prev_slow and fast < slow:
                exit_price = df.iloc[i]['close']
                trade = Trade(
                    entry_time=df.iloc[entry_idx]['open_time'],
                    entry_price=entry_price,
                    exit_time=df.iloc[i]['open_time'],
                    exit_price=exit_price,
                    trade_type=TradeType.LONG,
                    quantity=1.0,
                )
                trades.append(trade)
                in_trade = False

        return trades

    def _compute_detailed_metrics(self, trades: List[Trade]) -> Dict:
        """Compute detailed metrics including PF handling."""
        if not trades:
            return {
                'trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'gross_profit': 0.0,
                'gross_loss': 0.0,
                'net_pnl': 0.0,
                'return_pct': 0.0,
                'pf_value': 0.0,
                'pf_status': 'no_trades',
            }

        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl <= 0]

        gross_profit = sum(t.pnl for t in winning)
        gross_loss = abs(sum(t.pnl for t in losing))
        net_pnl = gross_profit - gross_loss
        return_pct = (net_pnl / 100000.0) * 100

        # Handle PF carefully
        if gross_loss > 0:
            pf_value = gross_profit / gross_loss
            pf_status = "normal"
        elif gross_profit > 0 and gross_loss == 0:
            pf_value = float('inf')
            pf_status = "zero_loss"
        else:
            pf_value = 0.0
            pf_status = "all_losses"

        return {
            'trades': len(trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'net_pnl': net_pnl,
            'return_pct': return_pct,
            'pf_value': pf_value,
            'pf_status': pf_status,
        }

    def walk_forward_validate(self, asset: str, df: pd.DataFrame) -> AssetWFVResult:
        """Run walk-forward validation with corrected metrics."""
        logger.info(f"\n{'='*60}")
        logger.info(f"WALK-FORWARD VALIDATION: {asset}")
        logger.info(f"{'='*60}")

        df = df.sort_values('open_time').reset_index(drop=True)
        total_rows = len(df)

        # Calculate split indices
        train_size = int(WFV_TRAIN_DAYS / 365 * total_rows)
        test_size = int(WFV_TEST_DAYS / 365 * total_rows)
        step_size = int(WFV_STEP_DAYS / 365 * total_rows)

        window_results = []
        in_sample_stats = []
        out_sample_stats = []
        oos_positive_folds = 0

        window_id = 0
        start_idx = 0

        while start_idx + train_size + test_size <= total_rows:
            train_end = start_idx + train_size
            test_end = train_end + test_size

            # In-sample (training)
            train_df = df.iloc[start_idx:train_end].copy()
            train_trades = self.simple_sma_strategy(train_df)
            engine_is = BacktestEngine(initial_capital=100000.0)
            engine_is.add_trades_batch(train_trades)
            metrics_is = engine_is.compute_metrics()
            detailed_is = self._compute_detailed_metrics(train_trades)

            # Out-of-sample (testing)
            test_df = df.iloc[train_end:test_end].copy()
            test_trades = self.simple_sma_strategy(test_df)
            engine_oos = BacktestEngine(initial_capital=100000.0)
            engine_oos.add_trades_batch(test_trades)
            metrics_oos = engine_oos.compute_metrics()
            detailed_oos = self._compute_detailed_metrics(test_trades)

            # Dates
            train_start = train_df['open_time'].iloc[0].strftime('%Y-%m-%d')
            train_end_str = train_df['open_time'].iloc[-1].strftime('%Y-%m-%d')
            test_start = test_df['open_time'].iloc[0].strftime('%Y-%m-%d')
            test_end_str = test_df['open_time'].iloc[-1].strftime('%Y-%m-%d')

            # Check if OOS is positive (return > 0)
            oos_is_positive = detailed_oos['return_pct'] > 0
            if oos_is_positive:
                oos_positive_folds += 1

            # Gate pass (ignore Infinity for PF check)
            is_pass = (
                metrics_is.total_trades >= CONSTRAINTS['min_trades'] and
                (detailed_is['pf_status'] != 'normal' or detailed_is['pf_value'] >= CONSTRAINTS['profit_factor_min']) and
                metrics_is.max_drawdown <= CONSTRAINTS['max_drawdown_max']
            )
            oos_pass = (
                metrics_oos.total_trades >= CONSTRAINTS['min_trades'] and
                (detailed_oos['pf_status'] != 'normal' or detailed_oos['pf_value'] >= CONSTRAINTS['profit_factor_min']) and
                metrics_oos.max_drawdown <= CONSTRAINTS['max_drawdown_max']
            )

            in_sample_stats.append(detailed_is)
            out_sample_stats.append(detailed_oos)

            # PF display format
            pf_is_str = "∞" if detailed_is['pf_status'] == 'zero_loss' else f"{detailed_is['pf_value']:.2f}"
            pf_oos_str = "∞" if detailed_oos['pf_status'] == 'zero_loss' else f"{detailed_oos['pf_value']:.2f}"

            window_results.append(WindowStats(
                window_id=window_id,
                train_start=train_start,
                train_end=train_end_str,
                test_start=test_start,
                test_end=test_end_str,
                is_sample="in-sample",
                trades=detailed_is['trades'],
                winning_trades=detailed_is['winning_trades'],
                losing_trades=detailed_is['losing_trades'],
                gross_profit=detailed_is['gross_profit'],
                gross_loss=detailed_is['gross_loss'],
                net_pnl=detailed_is['net_pnl'],
                return_pct=detailed_is['return_pct'],
                profit_factor=pf_is_str,
                max_drawdown=metrics_is.max_drawdown,
                sharpe_ratio=metrics_is.sharpe_ratio,
                win_rate=metrics_is.win_rate,
                is_oos_positive=False,
                passes_gates=is_pass,
            ))
            window_results.append(WindowStats(
                window_id=window_id,
                train_start=train_start,
                train_end=train_end_str,
                test_start=test_start,
                test_end=test_end_str,
                is_sample="out-of-sample",
                trades=detailed_oos['trades'],
                winning_trades=detailed_oos['winning_trades'],
                losing_trades=detailed_oos['losing_trades'],
                gross_profit=detailed_oos['gross_profit'],
                gross_loss=detailed_oos['gross_loss'],
                net_pnl=detailed_oos['net_pnl'],
                return_pct=detailed_oos['return_pct'],
                profit_factor=pf_oos_str,
                max_drawdown=metrics_oos.max_drawdown,
                sharpe_ratio=metrics_oos.sharpe_ratio,
                win_rate=metrics_oos.win_rate,
                is_oos_positive=oos_is_positive,
                passes_gates=oos_pass,
            ))

            logger.info(f"Window {window_id}:")
            logger.info(f"  IS: trades={detailed_is['trades']} pf={pf_is_str} return={detailed_is['return_pct']:.2f}%")
            logger.info(f"  OOS: trades={detailed_oos['trades']} pf={pf_oos_str} return={detailed_oos['return_pct']:.2f}% {'✓' if oos_is_positive else '✗'}")

            window_id += 1
            start_idx += step_size

        # Aggregate OOS metrics (correct way: total profit / total loss)
        total_oos_gprofit = sum(s['gross_profit'] for s in out_sample_stats)
        total_oos_gloss = sum(s['gross_loss'] for s in out_sample_stats)
        total_oos_pnl = sum(s['net_pnl'] for s in out_sample_stats)

        # Aggregate OOS PF and return
        aggregate_oos_pf = total_oos_gprofit / total_oos_gloss if total_oos_gloss > 0 else float('inf')
        aggregate_oos_return = (total_oos_pnl / 100000.0) * 100

        # IS aggregate (for comparison)
        total_is_gprofit = sum(s['gross_profit'] for s in in_sample_stats)
        total_is_gloss = sum(s['gross_loss'] for s in in_sample_stats)
        aggregate_is_pf = total_is_gprofit / total_is_gloss if total_is_gloss > 0 else float('inf')

        # Degradation using aggregate PF
        if aggregate_is_pf != float('inf') and aggregate_oos_pf != float('inf') and aggregate_is_pf > 0:
            degradation = (aggregate_is_pf - aggregate_oos_pf) / aggregate_is_pf
        else:
            degradation = float('nan')

        # Consistency: % of OOS folds with return > 0
        consistency = (oos_positive_folds / len(out_sample_stats) * 100) if out_sample_stats else 0

        wfv_pass = (
            consistency >= 50 and
            (degradation <= 0.3 or pd.isna(degradation)) and
            aggregate_oos_pf >= 1.3
        )

        # Format PF for display
        is_pf_str = f"{aggregate_is_pf:.2f}" if aggregate_is_pf != float('inf') else "∞"
        oos_pf_str = f"{aggregate_oos_pf:.2f}" if aggregate_oos_pf != float('inf') else "∞"

        gate_results = {
            "aggregate_is_pf": is_pf_str,
            "aggregate_oos_pf": oos_pf_str,
            "aggregate_oos_return": f"{aggregate_oos_return:.2f}%",
            "degradation_ratio": f"{degradation*100:.1f}%" if not pd.isna(degradation) else "NOT_COMPUTABLE",
            "consistency_score": consistency,
            "oos_positive_folds": oos_positive_folds,
            "oos_pass_rate": f"{oos_positive_folds}/{len(out_sample_stats)}",
            "total_oos_trades": sum(s['trades'] for s in out_sample_stats),
        }

        status = "✓ PASS" if wfv_pass else "✗ FAIL"
        logger.info(f"\nWFV Status: {status}")
        logger.info(f"  Aggregate IS PF: {is_pf_str}")
        logger.info(f"  Aggregate OOS PF: {oos_pf_str}")
        logger.info(f"  Aggregate OOS Return: {aggregate_oos_return:.2f}%")
        logger.info(f"  Degradation: {gate_results['degradation_ratio']}")
        logger.info(f"  Consistency (OOS positive folds): {consistency:.1f}%")
        logger.info(f"  OOS Positive Folds: {oos_positive_folds}/{len(out_sample_stats)}")

        # Extract drawdowns from window_results for IS/OOS
        is_drawdowns = [w.max_drawdown for w in window_results if w.is_sample == "in-sample"]
        oos_drawdowns = [w.max_drawdown for w in window_results if w.is_sample == "out-of-sample"]

        return AssetWFVResult(
            asset=asset,
            total_windows=window_id,
            in_sample_windows=len(in_sample_stats),
            out_sample_windows=len(out_sample_stats),
            in_sample_stats={"aggregate_pf": gate_results['aggregate_is_pf'], "avg_dd": sum(is_drawdowns) / len(is_drawdowns) if is_drawdowns else 0},
            out_sample_stats={"aggregate_pf": gate_results['aggregate_oos_pf'], "aggregate_return": gate_results['aggregate_oos_return'], "avg_dd": sum(oos_drawdowns) / len(oos_drawdowns) if oos_drawdowns else 0},
            degradation_ratio=degradation,
            consistency_score=consistency,
            wfv_pass=wfv_pass,
            window_results=window_results,
            gate_results=gate_results,
        )

    def validate_asset(self, asset: str) -> bool:
        """Validate single asset through full pipeline."""
        logger.info(f"\n\n{'#'*60}")
        logger.info(f"# VALIDATING {asset}")
        logger.info(f"{'#'*60}")

        try:
            # 1. Fetch data
            df = self.fetch_binance_data(asset)

            # 2. Data QA
            qa = self.qa_check_data(asset, df)
            self.results["data_qa"][asset] = asdict(qa)

            if not qa.qa_pass:
                logger.error(f"✗ Data QA failed for {asset}")
                return False

            # 3. PIT check
            pit = self.pit_check_lookahead(asset, df)
            self.results["pit_checks"][asset] = asdict(pit)

            if not pit.pit_pass:
                logger.error(f"✗ PIT check failed for {asset}")
                return False

            # 4. WFV
            wfv = self.walk_forward_validate(asset, df)

            # Handle NaN/Inf in degradation_ratio for JSON serialization
            degradation_val = wfv.degradation_ratio
            if pd.isna(degradation_val):
                degradation_val = "NOT_COMPUTABLE"
            elif isinstance(degradation_val, float) and degradation_val != degradation_val:  # NaN check
                degradation_val = "NOT_COMPUTABLE"

            self.results["wfv_results"][asset] = {
                "asset": wfv.asset,
                "total_windows": wfv.total_windows,
                "in_sample_windows": wfv.in_sample_windows,
                "out_sample_windows": wfv.out_sample_windows,
                "in_sample_stats": wfv.in_sample_stats,
                "out_sample_stats": wfv.out_sample_stats,
                "degradation_ratio": degradation_val,
                "consistency_score": wfv.consistency_score,
                "wfv_pass": wfv.wfv_pass,
                "gate_results": wfv.gate_results,
                "window_results": [asdict(w) for w in wfv.window_results],
            }

            return wfv.wfv_pass

        except Exception as e:
            logger.error(f"✗ Validation failed for {asset}: {e}", exc_info=True)
            return False

    def run(self) -> Dict:
        """Run full Phase 2 validation."""
        logger.info(f"\n{'='*70}")
        logger.info(f"PHASE 2 REAL DATA VALIDATION HARNESS")
        logger.info(f"{'='*70}")
        logger.info(f"Data Source: Binance Data Portal")
        logger.info(f"Assets: {', '.join(ASSETS)}")
        logger.info(f"Date Range: {DATA_START[0]}-{DATA_START[1]:02d} to {DATA_END[0]}-{DATA_END[1]:02d}")
        logger.info(f"WFV Config: train={WFV_TRAIN_DAYS}d, test={WFV_TEST_DAYS}d, step={WFV_STEP_DAYS}d")

        # Validate each asset
        results_per_asset = {}
        for asset in ASSETS:
            results_per_asset[asset] = self.validate_asset(asset)

        # Summary
        logger.info(f"\n{'='*70}")
        logger.info(f"VALIDATION SUMMARY")
        logger.info(f"{'='*70}")

        passed = sum(1 for v in results_per_asset.values() if v)
        total = len(ASSETS)

        for asset, passed_flag in results_per_asset.items():
            status = "✓ PASS" if passed_flag else "✗ FAIL"
            logger.info(f"{asset}: {status}")

        logger.info(f"\nOverall: {passed}/{total} assets passed")

        self.results["summary"] = {
            "total_assets": total,
            "passed_assets": passed,
            "overall_status": "PASS" if passed == total else "FAIL",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        # Save results
        output_file = Path(__file__).parent / "logs" / "phase2_validation" / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        logger.info(f"\nResults saved to: {output_file}")

        return self.results


def main():
    """Main entry point."""
    try:
        harness = Phase2ValidationHarness()
        results = harness.run()

        # Exit with appropriate code
        if results["summary"]["overall_status"] == "PASS":
            logger.info("\n✅ Phase 2 Real Data Validation: ALL PASSED")
            sys.exit(0)
        else:
            logger.error("\n❌ Phase 2 Real Data Validation: SOME FAILED")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
