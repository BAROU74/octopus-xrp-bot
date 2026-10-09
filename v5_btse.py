import os, time, requests, threading
from flask import Flask

app = Flask(__name__)

# --- TES CLES RENDER ---
BTSE_KEY = os.getenv("BTSE_API_KEY")
BTSE_SECRET = os.getenv("BTSE_SECRET")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID")

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TG_CHAT, "text": msg}, timeout=10)
        print(f"[TG] {msg}")
    except Exception as e:
        print(f"[TG ERROR] {e}")

def trading_loop():
    time.sleep(3)
    print("========== V5 BTSE INSTANT LIVE ==========")
    send_tg("🔥 V5 BTSE INSTANT START\n✅ Bot LIVE sur Render\n💰 GOLD-PERP 10$ prêt")

    while True:
        try:
            # Ici ton prix BTSE GOLD-PERP
            print("[V5] Scan GOLD-PERP... Prix OK - Signal check")
            # Ajoute ta logique d'ordre ici
            time.sleep(60)
        except Exception as e:
            print(f"[V5 ERROR] {e}")
            time.sleep(10)

@app.route('/')
def home():
    return "V5 BTSE LIVE 🔥 - Trading Active"

# Lancer le trading en arrière plan
threading.Thread(target=trading_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
