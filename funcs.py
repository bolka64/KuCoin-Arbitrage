import requests
import json
import time
import hashlib
import base64
import hmac
from kucoin.client import Client
import csv

# Iintialise Kucoin Account
api_key = "API_KEY"
api_secret = "API_SECRET"
api_passphrase = "API_PASS"
client = Client(api_key, api_secret, api_passphrase, sandbox=False)

# Fetch Pairs Information for Formatting Size and Price
pair_info = client.get_symbols()
for pair in pair_info:
  if pair['symbol'] == 'INJ-BTC':
    break

# Fetch pairs
def get_pairs():
    pairs=[]
    url = 'https://api.kucoin.com/api/v1/symbols'
    data = requests.get(url).json()['data']

    for pair in data:
        if pair['symbol'] != pair['name']:
            continue
        pairs.append([pair['symbol'], pair['baseCurrency'], pair['quoteCurrency']])

    return pairs

# Fetch Triangular Pairs
def fetch_triangular_pairs(pairs):
    pairs_list = pairs[0:]
    triangular_arbitrage_list = []
    remove_duplicates_list = []
    for pair_a in pairs_list:
        # pair_a = pair[0]
        a_base = pair_a[1]
        a_quote = pair_a[2]

        for pair_b in pairs_list:
            if pair_a != pair_b[0]:
                if pair_b[1] in pair_a or pair_b[2] in pair_a:
                    b_base = pair_b[1]
                    b_quote = pair_b[2]

                    for pair_c in pairs_list:
                        if pair_a != pair_c[0] and pair_b != pair_c[0]:
                            combine_all = [pair_a[0], pair_b[0], pair_c[0]]
                            c_base = pair_c[1]
                            c_quote = pair_c[2]

                            pair_box = [a_base, a_quote, b_base, b_quote, c_base, c_quote]

                            count_c_base = 0
                            for i in pair_box:
                                if i == c_base:
                                    count_c_base += 1
                            
                            count_c_quote = 0
                            for i in pair_box:
                                if i == c_quote:
                                    count_c_quote += 1
                            # print(count_c_base, count_c_quote)
                            if count_c_base == 2 and count_c_quote == 2 and c_base != c_quote:
                                # print(pair_a[0], pair_b[0], pair_c[0])
                                combined = pair_a[0] + ',' + pair_b[0] + ',' + pair_c[0]
                                unique_item = ''.join(sorted(combine_all))

                                if unique_item not in remove_duplicates_list:
                                    match_dict = {
                                        'a_base': a_base,
                                        'b_base': b_base,
                                        'c_base': c_base,
                                        'a_quote': a_quote,
                                        'b_quote': b_quote,
                                        'c_quote': c_quote,
                                        'pair_a': pair_a[0],
                                        'pair_b': pair_b[0],
                                        'pair_c': pair_c[0],
                                        'combined': combined
                                    }

                                    triangular_arbitrage_list.append(match_dict)
                                    remove_duplicates_list.append(unique_item)
                                    
    return triangular_arbitrage_list

# Fetch orderbook
def get_orderbook(pair):
    url = f'https://api.kucoin.com/api/v1/market/orderbook/level2_20?symbol={pair}'
    r = requests.get(url)

    return r.json()['data']

# Reformat Orderbook
def reformat_orderbook(prices, c_direction):
    price_list_main = []
    if c_direction == 'base_to_quote':
        for p in prices['bids']:
            bid_price = float(p[0])
            adj_price = bid_price
            adj_quantity = float(p[1])
            price_list_main.append([adj_price, adj_quantity])

    if c_direction == 'quote_to_base':
        for p in prices['asks']:
            ask_price = float(p[0])
            adj_price = 1/ask_price if ask_price != 0 else 0
            adj_quantity = float(p[1]) * ask_price
            price_list_main.append([adj_price, adj_quantity])

    return price_list_main

# Calculate Acquired Coin
def calculate_acquired_coin(amount_in, orderbook):
    # Initialise Variable
    trading_balance = amount_in
    quantity_bought = 0
    acquired_coin = 0
    counts = 0

    for level in orderbook:
        # Extract the level price and quantity
        level_price = level[0]
        level_available_quantity = level[1]

        # Amount In is <= first level total amount
        if trading_balance <= level_available_quantity:
            quantity_bought = trading_balance
            trading_balance = 0
            amount_bought = quantity_bought * level_price

        # Amount In is > a given level total amount
        if trading_balance > level_available_quantity:
            print(f'trading_balance_{counts} = {trading_balance}')
            print(f'level_available_quantity_{counts} = {level_available_quantity}')
            quantity_bought = level_available_quantity
            trading_balance -= quantity_bought
            amount_bought = quantity_bought * level_price

        # Accumulate Acquired Coin
        acquired_coin += amount_bought

        # Exit Trade
        if trading_balance == 0:
            print('counts = ', counts)
            return acquired_coin

        # Exit if not enough order book levels
        counts += 1
        if counts == len(orderbook):
            return 0
        
        
