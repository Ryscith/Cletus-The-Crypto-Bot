#  Version 0.1 - Model T
#  Author: Reilly Schultz
#  Date: August 16th, 2021

import config
import ccxt
import pandas as pd
pd.set_option('max_rows', 5)

import warnings
warnings.filterwarnings('ignore')

from datetime import datetime, timedelta
import schedule
from time import sleep
import csv

# Exchange information pulled from config file
exchange = ccxt.binanceus({
   "apiKey": config.BINANCE_API_KEY,
   "secret": config.BINANCE_SECRET_KEY
})

# Global string to hold the most recent trade
most_recent_trade = " "

# Default strategy for if there is no other strategy specified
default_strategy = {
   "Timeframe": "5m",
   "Coin Names": "DOGE/USD",
   "Percent of Portfolio": 80,
   "Long Term Period": 288,
   "Short Term Period": 60,
   "Smoothing": 2
}

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

def long_term_ema(df, long_period = 21, smoothing = 2): # Calculates the long term exponential moving average and adds it to the dataframe
   for current in range(1, len(df.index)):
      previous = current - 1
      if current < long_period:
         df['long_term_ema'][current] = None
      elif current == long_period:
         df['long_term_ema'][current] = (df['close'][current] * (smoothing / (1 + long_period))) + df['long_term_sma'][previous] * (1 - (smoothing / (1 + long_period)))
      else:
         df['long_term_ema'][current] = (df['close'][current] * (smoothing / (1 + long_period))) + df['long_term_ema'][previous] * (1 - (smoothing / (1 + long_period)))

def short_term_ema(df, short_period = 10, smoothing = 2): # Calculates the short term exponential moving average and adds it to the dataframe
   for current in range(1, len(df.index)):
      previous = current - 1
      if current < short_period:
         df['short_term_ema'][current] = None
      elif current == short_period:
         df['short_term_ema'][current] = (df['close'][current] * (smoothing / (1 + short_period))) + df['short_term_sma'][previous] * (1 - (smoothing / (1 + short_period)))
      else:
         df['short_term_ema'][current] = (df['close'][current] * (smoothing / (1 + short_period))) + df['short_term_ema'][previous] * (1 - (smoothing / (1 + short_period)))

def ema_crossover(df, short_period = 10, long_period = 21, smoothing = 2): # Adds all of the necessary trading info for the EMA crossover strategy to the dataframe
   df['atr'] = atr(df, short_period)
   df['trailing_stop'] = (df['close'] - (df['atr'] * 5))

   df['long_term_sma'] = df['close'].rolling(long_period).mean()
   df['short_term_sma'] = df['close'].rolling(short_period).mean()

   df['long_term_ema'] = None
   df['short_term_ema'] = None

   long_term_ema(df, long_period, smoothing)
   short_term_ema(df, short_period, smoothing)

   df['in_uptrend'] = None

   for current in range(1, len(df.index)):
      previous = current - 1

      # Adds uptrend indicators to the dataframe
      if (df['short_term_ema'][current] == None) or (df['long_term_ema'][current] == None):
         df['in_uptrend'][current] = None

      elif (df['short_term_ema'][current]) > (df['long_term_ema'][current]):
         df['in_uptrend'][current] = True

      else:
         df['in_uptrend'][current] = False

      # Keeps the trailing stop at it's high as long as the coin is in an uptrend
      if (df['trailing_stop'][previous] > df['trailing_stop'][current]) and df['in_uptrend'][current]:
         df['trailing_stop'][current] = df['trailing_stop'][previous]

