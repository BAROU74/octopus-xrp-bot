import os, time, hmac, hashlib, requests, threading
from flask import Flask
from datetime import datetime

BTSE_KEY = os.getenv("BTSE_API_KEY")
BTSE_SECRET = os.getenv("BTSE_API_SECRET")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = "https://api.btse.com"

app = Flask(__name__)
@app.route('/')
def home():
    return "V5 BTSE INSTANT LIVE - Trade immediat + Tudor >1.0%"

def send_tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": TG_CHAT, "text": msg}, timeout=10)
        print(f"TG: {msg}")
    except Exception as e:
        print(f"TG fail: {e}")

def btse_signature(path, nonce, data=""):
    msg = nonce + path + data
    return hmac.new(BTSE_SECRET.encode(), msg.encode(), hashlib.sha384).hexdigest()

def get_btse_price(symbol):
    try:
        # API futures BTSE officielle
        url = f"{BASE_URL}/futures/api/v3.2/market_summary?symbol={symbol}"
        r = requests.get(url, timeout=10)
        j = r.json()
        if isinstance(j, list): j = j[0]
        last = float(j.get('lastPrice') or j.get('close') or 0)
        # Variation jour
        pc = j.get('percentChange')
        if pc is None:
            # calcul avec open
            o = j.get('openPrice') or j.get('open') or last
            if o and float(o)!=0:
                pc = (last - float(o))/float(o)*100
            else:
                pc = 0.0
        return last, float(pc)
    except Exception as e:
        print(f"Prix {symbol} erreur: {e}")
        return None, None

def place_btse_order(symbol, side, size):
    # size = notional USD, ex 10 = 10$
    try:
        path = "/futures/api/v3.2/order"
        nonce = str(int(time.time()*1000))
        # BTSE futures order format correct
        import json
        body_dict = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "size": size,
            "time_in_force": "GTC"
        }
        body = json.dumps(body_dict)
        sig = btse_signature(path, nonce, body)
        headers = {"btse-api": BTSE_KEY, "btse-nonce": nonce, "btse-sign": sig, "Content-Type": "application/json"}
        r = requests.post(BASE_URL+path, headers=headers, data=body, timeout=15)
        print(f"ORDER {symbol} {side} {size}$ -> {r.text}")
        return r.text
    except Exception as e:
        return f"Erreur order: {e}"

def tudor_loop():
    # 1. MESSAGE DEMARRAGE
    send_tg("🔥 V5 BTSE INSTANT START\nTest trading immediat en cours...")
    time.sleep(2)

    # 2. TRADE IMMEDIAT A L'INSTALLATION
    try:
        gold_price, _ = get_btse_price("GOLD-PERP")
        send_tg(f"💰 GOLD-PERP actuel: {gold_price}$\n🚀 PLACEMENT ORDRE INSTANT 10$ LONG...")
        result = place_btse_order("GOLD-PERP", "BUY", 10)
        send_tg(f"✅ ORDRE INSTANT PLACÉ:\n{result}\n\nMaintenant passage en mode Tudor >1.0%")
    except Exception as e:
        send_tg(f"❌ Erreur ordre instant: {e}\nVerifie tes clés BTSE dans Render")

    # 3. BOUCLE TUDOR NORMALE
    while True:
        try:
            _, gold_chg = get_btse_price("GOLD-PERP")
            _, copper_chg = get_btse_price("COPPER-PERP")
            _, qqq_chg = get_btse_price("QQQ-PERP")
            _, spy_chg = get_btse_price("SPY-PERP")

            if None in [gold_chg, copper_chg, qqq_chg, spy_chg]:
                time.sleep(60)
                continue

            spread_gc = gold_chg - copper_chg
            spread_qs = qqq_chg - spy_chg

            print(f"[{datetime.now().strftime('%H:%M:%S')}] GOLD-COPPER={spread_gc:.2f}% QQQ-SPY={spread_qs:.2f}%")

            if spread_gc > 1.0 and spread_qs > -0.5:
                send_tg(f"🟢 SIGNAL TUDOR BTSE VALIDÉ\nGOLD-COPPER={spread_gc:.2f}% | QQQ-SPY={spread_qs:.2f}%\n🚀 AUTO BUY GOLD-PERP 100$")
                res = place_btse_order("GOLD-PERP", "BUY", 100)
                send_tg(f"✅ TRADE TUDOR EXECUTÉ:\n{res}")
                time.sleep(3600)

        except Exception as e:
            print(f"Loop err {e}")
        time.sleep(300)

threading.Thread(target=tudor_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
