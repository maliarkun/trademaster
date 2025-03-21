# Gerekli kütüphaneleri içe aktarır
from django.shortcuts import render  # HTML şablonlarını render etmek için
from django.http import JsonResponse  # JSON formatında yanıt döndürmek için
import requests  # HTTP istekleri yapmak için
from .models import TradingPair  # TradingPair modelini kullanmak için
from django.core.cache import cache  # Önbellekleme işlemleri için

# Telegram'a mesaj göndermek için kullanılan fonksiyon
def send_telegram_message(token, chat_id, message):
    """Telegram API'sini kullanarak belirtilen bot tokenı ve chat ID'si ile bir mesaj gönderir."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {"chat_id": chat_id, "text": message}
    response = requests.post(url, params=params)
    return response.json()

# İşlem çiftlerinin güncel fiyatlarını almak için kullanılan fonksiyon
def get_current_prices(pairs):
    """Verilen işlem çiftleri için CryptoCompare API'sinden güncel fiyatları çeker."""
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

# Geçmiş fiyat ve hacim verilerini almak ve önbelleğe kaydetmek için kullanılan fonksiyon
def get_historical_prices(base, quote, timeframe='day', limit=500):
    """CryptoCompare API'sinden geçmiş fiyat ve hacim verilerini çeker ve önbelleğe kaydeder."""
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
        cache.set(cache_key, (prices, volumes), 300)
        print(f"{base}/{quote} için veri uzunluğu: {len(prices)} ({timeframe})")
        return prices, volumes
    else:
        print(f"Hata: {base}/{quote} için veri çekilemedi. Mesaj: {data.get('Message', 'Bilinmeyen hata')}")
        return [], []

# Basit Hareketli Ortalama (SMA) hesaplamak için kullanılan fonksiyon
def calculate_sma(prices, period):
    """Belirtilen periyot için kapanış fiyatlarının Basit Hareketli Ortalamasını (SMA) hesaplar."""
    if not prices or len(prices) < period:
        return None
    return sum(price['close'] for price in prices[-period:]) / period

# Stochastic Osilatör hesaplamak için kullanılan fonksiyon
def calculate_stochastic(prices, period=14, smooth_k=3, smooth_d=3):
    """Stochastic Osilatör (%K ve %D) hesaplar ve alım/satış sinyali üretir."""
    if not prices or len(prices) < period + smooth_k + smooth_d - 1:
        return None, None, "Veri Yok"
    
    k_values = []
    for i in range(period - 1, len(prices)):
        sub_prices = prices[i - period + 1:i + 1]
        highest_high = max(price['high'] for price in sub_prices)
        lowest_low = min(price['low'] for price in sub_prices)
        current_close = prices[i]['close']
        if highest_high == lowest_low:
            k = 50
        else:
            k = 100 * (current_close - lowest_low) / (highest_high - lowest_low)
        k_values.append(k)
    
    k_smooth_values = []
    for i in range(smooth_k - 1, len(k_values)):
        k_smooth = sum(k_values[i - smooth_k + 1:i + 1]) / smooth_k
        k_smooth_values.append(k_smooth)
    
    d_smooth_values = []
    for i in range(smooth_d - 1, len(k_smooth_values)):
        d_smooth = sum(k_smooth_values[i - smooth_d + 1:i + 1]) / smooth_d
        d_smooth_values.append(d_smooth)
    
    if len(k_smooth_values) < 1 or len(d_smooth_values) < 1:
        return None, None, "Veri Yok"
    current_k = k_smooth_values[-1]
    current_d = d_smooth_values[-1]
    
    stoch_signal = "Nötr"
    if len(k_smooth_values) >= 2 and len(d_smooth_values) >= 2:
        prev_k = k_smooth_values[-2]
        prev_d = d_smooth_values[-2]
        if prev_k < prev_d and current_k > current_d and current_k < 20:
            stoch_signal = "Alım"
        elif prev_k > prev_d and current_k < current_d and current_k > 80:
            stoch_signal = "Satış"
    
    return round(current_k, 2), round(current_d, 2), stoch_signal

