"""Update market data with weekly OHLCV (better granularity than monthly)."""

import json
from pathlib import Path
from datetime import datetime

WEEKLY_DATA = {
    "BTC": {
        "summary": {"symbol": "BTCUSD", "tradingDays": 185, "changePctOverWindow": 18.18},
        "series": [
            {"date": "2026-09-21", "open": 81160.33, "high": 87397, "low": 80837.42, "close": 84266.19, "volume": 220383880871},
            {"date": "2026-09-14", "open": 76799.85, "high": 81925, "low": 74887.5, "close": 81159.64, "volume": 236731522150},
            {"date": "2026-09-07", "open": 80339.13, "high": 80462.23, "low": 76030, "close": 76799.85, "volume": 186343558065},
            {"date": "2026-08-31", "open": 77672.1, "high": 82283, "low": 76219.18, "close": 80339.13, "volume": 207951775356},
            {"date": "2026-08-24", "open": 77729.36, "high": 81479.5, "low": 76652, "close": 77665.14, "volume": 249669632881},
            {"date": "2026-08-17", "open": 62836.67, "high": 79500, "low": 62679.42, "close": 77729.36, "volume": 302940838017},
            {"date": "2026-08-10", "open": 64848.68, "high": 65341.83, "low": 62468.21, "close": 62836.66, "volume": 128129846954},
            {"date": "2026-08-03", "open": 63499.49, "high": 65426, "low": 62210.14, "close": 64848.69, "volume": 142109837499},
            {"date": "2026-07-27", "open": 65341.07, "high": 65705.08, "low": 62209.81, "close": 63499.49, "volume": 169561108289},
            {"date": "2026-07-20", "open": 64681.79, "high": 66923.95, "low": 63641, "close": 65341.07, "volume": 171036393031},
            {"date": "2026-07-13", "open": 63740.32, "high": 65559.5, "low": 61750.9, "close": 64681.78, "volume": 181922373750},
            {"date": "2026-07-06", "open": 63580.45, "high": 64669.42, "low": 61250, "close": 63740.32, "volume": 187710530383},
            {"date": "2026-06-29", "open": 59473.99, "high": 63940.79, "low": 57717.55, "close": 63580.44, "volume": 210566721885},
            {"date": "2026-06-22", "open": 63235.63, "high": 65553.39, "low": 58000, "close": 59474.01, "volume": 218768112658},
            {"date": "2026-06-15", "open": 65704.23, "high": 67264, "low": 62159.76, "close": 63235.63, "volume": 179141825363},
            {"date": "2026-06-08", "open": 63302.03, "high": 65764.16, "low": 60708.92, "close": 65706.62, "volume": 203064999678},
            {"date": "2026-06-01", "open": 73575.18, "high": 73978.52, "low": 59073.01, "close": 63302.73, "volume": 371152525597},
            {"date": "2026-05-25", "open": 76975.99, "high": 78015.46, "low": 72364.13, "close": 73575.17, "volume": 215798894643},
            {"date": "2026-05-18", "open": 77406.57, "high": 78123.68, "low": 74197.11, "close": 76975.99, "volume": 210409845985},
            {"date": "2026-05-11", "open": 82199.99, "high": 82379, "low": 76673.54, "close": 77407.59, "volume": 232642529263},
            {"date": "2026-05-04", "open": 78558.88, "high": 82814.23, "low": 78205, "close": 82199.99, "volume": 265983866603},
            {"date": "2026-04-27", "open": 78673.84, "high": 79496, "low": 74914, "close": 78558.89, "volume": 243674812314},
            {"date": "2026-04-20", "open": 73823.27, "high": 79523, "low": 73741.53, "close": 78673.83, "volume": 243965893453},
            {"date": "2026-04-13", "open": 70755.35, "high": 78390, "low": 70576.27, "close": 73823.14, "volume": 320589378332},
            {"date": "2026-04-06", "open": 69005, "high": 73822.95, "low": 67710.01, "close": 70755.35, "volume": 273884242849},
            {"date": "2026-03-30", "open": 65957.95, "high": 69285.99, "low": 65696.96, "close": 69005, "volume": 218148470636},
            {"date": "2026-03-25", "open": 70533.48, "high": 72030.29, "low": 64938.66, "close": 65956.94, "volume": 175220756973},
        ],
    },
    "ETH": {
        "summary": {"symbol": "ETHUSD", "tradingDays": 185, "changePctOverWindow": 24.91},
        "series": [
            {"date": "2026-09-21", "open": 2644, "high": 2807.1, "low": 2626.94, "close": 2708.1, "volume": 88399511066},
            {"date": "2026-09-14", "open": 2475.86, "high": 2667.53, "low": 2356.82, "close": 2644.31, "volume": 126490135071},
            {"date": "2026-09-07", "open": 2514.32, "high": 2667.01, "low": 2404.26, "close": 2475.86, "volume": 106108717577},
            {"date": "2026-08-31", "open": 2416.8, "high": 2546.54, "low": 2355.2, "close": 2514.31, "volume": 101489946680},
            {"date": "2026-08-24", "open": 2463.58, "high": 2567, "low": 2387.45, "close": 2416.86, "volume": 108642906697},
            {"date": "2026-08-17", "open": 1874.1, "high": 2548, "low": 1870.47, "close": 2463.39, "volume": 153982240559},
            {"date": "2026-08-10", "open": 1909.18, "high": 1929.93, "low": 1851.45, "close": 1874.13, "volume": 45588112176},
            {"date": "2026-08-03", "open": 1883.34, "high": 1942, "low": 1826.31, "close": 1909.09, "volume": 52480098816},
            {"date": "2026-07-27", "open": 1953.12, "high": 1979, "low": 1820.14, "close": 1883.35, "volume": 67929143272},
            {"date": "2026-07-20", "open": 1870.99, "high": 1965.01, "low": 1841.52, "close": 1952.93, "volume": 66903394078},
            {"date": "2026-07-13", "open": 1805.56, "high": 1944.82, "low": 1748.05, "close": 1870.89, "volume": 74120483010},
            {"date": "2026-07-06", "open": 1784.13, "high": 1831.62, "low": 1710.95, "close": 1805.51, "volume": 70280705451},
            {"date": "2026-06-29", "open": 1569.4, "high": 1806.51, "low": 1547.08, "close": 1784.2, "volume": 77769390915},
            {"date": "2026-06-22", "open": 1704.99, "high": 1777.83, "low": 1510, "close": 1569.41, "volume": 84839809383},
            {"date": "2026-06-15", "open": 1724.73, "high": 1848.42, "low": 1669.2, "close": 1704.8, "volume": 85531791661},
            {"date": "2026-06-08", "open": 1689.58, "high": 1731.39, "low": 1601.5, "close": 1724.73, "volume": 82726691973},
            {"date": "2026-06-01", "open": 2004.01, "high": 2018.48, "low": 1505, "close": 1689.75, "volume": 174838953747},
            {"date": "2026-05-25", "open": 2097.38, "high": 2139.94, "low": 1964.01, "close": 2004, "volume": 92018061686},
            {"date": "2026-05-18", "open": 2129.74, "high": 2156.48, "low": 2006.64, "close": 2097.35, "volume": 99501637518},
            {"date": "2026-05-11", "open": 2370.96, "high": 2375.28, "low": 2078.22, "close": 2129.74, "volume": 108018348631},
            {"date": "2026-05-04", "open": 2322.48, "high": 2424, "low": 2269.55, "close": 2371.12, "volume": 156146953388},
            {"date": "2026-04-27", "open": 2370.47, "high": 2405.01, "low": 2218.65, "close": 2322.5, "volume": 112447046660},
            {"date": "2026-04-20", "open": 2263.9, "high": 2425, "low": 2260.51, "close": 2370.47, "volume": 115742182352},
            {"date": "2026-04-13", "open": 2191.77, "high": 2466.5, "low": 2174.31, "close": 2263.89, "volume": 158728095188},
            {"date": "2026-04-06", "open": 2109.33, "high": 2330.56, "low": 2059.82, "close": 2191.8, "volume": 136982330505},
            {"date": "2026-03-30", "open": 1983.04, "high": 2167.56, "low": 1978.46, "close": 2109.24, "volume": 110414571469},
            {"date": "2026-03-25", "open": 2155.55, "high": 2199.81, "low": 1937.59, "close": 1982.96, "volume": 73260817755},
        ],
    },
}

