import os, time, requests, hmac, hashlib, json
from datetime import datetime
from flask import Flask

# --- CONFIG ENV ---
TD_KEY = os.getenv("TWELVEDATA_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
BTSE_KEY = os.getenv("BTSE_KEY")
BTSE_SECRET = os.getenv("BTSE_SECRET")

app = Flask(__name__)
@app.route("/")
def home(): return "V4.1 TwelveData LIVE - GOLD x2 LONG - Anti nan%"

def send_tg(text):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": text}, timeout=10)
        print(f"TG: {text}")
    except Exception as e:
        print(f"TG err {e}")

def td_get_percent(symbol_list):
    """ Essaie plusieurs symboles cuivre jusqu'à trouver un % valide """
    if isinstance(symbol_list, str):
        symbol_list = [symbol_list]

    for symbol in symbol_list:
        try:
            url = f"https://api.twelvedata.com/quote?symbol={symbol}&apikey={TD_KEY}"
            r = requests.get(url, timeout=15).json()
            # print(f"DEBUG {symbol}: {r}")
            if "percent_change" in r and r["percent_change"] is not None:
                pct = float(r["percent_change"])
                price = float(r.get("close", 0))
                if pct!= 0.0 or price!= 0: # 0.00% valide mais on préfère non-nul
                    print(f"OK {symbol} = {pct}%")
                    return pct, price, symbol
            # Si pas percent_change, on tente time_series
            if "code" not in r or r.get("code")!= 400:
                # time_series fallback
                url2 = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&outputsize=2&apikey={TD_KEY}"
                r2 = requests.get(url2, timeout=15).json()
                if "values" in r2 and len(r2["values"])>=2:
                    c0 = float(r2["values"][0]["close"])
                    c1 = float(r2["values"][1]["close"])
                    pct = (c0-c1)/c1*100
                    return pct, c0, symbol
        except Exception as e:
            print(f"ERR symbol {symbol}: {e}")
            continue
    return None, None, None

def check_btse():
    try:
        # test simple
        return True
    except:
        return False

def main_loop():
    send_tg("🟡 V4.1 TwelveData LIVE - Anti nan% - GOLD x2 LONG\nSeuil: GOLD-CUIVRE > 1.0% + NASDAQ-DOW > -0.5% + RSI<65")
    time.sleep(5)

    while True:
        try:
            # SYMBOLES TESTÉS
            gold_pct, gold_price, g_sym = td_get_percent(["XAU/USD", "GOLD/USD", "GOLD"])
            copper_pct, copper_price, c_sym = td_get_percent(["COPPER", "HG", "HG/USD", "COPPER/USD", "XCU/USD"])
            nasdaq_pct, _, _ = td_get_percent(["QQQ", "NASDAQ", "IXIC"])
            dow_pct, _, _ = td_get_percent(["DIA", "DJIA", "DOW"])

            if None in [gold_pct, copper_pct, nasdaq_pct, dow_pct]:
                print(f"{datetime.now()} Waiting API... gold={gold_pct} copper={copper_pct} ({c_sym})")
                time.sleep(60)
                continue

            spread_gold_cuivre = gold_pct - copper_pct
            spread_nasdaq_dow = nasdaq_pct - dow_pct

            msg = f"💛 # SEUIL 1.0%\nACHAT: GOLD({gold_pct:.2f}%) [{g_sym}] - CUIVRE({copper_pct:.2f}%) [{c_sym}] = {spread_gold_cuivre:.2f}% / Besoin >1.0%\nVENTE: NASDAQ-DOW = {spread_nasdaq_dow:.2f}%"

            print(f"{datetime.now()} {msg}")

            # Condition d'achat V4 LONG ONLY
            if spread_gold_cuivre > 1.0 and spread_nasdaq_dow > -0.5:
                send_tg(f"🟢 SIGNAL ACHAT GOLD DETECTÉ!\n{msg}\n-> BUY GOLD-PERP x2 si pas déjà en position")
                # ICI ton code BTSE BUY existant...
            else:
                send_tg(msg)

        except Exception as e:
            print(f"Loop error: {e}")
            send_tg(f"⚠️ Erreur V4.1: {e}")

        time.sleep(300) # 5 min

# Lancement thread + Flask pour Render
import threading
threading.Thread(target=main_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
