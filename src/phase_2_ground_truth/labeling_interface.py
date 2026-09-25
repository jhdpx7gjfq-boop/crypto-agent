#!/usr/bin/env python3
"""
Phase 2 Ground Truth Labeling Interface

Interactive CLI for labeling coins as Q1 (dormant) or Q2 (resurrection).
Supports CSV import/export and confidence level tracking.

Timeline: Oct 16-23, 2026 (overlaps Phase 1)
Gate: Ground Truth Freeze (Oct 23)
"""

import os
import sys
import json
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd

# Configuration
DATA_DIR = Path(__file__).parent.parent.parent / "data"
GT_DIR = DATA_DIR / "ground_truth" / "phase_2"
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_2"

# Setup logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"labeling_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Q1-Q2 Definitions (from PHASE_2_GROUND_TRUTH_SPEC.md)
Q1_DEFINITION = """
Q1: DORMANT TOKEN
- Market cap: <$50M
- 24h volume: <$1M
- Active addresses: <100K
- Dormancy period: ≥90 days (no significant activity)
- Status: Listed on CoinGecko but inactive
"""

Q2_DEFINITION = """
Q2: RESURRECTION (Token Revival)
- Volume increased 3x+ from dormant baseline
- Active addresses increased 2x+ from dormant baseline
- Price increased 50%+ from dormant low
- At least 2 of 3 conditions must be true
- Observation window: Last 6 months
"""

CONFIDENCE_LEVELS = {
    "1": ("Very Low", "Unsure, ambiguous data, insufficient evidence"),
    "2": ("Low", "Some evidence but conflicting signals"),
    "3": ("Medium", "Clear signals but some uncertainty"),
    "4": ("High", "Strong evidence, clear classification"),
    "5": ("Very High", "Definitive, unambiguous classification")
}


