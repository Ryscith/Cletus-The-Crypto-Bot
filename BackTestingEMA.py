#  Version 0.11 - Model T
#  Author: Reilly Schultz
#  Date: August 16th, 2021

import config
import ccxt
import pandas as pd
pd.set_option('max_rows', None)

import warnings
warnings.filterwarnings('ignore')

from datetime import datetime, timedelta
import schedule, time, csv

exchange = ccxt.binanceus({
   "apiKey": config.BINANCE_API_KEY,
   "secret": config.BINANCE_SECRET_KEY
})

def tr(df): # Calculates the true range and adds it to the dataframe
   df['previous_close'] = df['close'].shift(1)
   df['high-low'] = df['high'] - df['low']
   df['high-pc'] = abs(df['high'] - df['previous_close'])
   df['low-pc'] = abs(df['low'] - df['previous_close'])
   tr = df[['high-low', 'high-pc', 'low-pc']].max(axis=1)

   return tr

def atr(df, period = 14): # Calculates the average true range and adds it the dataframe
   df['tr'] = tr(df)

   the_atr = df['tr'].rolling(period).mean()

   df['atr'] = the_atr
   return the_atr

def long_term_ema(df, long_period = 21, smoothing = 2):
   for current in range(1, len(df.index)):
      previous = current - 1
      if current < long_period:
         df['long_term_ema'][current] = None
      elif current == long_period:
         df['long_term_ema'][current] = (df['close'][current] * (smoothing / (1 + long_period))) + df['long_term_sma'][previous] * (1 - (smoothing / (1 + long_period)))
      else:
         df['long_term_ema'][current] = (df['close'][current] * (smoothing / (1 + long_period))) + df['long_term_ema'][previous] * (1 - (smoothing / (1 + long_period)))

def short_term_ema(df, short_period = 10, smoothing = 2):
   for current in range(1, len(df.index)):
      previous = current - 1
      if current < short_period:
         df['short_term_ema'][current] = None
      elif current == short_period:
         df['short_term_ema'][current] = (df['close'][current] * (smoothing / (1 + short_period))) + df['short_term_sma'][previous] * (1 - (smoothing / (1 + short_period)))
      else:
         df['short_term_ema'][current] = (df['close'][current] * (smoothing / (1 + short_period))) + df['short_term_ema'][previous] * (1 - (smoothing / (1 + short_period)))


def ema_crossover(df, coin_name, short_period = 10, long_period = 21, smoothing = 2):
   test_original_balance = 10000
   test_running_balance = test_original_balance
   test_in_position = False
   test_sell_price = 0
   test_buy_price = 0
   test_buy_amt = 0
   test_wins = 0
   test_losses = 0

   df['atr'] = atr(df, short_period)
   df['trailing_stop'] = ((df['close']) - (df['atr'] * 5))

   df['long_term_sma'] = df['close'].rolling(long_period).mean()
   df['short_term_sma'] = df['close'].rolling(short_period).mean()

   df['long_term_ema'] = None
   df['short_term_ema'] = None

   long_term_ema(df, long_period, smoothing)
   short_term_ema(df, short_period, smoothing)

   df['in_uptrend'] = None

   for current in range(1, len(df.index)):
      previous = current - 1

      if (df['trailing_stop'][previous] > df['trailing_stop'][current]) and test_in_position:
         df['trailing_stop'][current] = df['trailing_stop'][previous]

      if (df['short_term_ema'][current] == None) or (df['long_term_ema'][current] == None):
         df['in_uptrend'][current] = None

      elif df['short_term_ema'][current] > df['long_term_ema'][current]:
         df['in_uptrend'][current] = True
      
      else:
         df['in_uptrend'][current] = False

      if df['in_uptrend'][current] and not (df['in_uptrend'][previous]) and not test_in_position:
         test_buy_price = df['close'][current]
         test_buy_amt = (test_running_balance * 1) / test_buy_price
         test_running_balance = test_running_balance - (test_buy_amt * test_buy_price)
         test_in_position = True
         print(f"Bought {test_buy_amt} {coin_name} at {test_buy_price} on {df['timestamp'][current]}")
         with open('record.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter='|')
            writer.writerow(['buy', test_buy_amt, test_buy_price, df['timestamp'][current]])

      elif not df['in_uptrend'][current] and df['in_uptrend'][previous] and test_in_position:
         test_sell_price = df['close'][current]
         test_running_balance = test_running_balance + (test_buy_amt * test_sell_price)
         test_in_position = False
         print(f"Sold {test_buy_amt} {coin_name} at {test_sell_price} on {df['timestamp'][current]} at a difference in price of {test_sell_price - test_buy_price}\n")
         with open('record.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter='|')
            writer.writerow(['sell', test_buy_amt, test_sell_price, df['timestamp'][current], [((test_sell_price / test_buy_price) * 100) - 100]])
         if test_buy_price < test_sell_price:
            test_wins = test_wins + 1
         else:
            test_losses = test_losses + 1
      
      elif df['close'][current] < df['trailing_stop'][current] and test_in_position:
         test_sell_price = df['close'][current]
         test_running_balance = test_running_balance + (test_buy_amt * test_sell_price)
         test_in_position = False
         print(f"Sold {test_buy_amt} {coin_name} at {test_sell_price} on {df['timestamp'][current]} at a difference in price of {test_sell_price - test_buy_price}\n")
         with open('record.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter='|')
            writer.writerow(['sell', test_buy_amt, test_sell_price, df['timestamp'][current], [((test_sell_price / test_buy_price) * 100) - 100]])
         if test_buy_price < test_sell_price:
            test_wins = test_wins + 1
         else:
            test_losses = test_losses + 1


   print(df)
   print(f"Starting Balance: ${test_original_balance}")
   if test_in_position:
      test_running_balance = test_running_balance + (test_buy_amt * df['close'][current])
      print(f"Final Balance: ${test_running_balance}")
   else:
      print(f"Final Balance: ${test_running_balance}")
   
   print(f"Percent Profit: {((test_running_balance / test_original_balance) * 100) - 100}%")
   print(f"Wins: {test_wins} Losses: {test_losses}")
   print(f"Win Rate: {(test_wins / (test_wins + test_losses)) * 100}%")

def buy_sell(df):
   print(df.tail(3))
   last_row_index = len(df.index) - 1
   previous_row_index = last_row_index - 1

   if not df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index]:
      print("I'm buyin'")

   if df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index]:
      print("I'm sellin'")

coin_name = 'ETH/USD'
bars = exchange.fetch_ohlcv(coin_name, timeframe = '5m', limit = 1000)

# Timedelta object to translate to EST time zone from UTC
est_translate = timedelta(hours=4)

# Initializing the dataframe
df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit = 'ms') - est_translate
ema_crossover(df, coin_name, short_period = 60, long_period = 288, smoothing = 2)