import requests
import json
import time
import hashlib
import base64
import hmac
from kucoin.client import Client
import pandas as pd
import numpy as np
from funcs import *


pairs = get_pairs()

# we dont use below line because we save tri_arb_pairs.json befor and just load the file.
# tri_arb_pairs = fetch_triangular_pairs(pairs)

# Reading Triangular Pairs .json File
f = open("tri_arb_pairs.json", "r")
tri_arb_pairs = json.load(f)
f.close()

price_dict = get_prices()

# Intialise Kucoin Account (madan1386 API)
api_key = "API_KEY"
api_secret = "API_SECRET"
api_passphrase = "API_PASS"
client = Client(api_key, api_secret, api_passphrase, sandbox=False)


while True:
    time.sleep(15)

    # Calculate Surface Arbitrage
    assets_dict = {'BTC': 0.0005145, 'ETH': 0.01189292, 'USDC': 0.01741752, 'KCS': 1.19072623, 'USDT': 6.54722888}
    start_coin_list = [0.0005145, 0.01189292, 0.01741752, 1.19072623, 6.54722888]
    start_amount = 0.0005

    surface_arb = calculate_surface_arb_rev_1(tri_arb_pairs, start_amount)
    if surface_arb != {}:
        if surface_arb['swap_1'] in start_coin_list:
            start_coin = surface_arb['swap_1']
            start_amount = assets_dict[start_coin]
            print(start_coin, start_amount)
            depth = get_depth(surface_arb, start_amount)
            print(surface_arb)
            print('+++++++++++++++++++++++++++++++++++++++++++')
            # send_to_telegram('Depth Done!')

            if depth['real_rate_perc'] > 0.3:
                drr = depth['real_rate_perc']
                print(f'Real Rate is: {drr} %')

                swap_1 = depth['swap_1']
                swap_2 = depth['swap_2']
                swap_3 = depth['swap_3']
                contract_1 = depth['contract_1']
                contract_2 = depth['contract_2']
                contract_3 = depth['contract_3']
                direction_trade_1 = depth['direction_trade_1']
                direction_trade_2 = depth['direction_trade_2']
                direction_trade_3 = depth['direction_trade_3']
                acquired_coin_1 = depth['acquired_coin_1']
                acquired_coin_2 = depth['acquired_coin_2']
                acquired_coin_3 = depth['acquired_coin_3']
                real_rate_perc = depth['real_rate_perc']
                profit_loss = depth['profit_loss']

                """TRADES"""             
                # Trade 1
                if direction_trade_1 == 'base_to_quote':
                    side_1 = 'sell'
                    qty_1 = start_amount
                    
                elif direction_trade_1 == 'quote_to_base':
                    side_1 = 'buy'
                    qty_1 = acquired_coin_1

                else:
                    print('Order 1 Error')
                    continue

                qty_1 = format_(contract_1, qty_1, side_1)

                print((side_1))
                print((contract_1))
                print((qty_1))

                order_1 = client.create_market_order(contract_1, side_1, size=qty_1)


                # Trade 2
                if direction_trade_2 == 'base_to_quote':
                    side_2 = 'sell'
                    qty_2 = acquired_coin_1
                elif direction_trade_2 == 'quote_to_base':
                    side_2 = 'buy'
                    qty_2 = acquired_coin_2

                else:
                    print('Order 2 Error')
                    continue

                qty_2 = format_(contract_2, qty_2, side_2)

                print((side_2))
                print((contract_2))
                print((qty_2))

                order_2 = client.create_market_order(contract_2, side_2, size=qty_2)

                time.sleep(0.1)
                # Trade 3
                if direction_trade_3 == 'base_to_quote':
                    side_3 = 'sell'
                    qty_3 = acquired_coin_2
                elif direction_trade_3 == 'quote_to_base':
                    side_3 = 'buy'
                    qty_3 = acquired_coin_3

                else:
                    print('Order 3 Error')
                    continue

                qty_3 = format_(contract_3, qty_3, side_3)

                print((side_3))
                print((contract_3))
                print((qty_3))

                try:
                    order_3 = client.create_market_order(contract_3, side_3, size=qty_3)

                except:
                    acc = client.get_accounts()
                    for ac in acc:
                        if ac['currency'] == swap_3:
                            qty = ac['available']

                    print(f'qty: {qty}')      
                    qty = format_(contract_3, qty, side_3)

                    print(f'formatted qty: {qty}')
                    order_3 = client.create_market_order(contract_3, side_3, size=qty)
                    
                print('**************************************** All Orders Done. *******************************************')
                summary = f'''
                Real Rate:  {drr} ,
                Side 1:  {side_1},
                Trade 1:  {contract_1},
                QTY 1:   {qty_1},

                Side 2:  {side_2},
                Trade 2:  {contract_2},
                QTY 2:   {qty_2},

                Side 3:  {side_3},
                Trade 3:  {contract_3},
                QTY 3:   {qty_3}              
                
                '''
                send_to_telegram(summary)
                break
                
            else:
                real_rate_perc = depth['real_rate_perc']
                print(f'Start Coin is {start_coin} and Real Rate is {real_rate_perc}')
                continue

        else:
            coin1 = surface_arb['swap_1']
            surface_profit_loss = surface_arb['profit_loss_perc']
            print(f'{coin1} is not in Starting Coins List but surface rate is {surface_profit_loss}')
            save_item_in_csv('coins_not_in_startcoins', coin1)
            continue

    else:
        print('NO SURFACE ARB.')
        continue



