"""Convert TipRanks monthly OHLCV to daily-compatible format for RRP validation."""

import json
from pathlib import Path

# Real data fetched from TipRanks (monthly bars)
REAL_DATA = {
    "BTC": {
        "summary": {
            "symbol": "BTCUSD",
            "windowStart": "2024-09-25",
            "windowEnd": "2026-09-25",
            "tradingDays": 731,
            "changePctOverWindow": 33.73,
        },
        "series": [
            {"symbol": "BTCUSD", "date": "2026-09-01", "endDate": "2026-09-25", "open": 78562.74, "high": 87397, "low": 74887.5, "close": 84425, "volume": 820522781071},
            {"symbol": "BTCUSD", "date": "2026-08-01", "endDate": "2026-08-31", "open": 62826.69, "high": 81479.5, "low": 62209.81, "close": 78562.74, "volume": 884000292422},
            {"symbol": "BTCUSD", "date": "2026-07-01", "endDate": "2026-07-31", "open": 58523.93, "high": 66923.95, "low": 57717.55, "close": 62825.9, "volume": 823927557627},
            {"symbol": "BTCUSD", "date": "2026-06-01", "endDate": "2026-06-30", "open": 73575.18, "high": 73978.52, "low": 58000, "close": 58523.93, "volume": 1038455282923},
            {"symbol": "BTCUSD", "date": "2026-05-01", "endDate": "2026-05-31", "open": 76305.78, "high": 82814.23, "low": 72364.13, "close": 73575.17, "volume": 1009292239788},
            {"symbol": "BTCUSD", "date": "2026-04-01", "endDate": "2026-04-30", "open": 68221.84, "high": 79523, "low": 65696.96, "close": 76305.78, "volume": 1135113008772},
            {"symbol": "BTCUSD", "date": "2026-03-01", "endDate": "2026-03-31", "open": 66971.54, "high": 76022.6, "low": 64938.66, "close": 68221.85, "volume": 1367098899028},
            {"symbol": "BTCUSD", "date": "2026-02-01", "endDate": "2026-02-28", "open": 78648, "high": 79339, "low": 60001, "close": 66967.85, "volume": 1435571601579},
            {"symbol": "BTCUSD", "date": "2026-01-01", "endDate": "2026-01-31", "open": 87497.95, "high": 97963.62, "low": 75644.15, "close": 78648, "volume": 1269604302763},
            {"symbol": "BTCUSD", "date": "2025-12-01", "endDate": "2025-12-31", "open": 90364, "high": 94640.66, "low": 83800, "close": 87497.94, "volume": 1545983468981},
            {"symbol": "BTCUSD", "date": "2025-11-01", "endDate": "2025-11-30", "open": 109555.63, "high": 111221.99, "low": 80524.65, "close": 90369.51, "volume": 2265472435026},
            {"symbol": "BTCUSD", "date": "2025-10-01", "endDate": "2025-10-31", "open": 114067.71, "high": 126296, "low": 103516.75, "close": 109555.27, "volume": 2315849280338},
            {"symbol": "BTCUSD", "date": "2025-09-01", "endDate": "2025-09-30", "open": 108247.95, "high": 117998.17, "low": 107250, "close": 114067.71, "volume": 1503477503857},
            {"symbol": "BTCUSD", "date": "2025-08-01", "endDate": "2025-08-31", "open": 115756.12, "high": 124533, "low": 107369.69, "close": 108247.95, "volume": 2099536455649},
            {"symbol": "BTCUSD", "date": "2025-07-01", "endDate": "2025-07-31", "open": 107173.21, "high": 123231.07, "low": 105119.7, "close": 115761.13, "volume": 2118488181137},
            {"symbol": "BTCUSD", "date": "2025-06-01", "endDate": "2025-06-30", "open": 104645.87, "high": 110651.12, "low": 98225.01, "close": 107173.21, "volume": 1467504742273},
            {"symbol": "BTCUSD", "date": "2025-05-01", "endDate": "2025-05-31", "open": 94182.55, "high": 112000, "low": 93363.28, "close": 104645.87, "volume": 1564386867065},
            {"symbol": "BTCUSD", "date": "2025-04-01", "endDate": "2025-04-30", "open": 82534.31, "high": 95976.34, "low": 74420.69, "close": 94182.54, "volume": 1141082935002},
            {"symbol": "BTCUSD", "date": "2025-03-01", "endDate": "2025-03-31", "open": 84297.74, "high": 95128.88, "low": 76555, "close": 82534.32, "volume": 1079106541740},
            {"symbol": "BTCUSD", "date": "2025-02-01", "endDate": "2025-02-28", "open": 102414.05, "high": 102781.65, "low": 78167.81, "close": 84297.73, "volume": 1285046267189},
            {"symbol": "BTCUSD", "date": "2025-01-01", "endDate": "2025-01-31", "open": 93347.59, "high": 109358.01, "low": 89028.64, "close": 102411.26, "volume": 1763520562025},
            {"symbol": "BTCUSD", "date": "2024-12-01", "endDate": "2024-12-31", "open": 96464.95, "high": 108388.88, "low": 91271.19, "close": 93354.22, "volume": 2464172359247},
            {"symbol": "BTCUSD", "date": "2024-11-01", "endDate": "2024-11-30", "open": 70198.02, "high": 99860, "low": 66783.77, "close": 96465.42, "volume": 2351553225101},
            {"symbol": "BTCUSD", "date": "2024-10-01", "endDate": "2024-10-31", "open": 63305.52, "high": 73624.98, "low": 58863.9, "close": 70197.83, "volume": 1084374845460},
            {"symbol": "BTCUSD", "date": "2024-09-25", "endDate": "2024-09-30", "open": 64272.93, "high": 66550, "low": 62652.99, "close": 63301.25, "volume": 174058147293},
        ],
    },
    "ETH": {
        "summary": {
            "symbol": "ETHUSD",
            "windowStart": "2024-09-25",
            "windowEnd": "2026-09-25",
            "tradingDays": 731,
            "changePctOverWindow": 5.26,
        },
        "series": [
            {"symbol": "ETHUSD", "date": "2026-09-01", "endDate": "2026-09-25", "open": 2466.84, "high": 2807.1, "low": 2355.2, "close": 2714.8, "volume": 408703566767},
            {"symbol": "ETHUSD", "date": "2026-08-01", "endDate": "2026-08-31", "open": 1860.8, "high": 2567, "low": 1820.14, "close": 2467.29, "volume": 386036590961},
            {"symbol": "ETHUSD", "date": "2026-07-01", "endDate": "2026-07-31", "open": 1569.45, "high": 1979, "low": 1550.59, "close": 1860.66, "volume": 323437074616},
            {"symbol": "ETHUSD", "date": "2026-06-01", "endDate": "2026-06-30", "open": 2004.01, "high": 2018.48, "low": 1505, "close": 1569.45, "volume": 449944799788},
            {"symbol": "ETHUSD", "date": "2026-05-01", "endDate": "2026-05-31", "open": 2256.8, "high": 2424, "low": 1964.01, "close": 2004, "volume": 493124264417},
            {"symbol": "ETHUSD", "date": "2026-04-01", "endDate": "2026-04-30", "open": 2103.41, "high": 2466.5, "low": 2015.85, "close": 2256.8, "volume": 554317840190},
            {"symbol": "ETHUSD", "date": "2026-03-01", "endDate": "2026-03-31", "open": 1964.7, "high": 2386.23, "low": 1907.99, "close": 2103.61, "volume": 666221435202},
            {"symbol": "ETHUSD", "date": "2026-02-01", "endDate": "2026-02-28", "open": 2449.44, "high": 2473.86, "low": 1742.79, "close": 1964.71, "volume": 802391784169},
            {"symbol": "ETHUSD", "date": "2026-01-01", "endDate": "2026-01-31", "open": 2966.68, "high": 3405.03, "low": 2238.74, "close": 2449.36, "volume": 756240801041},
            {"symbol": "ETHUSD", "date": "2025-12-01", "endDate": "2025-12-31", "open": 2991.68, "high": 3477.44, "low": 2716.82, "close": 2966.84, "volume": 696175284343},
            {"symbol": "ETHUSD", "date": "2025-11-01", "endDate": "2025-11-30", "open": 3846.44, "high": 3916.5, "low": 2620, "close": 2991.9, "volume": 1081097132979},
            {"symbol": "ETHUSD", "date": "2025-10-01", "endDate": "2025-10-31", "open": 4145.98, "high": 4759.16, "low": 3510, "close": 3845.79, "volume": 1477246556673},
            {"symbol": "ETHUSD", "date": "2025-09-01", "endDate": "2025-09-30", "open": 4391.9, "high": 4768.6, "low": 3825, "close": 4145.99, "volume": 1122144413034},
            {"symbol": "ETHUSD", "date": "2025-08-01", "endDate": "2025-08-31", "open": 3697.85, "high": 4955.9, "low": 3354.56, "close": 4391.91, "volume": 1381282925173},
            {"symbol": "ETHUSD", "date": "2025-07-01", "endDate": "2025-07-31", "open": 2486.16, "high": 3941.86, "low": 2372.62, "close": 3698.07, "volume": 1006425345805},
            {"symbol": "ETHUSD", "date": "2025-06-01", "endDate": "2025-06-30", "open": 2529.31, "high": 2880, "low": 2113, "close": 2486.15, "volume": 643540786092},
            {"symbol": "ETHUSD", "date": "2025-05-01", "endDate": "2025-05-31", "open": 1793.92, "high": 2789.5, "low": 1751.45, "close": 2529.31, "volume": 766220892499},
            {"symbol": "ETHUSD", "date": "2025-04-01", "endDate": "2025-04-30", "open": 1822.05, "high": 1956.55, "low": 1383.26, "close": 1793.79, "volume": 549719270553},
            {"symbol": "ETHUSD", "date": "2025-03-01", "endDate": "2025-03-31", "open": 2236.74, "high": 2551.49, "low": 1754.13, "close": 1822.03, "volume": 536575631408},
            {"symbol": "ETHUSD", "date": "2025-02-01", "endDate": "2025-02-28", "open": 3300, "high": 3330.9, "low": 2073.34, "close": 2236.36, "volume": 781844123132},
            {"symbol": "ETHUSD", "date": "2025-01-01", "endDate": "2025-01-31", "open": 3330.52, "high": 3746, "low": 2913.75, "close": 3299.99, "volume": 870972006408},
            {"symbol": "ETHUSD", "date": "2024-12-01", "endDate": "2024-12-31", "open": 3706.35, "high": 4109, "low": 3095.65, "close": 3330.32, "volume": 1218812620077},
            {"symbol": "ETHUSD", "date": "2024-11-01", "endDate": "2024-11-30", "open": 2514.74, "high": 3740.63, "low": 2355.43, "close": 3706.35, "volume": 1105801375509},
            {"symbol": "ETHUSD", "date": "2024-10-01", "endDate": "2024-10-31", "open": 2601.33, "high": 2768.22, "low": 2309.17, "close": 2514.84, "volume": 523187051714},
            {"symbol": "ETHUSD", "date": "2024-09-25", "endDate": "2024-09-30", "open": 2653.53, "high": 2729.39, "low": 2553.93, "close": 2601.27, "volume": 89029650167},
        ],
    },
    "SOL": {
        "series": [
            {"symbol": "SOLUSD", "date": "2026-09-01", "open": 103.03, "high": 121.77255, "low": 95.71, "close": 120.67, "volume": 85525465056},
            {"symbol": "SOLUSD", "date": "2026-08-01", "open": 72.81, "high": 110.65, "low": 70.51, "close": 103.04, "volume": 90234164272},
            {"symbol": "SOLUSD", "date": "2026-07-01", "open": 73.54, "high": 83.91, "low": 72.16, "close": 72.79, "volume": 59560435373},
            {"symbol": "SOLUSD", "date": "2026-06-01", "open": 82.31, "high": 82.98, "low": 60.11, "close": 73.55, "volume": 88780545137},
            {"symbol": "SOLUSD", "date": "2026-05-01", "open": 83.05, "high": 98.39, "low": 79.88, "close": 82.32, "volume": 119290843918},
            {"symbol": "SOLUSD", "date": "2026-04-01", "open": 83.12, "high": 90.8, "low": 76.69, "close": 83.05, "volume": 168044275056},
            {"symbol": "SOLUSD", "date": "2026-03-01", "open": 84.37, "high": 97.7, "low": 79, "close": 83.12, "volume": 131314448985},
            {"symbol": "SOLUSD", "date": "2026-02-01", "open": 105.44, "high": 106.58, "low": 67.48, "close": 84.37, "volume": 140111989934},
            {"symbol": "SOLUSD", "date": "2026-01-01", "open": 124.44, "high": 148.9, "low": 96.52, "close": 105.44, "volume": 140095907208},
            {"symbol": "SOLUSD", "date": "2025-12-01", "open": 133.48, "high": 146.92, "low": 116.82, "close": 124.45, "volume": 128525679129},
            {"symbol": "SOLUSD", "date": "2025-11-01", "open": 187.12, "high": 189.05, "low": 121.47, "close": 133.47, "volume": 182430048775},
            {"symbol": "SOLUSD", "date": "2025-10-01", "open": 208.75, "high": 237.96, "low": 172.78, "close": 187.14, "volume": 262348438794},
            {"symbol": "SOLUSD", "date": "2025-09-01", "open": 200.62, "high": 253.61, "low": 190.82, "close": 208.74, "volume": 249318644169},
            {"symbol": "SOLUSD", "date": "2025-08-01", "open": 172.18, "high": 217.95, "low": 155.75, "close": 200.63, "volume": 244217213754},
            {"symbol": "SOLUSD", "date": "2025-07-01", "open": 154.88, "high": 206.42, "low": 144.86, "close": 172.19, "volume": 227069963361},
            {"symbol": "SOLUSD", "date": "2025-06-01", "open": 156.55, "high": 168.38, "low": 126.03, "close": 154.88, "volume": 116048946180},
            {"symbol": "SOLUSD", "date": "2025-05-01", "open": 147.57, "high": 187.73, "low": 141.34, "close": 156.53, "volume": 132316922398},
            {"symbol": "SOLUSD", "date": "2025-04-01", "open": 124.51, "high": 157.08, "low": 95.16, "close": 147.56, "volume": 129131581732},
            {"symbol": "SOLUSD", "date": "2025-03-01", "open": 148.09, "high": 180, "low": 112, "close": 124.54, "volume": 121030145660},
            {"symbol": "SOLUSD", "date": "2025-02-01", "open": 231.69, "high": 234.12, "low": 125.36, "close": 148.09, "volume": 138799106277},
            {"symbol": "SOLUSD", "date": "2025-01-01", "open": 188.82, "high": 295, "low": 169.22, "close": 231.71, "volume": 248156073470},
            {"symbol": "SOLUSD", "date": "2024-12-01", "open": 237.74, "high": 247.1, "low": 175.01, "close": 188.82, "volume": 201042425293},
            {"symbol": "SOLUSD", "date": "2024-11-01", "open": 168.42, "high": 264.63, "low": 155.01, "close": 237.74, "volume": 245862257614},
            {"symbol": "SOLUSD", "date": "2024-10-01", "open": 152.5, "high": 183.3, "low": 133.1, "close": 168.43, "volume": 100366267319},
            {"symbol": "SOLUSD", "date": "2024-09-25", "open": 152.74, "high": 161.8, "low": 146.52, "close": 152.5, "volume": 17319151478},
        ],
    },
    "AVAX": {
        "series": [
            {"symbol": "AVAXUSD", "date": "2026-09-01", "open": 7.226, "high": 11.796, "low": 7.039, "close": 10.536, "volume": 13501444720},
            {"symbol": "AVAXUSD", "date": "2026-08-01", "open": 6.38, "high": 8.315, "low": 6.04, "close": 7.229, "volume": 8859780320},
            {"symbol": "AVAXUSD", "date": "2026-07-01", "open": 6.53, "high": 7.11, "low": 6.14, "close": 6.37, "volume": 7494211074},
            {"symbol": "AVAXUSD", "date": "2026-06-01", "open": 8.97, "high": 9.06, "low": 5.68, "close": 6.53, "volume": 9636866501},
            {"symbol": "AVAXUSD", "date": "2026-05-01", "open": 9.09, "high": 10.49, "low": 8.64, "close": 8.97, "volume": 7658870473},
            {"symbol": "AVAXUSD", "date": "2026-04-01", "open": 8.91, "high": 10.01, "low": 8.47, "close": 9.09, "volume": 8780999954},
            {"symbol": "AVAXUSD", "date": "2026-03-01", "open": 9.19, "high": 10.55, "low": 8.38, "close": 8.91, "volume": 9961399027},
            {"symbol": "AVAXUSD", "date": "2026-02-01", "open": 10.11, "high": 10.33, "low": 7.53, "close": 9.16, "volume": 10142909698},
            {"symbol": "AVAXUSD", "date": "2026-01-01", "open": 12.3, "high": 14.94, "low": 9.14, "close": 10.11, "volume": 11919764106},
            {"symbol": "AVAXUSD", "date": "2025-12-01", "open": 13.72, "high": 15.08, "low": 11.26, "close": 12.3, "volume": 11410629910},
            {"symbol": "AVAXUSD", "date": "2025-11-01", "open": 18.19, "high": 19, "low": 12.51, "close": 13.71, "volume": 15832959719},
            {"symbol": "AVAXUSD", "date": "2025-10-01", "open": 30.03, "high": 31.59, "low": 17, "close": 18.18, "volume": 27283393688},
            {"symbol": "AVAXUSD", "date": "2025-09-01", "open": 23.37, "high": 36.19, "low": 22.68, "close": 30.04, "volume": 37988806657},
            {"symbol": "AVAXUSD", "date": "2025-08-01", "open": 22.47, "high": 26.74, "low": 20.57, "close": 23.39, "volume": 21986503425},
            {"symbol": "AVAXUSD", "date": "2025-07-01", "open": 17.97, "high": 27.39, "low": 16.96, "close": 22.48, "volume": 20115558949},
            {"symbol": "AVAXUSD", "date": "2025-06-01", "open": 20.81, "high": 22.77, "low": 15.62, "close": 17.97, "volume": 10969136064},
            {"symbol": "AVAXUSD", "date": "2025-05-01", "open": 20.93, "high": 26.84, "low": 19.07, "close": 20.81, "volume": 14894481474},
            {"symbol": "AVAXUSD", "date": "2025-04-01", "open": 18.75, "high": 23.09, "low": 14.65, "close": 20.93, "volume": 10591735792},
            {"symbol": "AVAXUSD", "date": "2025-03-01", "open": 22.37, "high": 25.11, "low": 15.28, "close": 18.78, "volume": 11821240481},
            {"symbol": "AVAXUSD", "date": "2025-02-01", "open": 34.38, "high": 35.09, "low": 20.22, "close": 22.37, "volume": 13571732769},
            {"symbol": "AVAXUSD", "date": "2025-01-01", "open": 35.63, "high": 45.05, "low": 31.82, "close": 34.39, "volume": 16251541123},
            {"symbol": "AVAXUSD", "date": "2024-12-01", "open": 44.85, "high": 55.86, "low": 33.55, "close": 35.63, "volume": 33374062177},
            {"symbol": "AVAXUSD", "date": "2024-11-01", "open": 24.97, "high": 47.97, "low": 22.33, "close": 44.84, "volume": 29949609823},
            {"symbol": "AVAXUSD", "date": "2024-10-01", "open": 27.69, "high": 29.86, "low": 23.9, "close": 24.98, "volume": 10758717030},
            {"symbol": "AVAXUSD", "date": "2024-09-25", "open": 28.48, "high": 30.86, "low": 26.97, "close": 27.7, "volume": 2644227068},
        ],
    },
}


