import os, time, requests
from datetime import datetime

TD_KEY = os.getenv("TWELVEDATA_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_tg(text):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                       json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except: pass

def get_pct(symbol):
    try:
        url = f"https://api.twelvedata.com/quote?symbol={symbol}&apikey={TD_KEY}"
        r = requests.get(url, timeout=15).json()
        if "percent_change" in r:
            return float(r["percent_change"])
        # fallback time_series
        url2 = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&outputsize=2&apikey={TD_KEY}"
        r2 = requests.get(url2, timeout=15).json()
        vals = r2.get("values", [])
        if len(vals)>=2:
            c0=float(vals[0]["close"]); c1=float(vals[1]["close"])
            return (c0-c1)/c1*100
        return 0.0
    except Exception as e:
        print(f"ERR {symbol} {e}")
        return None

def loop():
    send_tg("🟡 V4.1 TwelveData LIVE - Anti nan% - GOLD x2 LONG")
    while True:
        gold = get_pct("XAU/USD")
        copper = get_pct("COPPER/USD")
        nasdaq = get_pct("QQQ")
        dow = get_pct("DIA")

        if None in [gold,copper,nasdaq,dow]:
            print(f"{datetime.now()} WAITING API...")
            time.sleep(60)
            continue

        spread = gold - copper
        risk = nasdaq - dow

        msg = f"# SEUIL 1.0%\nACHAT: GOLD({gold:.2f}%) - CUIVRE({copper:.2f}%) = {spread:.2f}% / Besoin >1.0%\nVENTE: NASDAQ-DOW = {risk:.2f}%"
        print(msg)
        send_tg(f"💛 {msg}")
        time.sleep(300)

# Flask keep alive for Render
from flask import Flask
app = Flask(__name__)
@app.route("/")
def home(): return "V4.1 TwelveData LIVE"

if __name__ == "__main__":
    import threading
    threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
