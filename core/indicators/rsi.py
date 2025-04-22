import pandas as pd
import numpy as np

def calculate_rsi(data, window=14):
    """
    RSI (Relative Strength Index) hesaplar.
    """
    if data is None or data.empty:
        print("Hata: Veri çerçevesi boş veya None")
        return None
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    data['rsi'] = 100 - (100 / (1 + rs))
    return data

def generate_signals(data):
    """
    RSI sinyalleri üretir.
    """
    if data is None or data.empty:
        print("Hata: Sinyal üretimi için veri yok")
        return None
    data['signal'] = np.where(data['rsi'] > 70, 'sell',
                              np.where(data['rsi'] < 30, 'buy', 'hold'))
    return data