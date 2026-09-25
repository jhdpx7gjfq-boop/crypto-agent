"""
Level 4: OOS/WFV Validation for Spring Detector

Walk-Forward Validation de Spring Detector sur 3+ régimes.
Mesure IC_OOS, stabilité, et reproductibilité.

Usage:
    python src/validation/level_4_oos_wfv.py --ticker BTC/USDT --start 2021-01-01
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RegimeDefinition:
    """Définition d'un régime de marché."""
    name: str
    start_date: str
    end_date: str
    description: str


# Régimes majeurs pour BTC depuis 2021
REGIMES = [
    RegimeDefinition(
        name="bull_2021",
        start_date="2021-01-01",
        end_date="2021-11-30",
        description="Bull market : accumulation → ATH $69k"
    ),
    RegimeDefinition(
        name="bear_2022",
        start_date="2022-01-01",
        end_date="2022-12-31",
        description="Bear market : correction → bottom ~$16k"
    ),
    RegimeDefinition(
        name="recovery_2023",
        start_date="2023-01-01",
        end_date="2023-12-31",
        description="Recovery & consolidation"
    ),
    RegimeDefinition(
        name="bull_2024_partial",
        start_date="2024-01-01",
        end_date="2024-09-25",
        description="Bull setup & volatility"
    ),
]


@dataclass
class WFVWindow:
    """Une fenêtre de walk-forward validation."""
    window_id: int
    regime: str
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_size: int
    test_size: int


