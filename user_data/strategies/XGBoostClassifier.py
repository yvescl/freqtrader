import logging
import numpy as np
from functools import reduce

import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.strategy import IStrategy

logger = logging.getLogger(__name__)

class XGBoostClassifierStrategy(IStrategy):
    """
    Clean XGBoost Classifier Strategy for FreqAI.
    (Relies on config.json for the model configuration)
    """

    minimal_roi = {"0": 0.1, "240": -1}
    stoploss = -0.01
    use_exit_signal = True
    process_only_new_candles = True
    startup_candle_count: int = 40
    can_short = True

    plot_config = {
        "main_plot": {},
        "subplots": {
            "&-s_is_up": {"&-s_is_up": {"color": "blue"}},  
            "do_predict": {"do_predict": {"color": "brown"}},
        },
    }

    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int, metadata: dict, **kwargs) -> DataFrame:
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=period, stds=2.2)
        
        # FIX: Added "%-" to these three columns!
        dataframe["%-bb_lowerband-period"] = bollinger["lower"]
        dataframe["%-bb_middleband-period"] = bollinger["mid"]
        dataframe["%-bb_upperband-period"] = bollinger["upper"]

        dataframe["%-bb_width-period"] = (
            dataframe["%-bb_upperband-period"] - dataframe["%-bb_lowerband-period"]
        ) / dataframe["%-bb_middleband-period"]
        
        dataframe["%-close-bb_lower-period"] = dataframe["close"] / dataframe["%-bb_lowerband-period"]
        
        dataframe["%-roc-period"] = ta.ROC(dataframe, timeperiod=period)
        
        dataframe["%-relative_volume-period"] = (
            dataframe["volume"] / dataframe["volume"].rolling(period).mean()
        )
        return dataframe

    def set_freqai_targets(self, dataframe, metadata, **kwargs):
        # 1. Calculate future mean
        future_mean = (
            dataframe["close"]
            .shift(-self.freqai_info["feature_parameters"]["label_period_candles"])
            .rolling(self.freqai_info["feature_parameters"]["label_period_candles"])
            .mean()
        )
        pct_change = (future_mean / dataframe["close"]) - 1
    
        # 2. Binary threshold: 0.5% profit
        threshold = 0.005 
    
        # 3. FIX: Use STRINGS instead of integers for the classes!
        dataframe["&-s_is_up"] = np.where(pct_change > threshold, 'up', 'down')
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.freqai.start(dataframe, metadata, self)
        return dataframe

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        # 1. Safely check if the AI column actually exists yet
        if '&-s_is_up_up' in df.columns:
            enter_long_conditions = [
                df['do_predict'] == 1,         # Safety check
                df['&-s_is_up_up'] > 0.54      # AI is >60% confident
            ]

            if enter_long_conditions:
                df.loc[
                    reduce(lambda x, y: x & y, enter_long_conditions),
                    ['enter_long', 'enter_tag']
                ] = (1, 'xgboost_classifier_buy')

        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        # 1. Safely check if the AI column actually exists yet
        if '&-s_is_up_down' in df.columns:
            exit_long_conditions = [
                df['do_predict'] == 1,
                df['&-s_is_up_down'] > 0.60    # AI is >60% confident setup is dead
            ]

            if exit_long_conditions:
                df.loc[
                    reduce(lambda x, y: x & y, exit_long_conditions),
                    'exit_long'
                ] = 1

        return df

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str, current_time, entry_tag, side: str, **kwargs) -> bool:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = df.iloc[-1].squeeze()

        if side == "long":
            if rate > (last_candle["close"] * (1 + 0.0025)):
                return False
        else:
            if rate < (last_candle["close"] * (1 - 0.0025)):
                return False

        return True