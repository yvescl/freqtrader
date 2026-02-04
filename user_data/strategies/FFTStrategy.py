import numpy as np
import pandas as pd
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class FftEwoStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '1h'
    
    # --- ADD THESE LINES ---
    stoploss = -0.10  # 10% stoploss
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.05
    startup_candle_count: int = 200
    # -----------------------
    
    # Strategy Parameters
    buy_params = {
        "fft_window": 128,
        "fft_keep_freq": 5,  # Higher = more noise, Lower = smoother
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1. Standard Indicators (EWO & RSI)
        # EWO is typically (5-period SMA - 35-period SMA)
        dataframe['sma_5'] = ta.SMA(dataframe, timeperiod=5)
        dataframe['sma_35'] = ta.SMA(dataframe, timeperiod=35)
        dataframe['ewo'] = ((dataframe['sma_5'] - dataframe['sma_35']) / dataframe['close']) * 100
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # 2. Fast Fourier Transform (FFT) Denoising
        # We apply FFT on a rolling window to avoid "look-ahead" bias
        def get_fft_denoised(series, window, keep):
            if len(series) < window:
                return series[-1]
            
            # Get the window of data
            segment = series[-window:].values
            # Transform to Frequency Domain
            coeffs = np.fft.fft(segment)
            # Zero out high frequencies (noise)
            coeffs[keep:-keep] = 0
            # Transform back to Time Domain
            reconstructed = np.fft.ifft(coeffs).real
            return reconstructed[-1] # Return the most recent point

        # Calculate FFT Curve
        window = self.buy_params['fft_window']
        keep = self.buy_params['fft_keep_freq']
        
        # Apply FFT as a rolling calculation
        dataframe['fft_cycle'] = dataframe['close'].rolling(window=window).apply(
            lambda x: get_fft_denoised(x, window, keep), raw=False
        )
        
        # FFT Slope (Is the cycle moving up or down?)
        dataframe['fft_slope'] = dataframe['fft_cycle'].diff()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # EWO Crossover (Wave 4 to 5 transition)
                qtpylib.crossed_above(dataframe['ewo'], 0) &
                
                # FFT Confirmation: Price is at/below the cycle and cycle is turning UP
                (dataframe['close'] <= dataframe['fft_cycle']) &
                (dataframe['fft_slope'] > 0) &

                # RSI Momentum Filter (The "Goldilocks" zone)
                (dataframe['rsi'] > 40) & 
                (dataframe['rsi'] < 65) &
                (dataframe['rsi'] > dataframe['rsi'].shift(1)) &
                
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Exit when FFT cycle starts to curve down (Cycle Peak)
                (dataframe['fft_slope'] < 0) |
                # Or when EWO shows momentum exhaustion
                (dataframe['ewo'] < dataframe['ewo'].shift(1)) & (dataframe['ewo'] > 0)
            ),
            'exit_long'] = 1
        return dataframe