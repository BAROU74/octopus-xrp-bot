import ccxt, time, os, requests, yfinance as yf
from flask import Flask
from threading import Thread

# --- CONFIG RENDER ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
BTSE_KEY = os.environ.get("BTSE_KEY")
BTSE_SECRET = os.environ.get("BTSE_SECRET")

# --- CONFIG V3 TEST MICRO ---
SOL_SIZE = 0.01 # 0.01 SOL comme tu veux
XRP_SIZE = 1 # 1 XRP comme tu veux
AMOUNT_USD = 2 # 2 USDT si on achète en USD
SEUIL = 1.8

TICKERS = {"GOLD":"GC=F", "CUIVRE":"HG=F", "NASDAQ":"QQQ", "DOW":"DIA"}

app = Flask(__name__)
@app.route('/')
def home():
    return "🔥 OCTOPUS V3 AUTO MICRO en ligne - 0.01 SOL / 1 XRP - Achète/Vend seul"

def send_telegram(msg):
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        except Exception as e:
            print(f"Erreur Telegram: {e}")

def get_change(ticker):
    try:
        d = yf.Ticker(ticker).history(period="2d", interval="60m")
        return ((d['Close'][-1]-d['Close'][-2])/d['Close'][-2])*100
    except:
        return 0

def run_bot():
    print("🐙 OCTOPUS V3 AUTO demarre sur Render")
    send_telegram("🔥 OCTOPUS V3 AUTO MICRO EN LIGNE\n0.01 SOL / 1 XRP\nAchète et vend tout seul comme convenu")
    
    # Pour le prix, on utilise Binance
    price_exchange = ccxt.binance()
    # Pour le trading, on utilise BTSE
    trade_exchange = None
    if BTSE_KEY and BTSE_SECRET:
        trade_exchange = ccxt.btse({'apiKey': BTSE_KEY, 'secret': BTSE_SECRET})

    while True:
        try:
            # --- 1. RECUPERE MACRO ---
            ch = {k: get_change(v) for k,v in TICKERS.items()}
            print(f"GOLD {ch['GOLD']:.2f}% CUIVRE {ch['CUIVRE']:.2f}% NASDAQ {ch['NASDAQ']:.2f}% DOW {ch['DOW']:.2f}%")
            
            ticker_xrp = price_exchange.fetch_ticker('XRP/USDT')
            price_xrp = ticker_xrp['last']
            print(f"Prix XRP: {price_xrp}")

            # --- 2. LOGIQUE V3 ACHAT ---
            # Si Cuivre surperforme Gold > 1.8% = Signal Risk-On = ACHAT
            if ch['CUIVRE'] - ch['GOLD'] > SEUIL:
                if trade_exchange:
                    try:
                        balance = trade_exchange.fetch_balance()
                        usdt_free = balance['USDT']['free'] if 'USDT' in balance else 0
                        if usdt_free > 3:
                            # Achète 1 XRP + 0.01 SOL
                            trade_exchange.create_market_buy_order('XRP/USDT', XRP_SIZE)
                            trade_exchange.create_market_buy_order('SOL/USDT', SOL_SIZE)
                            msg = f"🚨 V3 ACHAT AUTO: Cuivre {ch['CUIVRE']:.2f}% vs Gold {ch['GOLD']:.2f}%\nJ'ACHETE {XRP_SIZE} XRP + {SOL_SIZE} SOL"
                            print(msg)
                            send_telegram(msg)
                    except Exception as e:
                        print(f"Erreur trade achat: {e}")

            # --- 3. LOGIQUE V3 VENTE (inversement tout seul) ---
            # Si NASDAQ sous-performe DOW = Risk-Off = VENTE
            if ch['NASDAQ'] - ch['DOW'] < -SEUIL:
                if trade_exchange:
                    try:
                        # Vend tout
                        bal = trade_exchange.fetch_balance()
                        xrp_bal = bal['XRP']['free'] if 'XRP' in bal and bal['XRP'] else 0
                        sol_bal = bal['SOL']['free'] if 'SOL' in bal and bal['SOL'] else 0
                        if xrp_bal >= 1:
                            trade_exchange.create_market_sell_order('XRP/USDT', xrp_bal)
                        if sol_bal >= 0.01:
                            trade_exchange.create_market_sell_order('SOL/USDT', sol_bal)
                        msg = f"⚠️ V3 VENTE AUTO: NASDAQ {ch['NASDAQ']:.2f}% vs DOW {ch['DOW']:.2f}%\nJe VENDS tout seul"
                        print(msg)
                        send_telegram(msg)
                    except Exception as e:
                        print(f"Erreur trade vente: {e}")

        except Exception as e:
            print(f"Erreur: {e}")

        time.sleep(60) # Check toutes les 60 secondes

# --- LANCEMENT ---
if __name__ == "__main__":
    Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
