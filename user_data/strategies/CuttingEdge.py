from freqtrade.strategy import IStrategy, IntParameter
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class CuttingEdgeRegimeBot(IStrategy):
    timeframe = '5m'
    INTERFACE_VERSION = 3
    
    # Hyperoptable parameters for 2026 market volatility
    buy_rsi = IntParameter(20, 40, default=30, space="buy")
    efficiency_threshold = 0.6 # Only trade when the trend is 'clean'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1. Kaufman's Efficiency Ratio (ER) - Detects "Trend vs Noise"
        # ER = Total Price Change / Sum of Absolute Price Changes
        change = dataframe['close'].diff(10).abs()
        volatility = dataframe['close'].diff(1).abs().rolling(window=10).sum()
        dataframe['efficiency_ratio'] = change / volatility

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



        # 2. Volatility-Adjusted Bollinger Bands
        # Standard deviation 2.5 to catch 'extreme' 2026 spikes
        bollinger = qtpylib.bollinger_bands(dataframe['close'], window=20, stds=2.5)
        dataframe['bb_lower'] = bollinger['lower']
        
        # 3. Standard Momentum
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Condition 1: Market is NOT just random noise (High ER)
                (dataframe['efficiency_ratio'] > self.efficiency_threshold) &
                # Condition 2: Deep Mean Reversion (Price below extreme BB)
                (dataframe['close'] < dataframe['bb_lower']) &
                # Condition 3: RSI oversold hook
                (dataframe['rsi'] < self.buy_rsi.value) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit quickly as the 'Efficiency' drops (the trend is getting messy)
        dataframe.loc[
            (dataframe['rsi'] > 60) | (dataframe['efficiency_ratio'] < 0.3),
            'exit_long'] = 1
        return dataframe