def save_weekly_data(symbol: str, data: dict) -> str:
    from datetime import datetime

    output_dir = Path("./real_market_data")
    output_dir.mkdir(exist_ok=True)

    ohlcv = []
    for bar in reversed(data["series"]):
        date_str = bar["date"]
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        timestamp_ms = int(dt.timestamp() * 1000)

        ohlcv.append({
            "timestamp": timestamp_ms,
            "open": float(bar["open"]),
            "high": float(bar["high"]),
            "low": float(bar["low"]),
            "close": float(bar["close"]),
            "volume": float(bar["volume"]),
        })

    dataset = {
        "symbol": symbol,
        "source": "TipRanks (Weekly Aggregation)",
        "data_source_note": "Real market data: weekly OHLCV (185 trading days = 27 weeks)",
        "count": len(ohlcv),
        "granularity": "weekly",
        "date_range": {
            "start": ohlcv[0]["timestamp"],
            "end": ohlcv[-1]["timestamp"],
        },
        "candles": ohlcv,
    }

    filename = f"{symbol}_tipransk_weekly_6m.json"
    filepath = output_dir / filename

    with open(filepath, "w") as f:
        json.dump(dataset, f, indent=2)

    print(f"Saved {symbol}: {len(ohlcv)} weekly candles → {filepath}")
    return str(filepath)

if __name__ == "__main__":
    for symbol in ["BTC", "ETH"]:  # Only have these two fetched
        if symbol in WEEKLY_DATA:
            save_weekly_data(symbol, WEEKLY_DATA[symbol])

    print("\nWeekly market data updated. Rerun validation...")
