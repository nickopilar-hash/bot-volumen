import os
import time
import requests

# ---------- AJUSTES (puedes cambiarlos) ----------
TOP_N = 200            # cuántos pares USDT vigilar (los de más volumen)
RATIO = 4.0            # avisa si el volumen es 4 veces el normal
MIN_QUOTE_VOL = 50_000 # volumen mínimo de la vela en USDT (filtra monedas muertas)
INTERVAL = "5m"        # tamaño de vela
LOOKBACK = 20          # cuántas velas anteriores forman el "normal"
MAX_ALERTS = 10        # máximo de monedas por mensaje
# --------------------------------------------------

BASE = "https://data-api.binance.vision/api/v3"
TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
STABLES = {"USDC", "FDUSD", "TUSD", "USDP", "DAI", "EUR", "AEUR", "USDE", "XUSD", "BFUSD"}


def get(path, **params):
    r = requests.get(f"{BASE}/{path}", params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def send(text):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )


def fmt_money(x):
    if x >= 1_000_000:
        return f"${x / 1_000_000:.1f}M"
    return f"${x / 1_000:.0f}K"