def buy_sell(df, test_values, coin_name, most_recent_trade): # Executes trades
   last_row_index = len(df.index) - 1
   previous_row_index = last_row_index - 1

   if not df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index] and not test_values['in_position']:
      test_values['in_position'] = True
      test_values['buy_price'] = df['close'][last_row_index]
      test_values['buy_amt'] = (test_values['running_balance'] * 0.8) / test_values['buy_price']
      test_values['running_balance'] = test_values['running_balance'] - (test_values['buy_amt'] * test_values['buy_price'])

      print("###########################################################################################################")
      print(f"I'm buyin' {test_values['buy_amt']} {coin_name} at {test_values['buy_price']} on {df['timestamp'][last_row_index]}")
      print("###########################################################################################################")

      most_recent_trade = f"Bought {test_values['buy_amt']} {coin_name} at {test_values['buy_price']} on {df['timestamp'][last_row_index]}"

      # Assign variables to use for the writer function
      buy_amt = test_values['buy_amt']
      buy_price = test_values['buy_price']
      timestamp = df['timestamp'][last_row_index]

      with open('LiveTestingRecord.csv', 'a', newline='') as csvfile:
         writer = csv.writer(csvfile, delimiter='|')
         writer.writerow(['buy', buy_amt, buy_price, timestamp])

   elif df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index] and test_values['in_position']:
      test_values['in_position'] = False
      test_values['sell_price'] = df['close'][last_row_index]
      test_values['running_balance'] = test_values['running_balance'] + (test_values['buy_amt'] * test_values['sell_price'])
      if test_values['buy_price'] < test_values['sell_price']:
         test_values['wins'] = test_values['wins'] + 1
      else:
         test_values['losses'] = test_values['losses'] + 1
      
      print("###########################################################################################################")
      print(f"I'm sellin' {test_values['buy_amt']} {coin_name} at {test_values['sell_price']} on {df['timestamp'][last_row_index]} because there was an EMA cross")
      print("###########################################################################################################")

      most_recent_trade = f"Sold {test_values['buy_amt']} {coin_name} at {test_values['sell_price']} on {df['timestamp'][last_row_index]} because of an EMA cross"

      # Assign variables to use for the writer function
      buy_amt = test_values['buy_amt']
      buy_price = test_values['buy_price']
      sell_price = test_values['sell_price']
      timestamp = df['timestamp'][last_row_index]
      percent_profit = ((test_values['sell_price'] / test_values['buy_price']) * 100) - 100

      with open('LiveTestingRecord.csv', 'a', newline='') as csvfile:
         writer = csv.writer(csvfile, delimiter='|')
         writer.writerow(['sell', buy_amt, sell_price, timestamp, percent_profit])

   elif (df['close'][last_row_index] < df['trailing_stop'][last_row_index]) and test_values['in_position']:
      test_values['in_position'] = False
      test_values['sell_price'] = df['close'][last_row_index]
      test_values['running_balance'] = test_values['running_balance'] + (test_values['buy_amt'] * test_values['sell_price'])
      if test_values['buy_price'] < test_values['sell_price']:
         test_values['wins'] = test_values['wins'] + 1
      else:
         test_values['losses'] = test_values['losses'] + 1
      
      print("###########################################################################################################")
      print(f"I'm sellin' {test_values['buy_amt']} {coin_name} at {test_values['sell_price']} on {df['timestamp'][last_row_index]} because the price went below the trailing stop")
      print("###########################################################################################################")

      most_recent_trade = f"Sold {test_values['buy_amt']} {coin_name} at {test_values['sell_price']} on {df['timestamp'][last_row_index]} because of the trailing stop"

      # Assign variables to use for the writer function
      buy_amt = test_values['buy_amt']
      buy_price = test_values['buy_price']
      sell_price = test_values['sell_price']
      timestamp = df['timestamp'][last_row_index]
      percent_profit = ((test_values['sell_price'] / test_values['buy_price']) * 100) - 100

      with open('LiveTestingRecord.csv', 'a', newline='') as csvfile:
         writer = csv.writer(csvfile, delimiter='|')
         writer.writerow(['sell', buy_amt, sell_price, timestamp, percent_profit])
   
   print(df.tail(3))

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

def job(test_values, strategy, most_recent_trade):
   coin_name = strategy['Coin Names']
   timeframe = strategy['Timeframe']
   short_period = strategy['Short Term Period']
   long_period = strategy['Long Term Period']
   smoothing = strategy['Smoothing']

   restart_timer = 5 # How many seconds to wait if an exception occurs before trying again
   try:
      bars = exchange.fetch_ohlcv(coin_name, timeframe, limit = 1000)

      # Timedelta object to translate to EST time zone from UTC
      est_translate = timedelta(hours=4)

      # Initializing the dataframe
      df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
      df['timestamp'] = pd.to_datetime(df['timestamp'], unit = 'ms') - est_translate
      ema_crossover(df, short_period, long_period, smoothing)
      buy_sell(df, test_values, coin_name, most_recent_trade)

      # Outputting values to terminal
      print(f"\nTrading {coin_name} on the {timeframe} interval with a short period of {short_period} and a long period of {long_period}\n")

      print(f"Most Recent Activity: {most_recent_trade}")

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

      print('------------------------------------------------------------------------------------')

   except Exception:
      print('An error occured when trying to fetch new candlesticks')
      print(f'Retrying in {restart_timer} seconds')
      sleep(restart_timer)
      job(test_values, strategy, most_recent_trade)

def runBot(strategy):
   schedule.every(1).minute.do(job, test_values, strategy, most_recent_trade)

   while True:
      schedule.run_pending()
      sleep(10)

if __name__ == '__main__':
   runBot(default_strategy)