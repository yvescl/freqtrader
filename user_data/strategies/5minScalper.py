from freqtrade.strategy import IStrategy, informative
import talib.abstract as ta
from pandas import DataFrame
import datetime
from statsmodels.tsa.arima.model import ARIMA

import logging
logger = logging.getLogger(__name__)

class FiveMinScalper(IStrategy):
    INTERFACE_VERSION = 3  # Important for newer versions
    timeframe = '5m'
    
    # These settings manage your exits automatically
    minimal_roi = {"0": 0.02}
    stoploss = -0.10
    process_only_new_candles = False
    use_custom_stoploss = True
    trailing_stop = False

    @informative('1h')
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        # Standard 14-period ATR
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema9'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime, 
                    current_rate: float, current_profit: float, **kwargs) -> float:

        logger.info(f"Checking custom stoploss for {pair}. Current profit: {current_profit}")
        # Get the last analyzed candle
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        # Calculate ATR-based distance (e.g., 3x ATR)
        # This represents the "volatility buffer"
        if last_candle['atr'] > 0:
            # Distance as a percentage of current price
            atr_dist = (last_candle['atr'] * 3) / current_rate
        
            # return the distance from current_rate
            # Freqtrade will only update the stoploss if it moves UP
            return -atr_dist
        
        return self.stoploss # Fallback to default

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['ema200_1h'] < dataframe['close']) &
                (dataframe['ema9'] > dataframe['ema20']) &
                (dataframe['rsi'] > 30) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1  # Changed from 'buy' to 'enter_long'
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Technical exit: Sell if EMA9 crosses back below EMA20
        (This happens before ROI or Stoploss if the trend breaks)
        """
        dataframe.loc[
            (
                (dataframe['ema9'] < dataframe['ema20']) &
                (dataframe['volume'] > 0)
            ),
            'exit_long'] = 1
        return dataframe