def save_as_timestamp_format(symbol: str, data: dict) -> str:
    """Convert TipRanks monthly format to timestamp millisecond format."""
    from datetime import datetime

    output_dir = Path("./real_market_data")
    output_dir.mkdir(exist_ok=True)

    # Reverse chronologically and convert dates to millisecond timestamps
    ohlcv = []
    for bar in reversed(data["series"]):
        # Parse month-start date
        date_str = bar["date"]
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        timestamp_ms = int(dt.timestamp() * 1000)

        ohlcv.append(
            {
                "timestamp": timestamp_ms,
                "open": float(bar["open"]),
                "high": float(bar["high"]),
                "low": float(bar["low"]),
                "close": float(bar["close"]),
                "volume": float(bar["volume"]),
            }
        )

    # Save dataset
    dataset = {
        "symbol": symbol,
        "source": "TipRanks",
        "data_source_note": "Real market data: monthly OHLCV aggregation",
        "count": len(ohlcv),
        "date_range": {
            "start": ohlcv[0]["timestamp"],
            "end": ohlcv[-1]["timestamp"],
        },
        "candles": ohlcv,
    }

    filename = f"{symbol}_tipransk_real_730d.json"
    filepath = output_dir / filename

    with open(filepath, "w") as f:
        json.dump(dataset, f, indent=2)

    print(f"Saved {symbol}: {len(ohlcv)} candles → {filepath}")
    return str(filepath)


if __name__ == "__main__":
    for symbol in ["BTC", "ETH", "SOL", "AVAX"]:
        save_as_timestamp_format(symbol, REAL_DATA[symbol])

    print("\nReal market data saved to ./real_market_data/")
