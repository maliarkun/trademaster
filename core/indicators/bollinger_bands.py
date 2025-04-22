import pandas as pd
import numpy as np

def calculate_bollinger_bands(data, window=20, num_std=2):
    """
    Bollinger Bands hesaplar.
    """
    if data is None or data.empty:
        print("Hata: Veri çerçevesi boş veya None")
        return None
    rolling_mean = data['close'].rolling(window=window).mean()
    rolling_std = data['close'].rolling(window=window).std()
    data['middle_band'] = rolling_mean
    data['upper_band'] = rolling_mean + (rolling_std * num_std)
    data['lower_band'] = rolling_mean - (rolling_std * num_std)
    return data

def generate_signals(data):
    """
    Alım/satım sinyalleri üretir.
    """
    if data is None or data.empty:
        print("Hata: Sinyal üretimi için veri yok")
        return None
    data['signal'] = np.where(data['close'] > data['upper_band'], 'sell',
                              np.where(data['close'] < data['lower_band'], 'buy', 'hold'))
    return data