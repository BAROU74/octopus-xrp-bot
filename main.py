import ccxt, time, os
API_KEY = os.environ.get("BTSE_KEY")
API_SECRET = os.environ.get("BTSE_SECRET")
exchange = ccxt.btse({'apiKey': API_KEY,'secret': API_SECRET,})
LOWER = 1.49
AMOUNT_USD = 6.75
print("🐙 OCTOPUS demarre sur Koyeb - check toutes les 2H", flush=True)
while True:
    try:
        ticker = exchange.fetch_ticker('XRP/USDT')
        price = ticker['last']
        print(f"Prix XRP: {price} $ - {time.ctime()}", flush=True)
        balance = exchange.fetch_balance()
        usdt_free = balance['free'].get('USDT', 0)
        if usdt_free > 4:
            try:
                exchange.cancel_all_orders('XRP/USDT')
            except:
                pass
            amount = AMOUNT_USD / LOWER
            exchange.create_limit_buy_order('XRP/USDT', amount, LOWER)
            print(f"BUY place {amount} XRP @ {LOWER}$", flush=True)
        else:
            print(f"Ordre deja en place, j'attends...", flush=True)
    except Exception as e:
        print(f"Erreur: {e}", flush=True)
    time.sleep(7200)
