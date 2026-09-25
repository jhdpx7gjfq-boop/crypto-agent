# Deployment Guide

This guide covers different deployment options for the BTC Alert Bot.

## Table of Contents

1. [Local Development](#local-development)
2. [Heroku](#heroku)
3. [GitHub Actions](#github-actions)
4. [Docker](#docker)
5. [VPS/Server](#vpsserver)

## Local Development

### Prerequisites
- Python 3.11+
- pip

### Setup

```bash
# Clone and install
git clone https://github.com/jhdpx7gjfq-boop/crypto-agent.git
cd crypto-agent
pip install -r requirements.txt

# Run the bot
BOT_TOKEN=your_token CHAT_ID=your_chat_id python main.py
```

### Testing

```bash
pip install -r requirements-dev.txt
python -m pytest --cov
```

## Heroku

### Prerequisites
- Heroku account
- Heroku CLI installed

### Setup

```bash
# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Set environment variables
heroku config:set BOT_TOKEN=your_token -a your-app-name
heroku config:set CHAT_ID=your_chat_id -a your-app-name

# Deploy
git push heroku main

# Scale worker dyno
heroku ps:scale worker=1 -a your-app-name

# View logs
heroku logs --tail -a your-app-name
```

## GitHub Actions

### Prerequisites
- GitHub repository with secrets configured

### Setup

1. Go to repository **Settings → Secrets and variables → Actions**
2. Add these secrets:
   - `BOT_TOKEN` — Your Telegram bot token
   - `CHAT_ID` — Your Telegram chat ID
   - `HIGH_THRESHOLD` (optional) — Default 70000
   - `LOW_THRESHOLD` (optional) — Default 55000

3. The bot will run automatically every 5 minutes

### Customization

Edit `.github/workflows/bot.yml` to change:
- Schedule (cron expression on line 4)
- Thresholds
- Alert frequency

To disable, delete `.github/workflows/bot.yml` or set the workflow to manual-only.

## Docker

### Prerequisites
- Docker installed

### Build and Run

```bash
# Build image
docker build -t crypto-agent:latest .

# Run container
docker run -e BOT_TOKEN=your_token \
           -e CHAT_ID=your_chat_id \
           crypto-agent:latest

# Run single check (instead of continuous polling)
docker run -e BOT_TOKEN=your_token \
           -e CHAT_ID=your_chat_id \
           crypto-agent:latest \
           python main.py --check-once
```

### Docker Compose

```bash
# Create .env file
echo "BOT_TOKEN=your_token" > .env
echo "CHAT_ID=your_chat_id" >> .env

# Start bot
docker-compose up -d

# View logs
docker-compose logs -f

# Stop bot
docker-compose down
```

### Push to Registry

```bash
# Tag image
docker tag crypto-agent:latest your-registry/crypto-agent:latest

# Push
docker push your-registry/crypto-agent:latest
```

## VPS/Server

### Prerequisites
- Linux VPS (Ubuntu/Debian recommended)
- SSH access
- Python 3.11+

### Setup

```bash
# SSH into server
ssh user@your-vps

# Clone repository
git clone https://github.com/jhdpx7gjfq-boop/crypto-agent.git
cd crypto-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your credentials
cat > .env << EOF
BOT_TOKEN=your_token
CHAT_ID=your_chat_id
HIGH_THRESHOLD=70000
LOW_THRESHOLD=55000
POLL_SECONDS=60
EOF

# Test the bot
python main.py --check-once

# Optional: Set up as systemd service (see below)
```

### Systemd Service (for automatic startup)

Create `/etc/systemd/system/btc-alert.service`:

```ini
[Unit]
Description=BTC Alert Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/crypto-agent
Environment="PATH=/home/ubuntu/crypto-agent/venv/bin"
EnvironmentFile=/home/ubuntu/crypto-agent/.env
ExecStart=/home/ubuntu/crypto-agent/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable btc-alert
sudo systemctl start btc-alert

# Check status
sudo systemctl status btc-alert

# View logs
sudo journalctl -u btc-alert -f
```

### Update Credentials (if needed)

```bash
# Edit .env
nano .env

# Restart service
sudo systemctl restart btc-alert
```

## Monitoring and Troubleshooting

### Check Latest Price and Alert Status

```bash
# Run single check
python main.py --check-once
```

### View Logs

Depending on deployment:

```bash
# Local/VPS
tail -f /var/log/syslog | grep btc-alert

# Heroku
heroku logs --tail -a your-app-name

# Docker
docker logs -f container_id

# GitHub Actions
Click workflow run in repository Actions tab
```

### Common Issues

**"Failed to fetch BTC price"**
- Check internet connectivity
- Verify CoinGecko API is accessible
- Check for rate limiting (wait and retry)

**"Failed to send Telegram alert"**
- Verify BOT_TOKEN is correct
- Verify CHAT_ID exists and bot has permission
- Check Telegram API status

**Bot not starting**
- Verify environment variables are set
- Check Python version: `python --version`
- Review logs for error messages

## Cost Estimates

| Platform | Cost | Notes |
|----------|------|-------|
| GitHub Actions | Free | 2,000 minutes/month free tier |
| Heroku | Free (Eco dyno) | $5/month for reliable uptime |
| Docker Registry | Varies | Docker Hub free with rate limits |
| VPS | $5-20/month | DigitalOcean, Linode, etc. |
| Local/Home Lab | Free | Requires always-on computer |

## Security Best Practices

1. **Never commit credentials**
   - Use `.env` files (added to `.gitignore`)
   - Use platform-specific secrets management

2. **Rotate tokens regularly**
   - Telegram bot token: regenerate via BotFather
   - Update all deployed instances

3. **Monitor API usage**
   - CoinGecko: Free tier has rate limits
   - Telegram: Monitor for unusual activity

4. **Use HTTPS only**
   - All calls to CoinGecko and Telegram use HTTPS
   - Verify certificate validation in any proxies

## Next Steps

- Monitor bot alerts for accuracy
- Adjust thresholds based on trading strategy
- Set up additional alerts or notifications
- Consider extending with additional indicators
