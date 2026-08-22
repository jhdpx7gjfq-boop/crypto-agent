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

## Tests

```
pip install -r requirements-dev.txt
pytest
```
