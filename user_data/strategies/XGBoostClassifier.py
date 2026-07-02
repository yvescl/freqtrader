import logging
import numpy as np
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy

logger = logging.getLogger(__name__)

class XGBoostClassifierStrategy(IStrategy):
    # Standard Strategy Settings
    minimal_roi = {"0": 0.01, "30": 0.005, "60": 0}
    stoploss = -0.05
    timeframe = '5m'
    process_only_new_candles = True
    startup_candle_count: int = 40
    can_short = True

    # 1. SIMPLE FEATURES: Just RSI and Bollinger
    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int, metadata: dict, **kwargs) -> DataFrame:
        dataframe[f"%-rsi-period_{period}"] = ta.RSI(dataframe, timeperiod=period)
        dataframe[f"%-roc-period_{period}"] = ta.ROC(dataframe, timeperiod=period)
        return dataframe

    # 2. EASY TARGETS: Only 0.1% move required to label as 'up'
    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        label_period = self.freqai_info["feature_parameters"]["label_period_candles"]
        
        # Look ahead to see if price goes up at all
        future_close = dataframe["close"].shift(-label_period)
        pct_change = (future_close / dataframe["close"]) - 1
    
        # 0.1% is a very low bar, ensuring many 'up' labels
        dataframe["&-s_is_up"] = np.where(pct_change > 0.001, 'up', 'down')

        # Add this line right before 'return dataframe'
        print(f"DEBUG: {metadata['pair']} labels - {dataframe['&-s_is_up'].value_counts()}")

        return dataframe

    # 3. THE BRIDGE
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.freqai.start(dataframe, metadata, self)
        return dataframe

    # 4. AGGRESSIVE ENTRY: Trade if the AI is > 50% sure
    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df['enter_long'] = 0
        df['enter_short'] = 0 

        if '&-s_is_up_up' in df.columns:
            # We remove the '> 0.50' check entirely.
            # If the AI made a prediction (do_predict == 1), we TRADE.
            mask = (df['do_predict'] == 1)
        
            df.loc[mask, 'enter_long'] = 1
            df.loc[mask, 'enter_tag'] = 'forced_entry'

        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        return df