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

# Setting up basic exchange info
exchange = ccxt.binanceus({
   "apiKey": config.BINANCE_API_KEY,
   "secret": config.BINANCE_SECRET_KEY
})

balance = exchange.fetch_balance()

starting_balance = balance['USD']['free']

# Global string to hold the most recent trade
most_recent_trade = " "

# Default strategy for if there is no other strategy specified
default_strategy = {
   "Timeframe": "5m",
   "Coin Names": "ETH/USD",
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

def ema_crossover(df, short_period = 10, long_period = 21, smoothing = 2):# Adds all of the necessary trading info for the EMA crossover strategy to the dataframe
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

      if (df['short_term_ema'][current] == None) or (df['long_term_ema'][current] == None):
         df['in_uptrend'][current] = None

      elif (df['short_term_ema'][current]) > (df['long_term_ema'][current]):
         df['in_uptrend'][current] = True

      else:
         df['in_uptrend'][current] = False

      if (df['trailing_stop'][previous] > df['trailing_stop'][current]) and df['in_uptrend'][current]:
         df['trailing_stop'][current] = df['trailing_stop'][previous]

def buy_sell(df, coin_name, coin_ticker, most_recent_trade): # Executes trades
   last_row_index = len(df.index) - 1
   previous_row_index = last_row_index - 1
   balance = exchange.fetch_balance()

   if balance[coin_name]['free'] > 0:
      in_position = True
   else:
      in_position = False

   if not df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index] and not in_position:
      timestamp = df['timestamp'][last_row_index]
      buy_price = df['close'][last_row_index]
      buy_amt = (100.00) / buy_price
      exchange.create_market_buy_order(coin_ticker, buy_amt)
      print("###########################################################################################################")
      print(f"I'm buyin' {buy_amt} {coin_name} at ${buy_price} on {timestamp}")
      print("###########################################################################################################")

      most_recent_trade = f"Bought {buy_amt} {coin_name} at ${buy_price} on {timestamp}"

      with open('LiveTradingRecord.csv', 'a', newline='') as csvfile:
         writer = csv.writer(csvfile, delimiter='|')
         writer.writerow(['buy', buy_amt, buy_price, timestamp])

   elif df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index] and in_position:
      timestamp = df['timestamp'][last_row_index]
      sell_price = df['close'][last_row_index]
      sell_amt = balance[coin_name]['free']
      exchange.create_market_sell_order(coin_ticker, sell_amt)
      print("###########################################################################################################")
      print(f"I'm sellin' {sell_amt} {coin_name} at ${sell_price} on {timestamp} because there was an EMA cross")
      print("###########################################################################################################")

      most_recent_trade = f"Sold {sell_amt} {coin_name} at ${sell_price} on {timestamp} because of an EMA cross"
      
      with open('LiveTradingRecord.csv', 'a', newline='') as csvfile:
         writer = csv.writer(csvfile, delimiter='|')
         writer.writerow(['sell', sell_amt, sell_price, timestamp])
   
   elif df['close'][last_row_index] < df['trailing_stop'][last_row_index] and in_position:
      timestamp = df['timestamp'][last_row_index]
      sell_price = df['close'][last_row_index]
      sell_amt = balance[coin_name]['free']
      exchange.create_market_sell_order(coin_ticker, sell_amt)
      print("###########################################################################################################")
      print(f"I'm sellin' {sell_amt} {coin_name} at ${sell_price} on {timestamp} because the price went below the trailing stop")
      print("###########################################################################################################")

      most_recent_trade = f"Sold {sell_amt} {coin_name} at ${sell_price} on {timestamp} because of the trailing stop"
      
      with open('LiveTradingRecord.csv', 'a', newline='') as csvfile:
         writer = csv.writer(csvfile, delimiter='|')
         writer.writerow(['sell', sell_amt, sell_price, timestamp])

   print(df.tail(3))

def job(strategy, most_recent_trade):
   coin_name = strategy['Coin Names']
   timeframe = strategy['Timeframe']
   short_period = strategy['Short Term Period']
   long_period = strategy['Long Term Period']
   smoothing = strategy['Smoothing']

   restart_timer = 5 # How many seconds to wait if an exception occurs before trying again
   try:
      bars = exchange.fetch_ohlcv(coin_name, timeframe, limit = 750)

      # Timedelta object to translate to EST time zone from UTC
      est_translate = timedelta(hours=4)

      # Initializing the dataframe
      df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
      df['timestamp'] = pd.to_datetime(df['timestamp'], unit = 'ms') - est_translate
      ema_crossover(df, coin_name, short_period, long_period, smoothing)
      buy_sell(df, coin_name, most_recent_trade)
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
      job(strategy, most_recent_trade)

def runBot(strategy):
   schedule.every(1).minute.do(job, strategy, most_recent_trade)

   while True:
      schedule.run_pending()
      sleep(10)

if __name__ == '__main__':
   runBot(default_strategy)