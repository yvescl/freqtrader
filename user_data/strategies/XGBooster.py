import logging
import numpy as np
from pandas import DataFrame
import pandas_ta as ta
from freqtrade.strategy import IStrategy

logger = logging.getLogger(__name__)

class XGBoosterStrategy(IStrategy):
    """
    XBGoosterStrategy: A FreqAI strategy converted from App2.py logic.
    Uses XGBoost classification via FreqAI to predict > 0.5% upward moves.
    """
    INTERFACE_VERSION = 3

    # Strategy parameters
    timeframe = '1d'
    stoploss = -0.05
    minimal_roi = {"0": 0.1}

    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int,
                                       metadata: dict, **kwargs) -> DataFrame:
        """
        Feature engineering logic from App2.py.
        Columns added here are used as features (X) for training.
        """
        # 1. Price and Return Features
        dataframe['%Return'] = dataframe['close'].pct_change()
        dataframe['%SMA_10_Ratio'] = dataframe['close'] / dataframe['close'].rolling(window=10).mean()
        dataframe['%SMA_50_Ratio'] = dataframe['close'] / dataframe['close'].rolling(window=50).mean()
        
        # 2. Lags
        dataframe['%Lag_1_Return'] = dataframe['%Return'].shift(1)
        dataframe['%Lag_2_Return'] = dataframe['%Return'].shift(2)
        dataframe['%Return_Lag_3'] = dataframe['%Return'].shift(3)
        dataframe['%Return_Lag_4'] = dataframe['%Return'].shift(4)
        
        # 3. Volatility and Volume
        dataframe['%Volatility'] = dataframe['%Return'].rolling(window=14).std()
        dataframe['%Vol_Change'] = dataframe['volume'].pct_change()

        # 4. Technical Indicators using pandas_ta
        dataframe.ta.adx(append=True)
        dataframe.ta.atr(append=True)
        dataframe.ta.ema(length=200, append=True)
        dataframe.ta.rsi(append=True, length=14)
        dataframe.ta.macd(append=True)
        dataframe.ta.bbands(append=True, length=20, std=2.0)
        dataframe.ta.obv(append=True)
        dataframe.ta.mfi(append=True, length=14)

        # Mapping indicator names to be consistent with original App2.py feature names
        # MACD Histogram
        macd_h_col = [c for c in dataframe.columns if 'MACDH' in str(c).upper()]
        if macd_h_col:
            dataframe['%MACD_Hist'] = dataframe[macd_h_col[0]]

        # Bollinger Bands
        bbp_col = [c for c in dataframe.columns if 'BBP' in str(c).upper()]
        bbb_col = [c for c in dataframe.columns if 'BBB' in str(c).upper()]
        dataframe['%BB_PercentB'] = dataframe[bbp_col[0]] if bbp_col else 0
        dataframe['%BB_Bandwidth'] = dataframe[bbb_col[0]] if bbb_col else 0

        # Normalized OBV (Rolling Z-score)
        obv_col = [c for c in dataframe.columns if 'OBV' in str(c).upper()]
        if obv_col:
            obv_s = dataframe[obv_col[0]]
            dataframe['%OBV_Value'] = (obv_s - obv_s.rolling(window=20).mean()) / obv_s.rolling(window=20).std()

        # Ensuring RSI, ADX, ATR, and MFI are explicitly named for the feature list
        rsi_col = [c for c in dataframe.columns if 'RSI_14' in str(c).upper()]
        dataframe['%RSI_14'] = dataframe[rsi_col[0]] if rsi_col else 0

        adx_col = [c for c in dataframe.columns if 'ADX_14' in str(c).upper()]
        dataframe['%ADX_14'] = dataframe[adx_col[0]] if adx_col else 0

        atr_col = [c for c in dataframe.columns if 'ATR_14' in str(c).upper()]
        dataframe['%ATR_14'] = dataframe[atr_col[0]] if atr_col else 0

        mfi_col = [c for c in dataframe.columns if 'MFI_14' in str(c).upper()]
        dataframe['%MFI_14_Value'] = dataframe[mfi_col[0]] if mfi_col else 0


        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        Define the classification target (y) for the model.
        """
        # Label 1 if tomorrow's close is > 0.5% higher, else 0.
        # In FreqAI, target columns are prefixed with '&-'
        dataframe['&-target'] = (
            dataframe['close'].shift(-1) > dataframe['close'] * 1.005
        ).astype(int)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry point for the FreqAI pipeline.
        """
        dataframe = self.freqai.start(dataframe, metadata, self)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Signals to enter long when the model predicts '1'.
        """
        dataframe.loc[
            (
                (dataframe['&-target'] == 1) &
                (dataframe['do_predict'] == 1)
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exits are handled by ROI and Stoploss.
        Removing the 'exit on 0' logic as it prevents trades from staying open.
        """
        dataframe.loc[dataframe['do_predict'] == 1, 'exit_long'] = 0
        return dataframe
