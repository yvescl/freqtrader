# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy
from pandas import DataFrame
from typing import Dict, List
from functools import reduce
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
# --------------------------------


class ShortTermScalper(IStrategy):
    # Strategy parameters
    startup_candle_count: int = 30
    timeframe = '5m'
    stoploss = -0.03  # 3% strict stoploss
    minimal_roi = {
        "0": 0.02,    # Sell at 2% profit immediately
        "30": 0.01,   # After 30 mins, settle for 1%
        "60": 0       # After an hour, exit if break-even
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI - Short period for faster signals
        #dataframe['rsi'] = ta.RSI(dataframe, timeperiod=7)
        dataframe['rsi'] = qtpylib.rsi(dataframe['close'], window=14)
        
        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']

        macd = qtpylib.macd(dataframe['close'], fast=12, slow=26, smooth=9)
    
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['signal']
        dataframe['macdhist'] = macd['histogram']
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] < 30) & # Oversold
                (dataframe['close'] < dataframe['bb_lowerband']) & # Price below band
                (dataframe['volume'] > 0) # Safety check
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['bb_middleband']) # Reverted to mean
            ),
            'exit_long'] = 1
        return dataframe