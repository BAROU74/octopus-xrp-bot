import ccxt, time, os, requests, yfinance as yf
from flask import Flask
from threading import Thread

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
BTSE_KEY = os.environ.get("BTSE_KEY")
BTSE_SECRET = os.environ.get("BTSE_SECRET")

SOL_SIZE = 0.01
XRP_SIZE = 1
SEUIL = 1.0  # <-- MEILLEUR POUR 2$ - 1.0% au lieu de 1.8%
TICKERS = {"GOLD":"GLD", "CUIVRE":"COPX", "NASDAQ":"QQQ", "DOW":"DIA"}

app = Flask(__name__)
@app.route('/')
def home():
    return "🔥 V3.2 SEUIL 1.0% - BEST FOR 2$"

def send_telegram(msg):
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        except: pass

def get_change(ticker):
    try:
        d = yf.Ticker(ticker).history(period="5d", interval="1d")
        if d.empty or len(d) < 2: return 0
        return ((d['Close'].iloc[-1]-d['Close'].iloc[-2])/d['Close'].iloc[-2])*100
    except: return 0

def run_bot():
    print(f"🐙 V3.2 SEUIL {SEUIL}% BEST demarre")
    send_telegram(f"🔥 V3.2 EN LIGNE - SEUIL PASSÉ À {SEUIL}% (MEILLEUR)\nAncien: 1.8% trop prudent\nNouveau: 1.0% = 1-2 trades/semaine\nCalcul: CUIVRE - GOLD > {SEUIL}%")
    price_exchange = ccxt.binance({'enableRateLimit': True})
    trade_exchange = None
    if BTSE_KEY and BTSE_SECRET:
        try:
            trade_exchange = ccxt.btse({'apiKey': BTSE_KEY, 'secret': BTSE_SECRET, 'enableRateLimit': True})
            bal = trade_exchange.fetch_balance()
            print(f"BTSE connecté OK USDT {bal.get('USDT',{}).get('free',0)}")
            send_telegram(f"✅ BTSE OK - USDT libre: {bal.get('USDT',{}).get('free',0):.2f}$")
        except Exception as e:
            print(f"Erreur BTSE: {e}")
            send_telegram(f"❌ Erreur BTSE: {e}")
    
    loop_count = 0
    while True:
        try:
            loop_count += 1
            ch = {k: get_change(v) for k,v in TICKERS.items()}
            spread_achat = ch['CUIVRE'] - ch['GOLD']
            spread_vente = ch['NASDAQ'] - ch['DOW']
            print(f"SCAN #{loop_count} | Achat: {spread_achat:.2f}% (besoin >{SEUIL}%) | Vente: {spread_vente:.2f}%")
            
            if loop_count % 30 == 0:
                send_telegram(f"💓 #{loop_count} SEUIL {SEUIL}%\nACHAT: CUIVRE({ch['CUIVRE']:.2f}%) - GOLD({ch['GOLD']:.2f}%) = {spread_achat:.2f}% / Besoin >{SEUIL}%\nVENTE: NASDAQ-DOW = {spread_vente:.2f}%")

            if spread_achat > SEUIL and trade_exchange:
                try:
                    bal = trade_exchange.fetch_balance()
                    if bal.get('USDT',{}).get('free',0) > 3:
                        trade_exchange.create_market_buy_order('XRP/USDT', XRP_SIZE)
                        trade_exchange.create_market_buy_order('SOL/USDT', SOL_SIZE)
                        send_telegram(f"🚨 ACHAT AUTO V3.2 [{SEUIL}%]\nCUIVRE-GOLD = {spread_achat:.2f}% > {SEUIL}%\n1 XRP + 0.01 SOL achetés sur BTSE!")
                except Exception as e: print(f"Erreur achat: {e}")

            if spread_vente < -SEUIL and trade_exchange:
                try:
                    bal = trade_exchange.fetch_balance()
                    xrp_bal = bal.get('XRP',{}).get('free',0)
                    sol_bal = bal.get('SOL',{}).get('free',0)
                    if xrp_bal >= 0.9: trade_exchange.create_market_sell_order('XRP/USDT', xrp_bal)
                    if sol_bal >= 0.009: trade_exchange.create_market_sell_order('SOL/USDT', sol_bal)
                    if xrp_bal >= 0.9 or sol_bal >= 0.009:
                        send_telegram(f"⚠️ VENTE AUTO V3.2\nNASDAQ-DOW = {spread_vente:.2f}% < -{SEUIL}%")
                except Exception as e: print(f"Erreur vente: {e}")
        except Exception as e: print(f"Erreur loop: {e}")
        time.sleep(60)

if __name__ == "__main__":
    Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
