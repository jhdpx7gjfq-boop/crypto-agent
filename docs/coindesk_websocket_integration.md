# CoinDesk WebSocket Integration — Layer 1

## Overview

Real-time market data streaming from CoinDesk via WebSocket API for IGWT-PF26 Layer 1 (Data Intelligence).

**Status**: ✅ Implemented & Tested (23/23 tests passing)

## Features

- ✅ WebSocket connection management with automatic reconnection
- ✅ Real-time tick data parsing (CoinDesk message formats)
- ✅ Tick aggregation to OHLCV candles
- ✅ Subscription management (SUB_ADD/SUB_REMOVE)
- ✅ Header-based or URL parameter authentication
- ✅ Heartbeat monitoring (30s intervals)
- ✅ Error handling and graceful degradation

## Architecture

### Components

#### 1. `CoinDeskWebSocketCollector`
Core WebSocket client.

```python
from src.layers.layer1_data.coindesk_ws_collector import CoinDeskWebSocketCollector

# Initialize
collector = CoinDeskWebSocketCollector(
    api_key="your_coindesk_api_key",
    use_header_auth=True  # Recommended for production
)

# Connect
await collector.connect()

# Subscribe to BTC-USD
await collector.subscribe(
    market="cadli",
    instrument="BTC-USD",
    data_type="1101",
    groups=["VALUE", "CURRENT_HOUR"]
)

# Receive messages
async def handle_tick(message):
    tick = collector.parse_tick_data(message)
    if tick:
        print(f"BTC-USD: {tick.price}")

await collector.on_message(handle_tick)

# Close
await collector.close()
```

#### 2. `CoinDeskCollectorManager`
Higher-level manager with automatic candle aggregation.

```python
from src.layers.layer1_data.coindesk_ws_collector import CoinDeskCollectorManager
import asyncio

manager = CoinDeskCollectorManager("your_api_key")

# Register candle callback
def on_candle(candle: OHLCV):
    print(f"Candle: {candle.timestamp} | O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close}")

manager.on_candle(on_candle)

# Start collector
await manager.start()

# Subscribe
await manager.subscribe(market="cadli", instrument="BTC-USD")

# ... run your strategy ...

# Close
await manager.close()
```

#### 3. Integration with `DataCollector`

```python
from src.layers.layer1_data.collector import DataCollector

collector = DataCollector()

# Get CoinDesk WebSocket manager
ws_manager = collector.get_coindesk_ws_collector(
    api_key="your_api_key",
    use_header_auth=True
)

# Use with your data pipeline
```

## Message Types

CoinDesk WebSocket API sends several message types:

| Type | Description |
|------|-------------|
| 4000 | Session Welcome |
| 4001 | Streamer Error |
| 4002 | Rate Limit Error |
| 4003 | Subscription Error |
| 4004 | Subscription Validation Error |
| 4005 | Subscription Accepted |
| 4006 | Subscription Rejected |
| 4007 | Subscription Add Complete |
| 4008 | Subscription Remove Complete |
| 4013 | Heartbeat |
| 1101 | CADLI Tick Update |
| 1102 | Spot Trade Update |

## Data Models

### TickData
Real-time tick from exchange.

```python
@dataclass
class TickData:
    timestamp: datetime
    instrument: str      # e.g., "BTC-USD"
    price: float
    volume: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    sequence: Optional[int] = None
```

### OHLCV
Aggregated candle (from `src.core.models`).

```python
@dataclass
class OHLCV:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
```

## Configuration

### Environment Variables

```bash
export COINDESK_API_KEY="your_api_key"
```

### Best Practices

1. **Use Header Authentication** (production)
   ```python
   collector = CoinDeskWebSocketCollector(api_key, use_header_auth=True)
   ```
   - API key stays out of URL logs
   - Aligns with OAuth standards

2. **Implement Rate Limit Handling**
   - Monitor incoming rate limit messages (TYPE 4002)
   - Back off exponentially on reconnect

3. **Manage Subscriptions**
   ```python
   # Subscribe only to needed instruments
   await manager.subscribe("cadli", "BTC-USD")
   await manager.subscribe("cadli", "ETH-USD")
   
   # Unsubscribe when done
   await manager.unsubscribe("BTC-USD")
   ```

4. **Handle Disconnections**
   - Automatic reconnection with exponential backoff (max 5 attempts)
   - Configurable via `DEFAULT_RECONNECT_MAX`

## Integration with Layer 1 Pipeline

```python
import asyncio
from src.layers.layer1_data.collector import DataCollector
from src.core.pipeline import DecisionPipeline

async def run_realtime_pipeline():
    # Data collection
    collector = DataCollector()
    ws_manager = collector.get_coindesk_ws_collector("your_api_key")
    
    # Define data processing
    def process_candle(candle: OHLCV):
        # Feed to Layer 2 (Market Regime)
        # Feed to Layer 3 (BCE)
        # Feed to Layer 4 (X20)
        # ... etc
        print(f"Processing: {candle.instrument} @ {candle.close}")
    
    ws_manager.on_candle(process_candle)
    
    # Start
    await ws_manager.start()
    await ws_manager.subscribe("cadli", "BTC-USD")
    await ws_manager.subscribe("cadli", "ETH-USD")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        await ws_manager.close()

if __name__ == "__main__":
    asyncio.run(run_realtime_pipeline())
```

## Limitations

- **Tick Aggregation**: Simple window-based (100 ticks per candle)
  - For production, implement time-window aggregation
- **No Order Book**: Current implementation focuses on trade ticks
  - Order book replay available via `ORDERBOOK_REPLAY` subscription type
- **Rate Limits**: Subject to CoinDesk API rate limits per account tier

## Testing

Run test suite:

```bash
pytest tests/test_coindesk_ws_collector.py -v
```

**Test Coverage** (23/23 passing):
- ✅ TickData model validation
- ✅ WebSocket URL building (auth methods)
- ✅ Message parsing (trade ticks, errors)
- ✅ OHLCV aggregation (single/multiple ticks)
- ✅ Subscription management
- ✅ Manager lifecycle
- ✅ Integration with DataCollector

## Future Enhancements

1. **Time-Window Aggregation**: Replace tick-count with timestamp windows
2. **Order Book Support**: Subscribe to L2 order book updates
3. **Persistence**: Auto-save candles to Parquet/DuckDB
4. **Metrics**: Track latency, message counts, reconnections
5. **Alert System**: Trigger signals on candle close

## References

- [CoinDesk Data API Docs](https://developers.coindesk.com/documentation/data-streamer/introduction)
- [WebSocket Authentication](https://developers.coindesk.com/documentation/data-streamer/introduction#connection-and-authentication)
- [Message Types Reference](https://developers.coindesk.com/documentation/data-streamer/introduction#handling-responses-and-messages)

## Support

For issues or questions:
1. Check logs: `logger.debug()` enabled in collector
2. Verify API key and rate limits in CoinDesk dashboard
3. Test connection: `python -c "import websockets; print('OK')"`
4. Review error codes in CoinDesk documentation
