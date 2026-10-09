import os, time, requests, math
from datetime import datetime
from flask import Flask

TD_KEY = os.getenv("TWELVEDATA_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

app = Flask(__name__)
@app.route("/")
def home():
    return "V4.2 Tudor LIVE - En attente seuil 1.0% - OK"

def send_tg(text):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": text}, timeout=10)
        print(f"TG: {text}")
    except Exception as e:
        print(f"TG err {e}")

def td_get_percent(symbol_list):
    if isinstance(symbol_list, str):
        symbol_list = [symbol_list]
    for symbol in symbol_list:
        try:
            url = f"https://api.twelvedata.com/quote?symbol={symbol}&apikey={TD_KEY}"
            r = requests.get(url, timeout=15).json()
            if "percent_change" in r and r["percent_change"] is not None:
                pct = float(r["percent_change"])
                price = float(r.get("close", 0))
                if not math.isnan(pct) and pct!= 0.0:
                    return pct, price, symbol
            if "values" in r and len(r.get("values",[]))>=2:
                pass
            url2 = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&outputsize=2&apikey={TD_KEY}"
            r2 = requests.get(url2, timeout=15).json()
            if "values" in r2 and len(r2["values"])>=2:
                c0 = float(r2["values"][0]["close"])
                c1 = float(r2["values"][1]["close"])
                if c1!= 0:
                    pct = (c0-c1)/c1*100
                    if not math.isnan(pct):
                        return pct, c0, symbol
        except Exception as e:
            print(f"ERR {symbol}: {e}")
            continue
    return None, None, None

def td_get_rsi(symbol="XAU/USD"):
    try:
        url = f"https://api.twelvedata.com/rsi?symbol={symbol}&interval=1day&apikey={TD_KEY}"
        r = requests.get(url, timeout=15).json()
        if "values" in r and len(r["values"])>0:
            return float(r["values"][0]["rsi"])
    except Exception as e:
        print(f"RSI err {e}")
    return 50.0 # valeur neutre si API fail, ne bloque pas le tir

def main_loop():
    send_tg("🟡 V4.2 Tudor LIVE démarré\nSurveillance seuil: GOLD-CUIVRE >1.0% + NASDAQ-DOW >-0.5% + RSI<65")
    time.sleep(5)
    while True:
        try:
            gold_pct, gold_price, g_sym = td_get_percent(["XAU/USD", "GOLD/USD", "GOLD"])
            copper_pct, copper_price, c_sym = td_get_percent(["COPPER", "HG", "HG/USD", "COPPER/USD", "XCU/USD"])
            nasdaq_pct, _, _ = td_get_percent(["QQQ", "NASDAQ", "IXIC"])
            dow_pct, _, _ = td_get_percent(["DIA", "DJIA", "DOW"])
            rsi = td_get_rsi(g_sym or "XAU/USD")

            if None in [gold_pct, copper_pct, nasdaq_pct, dow_pct]:
                print(f"{datetime.now()} Waiting API... gold={gold_pct} copper={copper_pct}")
                time.sleep(60)
                continue

            spread_gold_cuivre = gold_pct - copper_pct
            spread_nasdaq_dow = nasdaq_pct - dow_pct

            # MESSAGE VEILLE (celui que tu avais de 11:37 à 11:57 qui est CORRECT)
            msg_veille = (
                f"💛 # SEUIL 1.0%\n"
                f"ACHAT: GOLD({gold_pct:.2f}%) [{g_sym}] - CUIVRE({copper_pct:.2f}%) [{c_sym}] = {spread_gold_cuivre:.2f}% / Besoin >1.0%\n"
                f"VENTE: NASDAQ-DOW = {spread_nasdaq_dow:.2f}% / Besoin >-0.5%\n"
                f"RSI GOLD: {rsi:.1f} / Besoin <65"
            )

            cond1 = spread_gold_cuivre > 1.0
            cond2 = spread_nasdaq_dow > -0.5
            cond3 = rsi < 65

            print(f"{datetime.now()} {msg_veille} | cond1={cond1} cond2={cond2} cond3={cond3}")

            if cond1 and cond2 and cond3:
                send_tg(f"🟢 SIGNAL ACHAT GOLD x2 DETECTÉ!\n{msg_veille}\n-> BUY GOLD-PERP x2")
                # TON CODE BTSE ICI
            else:
                send_tg(msg_veille)

        except Exception as e:
            print(f"Loop error: {e}")
            send_tg(f"⚠️ Erreur V4.2: {e}")

        time.sleep(300)

import threading
threading.Thread(target=main_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
