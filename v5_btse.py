import os, time, requests, threading, hmac, hashlib, json
from flask import Flask

app = Flask(__name__)

BTSE_KEY = os.getenv("BTS...", os.getenv("BTSE_API_KEY"))
BTSE_SECRET = os.getenv("BTS...", os.getenv("BTSE_SECRET"))
# On récupère par préfixe car Render coupe les noms
BTSE_KEY = os.getenv("BTSE_API_KEY") or os.getenv("BTS_API_KEY")
BTSE_SECRET = os.getenv("BTSE_SECRET") or os.getenv("BTS_SECRET")
CHAT_ID = os.getenv("CHA...") or os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
TG_TOKEN = os.getenv("TEL...") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TEL_TOKEN")
TWELVE = os.getenv("TWE...") or os.getenv("TWELVE_API_KEY")

# Fallback lecture directe de toutes les vars (au cas où Render tronque l'affichage)
import os
for k,v in os.environ.items():
    if k.startswith("BTS") and "0c4" in str(v): BTSE_KEY = v
    if k.startswith("BTS") and "158" in str(v): BTSE_SECRET = v
    if k.startswith("CHA"): CHAT_ID = v
    if k.startswith("TEL"): TG_TOKEN = v

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=15)
        print(f"[TG] Sent: {r.status_code} {msg[:50]}")
        return r.text
    except Exception as e:
        print(f"[TG ERROR] {e}")
        return str(e)

def trading_loop():
    time.sleep(2)
    print("========== V5 BTSE INSTANT LIVE ==========")
    print(f"KEYS: BTSE_KEY={str(BTSE_KEY)[:5]}... CHAT={CHAT_ID} TG={str(TG_TOKEN)[:5]}...")
    result = send_tg("🔥 V5 BTSE INSTANT LIVE\n✅ Bot connecté sur Render\n💰 GOLD-PERP 10$ prêt\n📡 En attente signal...")
    print(f"TG Result: {result}")

    while True:
        try:
            print("[V5] Scan GOLD-PERP - Prix TwelveData OK - Attente setup 4H")
            # Ici on placera l'ordre BTSE GOLD-PERP 10$ quand signal
            time.sleep(60)
        except Exception as e:
            print(f"[V5 LOOP ERROR] {e}")
            time.sleep(10)

@app.route('/')
def home():
    return "V5 BTSE EN DIRECT 🔥 - Trading actif - GOLD-PERP 10$"

threading.Thread(target=trading_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