class DataLoader:
    """Charge les données BTC depuis Binance ou fichier local."""

    @staticmethod
    def load_binance(ticker="BTCUSDT", interval="1d", start_date="2020-01-01"):
        """
        Charge données historiques depuis Binance.
        Nécessite : pip install ccxt
        """
        try:
            import ccxt
            exchange = ccxt.binance()

            start_ts = exchange.parse8601(f"{start_date}T00:00:00Z")
            ohlcv_data = []

            while start_ts < datetime.now().timestamp() * 1000:
                ohlcv = exchange.fetch_ohlcv(ticker, interval, since=int(start_ts))
                if not ohlcv:
                    break
                ohlcv_data.extend(ohlcv)
                start_ts = ohlcv[-1][0] + 1

            df = pd.DataFrame(
                ohlcv_data,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            return df.set_index("timestamp")

        except ImportError:
            logger.warning("ccxt not installed, using fallback")
            return None

    @staticmethod
    def load_csv(filepath: str) -> pd.DataFrame:
        """Charge données depuis CSV (backup)."""
        df = pd.read_csv(filepath, parse_dates=["timestamp"])
        return df.set_index("timestamp")


class WFVPipeline:
    """Walk-Forward Validation pipeline pour Spring Detector."""

    def __init__(self,
                 train_period_days: int = 180,
                 test_period_days: int = 30,
                 overlap_days: int = 0):
        self.train_period = timedelta(days=train_period_days)
        self.test_period = timedelta(days=test_period_days)
        self.overlap = timedelta(days=overlap_days)

    def create_windows(self, regime: RegimeDefinition) -> List[WFVWindow]:
        """Créer les fenêtres WFV pour un régime."""
        start = pd.to_datetime(regime.start_date)
        end = pd.to_datetime(regime.end_date)

        windows = []
        window_id = 0
        current_train_start = start

        while current_train_start + self.train_period < end:
            train_end = current_train_start + self.train_period
            test_start = train_end + self.overlap
            test_end = test_start + self.test_period

            if test_end > end:
                break

            windows.append(WFVWindow(
                window_id=window_id,
                regime=regime.name,
                train_start=current_train_start.strftime("%Y-%m-%d"),
                train_end=train_end.strftime("%Y-%m-%d"),
                test_start=test_start.strftime("%Y-%m-%d"),
                test_end=test_end.strftime("%Y-%m-%d"),
                train_size=int((train_end - current_train_start).days),
                test_size=int((test_end - test_start).days)
            ))

            # Sliding : avancer d'un mois
            current_train_start += timedelta(days=30)
            window_id += 1

        return windows

    def validate_window(self,
                       detector,
                       df: pd.DataFrame,
                       window: WFVWindow) -> Dict:
        """Valider Spring Detector sur une fenêtre WFV (PIT)."""

        # Filter data by date range (inclusive)
        train_mask = (df.index >= window.train_start) & (df.index <= window.train_end)
        test_mask = (df.index >= window.test_start) & (df.index <= window.test_end)

        train_data = df[train_mask]
        test_data = df[test_mask]

        if len(test_data) < 5:
            logger.warning(f"Not enough test data for window {window.window_id}")
            return None

        # Classifier each point in test set with PIT (point-in-time)
        predictions = []
        for test_timestamp in test_data.index:
            # PIT: use ONLY data available at this timestamp (exclusive)
            pit_data = df[df.index < test_timestamp]
            if len(pit_data) < 30:  # Minimum for range detection
                continue

            result = detector.classify(f"BTC_window{window.window_id}", pit_data)
            next_close = test_data.loc[test_timestamp, "close"] if test_timestamp in test_data.index else None

            predictions.append({
                "timestamp": test_timestamp,
                "state": result.state,
                "range_low": result.evidence.get("range_low"),
                "sweep_low": result.evidence.get("sweep_low"),
                "recovery_pct": result.evidence.get("recovery_pct"),
                "next_close": next_close,
            })

        if not predictions:
            logger.warning(f"No predictions for window {window.window_id}")
            return None

        return {
            "window_id": window.window_id,
            "regime": window.regime,
            "train_period": f"{window.train_start} to {window.train_end}",
            "test_period": f"{window.test_start} to {window.test_end}",
            "train_size": len(train_data),
            "test_size": len(test_data),
            "predictions": predictions,
            "n_predictions": len(predictions),
        }


class ICCalculator:
    """Calcule Information Coefficient et statistiques associées."""

    @staticmethod
    def compute_signal_target(predictions: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extrait signal et target pour IC calculation.

        Signal : score numérique du sweep depth
        Target : +1 si prix monte après (OOS), -1 si baisse
        """
        signals = []
        targets = []

        for i, pred in enumerate(predictions[:-1]):  # Skip last (pas de target future)
            if pred["sweep_low"] is None:
                continue

            # Signal : sweep depth (plus profond = plus de potentiel)
            sweep_depth = pred.get("sweep_depth", 0)
            signals.append(sweep_depth if sweep_depth else 0)

            # Target : prix monte-t-il dans les 5 prochains candles ?
            # (simplifié : utiliser recovery_pct du candle suivant)
            next_recovery = predictions[i + 1].get("recovery_pct", 0)
            targets.append(1 if next_recovery > 0 else -1)

        return np.array(signals), np.array(targets)

    @staticmethod
    def rank_ic(signals: np.ndarray, targets: np.ndarray) -> float:
        """Information Coefficient = corrélation Spearman."""
        if len(signals) < 2:
            return 0.0

        from scipy.stats import spearmanr
        corr, p_value = spearmanr(signals, targets)
        return float(corr) if not np.isnan(corr) else 0.0

    @staticmethod
    def hit_rate(predictions: List[Dict]) -> float:
        """Pourcentage de prédictions correctes (signal vs next move)."""
        correct = 0
        total = 0

        for i, pred in enumerate(predictions[:-1]):
            state = pred["state"]
            range_low = pred.get("range_low")
            next_close = pred.get("next_close")

            if range_low is None or next_close is None:
                continue

            # Signal validation:
            # SPRING_CANDIDATE should precede upward move
            # Non-SPRING should precede flat/down move
            next_move_up = next_close > range_low

            if state == "SPRING_CANDIDATE" and next_move_up:
                correct += 1
            elif state != "SPRING_CANDIDATE" and not next_move_up:
                correct += 1

            total += 1

        return correct / total if total > 0 else 0.5


class ValidationReporter:
    """Génère rapports de validation."""

    @staticmethod
    def summarize_oos(results: List[Dict]) -> Dict:
        """Résumé OOS des fenêtres WFV."""
        ics = []
        hit_rates = []

        for result in results:
            if result and "predictions" in result:
                signals, targets = ICCalculator.compute_signal_target(result["predictions"])
                if len(signals) > 0:
                    ic = ICCalculator.rank_ic(signals, targets)
                    hit_rate = ICCalculator.hit_rate(result["predictions"])

                    ics.append(ic)
                    hit_rates.append(hit_rate)

        if not ics:
            return {}

        return {
            "ic_mean": float(np.mean(ics)),
            "ic_std": float(np.std(ics)),
            "ic_min": float(np.min(ics)),
            "ic_max": float(np.max(ics)),
            "hit_rate_mean": float(np.mean(hit_rates)),
            "hit_rate_std": float(np.std(hit_rates)),
            "n_windows": len(ics),
            "stability": float(1 - (np.std(ics) / (np.mean(ics) + 1e-6))),
        }

    @staticmethod
    def generate_report(results: List[Dict], output_path: str):
        """Génère rapport JSON + texte."""
        summary = ValidationReporter.summarize_oos(results)

        report = {
            "validation_date": datetime.now().isoformat(),
            "component": "Spring Detector",
            "level": 4,
            "summary": summary,
            "window_results": results,
        }

        # Sauvegarder JSON
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        # Rapport texte
        txt_path = output_path.replace(".json", ".txt")
        with open(txt_path, "w") as f:
            f.write("=" * 60 + "\n")
            f.write("SPRING DETECTOR - LEVEL 4 VALIDATION REPORT\n")
            f.write("=" * 60 + "\n\n")

            f.write("SUMMARY OOS/WFV\n")
            f.write("-" * 60 + "\n")
            for key, val in summary.items():
                f.write(f"{key:25s}: {val:.6f}\n" if isinstance(val, float) else f"{key:25s}: {val}\n")

            f.write("\n\nCRITERIA CHECK\n")
            f.write("-" * 60 + "\n")
            f.write(f"✅ IC_OOS > 0.01        : {summary.get('ic_mean', 0) > 0.01}\n")
            f.write(f"✅ Hit rate > 52%      : {summary.get('hit_rate_mean', 0) > 0.52}\n")
            f.write(f"✅ Stability > 0.75    : {summary.get('stability', 0) > 0.75}\n")

            gate = (summary.get('ic_mean', 0) > 0.01 and
                   summary.get('hit_rate_mean', 0) > 0.52 and
                   summary.get('stability', 0) > 0.75)
            f.write(f"\n📊 GATE STATUS: {'✅ ACCEPT' if gate else '❌ REJECT'}\n")

        logger.info(f"Report saved: {output_path}")
        return report


if __name__ == "__main__":
    import argparse
    import os
    from src.data.spring_detector import SpringDetector
    from src.validation.data_sourcing import get_btc_data

    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="BTCUSDT")
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--source", default="binance", help="binance, yfinance, or CSV path")
    parser.add_argument("--output", default="reports/validation/spring_detector_level4.json")
    args = parser.parse_args()

    # Create output directory
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    logger.info("=" * 60)
    logger.info("Spring Detector Level 4 OOS/WFV Validation")
    logger.info("=" * 60)
    logger.info(f"Ticker: {args.ticker}")
    logger.info(f"Start: {args.start}")
    logger.info(f"Regimes: {len(REGIMES)}")
    logger.info(f"Source: {args.source}")

    # Load data
    logger.info("\n[1/5] Loading BTC OHLCV data...")
    df = get_btc_data(source=args.source, start_date=args.start)
    if df is None:
        logger.error("Failed to load data. Exiting.")
        exit(1)

    logger.info(f"✅ Loaded {len(df)} candles ({df.index[0]} to {df.index[-1]})")

    # Initialize detector and WFV pipeline
    detector = SpringDetector()
    pipeline = WFVPipeline(train_period_days=180, test_period_days=30, overlap_days=0)

    # Run WFV on each regime
    logger.info("\n[2/5] Creating WFV windows for each regime...")
    all_results = []

    for regime in REGIMES:
        logger.info(f"\n  Regime: {regime.name}")
        logger.info(f"  Period: {regime.start_date} to {regime.end_date}")
        logger.info(f"  Desc: {regime.description}")

        windows = pipeline.create_windows(regime)
        logger.info(f"  Created {len(windows)} WFV windows")

        # Run validation on each window
        logger.info(f"\n[3/5] Running Spring Detector on windows (PIT)...")
        for i, window in enumerate(windows):
            logger.info(f"    Window {window.window_id}/{len(windows)-1}: "
                       f"{window.train_start} to {window.test_end}")

            result = pipeline.validate_window(detector, df, window)
            if result:
                all_results.append(result)

    # Calculate metrics
    logger.info(f"\n[4/5] Calculating IC and Hit Rates...")
    summary = ValidationReporter.summarize_oos(all_results)

    logger.info(f"  IC Mean: {summary.get('ic_mean', 0):.6f}")
    logger.info(f"  IC Std: {summary.get('ic_std', 0):.6f}")
    logger.info(f"  Hit Rate: {summary.get('hit_rate_mean', 0):.4%}")
    logger.info(f"  Stability: {summary.get('stability', 0):.4f}")

    # Generate report
    logger.info(f"\n[5/5] Generating report...")
    report = ValidationReporter.generate_report(all_results, args.output)

    logger.info(f"✅ Report saved to {args.output}")
    logger.info("=" * 60)

    # Gate decision
    gate = (summary.get('ic_mean', 0) > 0.01 and
           summary.get('hit_rate_mean', 0) > 0.52 and
           summary.get('stability', 0) > 0.75)

    if gate:
        logger.info("✅ GATE PASSED: Spring Detector qualifies for Phase B")
    else:
        logger.info("❌ GATE FAILED: Refinement needed")
        if summary.get('ic_mean', 0) <= 0.01:
            logger.info("  → IC too low (need > 0.01)")
        if summary.get('hit_rate_mean', 0) <= 0.52:
            logger.info("  → Hit rate too low (need > 52%)")
        if summary.get('stability', 0) <= 0.75:
            logger.info("  → Stability too low (need > 0.75)")
