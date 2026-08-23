# crypto-agent
Crypto quant alert system

Polls the BTC/USD price from CoinGecko and sends a Telegram alert when it
crosses above or below configured thresholds.

## Setup

Set these environment variables (never commit real credentials to the repo):

- `BOT_TOKEN` — Telegram bot token
- `CHAT_ID` — Telegram chat ID to notify
- `HIGH_THRESHOLD` — optional, USD price above which a high alert fires (default `70000`)
- `LOW_THRESHOLD` — optional, USD price below which a dip alert fires (default `55000`)
- `POLL_SECONDS` — optional, polling interval in seconds (default `60`)

```
pip install -r requirements.txt
BOT_TOKEN=... CHAT_ID=... python main.py
```

This runs as a background `worker` process (see `Procfile`), not a `web`
process — on Heroku, scale it with `heroku ps:scale worker=1`.

## CoinGlass client

`coinglass.py` provides a `CoinGlassClient` for the [CoinGlass V4 API](https://docs.coinglass.com),
covering open interest, funding rate, liquidations, CVD (spot & futures) and
spot coin netflow — the market-microstructure data feeding IGWT's research.

Set `COINGLASS_API_KEY` (or pass `api_key=` explicitly), then:

```python
from coinglass import CoinGlassClient

client = CoinGlassClient()
oi = client.open_interest_history("binance", "BTCUSDT", "1h", limit=100)
funding = client.funding_rate_oi_weighted_history("BTC", "8h")
```

**Status: `UNVERIFIED`** (see `coinglass.py: COINGLASS_DATA_STATUS`). The
unit tests validate the client's behavior against mocked responses only
— they are not proof the endpoints, auth, or response schema match the
live API. Run `scripts/coinglass_verify.py` with a real `COINGLASS_API_KEY`
against an environment that has network access to `coinglass.com` (this
was written from a sandbox where that domain is blocked at the egress
proxy) to promote the status; see
`research/candidates/DATA-SRC-003_COINGLASS_API_V4/` for the full
validation pipeline and alpha candidates.

The client reads `API-KEY-MAX-LIMIT` / `API-KEY-USE-LIMIT` off every
response (`client.rate_limit_max` / `client.rate_limit_used`) instead of
hardcoding plan quotas, retries on HTTP 429 with capped exponential
backoff honoring `Retry-After`, and can space out calls locally via
`min_request_interval` (disabled by default). See
`tests/test_coinglass_resilience.py` for the behavior this covers.

## Tests

```
pip install -r requirements-dev.txt
pytest
```