# Yönsel Hareket Endeksi (+DI ve -DI) hesaplamak için kullanılan fonksiyon
def calculate_di(prices, period=14):
    """Belirtilen periyot için +DI ve -DI değerlerini hesaplar."""
    if not prices or len(prices) < period + 1:
        return None, None
    plus_dms, minus_dms, trs = [], [], []
    for i in range(1, len(prices)):
        high = prices[i]['high']
        low = prices[i]['low']
        prev_high = prices[i-1]['high']
        prev_low = prices[i-1]['low']
        prev_close = prices[i-1]['close']
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        plus_dm = high - prev_high if high - prev_high > prev_low - low else 0
        minus_dm = prev_low - low if prev_low - low > high - prev_high else 0
        trs.append(tr)
        plus_dms.append(plus_dm)
        minus_dms.append(minus_dm)
    if not trs:
        return None, None
    atr = sum(trs[-period:]) / period
    plus_di = 100 * (sum(plus_dms[-period:]) / period) / atr if atr else 0
    minus_di = 100 * (sum(minus_dms[-period:]) / period) / atr if atr else 0
    return round(plus_di, 2), round(minus_di, 2)

# Ortalama Yönsel Endeks (ADX) hesaplamak için kullanılan fonksiyon
def calculate_adx(prices, period=14):
    """Belirtilen periyot için ADX değerini hesaplar (trend gücü)."""
    if not prices or len(prices) < period + 1:
        return None
    trs, plus_dms, minus_dms = [], [], []
    for i in range(1, len(prices)):
        high = prices[i]['high']
        low = prices[i]['low']
        prev_high = prices[i-1]['high']
        prev_low = prices[i-1]['low']
        prev_close = prices[i-1]['close']
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        plus_dm = high - prev_high if high - prev_high > prev_low - low else 0
        minus_dm = prev_low - low if prev_low - low > high - prev_high else 0
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

