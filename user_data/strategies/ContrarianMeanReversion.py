import numpy as np
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class ContrarianMeanReversion(IStrategy):
    # Strategy interface version
    INTERFACE_VERSION = 3

    # Timeframe and ROI settings
    timeframe = '15m'
    
    # Contrarian targets are usually the "mean" (middle band), 
    # so we set a tight ROI to capture the snap-back.
    minimal_roi = {
        "0": 0.05,      # 5% profit at any time
        "15": 0.02,     # 2% after 15 mins
        "30": 0.01,     # 1% after 30 mins
        "60": 0          # Exit if breakeven after 1 hour
    }

    #can_short = True


    # Stoploss (Contrarian trades need strict stops to avoid "falling knives")
    stoploss = -0.03

    # Trailing stoploss
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Bollinger Bands (20 periods, 2 standard deviations)
        bollinger_short_freq = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=1)
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        
        dataframe['bb_lowerband_short_freq'] = bollinger_short_freq['lower']
        dataframe['bb_middleband_short_freq'] = bollinger_short_freq['mid']
        dataframe['bb_upperband_short_freq'] = bollinger_short_freq['upper']
        
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']

        # RSI for momentum confirmation
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        LONG ENTRY: Price is below the lower band and RSI is oversold.
        """
        dataframe.loc[
            (
                (dataframe['close'] < dataframe['bb_lowerband']) &
                (dataframe['rsi'] < 30) &
                (dataframe['volume'] > 0)  # Guard against illiquid bars
            ),
            'enter_long'] = 1

        """
        SHORT ENTRY (Optional): Price is above the upper band and RSI is overbought.
        Only works if 'can_short' is set to True in config/strategy.
        """
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['bb_upperband']) &
                (dataframe['rsi'] > 70) &
                (dataframe['volume'] > 0)
            ),
            'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        LONG EXIT: Price reverts to the mean (middle band) or RSI recovers.
        """
        dataframe.loc[
            (
                (dataframe['close'] >= dataframe['bb_middleband']) |
                (dataframe['rsi'] > 55)
            ),
            'exit_long'] = 1

        """
        SHORT EXIT: Price reverts to the mean or RSI cools down.
        """
        dataframe.loc[
            (
                (dataframe['close'] <= dataframe['bb_middleband']) |
                (dataframe['rsi'] < 45)
            ),
            'exit_short'] = 1

        return dataframe