import talib.abstract as ta
from pandas import DataFrame
from datetime import datetime
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, informative
import freqtrade.vendor.qtpylib.indicators as qtpylib

class FiveMinScalper(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5m'
    
    # Required for the engine to pre-calculate indicators
    startup_candle_count = 200
    process_only_new_candles = True

    # Risk Management
    stoploss = -0.10
    minimal_roi = {
        "0": 0.05,
        "15": 0.02,
        "30": 0.01
    }

    # Hyperoptable Parameters
    buy_rsi = IntParameter(20, 45, default=30, space="buy")
    atr_mult = DecimalParameter(1.0, 4.0, default=2.0, space="sell")

    @informative('1h')
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        The decorator handles all merging. 
        Columns created here will be available as '{column}_1h' in the main dataframe.
        """
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 5m timeframe indicators
        dataframe['ema9'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Suffix '_1h' is automatically handled by the decorator
                (dataframe['close'] > dataframe['ema200_1h']) &
                
                # Crossover logic
                (qtpylib.crossed_above(dataframe['ema9'], dataframe['ema20'])) &
                
                # RSI threshold
                (dataframe['rsi'] > self.buy_rsi.value) &
                
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Exit when trend flips
                (qtpylib.crossed_below(dataframe['ema9'], dataframe['ema20']))
            ),
            'exit_long'] = 1
        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime, 
                        current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Calculates a dynamic stoploss based on ATR.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if not dataframe.empty:
            last_candle = dataframe.iloc[-1]
            if last_candle['atr'] > 0:
                # Return the distance as a negative ratio
                return -(last_candle['atr'] * float(self.atr_mult.value)) / current_rate
        
        return self.stoploss