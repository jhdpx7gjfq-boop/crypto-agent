import logging
import os
import time

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def classify_zone(price, high_threshold, low_threshold):
    if price > high_threshold:
        return "high"
    if price < low_threshold:
        return "low"
    return None


def format_alert(zone, price):
    if zone == "high":
        return f"🔴 BTC HIGH ALERT: {price}$"
    return f"🟢 BTC DIP ALERT: {price}$"


def send(bot_token, chat_id, msg):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    response = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
    response.raise_for_status()


def get_btc():
    response = requests.get(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["bitcoin"]["usd"]


def poll_once(bot_token, chat_id, high_threshold, low_threshold, last_zone):
    try:
        btc = get_btc()
    except (requests.RequestException, KeyError, ValueError) as exc:
        logger.warning("Failed to fetch BTC price: %s", exc)
        return last_zone

    zone = classify_zone(btc, high_threshold, low_threshold)

    if zone is not None and zone != last_zone:
        try:
            send(bot_token, chat_id, format_alert(zone, btc))
        except requests.RequestException as exc:
            logger.warning("Failed to send Telegram alert: %s", exc)

    return zone


def main():
    bot_token = os.environ["BOT_TOKEN"]
    chat_id = os.environ["CHAT_ID"]
    high_threshold = float(os.environ.get("HIGH_THRESHOLD", 70000))
    low_threshold = float(os.environ.get("LOW_THRESHOLD", 55000))
    poll_seconds = int(os.environ.get("POLL_SECONDS", 60))

    last_zone = None
    while True:
        last_zone = poll_once(bot_token, chat_id, high_threshold, low_threshold, last_zone)
        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
