from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class TestStrategy(IStrategy):

    # 1. Fast settings for quick testing
    timeframe = '1m'          # Use 1m to see signals immediately
    stoploss = -0.10          # Wide stoploss to avoid instant closing
    startup_candle_count = 30 # Essential for MACD/RSI to calculate
    
    # 2. Minimal ROI (Profit taking)
    # This will exit as soon as it hits 1% profit
    minimal_roi = {"0": 0.01}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Correct RSI Syntax
        dataframe['rsi'] = qtpylib.rsi(dataframe['close'], window=14)
        #dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=14)
        
        # MACD using qtpylib
        macd = qtpylib.macd(dataframe['close'], fast=12, slow=26, smooth=16)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['signal']
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Loosened Logic: RSI is low OR MACD crosses up
        dataframe.loc[
            (
                (dataframe['rsi'] < 50) | # Very loose RSI (below midpoint)
                (qtpylib.crossed_above(dataframe['macd'], dataframe['macdsignal']))
            ) &
            (dataframe['volume'] > 0), # Ensure there is data
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit when RSI is high
        dataframe.loc[
            (dataframe['rsi'] > 70),
            'exit_long'] = 1
        return dataframe