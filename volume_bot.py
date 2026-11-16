import os
import time
import requests

# ---------- AJUSTES (puedes cambiarlos) ----------
TOP_N = 200            # cuántos pares USDT vigilar
RATIO = 3.0            # volumen mínimo vs. el normal (x veces)
MIN_QUOTE_VOL = 50_000 # volumen mínimo de la vela en USDT
INTERVAL = "5m"        # tamaño de vela
LOOKBACK = 20          # velas para calcular el volumen normal
BREAKOUT_N = 20        # velas para el máximo/mínimo a romper
SOLO_LARGOS = False    # True = ignora las rupturas a la baja
MAX_ALERTS = 10        # máximo de monedas por mensaje
# --------------------------------------------------


BASE = "https://data-api.binance.vision
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

    n = max(LOOKBACK, BREAKOUT_N)
    alertas = []
    for t in pares:
        symbol = t["symbol"]
        try:
            k = get("klines", symbol=symbol, interval=INTERVAL, limit=n + 2)
            if len(k) < n + 2:
                continue
            cerrada = k[-2]  # última vela ya cerrada

            # 1) Volumen alto
            hist_vol = k[-2 - LOOKBACK:-2]
            vol = float(cerrada[7])
            promedio = sum(float(v[7]) for v in hist_vol) / LOOKBACK
            if promedio <= 0 or vol < MIN_QUOTE_VOL:
                continue
            ratio = vol / promedio
            if ratio < RATIO:
                continue

            # 2) Ruptura de máximo o mínimo
            hist_px = k[-2 - BREAKOUT_N:-2]
            maximo = max(float(v[2]) for v in hist_px)
            minimo = min(float(v[3]) for v in hist_px)
            abre, cierra = float(cerrada[1]), float(cerrada[4])
            cambio = (cierra - abre) / abre * 100

            if cierra > maximo:
                alertas.append((ratio, "LARGO", symbol, vol, cambio, cierra, maximo))
            elif cierra < minimo and not SOLO_LARGOS:
                alertas.append((ratio, "CORTO", symbol, vol, cambio, cierra, minimo))
        except Exception as e:
            print(f"Error con {symbol}: {e}")
        time.sleep(0.05)

    alertas.sort(reverse=True)
    manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

    if alertas:
        lineas = [f"🔔 Ruptura con volumen (vela de {INTERVAL})"]
        for ratio, lado, symbol, vol, cambio, cierra, nivel in alertas[:MAX_ALERTS]:
            icono = "🟢" if lado == "LARGO" else "🔴"
            palabra = "máximo" if lado == "LARGO" else "mínimo"
            lineas.append(
                f"{icono} {lado} {symbol}: x{ratio:.1f} del normal · {fmt_money(vol)} · "
                f"{cambio:+.1f}%\n   cerró en {cierra:g}, rompió el {palabra} de {BREAKOUT_N} velas ({nivel:g})"
            )
        send("\n".join(lineas))
    elif manual:
        send(f"✅ Bot funcionando. Revisé {len(pares)} pares y ninguno tiene ruptura con volumen ahora.")

    print(f"Revisados {len(pares)} pares, {len(alertas)} alertas.")


if __name__ == "__main__":
    main()
