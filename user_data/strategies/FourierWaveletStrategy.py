import numpy as np
import pandas as pd
from freqtrade.strategy import IStrategy, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta
import pywt  # You would need to install PyWavelets: pip install PyWavelets

class FourierWaveletStrategy(IStrategy):
    """
    Example Freqtrade Strategy using Fourier Transforms and Wavelets for Feature Engineering.
    This is designed to be used with the FreqAI module.
    """
    
    # Strategy parameters
    timeframe = '5m'
    can_short = True
    stoploss = -0.10
    minimal_roi = {"0": 0.10}

    # FreqAI specific settings
    process_only_new_candles = True
    use_exit_signal = True

    # Hyperoptable prediction thresholds (prediction = expected pct change over label period).
    # Symmetric for long/short so the optimizer cannot overfit to market direction.
    entry_threshold = DecimalParameter(0.002, 0.030, default=0.010, decimals=3, space="buy")
    exit_threshold = DecimalParameter(-0.010, 0.005, default=0.000, decimals=3, space="sell")
    
    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int, **kwargs) -> DataFrame:
        """
        Main feature engineering function for FreqAI.
        Features must be prepended with '%'
        """
        
        # 1. Standard Technical Indicators
        dataframe['%-rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['%-mfi'] = ta.MFI(dataframe, timeperiod=14)
        
        # 2. Fourier Transform Features
        # We look for the dominant cycles in the price data
        def get_fourier_feature(data, window=30):
            # Applying Fast Fourier Transform
            close_prices = data.values
            fft_values = np.fft.fft(close_prices)
            # Filter out high frequencies (noise) by keeping only the first few components
            fft_values[6:] = 0 
            return np.real(np.fft.ifft(fft_values))[-1]

        # Rolling Fourier calculation (simplified example)
        # Note: In a production FreqAI strategy, you would optimize this for speed
        dataframe['%-fourier_recon'] = dataframe['close'].rolling(window=50).apply(
            lambda x: get_fourier_feature(x), raw=False
        )

        # 3. Wavelet Transform Features
        # Wavelets are great for non-stationary data (like crypto prices)
        def get_wavelet_feature(data):
            # Using Daubechies 4 wavelet for decomposition
            coeffs = pywt.wavedec(data, 'db4', level=2)
            # Return the mean of the detail coefficients (high-frequency parts)
            return np.mean(coeffs[1])

        dataframe['%-wavelet_detail'] = dataframe['close'].rolling(window=50).apply(
            lambda x: get_wavelet_feature(x), raw=False
        )

        return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, **kwargs) -> DataFrame:
        # Basic features like day of week, hour, etc.
        dataframe['%-day_of_week'] = (dataframe['date'].dt.dayofweek + 1) / 7
        dataframe['%-hour_of_day'] = (dataframe['date'].dt.hour + 1) / 24
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, **kwargs) -> DataFrame:
        """
        Define what the model is trying to predict.
        Targets must be prepended with '&'
        """
        # Predict the percentage change in the next 20 candles
        dataframe['&s-ext_price'] = (
            dataframe['close'].shift(-20) / dataframe['close'] - 1
        )
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # This calls the FreqAI model to get predictions
        dataframe = self.freqai.start(dataframe, metadata, self)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Use the FreqAI prediction for entry signals
        # Entry when the model is confident in a > 1% move
        dataframe.loc[
            (
                (dataframe['do_predict'] == 1) &
                (dataframe['&s-ext_price'] > self.entry_threshold.value)
            ),
            'enter_long'] = 1

        dataframe.loc[
            (
                (dataframe['do_predict'] == 1) &
                (dataframe['&s-ext_price'] < -self.entry_threshold.value)
            ),
            'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit when the predicted edge disappears
        dataframe.loc[
            (
                (dataframe['&s-ext_price'] < self.exit_threshold.value)
            ),
            'exit_long'] = 1

        dataframe.loc[
            (
                (dataframe['&s-ext_price'] > -self.exit_threshold.value)
            ),
            'exit_short'] = 1

        return dataframe
