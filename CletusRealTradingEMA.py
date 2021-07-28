import config
import ccxt
import pandas as pd
pd.set_option('max_rows', 5)

import warnings
warnings.filterwarnings('ignore')

from datetime import timedelta
import schedule
from time import sleep
import csv

exchange = ccxt.binanceus({
   "apiKey": config.BINANCE_API_KEY,
   "secret": config.BINANCE_SECRET_KEY
})

balance = exchange.fetch_balance()

starting_balance = balance['USD']['free']

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

def ema_crossover(df, short_period = 10, long_period = 21, smoothing = 2):
   df['long_term_sma'] = df['close'].rolling(long_period).mean()
   df['short_term_sma'] = df['close'].rolling(short_period).mean()

   df['long_term_ema'] = None
   df['short_term_ema'] = None

   long_term_ema(df, long_period, smoothing)
   short_term_ema(df, short_period, smoothing)

   df['in_uptrend'] = None

   for current in range(1, len(df.index)):
      if (df['short_term_ema'][current] == None) or (df['long_term_ema'][current] == None):
         df['in_uptrend'][current] = None

      elif (df['short_term_ema'][current]) > (df['long_term_ema'][current]):
         df['in_uptrend'][current] = True

      else:
         df['in_uptrend'][current] = False

def buy_sell(df, coin_name, coin_ticker):
   print(df.tail(3))
   last_row_index = len(df.index) - 1
   previous_row_index = last_row_index - 1
   balance = exchange.fetch_balance()
   usd_balance = balance['USD']['free']

   if balance[coin_name]['free'] > 0:
      in_position = True
   else:
      in_position = False

   if not df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index] and not in_position:
      timestamp = df['timestamp'][last_row_index]
      buy_price = df['close'][last_row_index]
      buy_amt = (100.00) / buy_price
      exchange.create_market_buy_order(coin_ticker, buy_amt)
      print(f"I'm buyin' {buy_amt} {coin_name} at ${buy_price} on {timestamp}")

      with open('LiveTradingRecord.csv', 'a', newline='') as csvfile:
         writer = csv.writer(csvfile, delimiter='|')
         writer.writerow(['buy', buy_amt, buy_price, timestamp])

   if df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index] and in_position:
      timestamp = df['timestamp'][last_row_index]
      sell_price = df['close'][last_row_index]
      sell_amt = balance[coin_name]['free']
      exchange.create_market_sell_order(coin_ticker, sell_amt)
      print(f"I'm sellin' {sell_amt} {coin_name} at ${sell_price} on {timestamp}")
      
      with open('LiveTradingRecord.csv', 'a', newline='') as csvfile:
         writer = csv.writer(csvfile, delimiter='|')
         writer.writerow(['sell', sell_amt, sell_price, timestamp])

def job():
   coin_name = 'DOGE'
   coin_ticker = coin_name + '/USD'
   timeframe = '5m'
   short_period = 60
   long_period = 288
   smoothing = 2

   restart_timer = 5 # How many seconds to wait if an exception occurs before trying again
   try:
      bars = exchange.fetch_ohlcv(coin_ticker, timeframe, limit = 750)

      # Timedelta object to translate to EST time zone from UTC
      est_translate = timedelta(hours=4)

      # Initializing the dataframe
      df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
      df['timestamp'] = pd.to_datetime(df['timestamp'], unit = 'ms') - est_translate
      ema_crossover(df, short_period, long_period, smoothing)
      buy_sell(df, coin_name, coin_ticker)
      balance = exchange.fetch_balance()
      usd_balance = balance['USD']['free']

      # Outputting values to terminal
      print(f"\nTrading {coin_name} on the {timeframe} interval with a short period of {short_period} and a long period of {long_period}\n")

      print(f"USD Balance: ${usd_balance}")
      print(f"{coin_name} Balance: {balance[coin_name]['free']}")
      print("-----------------------------------------------------------------------------------------------------------------------------------------")

   except Exception:
      print('An error occured when trying to fetch new candlesticks')
      print(f'Retrying in {restart_timer} seconds')
      sleep(restart_timer)
      job()


schedule.every(1).minute.do(job)

while True:
   schedule.run_pending()
   sleep(10)