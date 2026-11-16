
import os
import time
import requests

# ---------- AJUSTES (puedes cambiarlos) ----------
TOP_N = 200
RATIO = 4.0
MIN_QUOTE_VOL = 50_000
INTERVAL = "5m"
LOOKBACK = 20
MAX_ALERTS = 10
# --------------------------------------------------

BASE = "https://data-api.binance.vision/api/v3"
TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"].strip()
STABLES = {"USDC", "FDUSD", "TUSD", "USDP", "DAI", "EUR", "AEUR", "USDE", "XUSD", "BFUSD"}


def get(path, **params):
    r = requests.get(f"{BASE}/{path}", params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def send(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )
    print("Telegram respondio:", r.status_code, r.text)
    r.raise_for_status()


def fmt_money(x):
    if x >= 1_000_000:
        return f"${x / 1_000_000:.1f}M"
    return f"${x / 1_000:.0f}K"


def main():
    tickers = get("ticker/24hr")
    pares = [
        t for t in tickers
        if t["symbol"].endswith("USDT")
        and t["symbol"][:-4] not in STABLES
    ]
    pares.sort(key=lambda t: float(t["quoteVolume"]), reverse=True)
    pares = pares[:TOP_N]

    alertas = []
    for t in pares:
        symbol = t["symbol"]
        try:
            k = get("klines", symbol=symbol, interval=INTERVAL, limit=LOOKBACK + 2)
            if len(k) < LOOKBACK + 2:
                continue
            cerrada = k[-2]
            historial = k[-2 - LOOKBACK:-2]
            vol = float(cerrada[7])
            promedio = sum(float(v[7]) for v in historial) / LOOKBACK
            if promedio <= 0 or vol < MIN_QUOTE_VOL:
                continue
            ratio = vol / promedio
            if ratio >= RATIO:
                abre, cierra = float(cerrada[1]), float(cerrada[4])
                cambio = (cierra - abre) / abre * 100
                alertas.append((ratio, symbol, vol, cambio))
        except Exception as e:
            print(f"Error con {symbol}: {e}")
        time.sleep(0.05)

    alertas.sort(reverse=True)
    manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

    if alertas:
        lineas = [f"🔔 Volumen alto (vela de {INTERVAL})"]
        for ratio, symbol, vol, cambio in alertas[:MAX_ALERTS]:
            flecha = "🟢" if cambio >= 0 else "🔴"
            lineas.append(
                f"{flecha} {symbol}: x{ratio:.1f} del normal · {fmt_money(vol)} · {cambio:+.1f}%"
            )
        send("\n".join(lineas))
    elif manual:
        send(f"✅ Bot funcionando. Revisé {len(pares)} pares y ninguno tiene volumen alto ahora.")

    print(f"Revisados {len(pares)} pares, {len(alertas)} alertas.")


if __name__ == "__main__":
    main()
