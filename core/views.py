# Gerekli kütüphaneleri içe aktarır
from django.shortcuts import render  # HTML şablonlarını render etmek için kullanılır
from django.http import JsonResponse  # JSON formatında yanıt döndürmek için kullanılır
import requests  # HTTP istekleri yapmak için kullanılır
from .models import TradingPair  # TradingPair modelini veritabanından almak için kullanılır
from django.core.cache import cache  # Önbellekleme işlemleri için kullanılır

# Telegram'a mesaj göndermek için fonksiyon
def send_telegram_message(token, chat_id, message):
    """
    Telegram API'sini kullanarak belirtilen bot tokenı ve chat ID'si ile bir mesaj gönderir.
    
    Args:
        token (str): Telegram bot tokenı
        chat_id (str): Mesajın gönderileceği grup veya kanal ID'si
        message (str): Gönderilecek mesaj içeriği
    
    Returns:
        dict: Telegram API'den dönen JSON yanıtı
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {"chat_id": chat_id, "text": message}
    response = requests.post(url, params=params)
    return response.json()

# İşlem çiftlerinin güncel fiyatlarını almak için fonksiyon
def get_current_prices(pairs):
    """
    Verilen işlem çiftleri için CryptoCompare API'sinden güncel fiyatları çeker.
    
    Args:
        pairs (QuerySet): TradingPair modelinden alınan işlem çiftleri listesi
    
    Returns:
        dict: İşlem çiftleri ve güncel fiyatlarını içeren sözlük
    """
    if not pairs:
        return {}
    base_currencies = ','.join([pair.base_currency for pair in pairs])
    quote_currency = pairs[0].quote_currency
    url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={base_currencies}&tsyms={quote_currency}"
    response = requests.get(url)
    data = response.json()
    prices = {}
    for pair in pairs:
        base = pair.base_currency
        quote = pair.quote_currency
        price = data.get(base, {}).get(quote, 'Bilinmeyen')
        prices[f"{base}/{quote}"] = price
    return prices

# Geçmiş fiyat ve hacim verilerini almak ve önbelleğe kaydetmek için fonksiyon
def get_historical_prices(base, quote, timeframe='day', limit=500):
    """
    CryptoCompare API'sinden geçmiş fiyat ve hacim verilerini çeker ve önbelleğe kaydeder.
    
    Args:
        base (str): Temel para birimi (örneğin, BTC)
        quote (str): Karşıt para birimi (örneğin, USDT)
        timeframe (str): Veri zaman aralığı ('hour', '4hour', 'week', 'day')
        limit (int): Çekilecek veri sayısı (varsayılan: 500)
    
    Returns:
        tuple: (fiyat listesi, hacim listesi)
    """
    cache_key = f"historical_{base}_{quote}_{timeframe}_{limit}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        print(f"{base}/{quote} için önbellekten veri alındı ({timeframe}).")
        return cached_data
    
    if timeframe == 'hour':
        url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym={base}&tsym={quote}&limit={limit}"
    elif timeframe == '4hour':
        url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym={base}&tsym={quote}&limit={limit}&aggregate=4"
    elif timeframe == 'week':
        url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym={base}&tsym={quote}&limit={limit}&aggregate=7"
    else:
        url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym={base}&tsym={quote}&limit={limit}"
    
    response = requests.get(url)
    data = response.json()
    if data.get('Response') == 'Success' and 'Data' in data and 'Data' in data['Data']:
        entries = data['Data']['Data']
        prices = [{'high': float(entry['high']), 'low': float(entry['low']), 'close': float(entry['close']), 'time': entry['time']} for entry in entries]
        volumes = [float(entry['volumeto']) for entry in entries]
        cache.set(cache_key, (prices, volumes), 300)  # 5 dakika önbellekte tutar
        print(f"{base}/{quote} için veri uzunluğu: {len(prices)} ({timeframe})")
        return prices, volumes
    else:
        print(f"Hata: {base}/{quote} için veri çekilemedi. Mesaj: {data.get('Message', 'Bilinmeyen hata')}")
        return [], []

# Basit Hareketli Ortalama (SMA) hesaplamak için fonksiyon
def calculate_sma(prices, period):
    """
    Belirtilen periyot için kapanış fiyatlarının Basit Hareketli Ortalamasını (SMA) hesaplar.
    
    Args:
        prices (list): Fiyat verileri listesi
        period (int): Hesaplama periyodu
    
    Returns:
        float or None: SMA değeri, veri yetersizse None
    """
    if not prices or len(prices) < period:
        return None
    return sum(price['close'] for price in prices[-period:]) / period

# Stochastic Osilatör hesaplamak için fonksiyon
def calculate_stochastic(prices, period=14, smooth_k=3, smooth_d=3):
    """
    Stochastic Osilatör (%K ve %D) hesaplar ve alım/satış sinyali üretir.
    
    Args:
        prices (list): Fiyat verileri listesi
        period (int): Stochastic hesaplama periyodu (varsayılan: 14)
        smooth_k (int): %K yumuşatma periyodu (varsayılan: 3)
        smooth_d (int): %D yumuşatma periyodu (varsayılan: 3)
    
    Returns:
        tuple: (%K, %D, sinyal)
    """
    if not prices or len(prices) < period + smooth_k + smooth_d - 1:
        return None, None, "Veri Yok"
    
    k_values = []
    for i in range(period - 1, len(prices)):
        sub_prices = prices[i - period + 1:i + 1]
        highest_high = max(price['high'] for price in sub_prices)
        lowest_low = min(price['low'] for price in sub_prices)
        current_close = prices[i]['close']
        k = 50 if highest_high == lowest_low else 100 * (current_close - lowest_low) / (highest_high - lowest_low)
        k_values.append(k)
    
    k_smooth_values = [sum(k_values[i - smooth_k + 1:i + 1]) / smooth_k for i in range(smooth_k - 1, len(k_values))]
    d_smooth_values = [sum(k_smooth_values[i - smooth_d + 1:i + 1]) / smooth_d for i in range(smooth_d - 1, len(k_smooth_values))]
    
    if not k_smooth_values or not d_smooth_values:
        return None, None, "Veri Yok"
    
    current_k, current_d = k_smooth_values[-1], d_smooth_values[-1]
    stoch_signal = "Nötr"
    if len(k_smooth_values) >= 2 and len(d_smooth_values) >= 2:
        prev_k, prev_d = k_smooth_values[-2], d_smooth_values[-2]
        if prev_k < prev_d and current_k > current_d and current_k < 20:
            stoch_signal = "Alım"
        elif prev_k > prev_d and current_k < current_d and current_k > 80:
            stoch_signal = "Satış"
    
    return round(current_k, 2), round(current_d, 2), stoch_signal

# Yönsel Hareket Endeksi (+DI ve -DI) hesaplamak için fonksiyon
def calculate_di(prices, period=14):
    """
    Belirtilen periyot için +DI ve -DI değerlerini hesaplar.
    
    Args:
        prices (list): Fiyat verileri listesi
        period (int): Hesaplama periyodu (varsayılan: 14)
    
    Returns:
        tuple: (+DI, -DI)
    """
    if not prices or len(prices) < period + 1:
        return None, None
    plus_dms, minus_dms, trs = [], [], []
    for i in range(1, len(prices)):
        high, low = prices[i]['high'], prices[i]['low']
        prev_high, prev_low, prev_close = prices[i-1]['high'], prices[i-1]['low'], prices[i-1]['close']
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        plus_dm = max(high - prev_high, 0) if high - prev_high > prev_low - low else 0
        minus_dm = max(prev_low - low, 0) if prev_low - low > high - prev_high else 0
        trs.append(tr)
        plus_dms.append(plus_dm)
        minus_dms.append(minus_dm)
    if not trs:
        return None, None
    atr = sum(trs[-period:]) / period
    plus_di = 100 * (sum(plus_dms[-period:]) / period) / atr if atr else 0
    minus_di = 100 * (sum(minus_dms[-period:]) / period) / atr if atr else 0
    return round(plus_di, 2), round(minus_di, 2)

# Ortalama Yönsel Endeks (ADX) hesaplamak için fonksiyon
def calculate_adx(prices, period=14):
    """
    Belirtilen periyot için ADX değerini hesaplar (trend gücü).
    
    Args:
        prices (list): Fiyat verileri listesi
        period (int): Hesaplama periyodu (varsayılan: 14)
    
    Returns:
        float or None: ADX değeri, veri yetersizse None
    """
    if not prices or len(prices) < period + 1:
        return None
    trs, plus_dms, minus_dms = [], [], []
    for i in range(1, len(prices)):
        high, low = prices[i]['high'], prices[i]['low']
        prev_high, prev_low, prev_close = prices[i-1]['high'], prices[i-1]['low'], prices[i-1]['close']
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        plus_dm = max(high - prev_high, 0) if high - prev_high > prev_low - low else 0
        minus_dm = max(prev_low - low, 0) if prev_low - low > high - prev_high else 0
        trs.append(tr)
        plus_dms.append(plus_dm)
        minus_dms.append(minus_dm)
    if not trs:
        return None
    atr = sum(trs[-period:]) / period
    plus_di = 100 * (sum(plus_dms[-period:]) / period) / atr if atr else 0
    minus_di = 100 * (sum(minus_dms[-period:]) / period) / atr if atr else 0
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if plus_di + minus_di else 0
    return round(dx, 2)

# Göreceli Güç Endeksi (RSI) hesaplamak için fonksiyon
def calculate_rsi(prices, period=14):
    """
    Belirtilen periyot için RSI değerini hesaplar (momentum göstergesi).
    
    Args:
        prices (list): Fiyat verileri listesi
        period (int): Hesaplama periyodu (varsayılan: 14)
    
    Returns:
        float or None: RSI değeri, veri yetersizse None
    """
    if not prices or len(prices) < period + 1:
        return None
    changes = [prices[i]['close'] - prices[i-1]['close'] for i in range(1, len(prices))]
    if len(changes) < period:
        return None
    gains = [chg if chg > 0 else 0 for chg in changes[-period:]]
    losses = [-chg if chg < 0 else 0 for chg in changes[-period:]]
    avg_gain, avg_loss = sum(gains) / period, sum(losses) / period
    rsi = 100 if avg_loss == 0 and avg_gain > 0 else 50 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))
    return round(rsi, 2)

# Ichimoku Bulutu hesaplamak için fonksiyon
def calculate_ichimoku(prices, tenkan_period=9, kijun_period=26, senkou_b_period=52):
    """
    Ichimoku Bulutu bileşenlerini hesaplar: Tenkan-sen, Kijun-sen, Senkou Span A/B, Chikou Span.
    
    Args:
        prices (list): Fiyat verileri listesi
        tenkan_period (int): Tenkan-sen periyodu (varsayılan: 9)
        kijun_period (int): Kijun-sen periyodu (varsayılan: 26)
        senkou_b_period (int): Senkou Span B periyodu (varsayılan: 52)
    
    Returns:
        dict or None: Ichimoku bileşenleri, veri yetersizse None
    """
    if not prices or len(prices) < max(tenkan_period, kijun_period, senkou_b_period):
        return None
    tenkan_sen = (max(p['high'] for p in prices[-tenkan_period:]) + min(p['low'] for p in prices[-tenkan_period:])) / 2
    kijun_sen = (max(p['high'] for p in prices[-kijun_period:]) + min(p['low'] for p in prices[-kijun_period:])) / 2
    senkou_span_a = (tenkan_sen + kijun_sen) / 2
    senkou_span_b = (max(p['high'] for p in prices[-senkou_b_period:]) + min(p['low'] for p in prices[-senkou_b_period:])) / 2
    chikou_span = prices[-26]['close'] if len(prices) >= 26 else None
    return {
        'tenkan_sen': round(tenkan_sen, 2),
        'kijun_sen': round(kijun_sen, 2),
        'senkou_span_a': round(senkou_span_a, 2),
        'senkou_span_b': round(senkou_span_b, 2),
        'chikou_span': round(chikou_span, 2) if chikou_span else None
    }

# ATR (Average True Range) hesaplamak için fonksiyon
def calculate_atr(prices, period=14):
    """
    ATR (Average True Range) hesaplar: Piyasanın volatilitesini ölçer.
    
    Args:
        prices (list): Fiyat verileri listesi
        period (int): Hesaplama periyodu (varsayılan: 14)
    
    Returns:
        float or None: ATR değeri, veri yetersizse None
    """
    if not prices or len(prices) < period + 1:
        return None
    tr_list = [max(prices[i]['high'] - prices[i]['low'], abs(prices[i]['high'] - prices[i-1]['close']), abs(prices[i]['low'] - prices[i-1]['close'])) for i in range(1, len(prices))]
    atr = sum(tr_list[-period:]) / period
    return round(atr, 2)

# VWAP (Volume Weighted Average Price) hesaplamak için fonksiyon
def calculate_vwap(prices, volumes):
    """
    VWAP (Volume Weighted Average Price) hesaplar: Hacme dayalı ortalama fiyat.
    
    Args:
        prices (list): Fiyat verileri listesi
        volumes (list): Hacim verileri listesi
    
    Returns:
        float or None: VWAP değeri, veri yetersizse None
    """
    if not prices or not volumes or len(prices) != len(volumes):
        return None
    total_volume = sum(volumes)
    if total_volume == 0:
        return None
    vwap = sum(p['close'] * v for p, v in zip(prices, volumes)) / total_volume
    return round(vwap, 2)

# Tüm işlem çiftleri için analiz yapan ana fonksiyon
def trading_pairs(request):
    """
    Tüm işlem çiftleri için teknik analiz yapar ve sonuçları trading_pairs.html şablonuna render eder.
    
    Args:
        request (HttpRequest): Django HTTP isteği nesnesi
    
    Returns:
        HttpResponse: Render edilmiş HTML sayfası
    """
    try:
        pairs = TradingPair.objects.all()
        current_prices = get_current_prices(pairs)
        price_data = {}
        token = "5345035136:AAF9PZB78SvEm55M538OJtRirA33H1PaqUY"  # Telegram bot tokenı
        chat_id = "-1001423950701"  # Telegram grup veya kanal ID'si
        
        for pair in pairs:
            key = f"{pair.base_currency}/{pair.quote_currency}"
            historical_prices, volumes = get_historical_prices(pair.base_currency, pair.quote_currency)
            if not historical_prices:
                continue
            
            # SMA Hesaplamaları
            sma_50 = calculate_sma(historical_prices, 50)
            sma_200 = calculate_sma(historical_prices, 200)
            sma_50_rounded = round(sma_50, 2) if sma_50 else 'Veri Yok'
            sma_200_rounded = round(sma_200, 2) if sma_200 else 'Veri Yok'
            signal = "Belirsiz"
            if sma_50 and sma_200:
                signal = "Golden Cross (Alım)" if sma_50 > sma_200 else "Death Cross (Satış)"
            
            # Stochastic Hesaplamaları
            stoch_k, stoch_d, stoch_signal = calculate_stochastic(historical_prices)
            stoch_k = stoch_k if stoch_k is not None else 'Veri Yok'
            stoch_d = stoch_d if stoch_d is not None else 'Veri Yok'
            stoch_signal = stoch_signal if stoch_signal != "Veri Yok" else 'Veri Yok'
            
            # ADX ve DI Hesaplamaları
            adx = calculate_adx(historical_prices)
            plus_di, minus_di = calculate_di(historical_prices)
            adx_signal = "Zayıf Trend"
            if adx and adx > 25:
                adx_signal = "Güçlü Yükseliş" if plus_di > minus_di else "Güçlü Düşüş" if plus_di < minus_di else "Güçlü Trend (Yön Belirsiz)"
            
            # RSI Hesaplamaları
            rsi = calculate_rsi(historical_prices)
            rsi_signal = "Nötr"
            if rsi is not None:
                rsi_signal = "Aşırı Satım (Alım)" if rsi < 30 else "Aşırı Alım (Satış)" if rsi > 70 else "Nötr"
            
            # Güncel Fiyat
            current_price = current_prices.get(key, 'Bilinmeyen')
            current_price = float(historical_prices[-1]['close']) if current_price == 'Bilinmeyen' and historical_prices else float(current_price) if current_price != 'Bilinmeyen' else 'Veri Yok'
            
            # Ichimoku Hesaplamaları ve Sinyalleri
            ichimoku = calculate_ichimoku(historical_prices)
            if ichimoku:
                ichimoku_signal = "Yükseliş Trendi" if current_price > ichimoku['kijun_sen'] else "Düşüş Trendi" if current_price < ichimoku['kijun_sen'] else "Nötr"
                if len(historical_prices) >= 2:
                    prev_ichimoku = calculate_ichimoku(historical_prices[:-1])
                    if prev_ichimoku and prev_ichimoku['tenkan_sen'] < prev_ichimoku['kijun_sen'] and ichimoku['tenkan_sen'] > ichimoku['kijun_sen']:
                        ichimoku_signal += " (Alım Sinyali)"
                    elif prev_ichimoku and prev_ichimoku['tenkan_sen'] > prev_ichimoku['kijun_sen'] and ichimoku['tenkan_sen'] < ichimoku['kijun_sen']:
                        ichimoku_signal += " (Satış Sinyali)"
                ichimoku_signal += " (Bulut Üstünde)" if current_price > max(ichimoku['senkou_span_a'], ichimoku['senkou_span_b']) else " (Bulut Altında)" if current_price < min(ichimoku['senkou_span_a'], ichimoku['senkou_span_b']) else " (Bulut İçinde)"
            else:
                ichimoku_signal = 'Veri Yok'
            
            # ATR ve VWAP Hesaplamaları
            atr = calculate_atr(historical_prices)
            atr_signal = "Yüksek Volatilite" if atr and atr > 1000 else "Normal Volatilite"
            vwap = calculate_vwap(historical_prices, volumes) if volumes else 'Veri Yok'
            vwap_signal = "Fiyat Ortalamanın Üzerinde" if vwap and current_price and current_price > vwap else "Fiyat Ortalamanın Altında" if vwap and current_price else "Veri Yok"
            
            # Fibonacci Seviyeleri ve İhtimaller
            if historical_prices:
                highest_high = max(price['high'] for price in historical_prices)
                lowest_low = min(price['low'] for price in historical_prices)
                price_range = highest_high - lowest_low
                fibonacci_levels_raw = {
                    '0%': lowest_low,
                    '23.6%': lowest_low + 0.236 * price_range,
                    '38.2%': lowest_low + 0.382 * price_range,
                    '50%': lowest_low + 0.5 * price_range,
                    '61.8%': lowest_low + 0.618 * price_range,
                    '100%': highest_high,
                }
                closest_level = min(fibonacci_levels_raw, key=lambda level: abs(fibonacci_levels_raw[level] - current_price) if current_price != 'Veri Yok' else float('inf'))
                distance = abs(fibonacci_levels_raw[closest_level] - current_price) if current_price != 'Veri Yok' else float('inf')
                distance_factor = max(0, 1 - (distance / (price_range * 0.5))) if price_range > 0 else 0
                turn_probability = round(30 * distance_factor)
                rise_probability = fall_probability = 35
                
                # Teknik göstergelere göre ihtimalleri ayarla
                if signal == "Golden Cross (Alım)":
                    rise_probability += 15 * distance_factor
                    fall_probability -= 15 * distance_factor
                elif signal == "Death Cross (Satış)":
                    fall_probability += 15 * distance_factor
                    rise_probability -= 15 * distance_factor
                if stoch_signal == "Alım":
                    rise_probability += 10 * distance_factor
                    fall_probability -= 10 * distance_factor
                elif stoch_signal == "Satış":
                    fall_probability += 10 * distance_factor
                    rise_probability -= 10 * distance_factor
                if adx_signal == "Güçlü Yükseliş":
                    rise_probability += 10 * distance_factor
                elif adx_signal == "Güçlü Düşüş":
                    fall_probability += 10 * distance_factor
                if rsi is not None:
                    if rsi < 30:
                        rise_probability += 10 * distance_factor
                        fall_probability -= 10 * distance_factor
                    elif rsi > 70:
                        fall_probability += 10 * distance_factor
                        rise_probability -= 10 * distance_factor
                if "Yükseliş Trendi" in ichimoku_signal:
                    rise_probability += 10 * distance_factor
                elif "Düşüş Trendi" in ichimoku_signal:
                    fall_probability += 10 * distance_factor
                if atr_signal == "Yüksek Volatilite":
                    turn_probability += 10 * distance_factor
                if vwap_signal == "Fiyat Ortalamanın Üzerinde":
                    rise_probability += 10 * distance_factor
                elif vwap_signal == "Fiyat Ortalamanın Altında":
                    fall_probability += 10 * distance_factor
                
                # İhtimalleri normalize et
                total = turn_probability + rise_probability + fall_probability
                if total > 0:
                    turn_probability = round((turn_probability / total) * 100)
                    rise_probability = round((rise_probability / total) * 100)
                    fall_probability = round((fall_probability / total) * 100)
                else:
                    turn_probability, rise_probability, fall_probability = 33, 33, 34
            else:
                closest_level = turn_probability = rise_probability = fall_probability = 'Veri Yok'
            
            # Analiz sonuçlarını kaydet
            price_data[key] = {
                'current_price': current_price,
                'sma_50': sma_50_rounded,
                'sma_200': sma_200_rounded,
                'signal': signal,
                'stoch_k': stoch_k,
                'stoch_d': stoch_d,
                'stoch_signal': stoch_signal,
                'adx': adx if adx else 'Veri Yok',
                'adx_signal': adx_signal,
                'rsi': rsi if rsi is not None else 'Veri Yok',
                'rsi_signal': rsi_signal,
                'closest_fibonacci_level': closest_level,
                'turn_probability': turn_probability,
                'rise_probability': rise_probability,
                'fall_probability': fall_probability,
                'ichimoku': ichimoku if ichimoku else 'Veri Yok',
                'ichimoku_signal': ichimoku_signal,
                'atr': atr if atr else 'Veri Yok',
                'atr_signal': atr_signal,
                'vwap': vwap if vwap else 'Veri Yok',
                'vwap_signal': vwap_signal
            }
            
            # Telegram Bildirimi (Modelde `last_signal` ve `notification_threshold` alanları varsayılmıştır)
            if rise_probability != 'Veri Yok':
                current_signal = "yükseliş" if rise_probability > fall_probability else "düşüş"
                if not hasattr(pair, 'last_signal') or not hasattr(pair, 'notification_threshold'):
                    print(f"Uyarı: {key} için last_signal veya notification_threshold tanımlı değil.")
                elif pair.last_signal != current_signal:
                    if current_signal == "yükseliş" and rise_probability >= getattr(pair, 'notification_threshold', 50):
                        message = f"{key} için Yükselme İhtimali: %{rise_probability} (Güncel Fiyat: {current_price})"
                        send_telegram_message(token, chat_id, message)
                        pair.last_signal = "yükseliş"
                        pair.save()
                    elif current_signal == "düşüş" and fall_probability >= getattr(pair, 'notification_threshold', 50):
                        message = f"{key} için Düşüş İhtimali: %{fall_probability} (Güncel Fiyat: {current_price})"
                        send_telegram_message(token, chat_id, message)
                        pair.last_signal = "düşüş"
                        pair.save()
        
        return render(request, 'trading_pairs.html', {'price_data': price_data})
    
    except Exception as e:
        print(f"Hata oluştu: {e}")
        return render(request, 'error.html', {'error': str(e)})

# Belirli bir işlem çifti için detaylı analiz yapan fonksiyon
def pair_detail(request, pair):
    """
    Belirli bir işlem çifti için teknik analiz yapar ve pair_detail.html şablonuna render eder.
    
    Args:
        request (HttpRequest): Django HTTP isteği nesnesi
        pair (str): Analiz edilecek işlem çifti (örneğin, "BTC/USDT")
    
    Returns:
        HttpResponse: Render edilmiş HTML sayfası
    """
    try:
        timeframe = request.GET.get('timeframe', 'day')
        base, quote = pair.split('/')
        historical_prices, volumes = get_historical_prices(base, quote, timeframe=timeframe)
        if not historical_prices:
            return render(request, 'error.html', {'error': f"{pair} için veri bulunamadı."})
        
        current_price = get_current_prices([TradingPair(base_currency=base, quote_currency=quote)]).get(pair, 'Bilinmeyen')
        current_price = float(historical_prices[-1]['close']) if current_price == 'Bilinmeyen' and historical_prices else float(current_price) if current_price != 'Bilinmeyen' else 'Veri Yok'
        
        # Teknik Göstergeler
        sma_50 = calculate_sma(historical_prices, 50)
        sma_200 = calculate_sma(historical_prices, 200)
        sma_50_rounded = round(sma_50, 2) if sma_50 else 'Veri Yok'
        sma_200_rounded = round(sma_200, 2) if sma_200 else 'Veri Yok'
        
        stoch_k, stoch_d, stoch_signal = calculate_stochastic(historical_prices)
        stoch_k, stoch_d, stoch_signal = [stoch_k, stoch_d, stoch_signal] if stoch_k is not None else ['Veri Yok'] * 3
        
        adx = calculate_adx(historical_prices)
        rsi = calculate_rsi(historical_prices)
        
        ichimoku = calculate_ichimoku(historical_prices)
        if ichimoku:
            ichimoku_signal = "Yükseliş Trendi" if current_price > ichimoku['kijun_sen'] else "Düşüş Trendi" if current_price < ichimoku['kijun_sen'] else "Nötr"
            if len(historical_prices) >= 2:
                prev_ichimoku = calculate_ichimoku(historical_prices[:-1])
                if prev_ichimoku and prev_ichimoku['tenkan_sen'] < prev_ichimoku['kijun_sen'] and ichimoku['tenkan_sen'] > ichimoku['kijun_sen']:
                    ichimoku_signal += " (Alım Sinyali)"
                elif prev_ichimoku and prev_ichimoku['tenkan_sen'] > prev_ichimoku['kijun_sen'] and ichimoku['tenkan_sen'] < ichimoku['kijun_sen']:
                    ichimoku_signal += " (Satış Sinyali)"
            ichimoku_signal += " (Bulut Üstünde)" if current_price > max(ichimoku['senkou_span_a'], ichimoku['senkou_span_b']) else " (Bulut Altında)" if current_price < min(ichimoku['senkou_span_a'], ichimoku['senkou_span_b']) else " (Bulut İçinde)"
        else:
            ichimoku_signal = 'Veri Yok'
        
        atr = calculate_atr(historical_prices)
        vwap = calculate_vwap(historical_prices, volumes) if volumes else 'Veri Yok'
        
        # 7 Günlük Fiyat Değişimi
        price_change_7d = round(((historical_prices[-1]['close'] - historical_prices[-7]['close']) / historical_prices[-7]['close']) * 100, 2) if len(historical_prices) >= 7 else 'Veri Yok'
        
        # Fibonacci Seviyeleri
        highest_high = max(price['high'] for price in historical_prices)
        lowest_low = min(price['low'] for price in historical_prices)
        price_range = highest_high - lowest_low
        fibonacci_levels_raw = {
            '0%': lowest_low,
            '23.6%': lowest_low + 0.236 * price_range,
            '38.2%': lowest_low + 0.382 * price_range,
            '50%': lowest_low + 0.5 * price_range,
            '61.8%': lowest_low + 0.618 * price_range,
            '100%': highest_high,
        }
        fibonacci_levels = {level: {'value': round(value, 2), 'turn_probability': 30, 'rise_probability': 35, 'fall_probability': 35} for level, value in fibonacci_levels_raw.items()}
        closest_level = min(fibonacci_levels_raw, key=lambda level: abs(fibonacci_levels_raw[level] - current_price) if current_price != 'Veri Yok' else float('inf'))
        
        context = {
            'pair': pair,
            'current_price': current_price,
            'sma_50': sma_50_rounded,
            'sma_200': sma_200_rounded,
            'stoch_k': stoch_k,
            'stoch_d': stoch_d,
            'stoch_signal': stoch_signal,
            'adx': adx if adx else 'Veri Yok',
            'rsi': rsi if rsi is not None else 'Veri Yok',
            'price_change_7d': price_change_7d,
            'historical_prices': historical_prices,
            'fibonacci_levels': fibonacci_levels,
            'closest_level': closest_level,
            'timeframe': timeframe,
            'ichimoku': ichimoku if ichimoku else 'Veri Yok',
            'ichimoku_signal': ichimoku_signal,
            'atr': atr if atr else 'Veri Yok',
            'vwap': vwap if vwap else 'Veri Yok'
        }
        return render(request, 'pair_detail.html', context)
    
    except Exception as e:
        print(f"Hata oluştu: {e}")
        return render(request, 'error.html', {'error': str(e)})

# Güncel fiyatları JSON formatında döndüren fonksiyon
def get_prices_json(request):
    """
    Tüm işlem çiftlerinin güncel fiyatlarını JSON formatında döndürür (AJAX için).
    
    Args:
        request (HttpRequest): Django HTTP isteği nesnesi
    
    Returns:
        JsonResponse: Güncel fiyatları içeren JSON yanıtı
    """
    pairs = TradingPair.objects.all()
    prices = get_current_prices(pairs)
    return JsonResponse(prices)