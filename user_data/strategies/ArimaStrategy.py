import numpy as np
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy, timeframe_to_prev_date
from statsmodels.tsa.arima.model import ARIMA
import talib.abstract as ta
import logging
import warnings

# Suppress math warnings that clutter the logs
warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

class ArimaStrategy(IStrategy):
    # Strategy Settings
    INTERFACE_VERSION = 3
    timeframe = '1h'  # ARIMA performs better on 1h+
    startup_candle_count: int = 120
    process_only_new_candles = False
    
    # Custom Stoploss Settings
    use_custom_stoploss = True
    stoploss = -0.10  # Hard emergency stop
    
    # ROI table: Minimal 2% profit
    minimal_roi = {"0": 0.05}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1. Standard Indicators
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # 2. Prepare ARIMA data
        dataframe['arima_forecast'] = np.nan
        window = 100
        
        # Limit loop in live/dry run to keep the bot responsive
        if self.config.get('runmode') in ['live', 'dry_run']:
            start_idx = max(window, len(dataframe) - 20)
        else:
            start_idx = window

        # 3. The ARIMA Loop
        for i in range(start_idx, len(dataframe)):
            # Slice and Scale: Scaling by 1000 prevents math errors on small prices
            df_slice = dataframe['close'].iloc[i-window:i].copy().reset_index(drop=True)
            scale_factor = 1000
            scaled_data = df_slice.values * scale_factor
            
            # Variance check: Skip if price is flat
            if np.var(scaled_data) < 0.01:
                continue

            try:
                # Order (1,1,0) is used for speed and convergence stability
                model = ARIMA(scaled_data, order=(15, 1, 0))
                model_fit = model.fit(method='yule_walker') # Robust linear estimator
                
                forecast = model_fit.forecast(steps=2)
                dataframe.iloc[i, dataframe.columns.get_loc('arima_forecast')] = forecast[0] / scale_factor
            except Exception:
                logger.info("ARIMA exception")
                continue

        # Fill NaNs so logic doesn't break
        dataframe['arima_forecast'] = dataframe['arima_forecast'].ffill().fillna(dataframe['close'])
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Entry: Forecast expects price higher than current close
                (dataframe['arima_forecast'] > dataframe['close'] * 1.01) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # We rely primarily on ATR Stoploss and ROI, 
        # but we exit if the ARIMA trend flips negative.
        dataframe.loc[
            (
                (dataframe['arima_forecast'] < dataframe['close'])
            ),
            'exit_long'] = 1
        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: 'datetime', 
                        current_rate: float, current_profit: float, **kwargs) -> float:
        
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        # ATR-based Trailing Stop (3x Volatility)
        if not np.isnan(last_candle['atr']):
            atr_dist = (last_candle['atr'] * 3) / current_rate
            return -atr_dist
            
        return self.stoploss