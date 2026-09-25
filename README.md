# crypto-agent

Crypto quant alert system that monitors BTC/USD price and sends Telegram alerts when price crosses configured thresholds.

## Features

- Real-time BTC price monitoring via CoinGecko API
- Configurable high/low price thresholds
- Telegram notifications on threshold crossings
- Both continuous polling and single-check modes
- Runs on Heroku, GitHub Actions, or any Python environment
- 84% test coverage with 15 comprehensive tests
- Automatic code quality enforcement (ruff linting + format checking)

## Setup

### Environment Variables

Set these (never commit real credentials):

- `BOT_TOKEN` — Telegram bot token (required)
- `CHAT_ID` — Telegram chat ID to notify (required)
- `HIGH_THRESHOLD` — USD price above which a high alert fires (default: `70000`)
- `LOW_THRESHOLD` — USD price below which a dip alert fires (default: `55000`)
- `POLL_SECONDS` — polling interval in seconds, for continuous mode (default: `60`)

### Local Development

```bash
pip install -r requirements.txt
BOT_TOKEN=... CHAT_ID=... python main.py
```

### Single Check Mode

Run the bot once and exit (useful for cron jobs or GitHub Actions):

```bash
BOT_TOKEN=... CHAT_ID=... python main.py --check-once
```

### Heroku Deployment

This runs as a background `worker` process (see `Procfile`), not a web process:

```bash
heroku ps:scale worker=1
```

### GitHub Actions Deployment

1. Add these repository secrets:
   - `BOT_TOKEN`
   - `CHAT_ID`
   - `HIGH_THRESHOLD` (optional)
   - `LOW_THRESHOLD` (optional)

2. The bot will run automatically every 5 minutes via the `.github/workflows/bot.yml` workflow
3. Manually trigger via GitHub Actions UI

## Development

### Tests

```bash
pip install -r requirements-dev.txt
python -m pytest --cov=. --cov-report=term-missing
```

### Code Quality

```bash
ruff check .              # Lint
ruff format .             # Auto-format
python -m pytest          # Run tests
```

All code quality checks run automatically in CI. Contributions must pass:
- ruff linting
- ruff format checking
- pytest tests
