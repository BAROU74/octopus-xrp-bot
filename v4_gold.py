import ccxt, time, os, requests, yfinance as yf, pandas as pd
from flask import Flask
from threading import Thread

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
BTSE_KEY = os.environ.get("BTSE_KEY")
BTSE_SECRET = os.environ.get("BTSE_SECRET")

SEUIL_PEUR = 1.0  # GOLD - CUIVRE > 1.0% = PEUR
SEUIL_RISKON = 1.0 # CUIVRE - GOLD > 1.0% = On sort de GOLD
LEVIER = 2
TP_PCT = 2.5
SL_PCT = 1.5
TICKERS = {"GOLD":"GLD", "CUIVRE":"COPX", "NASDAQ":"QQQ", "DOW":"DIA", "PAXG":"PAXG-USD"}

SYMBOL_BTSE = "PAXG-PERP" # BTSE format, fallback géré dans le code

app = Flask(__name__)
@app.route('/')
def home(): return "🟡 V4 GOLD PERP LONG x2"

def send_telegram(msg):
    if TELEGRAM_TOKEN and CHAT_ID:
        try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        except: pass

def get_change(ticker):
    try:
        d = yf.Ticker(ticker).history(period="5d", interval="1d")
        if len(d) < 2: return 0
        return ((d['Close'].iloc[-1]-d['Close'].iloc[-2])/d['Close'].iloc[-2])*100
    except: return 0

def get_rsi_ema(ticker):
    try:
        d = yf.Ticker(ticker).history(period="3mo", interval="1d")
        if len(d) < 60: return 50, 0, d['Close'].iloc[-1]
        delta = d['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        ema50 = d['Close'].ewm(span=50).mean().iloc[-1]
        price = d['Close'].iloc[-1]
        return rsi.iloc[-1], ema50, price
    except: return 50, 0, 0

def run_bot():
    print(f"🟡 V4 GOLD x{LEVIER} demarre")
    send_telegram(f"🟡 V4 GOLD PERP LONG ONLY x{LEVIER} EN LIGNE\nAchat si: GOLD-CUIVRE > {SEUIL_PEUR}% + NASDAQ-DOW < -0.5% + RSI<65\nVente: TP +{TP_PCT}% / SL -{SL_PCT}% ou Risk-ON")
    ex = None
    if BTSE_KEY and BTSE_SECRET:
        try:
            ex = ccxt.btse({'apiKey': BTSE_KEY, 'secret': BTSE_SECRET, 'enableRateLimit': True, 'options': {'defaultType': 'future'}})
            bal = ex.fetch_balance()
            print(f"BTSE FUTURE OK USDT {bal.get('USDT',{}).get('free',0)}")
            # Set leverage
            try: ex.set_leverage(LEVIER, SYMBOL_BTSE)
            except: pass
        except Exception as e:
            print(f"Erreur BTSE: {e}")
            send_telegram(f"❌ BTSE V4 Erreur: {e}")

    entry_price = None
    loop = 0
    while True:
        try:
            loop+=1
            ch = {k: get_change(v) for k,v in TICKERS.items() if k!="PAXG"}
            rsi, ema50, price_gold = get_rsi_ema(TICKERS["PAXG"])
            spread_peur = ch['GOLD'] - ch['CUIVRE']
            spread_tech = ch['NASDAQ'] - ch['DOW']
            spread_riskon = ch['CUIVRE'] - ch['GOLD']
            print(f"V4 #{loop} | PEUR={spread_peur:.2f}% (>{SEUIL_PEUR}?) | TECH={spread_tech:.2f}% | RSI={rsi:.1f}")

            if loop % 20 == 0:
                send_telegram(f"💓 V4 #{loop}\nPEUR GOLD-CUIVRE={spread_peur:.2f}% besoin >{SEUIL_PEUR}%\nTECH NASDAQ-DOW={spread_tech:.2f}% besoin <-0.5%\nRSI GOLD={rsi:.1f} EMA50={ema50:.2f}")

            if ex:
                pos = 0
                try:
                    positions = ex.fetch_positions([SYMBOL_BTSE])
                    for p in positions:
                        if float(p.get('contracts',0))>0: 
                            pos = float(p.get('contracts',0))
                            entry_price = float(p.get('entryPrice',0))
                except: pass

                # CONDITION ACHAT
                if pos==0 and spread_peur > SEUIL_PEUR and spread_tech < -0.5 and rsi < 65 and price_gold > ema50:
                    try:
                        bal = ex.fetch_balance()
                        usdt = float(bal.get('USDT',{}).get('free',0))
                        amount_usd = usdt * 0.30 # 30% du capital
                        if amount_usd > 5:
                            # Convert USD to PAXG qty
                            qty = round((amount_usd * LEVIER) / price_gold, 4)
                            ex.create_market_buy_order(SYMBOL_BTSE, qty)
                            send_telegram(f"🟡 ACHAT GOLD LONG x{LEVIER}\nPEUR={spread_peur:.2f}% TECH={spread_tech:.2f}% RSI={rsi:.1f}\nQty {qty} PAXG ~{amount_usd:.2f}$")
                    except Exception as e: print(f"Erreur achat V4 {e}"); send_telegram(f"❌ Erreur achat V4 {e}")

                # CONDITIONS VENTE
                if pos>0 and entry_price:
                    pnl_pct = ((price_gold - entry_price)/entry_price)*100 * LEVIER
                    if pnl_pct >= TP_PCT or pnl_pct <= -SL_PCT or spread_riskon > SEUIL_RISKON:
                        try:
                            ex.create_market_sell_order(SYMBOL_BTSE, pos)
                            reason = "TP" if pnl_pct>=TP_PCT else "SL" if pnl_pct<=-SL_PCT else "RISK-ON"
                            send_telegram(f"💰 VENTE GOLD {reason} PnL {pnl_pct:.2f}%\nPEUR={spread_peur:.2f}%")
                            entry_price=None
                        except Exception as e: print(f"Erreur vente V4 {e}")
        except Exception as e: print(f"Loop V4 erreur {e}")
        time.sleep(90)

if __name__ == "__main__":
    Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