# Get Highest Bid and Lowest Ask Price
def get_prices():
    url = 'https://api.kucoin.com/api/v1/market/allTickers'
    r = requests.get(url).json()
    price_dict={}
    for pair in r['data']['ticker']:
        # buy -----> highest bid
        # sell ----> lowest ask
        # ASK > BID
        price_dict[f'{pair["symbol"]}'] = {'lowestAsk': pair['sell'], 'highestBid': pair['buy']}

    return price_dict

# Get Bid and Ask Price
def get_bid_ask(pair, pos, price_dict):
  # r = requests.get('https://poloniex.com/public?command=returnTicker').json()
  if pos == 'ask':
    return price_dict[pair]['lowestAsk']
  if pos == 'bid':
    return price_dict[pair]['highestBid']

# Set Order
def order(side, symbol, size):
  api_key = "API_KEY"
  api_secret = "API_SECRET"
  api_passphrase = "API_PASS"

  url = "https://api.kucoin.com/api/v1/orders"

  now = int(time.time() * 1000)

  data = {"clientOid": "AAbb", "side": side, "symbol": symbol, "type": "market", "size": size}
  data_json = json.dumps(data)

  str_to_sign = str(now) + 'POST' + '/api/v1/orders' + data_json

  signature = base64.b64encode(hmac.new(api_secret.encode(
      'utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())

  passphrase = base64.b64encode(hmac.new(api_secret.encode(
      'utf-8'), api_passphrase.encode('utf-8'), hashlib.sha256).digest())

  headers = {
      "KC-API-SIGN": signature,
      "KC-API-TIMESTAMP": str(now),
      "KC-API-KEY": api_key,
      "KC-API-PASSPHRASE": passphrase,
      "KC-API-KEY-VERSION": "2",
      "Content-Type": "application/json"
  }
  try:
      res = requests.post(url, headers=headers, data=data_json).json()
      
      # return res

  except Exception as err:
      return err
  
  
# Calculate Surface Arbitrage
def calculate_surface_arb_rev_1(tri_arb_pairs, start_amount):
  # price_json = requests.get('https://poloniex.com/public?command=returnTicker').json()

  price_dict = get_prices()

  for tpair in tri_arb_pairs:
    """
      GENERAL RULES:
        BASE ----> QUOTE  : BID
        QUOTE ----> BASE  : 1 / ASK
        ASK > BID
    """
    # Get Variables
    surface_dict = {}
    min_surface_rate = 0.3
    start_amount = float(start_amount)
    contract_2 = 0
    contract_3 = 0
    start_coin_list = ['USDT', 'BTC', 'ETH']

    pair_a = tpair['pair_a']
    pair_b = tpair['pair_b']
    pair_c = tpair['pair_c']

    a_base = tpair['a_base']
    a_quote = tpair['a_quote']
    b_base = tpair['b_base']
    b_quote = tpair['b_quote']
    c_base = tpair['c_base']
    c_quote = tpair['c_quote']

    # a_ask = float(bid_ask_price(pair_a)['asks'][0])
    # a_bid = float(bid_ask_price(pair_a)['bids'][0])
    # b_ask = float(bid_ask_price(pair_b)['asks'][0])
    # b_bid = float(bid_ask_price(pair_b)['bids'][0])
    # c_ask = float(bid_ask_price(pair_c)['asks'][0])
    # c_bid = float(bid_ask_price(pair_c)['bids'][0])

    a_ask = float(get_bid_ask(a_base + '-' + a_quote, 'ask', price_dict))
    a_bid = float(get_bid_ask(a_base + '-' + a_quote, 'bid', price_dict))
    b_ask = float(get_bid_ask(b_base + '-' + b_quote, 'ask', price_dict))
    b_bid = float(get_bid_ask(b_base + '-' + b_quote, 'bid', price_dict))
    c_ask = float(get_bid_ask(c_base + '-' + c_quote, 'ask', price_dict))
    c_bid = float(get_bid_ask(c_base + '-' + c_quote, 'bid', price_dict))

    calculated = 0

    acquired_coin_t1 = 0
    acquired_coin_t2 = 0
    acquired_coin_t3 = 0

    direction_trade_1 = 0
    direction_trade_2 = 0
    direction_trade_3 = 0

    # forward: base ----> quote
    # reserve: quote ---> base
    direction = ['forward', 'reverse']

    for dir in direction:
      swap_1 = 0
      swap_2 = 0
      swap_3 = 0

      swap_price_1 = 0
      swap_price_2 = 0
      swap_price_3 = 0

      if dir == 'forward':
        swap_1 = a_base
        swap_2 = a_quote
        swap_price_1 = a_bid
        direction_trade_1 = 'base_to_quote'

      if dir == 'reverse':
        swap_1 = a_quote
        swap_2 = a_base
        swap_price_1 = 1/a_ask
        direction_trade_1 = 'quote_to_base'

      contract_1 = pair_a
      acquired_coin_t1 = start_amount * swap_price_1

      """ FORWARD """
      #SCENARIO 1: if a_quote = b_quote
      if dir == 'forward':
        if a_quote == b_quote and calculated == 0:
          swap_price_2 = 1/b_ask
          acquired_coin_t2 = acquired_coin_t1 * swap_price_2
          direction_trade_2 = 'quote_to_base'
          contract_2 = pair_b

          # if b_base = c_base
          if b_base == c_base:
            swap_3 = c_base
            swap_price_3 = c_bid
            direction_trade_3 = 'base_to_quote'
            contract_3 = pair_c


          # if b_base = c_quote
          if b_base == c_quote:
            swap_3 = c_quote
            swap_price_3 = 1/c_ask
            direction_trade_3 = 'quote_to_base'
            contract_3 = pair_c

          acquired_coin_t3 = acquired_coin_t2 * swap_price_3
          calculated = 1

      # SCENARIO 2: if a_quote = b_base
      if dir == 'forward':
        if a_quote == b_base and calculated == 0:
          swap_price_2 = b_bid
          acquired_coin_t2 = acquired_coin_t1 * swap_price_2
          direction_trade_2 = 'base_to_quote'
          contract_2 = pair_b

          # if b_quote = c_base
          if b_quote == c_base:
            swap_3 = c_base
            swap_price_3 = c_bid
            direction_trade_3 = 'base_to_quote'
            contract_3 = pair_c

          # if b_quote = c_quote
          if b_quote == c_quote:
            swap_3 = c_quote
            swap_price_3 = 1/c_ask
            direction_trade_3 = 'quote_to_base'
            contract_3 = pair_c

          acquired_coin_t3 = acquired_coin_t2 * swap_price_3
          calculated = 1

      #SCENARIO 3: if a_quote = c_quote
      if dir == 'forward':
        if a_quote == c_quote and calculated == 0:
          swap_price_2 = 1/c_ask
          acquired_coin_t2 = acquired_coin_t1 * swap_price_2
          direction_trade_2 = 'quote_to_base'
          contract_2 = pair_c

          # if c_base = b_base
          if c_base == b_base:
            swap_3 = b_base
            swap_price_3 = b_bid
            direction_trade_3 = 'base_to_quote'
            contract_3 = pair_b

          # if c_base = b_quote
          if c_base == b_quote:
            swap_3 = b_quote
            swap_price_3 = 1/b_ask
            direction_trade_3 = 'quote_to_base'
            contract_3 = pair_b

          acquired_coin_t3 = acquired_coin_t2 * swap_price_3
          calculated = 1

      # SCENARIO 4: if a_quote = c_base
      if dir == 'forward':
        if a_quote == c_base and calculated == 0:
          swap_price_2 = c_bid
          acquired_coin_t2 = acquired_coin_t1 * swap_price_2
          direction_trade_2 = 'base_to_quote'
          contract_2 = pair_c

          # if c_quote = b_base
          if c_quote == b_base:
            swap_3 = b_base
            swap_price_3 = b_bid
            direction_trade_3 = 'base_to_quote'
            contract_3 = pair_b

          # if c_quote = b_quote
          if c_quote == b_quote:
            swap_3 = b_quote
            swap_price_3 = 1/b_ask
            direction_trade_3 = 'quote_to_base'
            contract_3 = pair_b

          acquired_coin_t3 = acquired_coin_t2 * swap_price_3
          calculated = 1


      """ REVERSE """
      #SCENARIO 1: if a_base = b_quote
      if dir == 'reverse':
        if a_base == b_quote and calculated == 0:
          swap_price_2 = 1/b_ask
          acquired_coin_t2 = acquired_coin_t1 * swap_price_2
          direction_trade_2 = 'quote_to_base'
          contract_2 = pair_b

          # if b_base = c_base
          if b_base == c_base:
            swap_3 = c_base
            swap_price_3 = c_bid
            direction_trade_3 = 'base_to_quote'
            contract_3 = pair_c

          # if b_base = c_quote
          if b_base == c_quote:
            swap_3 = c_quote
            swap_price_3 = 1/c_ask
            direction_trade_3 = 'quote_to_base'
            contract_3 = pair_c

          acquired_coin_t3 = acquired_coin_t2 * swap_price_3
          calculated = 1

      # SCENARIO 2: if a_base = b_base
      if dir == 'reverse':
        if a_base == b_base and calculated == 0:
          swap_price_2 = b_bid
          acquired_coin_t2 = acquired_coin_t1 * swap_price_2
          direction_trade_2 = 'base_to_quote'
          contract_2 = pair_b

          # if b_quote = c_base
          if b_quote == c_base:
            swap_3 = c_base
            swap_price_3 = c_bid
            direction_trade_3 = 'base_to_quote'
            contract_3 = pair_c

          # if b_quote = c_quote
          if b_quote == c_quote:
            swap_3 = c_quote
            swap_price_3 = 1/c_ask
            direction_trade_3 = 'quote_to_base'
            contract_3 = pair_c

          acquired_coin_t3 = acquired_coin_t2 * swap_price_3
          calculated = 1

      #SCENARIO 3: if a_base = c_quote
      if dir == 'reverse':
        if a_base == c_quote and calculated == 0:
          swap_price_2 = 1/c_ask
          acquired_coin_t2 = acquired_coin_t1 * swap_price_2
          direction_trade_2 = 'quote_to_base'
          contract_2 = pair_c

          # if c_base = b_base
          if c_base == b_base:
            swap_3 = b_base
            swap_price_3 = b_bid
            direction_trade_3 = 'base_to_quote'
            contract_3 = pair_b

          # if c_base = b_quote
          if c_base == b_quote:
            swap_3 = b_quote
            swap_price_3 = 1/b_ask
            direction_trade_3 = 'quote_to_base'
            contract_3 = pair_b

          acquired_coin_t3 = acquired_coin_t2 * swap_price_3
          calculated = 1

      # SCENARIO 4: if a_base = c_base
      if dir == 'reverse':
        if a_base == c_base and calculated == 0:
          swap_price_2 = c_bid
          acquired_coin_t2 = acquired_coin_t1 * swap_price_2
          direction_trade_2 = 'base_to_quote'
          contract_2 = pair_c

          # if c_quote = b_base
          if c_quote == b_base:
            swap_3 = b_base
            swap_price_3 = b_bid
            direction_trade_3 = 'base_to_quote'
            contract_3 = pair_b

          # if c_quote = b_quote
          if c_quote == b_quote:
            swap_3 = b_quote
            swap_price_3 = 1/b_ask
            direction_trade_3 = 'quote_to_base'
            contract_3 = pair_b

          acquired_coin_t3 = acquired_coin_t2 * swap_price_3
          calculated = 1

      """ PROFIT LOSS OUTPUT """
      profit_loss = acquired_coin_t3 - start_amount
      profit_loss_perc = (profit_loss / start_amount)*100 if profit_loss != 0 else 0


      # Report

      trade_log1 = f'start with {start_amount} of {swap_1}. exchange {start_amount} of {swap_1} at price {swap_price_1} to {acquired_coin_t1} of {swap_2}.'
      trade_log2 = f'exchange {acquired_coin_t1} of {swap_2} at price {swap_price_2} to {acquired_coin_t2} of {swap_3}. '
      trade_log3 = f'exchange {acquired_coin_t2} of {swap_3} at price {swap_price_3} to {acquired_coin_t3} of {swap_1}.'

      # Output results
      if profit_loss_perc > min_surface_rate:
        surface_dict = {
            'pair_a': pair_a,
            'pair_b': pair_b,
            'pair_c': pair_c,
            'swap_1': swap_1,
            'swap_2': swap_2,
            'swap_3': swap_3,
            'contract_1': contract_1,
            'contract_2': contract_2,
            'contract_3': contract_3,
            'direction_trade_1': direction_trade_1,
            'direction_trade_2': direction_trade_2,
            'direction_trade_3': direction_trade_3,
            'start_amount': start_amount,
            'acquired_coin_t1': acquired_coin_t1,
            'acquired_coin_t2': acquired_coin_t2,
            'acquired_coin_t3': acquired_coin_t3,
            'swap_price_1': swap_price_1,
            'swap_price_2': swap_price_2,
            'swap_price_3': swap_price_3,
            'profit_loss': profit_loss,
            'profit_loss_perc': profit_loss_perc,
            'direction': dir,
            'trade_description_1': trade_log1,
            'trade_description_2': trade_log2,
            'trade_description_3': trade_log3,
            'c_quote': c_quote,
            'c_base': c_base,
            'b_quote': b_quote,
            'b_base': b_base,
            'a_quote': a_quote,
            'a_base': a_base
        }
        return surface_dict

  return surface_dict


# Calculate Depth orderbook
def get_depth(surface_arb, start_amount):
    swap_1 = surface_arb['swap_1']
    swap_2 = surface_arb['swap_2']
    swap_3 = surface_arb['swap_3']
    #   start_amount = surface_arb['start_amount']

    # Define Pairs
    contract_1 = surface_arb['contract_1']
    contract_2 = surface_arb['contract_2']
    contract_3 = surface_arb['contract_3']

    # Define Direction of Trade
    direction_trade_1 = surface_arb['direction_trade_1']
    direction_trade_2 = surface_arb['direction_trade_2']
    direction_trade_3 = surface_arb['direction_trade_3']

    # Get Orderbook for First Trade
    depth_1_price = get_orderbook(contract_1)
    depth_1_reformatted_prices = reformat_orderbook(depth_1_price, direction_trade_1)

    depth_2_price = get_orderbook(contract_2)
    depth_2_reformatted_prices = reformat_orderbook(depth_2_price, direction_trade_2)

    depth_3_price = get_orderbook(contract_3)
    depth_3_reformatted_prices = reformat_orderbook(depth_3_price, direction_trade_3)

    # Get Acquired Coin
    acquired_coin_1 = calculate_acquired_coin(start_amount, depth_1_reformatted_prices)
    acquired_coin_2 = calculate_acquired_coin(acquired_coin_1, depth_2_reformatted_prices)
    acquired_coin_3 = calculate_acquired_coin(acquired_coin_2, depth_3_reformatted_prices)

    # Calculate Profit Loss
    profit_loss = acquired_coin_3 - start_amount
    real_rate_perc = (profit_loss/start_amount) * 100 if start_amount != 0 else 0

    #   if real_rate_perc > 0:
    return {
        'profit_loss': profit_loss,
        'real_rate_perc': real_rate_perc,
        'contract_1': contract_1,
        'contract_2': contract_2,
        'contract_3': contract_3,
        'direction_trade_1': direction_trade_1,
        'direction_trade_2': direction_trade_2,
        'direction_trade_3': direction_trade_3,
        'swap_1': swap_1,
        'swap_2': swap_2,
        'swap_3': swap_3,
        'acquired_coin_1': acquired_coin_1,
        'acquired_coin_2': acquired_coin_2,
        'acquired_coin_3': acquired_coin_3,
        'start_amount': start_amount
    }

    #   else:
    #     # return {'real_rate_perc': real_rate_perc}
    #     return {}

# Format Price and Size of Pairs for Order
def format_(pair, size, side):
  for p in pair_info:
    if p['symbol'] == pair:
      # if side == 'buy':
      #   increment = p['quoteIncrement']
      #   break
      # elif side == 'sell':
      #   increment = p['baseIncrement']
      #   break
      q_increment = p['quoteIncrement']
      b_increment = p['baseIncrement']

      if len(q_increment) >= len(b_increment):
        increment = b_increment
      else:
        increment = q_increment
      
      break
  
  if '.' in str(size):
    p = str(size).split('.')
  else:
    return size
    
  x = increment.split('.')
  f = len(x[1])

  size = p[0]+'.'+p[1][:f]

  return size

def send_to_telegram(text):
  TOKEN = "TOKEN"
  chat_id = ""
  message = text
  url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
  r = requests.get(url)

def save_item_in_file(file_name, item):
   with open (f'{file_name}.txt', 'a') as f:
    f.write(item)

def save_item_in_csv(file_name, item):
  with open(f'{file_name}.csv', 'a', newline='') as file:
    writer = csv.writer(file)    
    writer.writerow([item])
# 
