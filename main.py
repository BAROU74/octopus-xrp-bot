import ccxt, time, os, requests, yfinance as yf
from flask import Flask
from threading import Thread

# --- CONFIG RENDER ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
BTSE_KEY = os.environ.get("BTSE_KEY")
BTSE_SECRET = os.environ.get("BTSE_SECRET")

# --- CONFIG V3 TEST MICRO ---
SOL_SIZE = 0.01
XRP_SIZE = 1
SEUIL = 1.8
# On a enlevé GC=F et HG=F qui bloquent Yahoo, on prend des proxies fiables
TICKERS = {"GOLD":"GLD", "CUIVRE":"COPX", "NASDAQ":"QQQ", "DOW":"DIA"}

app = Flask(__name__)
@app.route('/')
def home():
    return "🔥 OCTOPUS V3.1 MICRO IMMORTEL - 0.01 SOL / 1 XRP - Fix Yahoo"

def send_telegram(msg):
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
            print(f"Telegram envoyé: {msg[:30]}...")
        except Exception as e:
            print(f"Erreur Telegram: {e}")

def get_change(ticker):
    try:
        # FIX DEFINITIF Yahoo
        d = yf.Ticker(ticker).history(period="5d", interval="1d")
        if d.empty or len(d) < 2:
            print(f"{ticker} vide, on skip -> 0%")
            return 0
        # On prend les 2 derniers closes journaliers, beaucoup plus stable
        return ((d['Close'].iloc[-1]-d['Close'].iloc[-2])/d['Close'].iloc[-2])*100
    except Exception as e:
        print(f"Erreur yfinance {ticker}: {e}")
        return 0

def run_bot():
    print("🐙 OCTOPUS V3.1 demarre sur Render - FIX YAHOO")
    send_telegram("🔥 OCTOPUS V3.1 IMMORTEL EN LIGNE\n✅ Fix Yahoo Gold/Cuivre (GLD/COPX)\n✅ 0.01 SOL / 1 XRP\n✅ Achat/Vente AUTO actif\n✅ Heartbeat toutes les 30min")
    
    price_exchange = ccxt.binance({'enableRateLimit': True})
    trade_exchange = None
    if BTSE_KEY and BTSE_SECRET:
        try:
            trade_exchange = ccxt.btse({'apiKey': BTSE_KEY, 'secret': BTSE_SECRET, 'enableRateLimit': True})
            print("BTSE connecté")
        except Exception as e:
            print(f"Erreur BTSE init: {e}")

    loop_count = 0
    while True:
        try:
            loop_count += 1
            ch = {k: get_change(v) for k,v in TICKERS.items()}
            print(f"SCAN #{loop_count} -> GOLD {ch['GOLD']:.2f}% CUIVRE {ch['CUIVRE']:.2f}% NASDAQ {ch['NASDAQ']:.2f}% DOW {ch['DOW']:.2f}%")
            
            # Heartbeat toutes les 30 min pour que tu sois rassuré
            if loop_count % 30 == 0:
                send_telegram(f"💓 V3.1 Heartbeat - Je suis vivant - Scan #{loop_count}\nGOLD {ch['GOLD']:.2f}% CUIVRE {ch['CUIVRE']:.2f}% NASDAQ {ch['NASDAQ']:.2f}%")

            # Prix XRP via Yahoo en secours si Binance bloque
            try:
                ticker_xrp = price_exchange.fetch_ticker('XRP/USDT')
                price_xrp = ticker_xrp['last']
            except:
                price_xrp = yf.Ticker("XRP-USD").history(period="1d")['Close'].iloc[-1]
            print(f"Prix XRP: {price_xrp}")

            # --- LOGIQUE ACHAT ---
            if ch['CUIVRE'] - ch['GOLD'] > SEUIL:
                print(f"🔥 SIGNAL ACHAT DETECTE: {ch['CUIVRE']-ch['GOLD']:.2f}%")
                if trade_exchange:
                    try:
                        balance = trade_exchange.fetch_balance()
                        usdt_free = balance.get('USDT', {}).get('free', 0) if balance else 0
                        print(f"USDT dispo: {usdt_free}")
                        if usdt_free > 3:
                            trade_exchange.create_market_buy_order('XRP/USDT', XRP_SIZE)
                            time.sleep(1)
                            trade_exchange.create_market_buy_order('SOL/USDT', SOL_SIZE)
                            msg = f"🚨 V3.1 ACHAT AUTO\nCuivre {ch['CUIVRE']:.2f}% vs Gold {ch['GOLD']:.2f}% = +{ch['CUIVRE']-ch['GOLD']:.2f}%\nJ'ACHETE {XRP_SIZE} XRP + {SOL_SIZE} SOL à {price_xrp}$"
                            send_telegram(msg)
                    except Exception as e:
                        print(f"Erreur trade achat: {e}")
                        send_telegram(f"⚠️ Erreur achat: {e}")
                else:
                    send_telegram(f"🚨 V3.1 SIGNAL ACHAT (Mode Alerte - BTSE non connecté)\nCuivre {ch['CUIVRE']:.2f}% vs Gold {ch['GOLD']:.2f}%\nIl faudrait acheter {XRP_SIZE} XRP + {SOL_SIZE} SOL")

            # --- LOGIQUE VENTE ---
            if ch['NASDAQ'] - ch['DOW'] < -SEUIL:
                print(f"⚠️ SIGNAL VENTE DETECTE: {ch['NASDAQ']-ch['DOW']:.2f}%")
                if trade_exchange:
                    try:
                        bal = trade_exchange.fetch_balance()
                        xrp_bal = bal.get('XRP', {}).get('free', 0) if bal else 0
                        sol_bal = bal.get('SOL', {}).get('free', 0) if bal else 0
                        if xrp_bal >= 0.9:
                            trade_exchange.create_market_sell_order('XRP/USDT', xrp_bal)
                        if sol_bal >= 0.009:
                            trade_exchange.create_market_sell_order('SOL/USDT', sol_bal)
                        send_telegram(f"⚠️ V3.1 VENTE AUTO\nNASDAQ {ch['NASDAQ']:.2f}% vs DOW {ch['DOW']:.2f}%\nJe VENDS tout")
                    except Exception as e:
                        print(f"Erreur trade vente: {e}")

        except Exception as e:
            print(f"Erreur boucle principale: {e}")
            time.sleep(5)

        time.sleep(60)

# --- LANCEMENT ---
if __name__ == "__main__":
    Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
