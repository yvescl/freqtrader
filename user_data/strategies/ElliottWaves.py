from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
import freqtrade.vendor.qtpylib.indicators as qtpylib

class ElliottWaveStrategy(IStrategy):

    order_types = {
    'entry': 'market',
    'exit': 'market',
    'emergency_exit': 'market',
    'stoploss': 'market',
    'stoploss_on_exchange': False
    }
    timeframe = '5m'
    # Stoploss settings
    stoploss = -0.10  # Hard stop at -10%

    # Trailing stoploss
    trailing_stop = True
    trailing_stop_positive = 0.01          # Start trailing when at 1% profit
    trailing_stop_positive_offset = 0.02   # Give it 2% "room" to breathe
    trailing_only_offset_is_reached = True
    minimal_roi = {
        "0": 0.05,      # Sell immediately at 5% profit
        "30": 0.02,     # After 30 mins, sell if at 2% profit
        "60": 0.01,     # After 1 hour, sell if at 1% profit
        "120": 0        # After 2 hours, sell if we are at break-even
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1. Calculate Elliott Wave Oscillator (EWO)
        # EWO = SMA(5) - SMA(35)
        #sma5 = qtpylib.sma(dataframe, window=5, min_periods=None)
        #sma35 = qtpylib.sma(dataframe, window=35, min_periods=None)
        sma5 = ta.SMA(dataframe, timeperiod=5)
        sma35 = ta.SMA(dataframe, timeperiod=35)
        dataframe['sma5'] = ta.SMA(dataframe, timeperiod=5)
        dataframe['sma35'] = ta.SMA(dataframe, timeperiod=35)
        # Normalized EWO
        dataframe['ewo'] = (sma5 - sma35) / dataframe['close'] * 100

        # 2. Add standard confirmation (RSI)
        #dataframe['rsi'] = qtpylib.rsi(dataframe['close'], window=14)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        #####################################################################
        log_h_l = np.log(dataframe['high'] / dataframe['low'])
        log_c_o = np.log(dataframe['close'] / dataframe['open'])
    
        gk_variance = (0.5 * log_h_l**2) - ((2 * np.log(2) - 1) * log_c_o**2)
    
        # Use np.maximum to prevent negative numbers due to floating point math before sqrt
        dataframe['gk_vol'] = np.sqrt(np.maximum(gk_variance, 0))

        # 2. Smooth it (Optional but recommended)
        # This helps you identify if volatility is rising or falling
        dataframe['gk_vol_sma'] = ta.SMA(dataframe['gk_vol'], timeperiod=14)
        #####################################################################
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Logic: Looking for the end of Wave 4 (Return to zero)
                (dataframe['ewo'].shift(1) < 0) & 
                (dataframe['ewo'] > 0) & # EWO flips positive after a correction
                #(qtpylib.crossed_above(dataframe['ewo'], 0)) &
                (dataframe['rsi'] > 40) & 
                (dataframe['rsi'] < 65) &
                (dataframe['rsi'] > dataframe['rsi'].shift(1)) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Logic A: Sell into strength (Loosened)
                # We removed the requirement for the current candle to be green
                (dataframe['rsi'] > 70) & 
                (dataframe['rsi'] < dataframe['rsi'].shift(1)) # RSI has just started to hook down
            ) |
            (
                # Logic B: Trend Failure (More responsive)
                # Exit if EWO is negative AND falling, rather than a massive 30% jump
                (dataframe['ewo'] < 0) &
                (dataframe['ewo'] < dataframe['ewo'].shift(1)) &
                (dataframe['rsi'] < 45)
            ),
            'exit_tag'] = 'technical_exit'
        return dataframe