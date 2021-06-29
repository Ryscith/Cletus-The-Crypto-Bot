import config
import ccxt
import pandas as pd
pd.set_option('max_rows', 5)

import warnings
warnings.filterwarnings('ignore')

from datetime import datetime, timedelta
import schedule
from time import time, sleep
import csv

exchange = ccxt.binanceus({
   "apiKey": config.BINANCE_API_KEY,
   "secret": config.BINANCE_SECRET_KEY
})

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

      elif (df['short_term_ema'][current] + 0.001) > (df['long_term_ema'][current]):
         df['in_uptrend'][current] = True

      else:
         df['in_uptrend'][current] = False

def buy_sell(df, test_values, coin_name):
   print(df.tail(3))
   last_row_index = len(df.index) - 1
   previous_row_index = last_row_index - 1

   if not df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index] and not test_values['in_position']:
      test_values['in_position'] = True
      test_values['buy_price'] = df['close'][last_row_index]
      test_values['buy_amt'] = (test_values['running_balance'] * 0.8) / test_values['buy_price']
      test_values['running_balance'] = test_values['running_balance'] - (test_values['buy_amt'] * test_values['buy_price'])
      print(f"I'm buyin' {test_values['buy_amt']} {coin_name} at {test_values['buy_price']} on {df['timestamp'][last_row_index]}")
      with open('record.csv', 'a', newline='') as csvfile:
         spamwriter = csv.writer(csvfile, delimiter='|')
         spamwriter.writerow(['buy', test_values['buy_amt'], test_values['buy_price'], df['timestamp'][last_row_index]])

   if df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index] and test_values['in_position']:
      test_values['in_position'] = False
      test_values['sell_price'] = df['close'][last_row_index]
      test_values['running_balance'] = test_values['running_balance'] + (test_values['buy_amt'] * test_values['sell_price'])
      if test_values['buy_price'] < test_values['sell_price']:
         test_values['wins'] = test_values['wins'] + 1
      else:
         test_values['losses'] = test_values['losses'] + 1
      print(f"I'm sellin' {test_values['buy_amt']} {coin_name} at {test_values['sell_price']} on {df['timestamp'][last_row_index]}")
      with open('record.csv', 'a', newline='') as csvfile:
               spamwriter = csv.writer(csvfile, delimiter='|')
               spamwriter.writerow(['sell', test_values['buy_amt'], test_values['sell_price'], df['timestamp'][last_row_index], [((test_values['sell_price'] / test_values['buy_price']) * 100) - 100]])

test_values = {
   'original_balance': 10000,
   'running_balance': 10000,
   'in_position': False,
   'sell_price': 0,
   'buy_price': 0,
   'buy_amt': 0,
   'wins': 0,
   'losses': 0,
}

def job(test_values):
   coin_name = 'DOGE/USDT'
   
   restart_timer = 5 # How many seconds to wait if an exception occurs before trying again
   try:
      bars = exchange.fetch_ohlcv(coin_name, timeframe = '15m', limit = 250)

      # Timedelta object to translate to EST time zone from UTC
      est_translate = timedelta(hours=4)

      # Initializing the dataframe
      df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
      df['timestamp'] = pd.to_datetime(df['timestamp'], unit = 'ms') - est_translate
      ema_crossover(df, coin_name, short_period = 48, long_period = 84, smoothing = 2)
      buy_sell(df, test_values, coin_name)

      print(f"Starting Balance: ${test_values['original_balance']}")
      if test_values['in_position']:
         print(f"Running Balance: ${test_values['running_balance'] + (test_values['buy_amt'] * df['close'][len(df.index) - 1])}")
         print(f"Percent Profit: {(((test_values['running_balance'] + (test_values['buy_amt'] * df['close'][len(df.index) - 1])) / test_values['original_balance']) * 100) - 100}%")
      else:
         print(f"Running Balance: ${test_values['running_balance']}")
         print(f"Percent Profit: {((test_values['running_balance'] / test_values['original_balance']) * 100) - 100}%")

      print(f"Wins: {test_values['wins']} Losses: {test_values['losses']}")
      if test_values['wins'] > 1:
         print(f"Win Rate: {(test_values['wins'] / (test_values['wins'] + test_values['losses'])) * 100}%")
      else:
         print(f'Win Rate: Not Enough Data')

      print('---------------------------------------------------')

   except Exception:
      print('An error occured when trying to fetch new candlesticks')
      print(f'Retrying in {restart_timer} seconds')
      sleep(restart_timer)
      job(test_values)


schedule.every(1).minute.do(job, test_values)

while True:
   schedule.run_pending()
   sleep(10)