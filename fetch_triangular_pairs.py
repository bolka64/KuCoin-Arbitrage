import json
from kucoin.client import Client
from funcs import *


api_key = "API_KEY"
api_secret = "API_SECRET"
api_passphrase = "API_PASS"
client = Client(api_key, api_secret, api_passphrase, sandbox=False)

tickers = client.get_ticker()['ticker']

with open('tickers.json', 'w', encoding='utf-8') as f:
    json.dump(tickers, f, ensure_ascii=False, indent=4)

class_A_pairs=[]
pairs = get_pairs()
for pair in pairs:
    for ticker in tickers:
        if ticker['symbol'] == pair[0] :
            if ticker['takerCoefficient'] == '1':
                class_A_pairs.append(pair)

tri_arb_pairs = fetch_triangular_pairs(class_A_pairs)

with open('tri_arb_pairs.json', 'w', encoding='utf-8') as f:
    json.dump(tri_arb_pairs, f, ensure_ascii=False, indent=4)

print('done')
send_to_telegram('DONE')