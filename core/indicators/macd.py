import pandas as pd
import numpy as np

def calculate_macd(data, fast=12, slow=26, signal=9):
    """
    MACD (Moving Average Convergence Divergence) hesaplar.
    """
    if data is None or data.empty:
        print("Hata: Veri çerçevesi boş veya None")
        return None
    ema_fast = data['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
    data['macd'] = ema_fast - ema_slow
    data['signal_line'] = data['macd'].ewm(span=signal, adjust=False).mean()
    return data

def generate_signals(data):
    """
    MACD sinyalleri üretir.
    """
    if data is None or data.empty:
        print("Hata: Sinyal üretimi için veri yok")
        return None
    data['signal'] = np.where(data['macd'] > data['signal_line'], 'buy',
                              np.where(data['macd'] < data['signal_line'], 'sell', 'hold'))
    return data