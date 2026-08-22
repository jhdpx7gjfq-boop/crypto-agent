import logging
import os
import time

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
HIGH_THRESHOLD = float(os.environ.get("HIGH_THRESHOLD", 70000))
LOW_THRESHOLD = float(os.environ.get("LOW_THRESHOLD", 55000))
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", 60))


def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    response.raise_for_status()


def get_btc():
    response = requests.get(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["bitcoin"]["usd"]


def main():
    last_zone = None
    while True:
        try:
            btc = get_btc()
        except requests.RequestException as exc:
            logger.warning("Failed to fetch BTC price: %s", exc)
            time.sleep(POLL_SECONDS)
            continue

        if btc > HIGH_THRESHOLD:
            zone = "high"
        elif btc < LOW_THRESHOLD:
            zone = "low"
        else:
            zone = None

        if zone is not None and zone != last_zone:
            try:
                if zone == "high":
                    send(f"🔴 BTC HIGH ALERT: {btc}$")
                else:
                    send(f"🟢 BTC DIP ALERT: {btc}$")
            except requests.RequestException as exc:
                logger.warning("Failed to send Telegram alert: %s", exc)

        last_zone = zone
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