class LabelingInterface:
    def __init__(self, data_dir=GT_DIR):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.labels = {}
        self.confidence_scores = {}
        self.labeler_name = None

    def display_coin_info(self, coin_id: str, coin_symbol: str) -> None:
        """Display coin information for labeling context"""
        print(f"\n{'='*60}")
        print(f"COIN: {coin_symbol.upper()} ({coin_id})")
        print(f"{'='*60}")

        # Try to load OHLCV data if available
        parquet_file = DATA_DIR / "raw" / "phase_1" / f"{coin_symbol}_{coin_id}.parquet"
        if parquet_file.exists():
            try:
                df = pd.read_parquet(parquet_file)
                print(f"\nData Points: {len(df)}")
                print(f"Price Range: ${df['close'].min():.8f} - ${df['close'].max():.8f}")
                print(f"Latest Price: ${df['close'].iloc[-1]:.8f}")
                print(f"Volume (avg): {df['volume'].mean():.2f}")
                print(f"Date Range: {df.index.min().date()} to {df.index.max().date()}")
            except Exception as e:
                logger.debug(f"Could not load data for {coin_symbol}: {e}")

        print(f"\n{Q1_DEFINITION}")
        print(f"\n{Q2_DEFINITION}")

    def get_label_input(self) -> Tuple[str, int]:
        """Get label and confidence from user"""
        while True:
            print("\nLabel this coin:")
            print("  Q1 = Dormant (inactive, low volume, low addresses)")
            print("  Q2 = Resurrection (revival, 3x vol, 2x addr, 50% price)")
            print("  SKIP = Skip this coin")
            print("  EXIT = Exit labeling")

            label_input = input("\nEnter label (Q1/Q2/SKIP/EXIT): ").strip().upper()

            if label_input in ["Q1", "Q2", "SKIP", "EXIT"]:
                if label_input == "EXIT":
                    return "EXIT", 0
                elif label_input == "SKIP":
                    return "SKIP", 0
                else:
                    # Get confidence
                    while True:
                        conf_input = input("Confidence level (1-5): ").strip()
                        if conf_input in ["1", "2", "3", "4", "5"]:
                            conf_level, conf_desc = CONFIDENCE_LEVELS[conf_input]
                            print(f"  ✓ {conf_level}: {conf_desc}")
                            return label_input, int(conf_input)
                        else:
                            print("  Please enter 1-5")
            else:
                print("  Invalid input. Please enter Q1, Q2, SKIP, or EXIT")

    def label_coins_interactive(self, coin_list: List[Tuple[str, str]], start_index: int = 0):
        """Interactive labeling session"""
        print(f"\n{'='*60}")
        print("PHASE 2 GROUND TRUTH LABELING")
        print(f"{'='*60}")

        # Get labeler name
        if not self.labeler_name:
            self.labeler_name = input("Labeler name: ").strip()

        labeled_count = 0
        skipped_count = 0

        for i in range(start_index, len(coin_list)):
            coin_id, coin_symbol = coin_list[i]

            # Display info
            self.display_coin_info(coin_id, coin_symbol)

            # Get label
            label, confidence = self.get_label_input()

            if label == "EXIT":
                print(f"\nSession ended by user")
                break
            elif label == "SKIP":
                print(f"→ Skipped {coin_symbol}")
                skipped_count += 1
            else:
                self.labels[coin_id] = {
                    "symbol": coin_symbol,
                    "label": label,
                    "confidence": confidence
                }
                self.confidence_scores[coin_id] = confidence
                labeled_count += 1
                print(f"✓ Labeled {coin_symbol} as {label} (confidence: {confidence})")

            # Progress
            print(f"\nProgress: {labeled_count} labeled, {skipped_count} skipped, {i+1}/{len(coin_list)}")

            # Ask to continue
            if i < len(coin_list) - 1:
                cont = input("\nContinue? (Y/N): ").strip().upper()
                if cont != "Y":
                    break

        # Summary
        print(f"\n{'='*60}")
        print(f"LABELING SESSION COMPLETE")
        print(f"{'='*60}")
        print(f"Labeled: {labeled_count} coins")
        print(f"Skipped: {skipped_count} coins")
        print(f"Session time: {datetime.now().isoformat()}")

        return labeled_count, skipped_count

    def import_from_csv(self, csv_file: Path) -> int:
        """Import labels from CSV file"""
        logger.info(f"Importing labels from {csv_file}")

        count = 0
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                coin_id = row.get("coin_id")
                symbol = row.get("symbol")
                label = row.get("label")
                confidence = int(row.get("confidence", 1))

                if coin_id and label:
                    self.labels[coin_id] = {
                        "symbol": symbol,
                        "label": label,
                        "confidence": confidence
                    }
                    count += 1

        logger.info(f"Imported {count} labels")
        return count

    def export_to_csv(self, output_file: Path) -> Path:
        """Export labels to CSV"""
        logger.info(f"Exporting labels to {output_file}")

        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["coin_id", "symbol", "label", "confidence", "labeler", "timestamp"])
            writer.writeheader()

            for coin_id, label_info in self.labels.items():
                writer.writerow({
                    "coin_id": coin_id,
                    "symbol": label_info["symbol"],
                    "label": label_info["label"],
                    "confidence": label_info["confidence"],
                    "labeler": self.labeler_name or "unknown",
                    "timestamp": datetime.now().isoformat()
                })

        logger.info(f"Exported {len(self.labels)} labels to {output_file}")
        return output_file

    def export_to_json(self, output_file: Path) -> Path:
        """Export labels to JSON"""
        logger.info(f"Exporting labels to {output_file}")

        output_file.parent.mkdir(parents=True, exist_ok=True)

        export_data = {
            "timestamp": datetime.now().isoformat(),
            "labeler": self.labeler_name or "unknown",
            "total_labels": len(self.labels),
            "labels": self.labels,
            "confidence_distribution": self._get_confidence_distribution()
        }

        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported {len(self.labels)} labels to {output_file}")
        return output_file

    def _get_confidence_distribution(self) -> Dict:
        """Get distribution of confidence levels"""
        dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for conf in self.confidence_scores.values():
            if conf in dist:
                dist[conf] += 1
        return dist

    def get_summary(self) -> Dict:
        """Get labeling summary statistics"""
        q1_count = sum(1 for l in self.labels.values() if l["label"] == "Q1")
        q2_count = sum(1 for l in self.labels.values() if l["label"] == "Q2")

        avg_confidence = sum(self.confidence_scores.values()) / len(self.confidence_scores) if self.confidence_scores else 0

        return {
            "total_labeled": len(self.labels),
            "q1_count": q1_count,
            "q2_count": q2_count,
            "q1_percent": round(100 * q1_count / len(self.labels), 1) if self.labels else 0,
            "q2_percent": round(100 * q2_count / len(self.labels), 1) if self.labels else 0,
            "avg_confidence": round(avg_confidence, 2),
            "confidence_distribution": self._get_confidence_distribution(),
            "labeler": self.labeler_name or "unknown",
            "timestamp": datetime.now().isoformat()
        }


def create_labeling_template(output_file: Path, coin_list: List[Tuple[str, str]]) -> Path:
    """Create CSV template for offline labeling"""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["coin_id", "symbol", "label", "confidence", "notes"])
        writer.writeheader()

        for coin_id, symbol in coin_list:
            writer.writerow({
                "coin_id": coin_id,
                "symbol": symbol,
                "label": "",  # Q1, Q2, or SKIP
                "confidence": "",  # 1-5
                "notes": ""  # Optional notes
            })

    logger.info(f"Created labeling template: {output_file}")
    return output_file


if __name__ == "__main__":
    # Example: Load coin list and start interactive labeling
    interface = LabelingInterface()

    # Create template or import existing labels
    if len(sys.argv) > 1:
        if sys.argv[1] == "--import":
            csv_file = Path(sys.argv[2])
            interface.import_from_csv(csv_file)
            summary = interface.get_summary()
            print(json.dumps(summary, indent=2))
        elif sys.argv[1] == "--template":
            output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else GT_DIR / "labeling_template.csv"
            # Load coin list from Phase 1 data
            data_dir = DATA_DIR / "raw" / "phase_1"
            coin_files = list(data_dir.glob("*.parquet"))
            coin_list = [(f.stem.split("_")[1], f.stem.split("_")[0]) for f in coin_files]
            create_labeling_template(output_file, coin_list)
    else:
        print("Usage:")
        print("  python3 labeling_interface.py --template [output_file]")
        print("  python3 labeling_interface.py --import <csv_file>")
