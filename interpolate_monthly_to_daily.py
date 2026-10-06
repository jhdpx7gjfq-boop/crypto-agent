#!/usr/bin/env python3
"""
Interpolate monthly OHLCV candles to daily granularity.

Given monthly data (25 candles = 2 years), generates synthetic daily candles
by interpolating OHLC values and distributing volume across trading days.

Note: This is synthetic data interpolated from real aggregated monthly candles.
Not true daily prices, but suitable for validation window analysis.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


def interpolate_monthly_to_daily(monthly_data: Dict) -> Dict:
    """
    Interpolate monthly candles to daily granularity.

    Strategy:
    - Each monthly candle spans ~30 days (adjusted for actual days in month)
    - Open: use monthly open for first day, interpolate toward close
    - High: assume high reached mid-month, interpolate down
    - Low: distributed throughout, use monthly low as minimum
    - Close: converge to monthly close by month-end
    - Volume: distribute across trading days (assume ~22 trading days/month)
    """

    symbol = monthly_data.get("symbol", "UNKNOWN")
    monthly_candles = monthly_data.get("candles", [])

    if not monthly_candles:
        return None

    daily_candles = []

    for month_idx, monthly in enumerate(monthly_candles):
        month_open = float(monthly["open"])
        month_high = float(monthly["high"])
        month_low = float(monthly["low"])
        month_close = float(monthly["close"])
        month_volume = float(monthly["volume"])
        month_ts_raw = int(monthly["timestamp"])

        # Convert milliseconds to seconds if needed
        month_ts = month_ts_raw // 1000 if month_ts_raw > 9999999999 else month_ts_raw

        # Estimate days in this month
        # Use timestamp to determine actual date
        month_date = datetime.fromtimestamp(month_ts)

        # Get days in this month
        if month_idx < len(monthly_candles) - 1:
            next_ts_raw = int(monthly_candles[month_idx + 1]["timestamp"])
            next_ts = next_ts_raw // 1000 if next_ts_raw > 9999999999 else next_ts_raw
            next_date = datetime.fromtimestamp(next_ts)
            days_in_period = (next_date - month_date).days
        else:
            # Last month: estimate 30 days
            days_in_period = 30

        # Assume 22 trading days per month (on average)
        trading_days = min(days_in_period, 22)
        if trading_days < 5:
            trading_days = 22  # Fallback if calculation seems wrong

        # Volume per trading day
        vol_per_day = month_volume / trading_days

        # Generate daily candles for this month
        for day_offset in range(trading_days):
            day_ts = month_ts + (day_offset * 86400)  # Add days in seconds
            day_frac = day_offset / max(trading_days - 1, 1)  # 0 to 1

            # Interpolate OHLC
            # Open: start at month_open, gradually trend to close
            day_open = month_open + (month_close - month_open) * day_frac * 0.5

            # High: assume peak early-mid month, then decline
            high_peak_frac = 0.3  # High reached ~30% through month
            if day_frac < high_peak_frac:
                # Rising to peak
                day_high = month_open + (month_high - month_open) * (day_frac / high_peak_frac)
            else:
                # Declining from peak
                day_high = month_high - (month_high - month_close) * ((day_frac - high_peak_frac) / (1 - high_peak_frac))

            # Low: distributed throughout, floor at month_low
            day_low = month_low + (month_close - month_low) * (1 - day_frac) * 0.3
            day_low = max(day_low, month_low * 0.99)

            # Close: converge to month_close by end of month
            day_close = month_open + (month_close - month_open) * day_frac

            # Ensure valid OHLC relationships
            day_high = max(day_high, day_open, day_close)
            day_low = min(day_low, day_open, day_close)

            daily_candle = {
                "timestamp": day_ts,
                "open": round(day_open, 2),
                "high": round(day_high, 2),
                "low": round(day_low, 2),
                "close": round(day_close, 2),
                "volume": round(vol_per_day, 2)
            }

            daily_candles.append(daily_candle)

    return {
        "symbol": symbol,
        "source": f"Interpolated from {monthly_data.get('source', 'Unknown')}",
        "data_note": "Synthetic daily candles interpolated from monthly OHLCV aggregates. Not true daily prices, but suitable for validation window analysis.",
        "original_count": len(monthly_candles),
        "interpolated_count": len(daily_candles),
        "count": len(daily_candles),
        "date_range": {
            "start": daily_candles[0]["timestamp"] if daily_candles else None,
            "end": daily_candles[-1]["timestamp"] if daily_candles else None,
            "days_coverage": len(daily_candles)
        },
        "candles": daily_candles
    }


def main():
    """Interpolate all monthly OHLCV files to daily."""
    data_dir = Path(__file__).parent / "real_market_data"

    print(f"\n{'='*70}")
    print(f"Monthly → Daily Interpolation")
    print(f"{'='*70}\n")

    # Find all monthly data files
    monthly_files = list(data_dir.glob("*_tipransk_real_730d.json"))

    if not monthly_files:
        print(f"❌ No monthly OHLCV files found in {data_dir}")
        return False

    results = {}

    for monthly_file in sorted(monthly_files):
        print(f"Processing: {monthly_file.name}")

        try:
            with open(monthly_file, "r") as f:
                monthly_data = json.load(f)

            # Interpolate
            daily_data = interpolate_monthly_to_daily(monthly_data)

            if not daily_data:
                print(f"  ❌ Interpolation failed\n")
                results[monthly_file.stem] = {"status": "failed"}
                continue

            # Save interpolated data
            symbol = daily_data["symbol"]
            output_file = data_dir / f"{symbol}_interpolated_daily_{daily_data['count']}d.json"

            with open(output_file, "w") as f:
                json.dump(daily_data, f, indent=2)

            print(f"  ✅ Interpolated {daily_data['original_count']} months → {daily_data['count']} days")
            print(f"  📁 Saved: {output_file.name}\n")

            results[symbol] = {
                "status": "success",
                "monthly_candles": daily_data["original_count"],
                "daily_candles": daily_data["count"],
                "file": output_file.name
            }

        except Exception as e:
            print(f"  ❌ Error: {e}\n")
            results[monthly_file.stem] = {"status": "failed", "error": str(e)}

    # Summary
    print(f"{'='*70}")
    print(f"Summary:")
    print(f"{'='*70}")

    for symbol, result in results.items():
        if result["status"] == "success":
            print(f"✅ {symbol}: {result['monthly_candles']} months → {result['daily_candles']} daily candles")
            print(f"   File: {result['file']}")
        else:
            print(f"❌ {symbol}: Failed ({result.get('error', 'Unknown error')})")

    success_count = sum(1 for r in results.values() if r["status"] == "success")
    total_count = len(results)

    print(f"\n{success_count}/{total_count} symbols processed successfully")
    print(f"{'='*70}\n")

    return success_count == total_count


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
