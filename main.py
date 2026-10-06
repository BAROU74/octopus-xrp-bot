import ccxt, time, os
from flask import Flask
from threading import Thread
import requests

# --- CONFIG RENDER ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
BTSE_KEY = os.environ.get("BTSE_KEY")
BTSE_SECRET = os.environ.get("BTSE_SECRET")

LOWER = 1.49
AMOUNT_USD = 6.75

# --- PETIT SERVEUR WEB POUR RENDER ---
app = Flask(__name__)
@app.route('/')
def home():
    return "🐙 OCTOPUS XRP en ligne - Attente XRP @ 1.49$"

def send_telegram(msg):
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg})
        except Exception as e:
            print(f"Erreur Telegram: {e}")

# --- LOGIQUE DU BOT ---
def run_bot():
    print("🐙 OCTOPUS demarre sur Render - check toutes les 2H", flush=True)
    send_telegram("🐙 OCTOPUS démarré sur Render!")

    # Pour le prix, on utilise Binance (public, gratuit, sans clé)
    price_exchange = ccxt.binance()
    
    # Pour le trading, on utilise BTSE seulement si tu as les clés
    trade_exchange = None
    if BTSE_KEY and BTSE_SECRET:
        trade_exchange = ccxt.btse({'apiKey': BTSE_KEY,'secret': BTSE_SECRET,})

    while True:
        try:
            ticker = price_exchange.fetch_ticker('XRP/USDT')
            price = ticker['last']
            print(f"Prix XRP: {price} $ - {time.ctime()}", flush=True)

            # Si on touche le prix bas
            if price <= LOWER:
                send_telegram(f"🚨 ALERTE XRP: {price}$ <= {LOWER}$ - J'achète!")

            # Si BTSE configuré, place l'ordre
            if trade_exchange:
                try:
                    balance = trade_exchange.fetch_balance()
                    usdt_free = balance['free'].get('USDT', 0)
                    if usdt_free > 4:
                        try:
                            trade_exchange.cancel_all_orders('XRP/USDT')
                        except:
                            pass
                        amount = AMOUNT_USD / LOWER
                        trade_exchange.create_limit_buy_order('XRP/USDT', amount, LOWER)
                        msg = f"BUY place {amount} XRP @ {LOWER}$"
                        print(msg, flush=True)
                        send_telegram(msg)
                    else:
                        print(f"Ordre deja en place, j'attends...", flush=True)
                except Exception as e:
                    print(f"Erreur trading BTSE: {e}", flush=True)
            else:
                print("Pas de clé BTSE -> mode surveillance seule (Telegram ok)", flush=True)

        except Exception as e:
            print(f"Erreur: {e}", flush=True)
        
        time.sleep(7200) # 2 heures

# --- LANCEMENT ---
if __name__ == "__main__":
    Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