# Göreceli Güç Endeksi (RSI) hesaplamak için kullanılan fonksiyon
def calculate_rsi(prices, period=14):
    """Belirtilen periyot için RSI değerini hesaplar (momentum göstergesi)."""
    if not prices or len(prices) < period + 1:
        return None
    changes = [prices[i]['close'] - prices[i-1]['close'] for i in range(1, len(prices))]
    if len(changes) < period:
        return None
    gains = [chg if chg > 0 else 0 for chg in changes[-period:]]
    losses = [-chg if chg < 0 else 0 for chg in changes[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        rsi = 100 if avg_gain > 0 else 50
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

# Ichimoku Bulutu hesaplamak için kullanılan fonksiyon
def calculate_ichimoku(prices, tenkan_period=9, kijun_period=26, senkou_b_period=52):
    """Ichimoku Bulutu bileşenlerini hesaplar: Tenkan-sen, Kijun-sen, Senkou Span A/B, Chikou Span."""
    if not prices or len(prices) < max(tenkan_period, kijun_period, senkou_b_period):
        return None
    
    tenkan_sen = (max([p['high'] for p in prices[-tenkan_period:]]) + 
                  min([p['low'] for p in prices[-tenkan_period:]])) / 2
    kijun_sen = (max([p['high'] for p in prices[-kijun_period:]]) + 
                 min([p['low'] for p in prices[-kijun_period:]])) / 2
    senkou_span_a = (tenkan_sen + kijun_sen) / 2
    senkou_span_b = (max([p['high'] for p in prices[-senkou_b_period:]]) + 
                     min([p['low'] for p in prices[-senkou_b_period:]])) / 2
    chikou_span = prices[-26]['close'] if len(prices) >= 26 else None

    return {
        'tenkan_sen': round(tenkan_sen, 2),
        'kijun_sen': round(kijun_sen, 2),
        'senkou_span_a': round(senkou_span_a, 2),
        'senkou_span_b': round(senkou_span_b, 2),
        'chikou_span': round(chikou_span, 2) if chikou_span else None
    }

# ATR (Average True Range) hesaplamak için kullanılan fonksiyon
def calculate_atr(prices, period=14):
    """ATR (Average True Range) hesaplar: Piyasanın volatilitesini ölçer."""
    if not prices or len(prices) < period + 1:
        return None
    
    tr_list = []
    for i in range(1, len(prices)):
        tr = max(prices[i]['high'] - prices[i]['low'],
                 abs(prices[i]['high'] - prices[i-1]['close']),
                 abs(prices[i]['low'] - prices[i-1]['close']))
        tr_list.append(tr)
    
    atr = sum(tr_list[-period:]) / period
    return round(atr, 2)

# VWAP (Volume Weighted Average Price) hesaplamak için kullanılan fonksiyon
def calculate_vwap(prices, volumes):
    """VWAP (Volume Weighted Average Price) hesaplar: Hacme dayalı ortalama fiyat."""
    if not prices or not volumes or len(prices) != len(volumes):
        return None
    
    total_volume = sum(volumes)
    if total_volume == 0:
        return None
    
    vwap = sum([p['close'] * v for p, v in zip(prices, volumes)]) / total_volume
    return round(vwap, 2)

# Tüm işlem çiftleri için analiz yapan ana fonksiyon
def trading_pairs(request):
    """Tüm işlem çiftleri için teknik analiz yapar ve sonuçları trading_pairs.html şablonuna render eder."""
    try:
        pairs = TradingPair.objects.all()
        current_prices = get_current_prices(pairs)
        price_data = {}
        token = "5345035136:AAF9PZB78SvEm55M538OJtRirA33H1PaqUY"
        chat_id = "-1001423950701"
        
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
            
            # SMA Sinyali
            signal = "Belirsiz"
            if sma_50 and sma_200:
                if sma_50 > sma_200:
                    signal = "Golden Cross (Alım)"
                elif sma_50 < sma_200:
                    signal = "Death Cross (Satış)"
            
            # Stochastic Hesaplamaları
            stoch_k, stoch_d, stoch_signal = calculate_stochastic(historical_prices)
            if stoch_k is None or stoch_d is None:
                stoch_k = 'Veri Yok'
                stoch_d = 'Veri Yok'
                stoch_signal = 'Veri Yok'
            
            # ADX ve DI Hesaplamaları
            adx = calculate_adx(historical_prices)
            plus_di, minus_di = calculate_di(historical_prices)
            adx_signal = "Zayıf Trend"
            if adx and adx > 25:
                if plus_di > minus_di:
                    adx_signal = "Güçlü Yükseliş"
                elif plus_di < minus_di:
                    adx_signal = "Güçlü Düşüş"
                else:
                    adx_signal = "Güçlü Trend (Yön Belirsiz)"
            
            # RSI Hesaplamaları
            rsi = calculate_rsi(historical_prices)
            rsi_signal = "Nötr"
            if rsi is not None:
                if rsi < 30:
                    rsi_signal = "Aşırı Satım (Alım)"
                elif rsi > 70:
                    rsi_signal = "Aşırı Alım (Satış)"
            
            # Güncel Fiyat
            current_price = current_prices.get(key, 'Bilinmeyen')
            if current_price == 'Bilinmeyen':
                current_price = float(historical_prices[-1]['close']) if historical_prices else 'Veri Yok'
            else:
                current_price = float(current_price)
            
            # Yeni Göstergeleri Hesapla
            ichimoku = calculate_ichimoku(historical_prices)
            atr = calculate_atr(historical_prices)
            atr_signal = "Yüksek Volatilite" if atr and atr > 1000 else "Normal Volatilite"
            vwap = calculate_vwap(historical_prices, volumes) if volumes else 'Veri Yok'
            vwap_signal = "Fiyat Ortalamanın Üzerinde" if vwap and current_price and current_price > vwap else "Fiyat Ortalamanın Altında" if vwap and current_price else "Veri Yok"
            
            # Ichimoku Sinyalleri
            if ichimoku:
                ichimoku_signal = ""
                if current_price > ichimoku['kijun_sen']:
                    ichimoku_signal = "Yükseliş Trendi"
                elif current_price < ichimoku['kijun_sen']:
                    ichimoku_signal = "Düşüş Trendi"
                else:
                    ichimoku_signal = "Nötr"
                
                if len(historical_prices) >= 2:
                    prev_ichimoku = calculate_ichimoku(historical_prices[:-1])
                    if prev_ichimoku:
                        prev_tenkan = prev_ichimoku['tenkan_sen']
                        prev_kijun = prev_ichimoku['kijun_sen']
                        current_tenkan = ichimoku['tenkan_sen']
                        current_kijun = ichimoku['kijun_sen']
                        if prev_tenkan < prev_kijun and current_tenkan > current_kijun:
                            ichimoku_signal += " (Alım Sinyali)"
                        elif prev_tenkan > prev_kijun and current_tenkan < current_kijun:
                            ichimoku_signal += " (Satış Sinyali)"
                
                if current_price > max(ichimoku['senkou_span_a'], ichimoku['senkou_span_b']):
                    ichimoku_signal += " (Bulut Üstünde)"
                elif current_price < min(ichimoku['senkou_span_a'], ichimoku['senkou_span_b']):
                    ichimoku_signal += " (Bulut Altında)"
                else:
                    ichimoku_signal += " (Bulut İçinde)"
            else:
                ichimoku_signal = 'Veri Yok'
            
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
                
                closest_level = None
                min_diff = float('inf')
                turn_probability = 0
                rise_probability = 0
                fall_probability = 0
                for level, value in fibonacci_levels_raw.items():
                    diff = abs(current_price - value)
                    if diff < min_diff:
                        min_diff = diff
                        closest_level = level
                        distance_factor = max(0, 1 - (diff / (price_range * 0.5)))
                        turn_probability = 30 * distance_factor
                        rise_probability = 35
                        fall_probability = 35
                        
                        # Mevcut Sinyaller
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
                        
                        # Yeni Göstergeler: Ichimoku Signal
                        if "Yükseliş Trendi" in ichimoku_signal:
                            rise_probability += 10 * distance_factor
                        elif "Düşüş Trendi" in ichimoku_signal:
                            fall_probability += 10 * distance_factor
                        if "Alım Sinyali" in ichimoku_signal:
                            rise_probability += 5 * distance_factor
                        elif "Satış Sinyali" in ichimoku_signal:
                            fall_probability += 5 * distance_factor
                        
                        # Yeni Göstergeler: ATR Signal
                        if atr_signal == "Yüksek Volatilite":
                            turn_probability += 10 * distance_factor
                        
                        # Yeni Göstergeler: VWAP Signal
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
                            turn_probability = 33
                            rise_probability = 33
                            fall_probability = 34
            else:
                closest_level = 'Veri Yok'
                turn_probability = 'Veri Yok'
                rise_probability = 'Veri Yok'
                fall_probability = 'Veri Yok'
            
            # Analiz sonuçlarını sözlüğe ekle
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
            
            # Telegram Bildirimi
            if rise_probability != 'Veri Yok' and rise_probability >= pair.notification_threshold:
                message = f"{key} için Yükselme İhtimali: %{rise_probability} (Güncel Fiyat: {current_price})"
                send_telegram_message(token, chat_id, message)
        
        return render(request, 'trading_pairs.html', {'price_data': price_data})
    
    except Exception as e:
        print(f"Hata oluştu: {e}")
        return render(request, 'error.html', {'error': str(e)})

# Belirli bir işlem çifti için detaylı analiz yapan fonksiyon
def pair_detail(request, pair):
    """Belirli bir işlem çifti için teknik analiz yapar ve pair_detail.html şablonuna render eder."""
    try:
        timeframe = request.GET.get('timeframe', 'day')
        base, quote = pair.split('/')
        
        historical_prices, volumes = get_historical_prices(base, quote, timeframe=timeframe)
        if not historical_prices:
            return render(request, 'error.html', {'error': f"{pair} için veri bulunamadı."})
        
        current_price = get_current_prices([TradingPair(base_currency=base, quote_currency=quote)]).get(pair, 'Bilinmeyen')
        if current_price == 'Bilinmeyen':
            current_price = float(historical_prices[-1]['close']) if historical_prices else 'Veri Yok'
        else:
            current_price = float(current_price)
        
        # Teknik göstergeleri hesapla
        sma_50 = calculate_sma(historical_prices, 50)
        sma_200 = calculate_sma(historical_prices, 200)
        sma_50_rounded = round(sma_50, 2) if sma_50 else 'Veri Yok'
        sma_200_rounded = round(sma_200, 2) if sma_200 else 'Veri Yok'
        
        stoch_k, stoch_d, stoch_signal = calculate_stochastic(historical_prices)
        if stoch_k is None or stoch_d is None:
            stoch_k = 'Veri Yok'
            stoch_d = 'Veri Yok'
            stoch_signal = 'Veri Yok'
        
        adx = calculate_adx(historical_prices)
        rsi = calculate_rsi(historical_prices)
        
        # Yeni Göstergeleri Hesapla
        ichimoku = calculate_ichimoku(historical_prices)
        atr = calculate_atr(historical_prices)
        vwap = calculate_vwap(historical_prices, volumes) if volumes else 'Veri Yok'
        
        # Ichimoku Sinyalleri
        if ichimoku:
            ichimoku_signal = ""
            if current_price > ichimoku['kijun_sen']:
                ichimoku_signal = "Yükseliş Trendi"
            elif current_price < ichimoku['kijun_sen']:
                ichimoku_signal = "Düşüş Trendi"
            else:
                ichimoku_signal = "Nötr"
            
            if len(historical_prices) >= 2:
                prev_ichimoku = calculate_ichimoku(historical_prices[:-1])
                if prev_ichimoku:
                    prev_tenkan = prev_ichimoku['tenkan_sen']
                    prev_kijun = prev_ichimoku['kijun_sen']
                    current_tenkan = ichimoku['tenkan_sen']
                    current_kijun = ichimoku['kijun_sen']
                    if prev_tenkan < prev_kijun and current_tenkan > current_kijun:
                        ichimoku_signal += " (Alım Sinyali)"
                    elif prev_tenkan > prev_kijun and current_tenkan < current_kijun:
                        ichimoku_signal += " (Satış Sinyali)"
            
            if current_price > max(ichimoku['senkou_span_a'], ichimoku['senkou_span_b']):
                ichimoku_signal += " (Bulut Üstünde)"
            elif current_price < min(ichimoku['senkou_span_a'], ichimoku['senkou_span_b']):
                ichimoku_signal += " (Bulut Altında)"
            else:
                ichimoku_signal += " (Bulut İçinde)"
        else:
            ichimoku_signal = 'Veri Yok'
        
        # 7 günlük fiyat değişimi
        price_change_7d = 'Veri Yok'
        if len(historical_prices) >= 7:
            price_change_7d = ((historical_prices[-1]['close'] - historical_prices[-7]['close']) / historical_prices[-7]['close']) * 100
            price_change_7d = round(price_change_7d, 2)
        
        # Fibonacci seviyeleri
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
        
        fibonacci_levels = {}
        closest_level = None
        min_diff = float('inf')
        for level, value in fibonacci_levels_raw.items():
            diff = abs(current_price - value)
            if diff < min_diff:
                min_diff = diff
                closest_level = level
            fibonacci_levels[level] = {
                'value': round(value, 2),
                'turn_probability': 30,
                'rise_probability': 35,
                'fall_probability': 35
            }
        
        # Şablona gönderilecek bağlam
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
    """Tüm işlem çiftlerinin güncel fiyatlarını JSON formatında döndürür (AJAX için)."""
    pairs = TradingPair.objects.all()
    prices = get_current_prices(pairs)
    return JsonResponse(prices)