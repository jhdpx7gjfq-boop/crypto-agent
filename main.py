import requests
import time

BOT_TOKEN = "TON_TOKEN_ICI"
CHAT_ID = "TON_CHAT_ID_ICI"

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})

def get_btc():
    data = requests.get(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    ).json()
    return data["bitcoin"]["usd"]

while True:

    btc = get_btc()

    if btc > 70000:
        send(f"🔴 BTC HIGH ALERT: {btc}$")

    elif btc < 55000:
        send(f"🟢 BTC DIP ALERT: {btc}$")

    time.sleep(60)
