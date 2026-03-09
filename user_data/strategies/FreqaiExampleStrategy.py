import logging
import numpy as np
from functools import reduce

import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.strategy import IStrategy


logger = logging.getLogger(__name__)


class FreqaiExampleStrategy(IStrategy):
    """
    Example strategy showing how the user connects their own
    IFreqaiModel to the strategy.

    Warning! This is a showcase of functionality,
    which means that it is designed to show various functions of FreqAI
    and it runs on all computers. We use this showcase to help users
    understand how to build a strategy, and we use it as a benchmark
    to help debug possible problems.

    This means this is *not* meant to be run live in production.
    """

    minimal_roi = {"0": 0.1, "240": -1}

    plot_config = {
        "main_plot": {},
        "subplots": {
            "&-s_is_up": {"&-s_is_up": {"color": "blue"}},  # <-- Updated to new target
            "do_predict": {
                "do_predict": {"color": "brown"},
            },
        },
    }

    process_only_new_candles = True
    stoploss = -0.01
    use_exit_signal = True
    # this is the maximum period fed to talib (timeframe independent)
    startup_candle_count: int = 40
    can_short = True


    def feature_engineering_expand_all(
        self, dataframe: DataFrame, period: int, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        This function will automatically expand the defined features on the config defined
        `indicator_periods_candles`, `include_timeframes`, `include_shifted_candles`, and
        `include_corr_pairs`. In other words, a single feature defined in this function
        will automatically expand to a total of
        `indicator_periods_candles` * `include_timeframes` * `include_shifted_candles` *
        `include_corr_pairs` numbers of features added to the model.

        All features must be prepended with `%` to be recognized by FreqAI internals.

        Access metadata such as the current pair/timeframe with:

        `metadata["pair"]` `metadata["tf"]`

        More details on how these config defined parameters accelerate feature engineering
        in the documentation at:

        https://www.freqtrade.io/en/latest/freqai-parameter-table/#feature-parameters

        https://www.freqtrade.io/en/latest/freqai-feature-engineering/#defining-the-features

        :param dataframe: strategy dataframe which will receive the features
        :param period: period of the indicator - usage example:
        :param metadata: metadata of current pair
        dataframe["%-ema-period"] = ta.EMA(dataframe, timeperiod=period)
        """

        #dataframe["%-rsi-period"] = ta.RSI(dataframe, timeperiod=period)
        #dataframe["%-mfi-period"] = ta.MFI(dataframe, timeperiod=period)
        #dataframe["%-adx-period"] = ta.ADX(dataframe, timeperiod=period)
        #dataframe["%-sma-period"] = ta.SMA(dataframe, timeperiod=period)
        #dataframe["%-ema-period"] = ta.EMA(dataframe, timeperiod=period)
        #dataframe["%-ema-200"] = ta.EMA(dataframe, timeperiod=200)

        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=period, stds=2.2
        )
        dataframe["bb_lowerband-period"] = bollinger["lower"]
        dataframe["bb_middleband-period"] = bollinger["mid"]
        dataframe["bb_upperband-period"] = bollinger["upper"]

        dataframe["%-bb_width-period"] = (
            dataframe["bb_upperband-period"] - dataframe["bb_lowerband-period"]
        ) / dataframe["bb_middleband-period"]
        dataframe["%-close-bb_lower-period"] = dataframe["close"] / dataframe["bb_lowerband-period"]

        dataframe["%-roc-period"] = ta.ROC(dataframe, timeperiod=period)

        dataframe["%-relative_volume-period"] = (
            dataframe["volume"] / dataframe["volume"].rolling(period).mean()
        )

        # Distance from a moving average (is the price overextended?)
        #dataframe['%-ema_rel'] = (dataframe['close'] - ta.EMA(dataframe, timeperiod=20)) / dataframe['close']

        # Price volatility (Standard Deviation)
        #dataframe['%-volatility'] = dataframe['close'].rolling(window=20).std()

        # Is current volume higher than the 10-day average?
        #dataframe["%-relative_volume"] = dataframe["volume"] / dataframe["volume"].rolling(20).mean()

        return dataframe

    def feature_engineering_expand_basic(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        This function will automatically expand the defined features on the config defined
        `include_timeframes`, `include_shifted_candles`, and `include_corr_pairs`.
        In other words, a single feature defined in this function
        will automatically expand to a total of
        `include_timeframes` * `include_shifted_candles` * `include_corr_pairs`
        numbers of features added to the model.

        Features defined here will *not* be automatically duplicated on user defined
        `indicator_periods_candles`

        All features must be prepended with `%` to be recognized by FreqAI internals.

        Access metadata such as the current pair/timeframe with:

        `metadata["pair"]` `metadata["tf"]`

        More details on how these config defined parameters accelerate feature engineering
        in the documentation at:

        https://www.freqtrade.io/en/latest/freqai-parameter-table/#feature-parameters

        https://www.freqtrade.io/en/latest/freqai-feature-engineering/#defining-the-features

        :param dataframe: strategy dataframe which will receive the features
        :param metadata: metadata of current pair
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-ema-200"] = ta.EMA(dataframe, timeperiod=200)
        """
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-raw_volume"] = dataframe["volume"]
        dataframe["%-raw_price"] = dataframe["close"]
        return dataframe

    def feature_engineering_standard(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        This optional function will be called once with the dataframe of the base timeframe.
        This is the final function to be called, which means that the dataframe entering this
        function will contain all the features and columns created by all other
        freqai_feature_engineering_* functions.

        This function is a good place to do custom exotic feature extractions (e.g. tsfresh).
        This function is a good place for any feature that should not be auto-expanded upon
        (e.g. day of the week).

        All features must be prepended with `%` to be recognized by FreqAI internals.

        Access metadata such as the current pair with:

        `metadata["pair"]`

        More details about feature engineering available:

        https://www.freqtrade.io/en/latest/freqai-feature-engineering

        :param dataframe: strategy dataframe which will receive the features
        :param metadata: metadata of current pair
        usage example: dataframe["%-day_of_week"] = (dataframe["date"].dt.dayofweek + 1) / 7
        """
        #dataframe["%-day_of_week"] = dataframe["date"].dt.dayofweek
        #dataframe["%-hour_of_day"] = dataframe["date"].dt.hour

        dataframe['%-day_cos'] = np.cos(2 * np.pi * dataframe['date'].dt.dayofweek / 7)
        dataframe['%-day_sin'] = np.sin(2 * np.pi * dataframe['date'].dt.dayofweek / 7)
        dataframe["%-hour_sin"] = np.sin(2 * np.pi * dataframe["date"].dt.hour / 24)
        dataframe["%-hour_cos"] = np.cos(2 * np.pi * dataframe["date"].dt.hour / 24)

        dataframe.fillna(0, inplace=True)

        return dataframe

    def set_freqai_targets(self, dataframe, metadata, **kwargs):
    
        # 1. Calculate the smoothed future percentage change (your original brilliant math)
        future_mean = (
            dataframe["close"]
            .shift(-self.freqai_info["feature_parameters"]["label_period_candles"])
            .rolling(self.freqai_info["feature_parameters"]["label_period_candles"])
            .mean()
        )
        pct_change = (future_mean / dataframe["close"]) - 1
    
        # 2. Define your profit threshold (e.g., 0.005 means 0.5% profit)
        # If the future move is greater than this, classify as a "1" (Good setup)
        # If it is less than this, or negative, classify as a "0" (Bad setup)
        threshold = 0.005 
    
        # 3. Create the classification target
        dataframe["&-s_is_up"] = np.where(pct_change > threshold, 1, 0)
    
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # All indicators must be populated by feature_engineering_*() functions

        # the model will return all labels created by user in `set_freqai_targets()`
        # (& appended targets), an indication of whether or not the prediction should be accepted,
        # the target mean/std values for each of the labels created by user in
        # `set_freqai_targets()` for each training period.

        dataframe = self.freqai.start(dataframe, metadata, self)

        return dataframe

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        
        enter_long_conditions = [
            df['do_predict'] == 1,  # FreqAI's default prediction column for Classifiers
            # OR if you are using the specific target name:
            # df['&-s_is_up'] == 1 
        ]

        if enter_long_conditions:
            df.loc[
                reduce(lambda x, y: x & y, enter_long_conditions),
                ['enter_long', 'enter_tag']
            ] = (1, 'freqai_classifier_buy')

        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        
        exit_long_conditions = [
            df['do_predict'] == 0,  # "No, the price is not going up"
            # OR: df['&-s_is_up'] == 0
        ]

        if exit_long_conditions:
            df.loc[
                reduce(lambda x, y: x & y, exit_long_conditions),
                'exit_long'
            ] = 1

        return df
    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time,
        entry_tag,
        side: str,
        **kwargs,
    ) -> bool:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = df.iloc[-1].squeeze()

        if side == "long":
            if rate > (last_candle["close"] * (1 + 0.0025)):
                return False
        else:
            if rate < (last_candle["close"] * (1 - 0.0025)):
                return False

        return True
