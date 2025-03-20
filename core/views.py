# Gerekli kütüphaneleri içe aktarır
from django.shortcuts import render  # HTML şablonlarını render etmek için
from django.http import JsonResponse  # JSON formatında yanıt döndürmek için
import requests  # HTTP istekleri yapmak için
from .models import TradingPair  # TradingPair modelini kullanmak için
from django.core.cache import cache  # Önbellekleme işlemleri için

# Telegram'a mesaj göndermek için kullanılan fonksiyon
def send_telegram_message(token, chat_id, message):
    """Telegram API'sini kullanarak belirtilen bot tokenı ve chat ID'si ile bir mesaj gönderir."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"  # Telegram API endpoint'i
    params = {"chat_id": chat_id, "text": message}  # Gönderilecek parametreler
    response = requests.post(url, params=params)  # POST isteği ile mesaj gönderimi
    return response.json()  # API'den gelen JSON yanıtı döndürür

# İşlem çiftlerinin güncel fiyatlarını almak için kullanılan fonksiyon
def get_current_prices(pairs):
    """Verilen işlem çiftleri için CryptoCompare API'sinden güncel fiyatları çeker."""
    if not pairs:  # Eğer işlem çifti listesi boşsa boş bir sözlük döndür
        return {}
    base_currencies = ','.join([pair.base_currency for pair in pairs])  # Temel para birimlerini virgülle birleştir
    quote_currency = pairs[0].quote_currency  # Alıntı para birimini ilk çiftten al
    url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={base_currencies}&tsyms={quote_currency}"  # API URL'si
    response = requests.get(url)  # GET isteği ile fiyatları çek
    data = response.json()  # Yanıtı JSON formatına çevir
    prices = {}  # Fiyatları saklamak için sözlük
    for pair in pairs:
        base = pair.base_currency  # Temel para birimi
        quote = pair.quote_currency  # Alıntı para birimi
        price = data.get(base, {}).get(quote, 'Bilinmeyen')  # Fiyatı al, yoksa 'Bilinmeyen' döndür
        prices[f"{base}/{quote}"] = price  # Çift adıyla birlikte fiyatı sakla
    return prices  # Fiyat sözlüğünü döndür

# Geçmiş fiyat verilerini almak ve önbelleğe kaydetmek için kullanılan fonksiyon
def get_historical_prices(base, quote, timeframe='day', limit=500):
    """CryptoCompare API'sinden geçmiş fiyat verilerini çeker ve önbelleğe kaydeder."""
    cache_key = f"historical_{base}_{quote}_{timeframe}_{limit}"  # Önbellek anahtarı oluştur
    cached_data = cache.get(cache_key)  # Önbellekten veriyi kontrol et
    if cached_data is not None:  # Eğer önbellekte veri varsa
        print(f"{base}/{quote} için önbellekten veri alındı ({timeframe}).")  # Bilgi yazdır
        return cached_data  # Önbellek verisini döndür
    
    # Zaman dilimine göre API URL'sini belirle
    if timeframe == 'hour':
        url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym={base}&tsym={quote}&limit={limit}"  # Saatlik veri
    elif timeframe == '4hour':
        url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym={base}&tsym={quote}&limit={limit}&aggregate=4"  # 4 saatlik veri
    elif timeframe == 'week':
        url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym={base}&tsym={quote}&limit={limit}&aggregate=7"  # Haftalık veri
    else:  # Varsayılan: günlük
        url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym={base}&tsym={quote}&limit={limit}"  # Günlük veri
    
    response = requests.get(url)  # API'den veriyi çek
    data = response.json()  # Yanıtı JSON formatına çevir
    # API yanıtı başarılıysa ve gerekli veri mevcutsa
    if data.get('Response') == 'Success' and 'Data' in data and 'Data' in data['Data']:
        # Veriyi liste formatında hazırla (high, low, close, time)
        prices = [{'high': float(entry['high']), 'low': float(entry['low']), 'close': float(entry['close']), 'time': entry['time']} for entry in data['Data']['Data']]
        print(f"{base}/{quote} için veri uzunluğu: {len(prices)} ({timeframe})")  # Veri uzunluğunu yazdır
        cache.set(cache_key, prices, 300)  # Veriyi 5 dakika (300 saniye) önbelleğe kaydet
        return prices  # Fiyat listesini döndür
    else:
        print(f"Hata: {base}/{quote} için veri çekilemedi. Mesaj: {data.get('Message', 'Bilinmeyen hata')}")  # Hata mesajını yazdır
        return []  # Boş liste döndür

# Basit Hareketli Ortalama (SMA) hesaplamak için kullanılan fonksiyon
def calculate_sma(prices, period):
    """Belirtilen periyot için kapanış fiyatlarının Basit Hareketli Ortalamasını (SMA) hesaplar."""
    if not prices or len(prices) < period:  # Yeterli veri yoksa None döndür
        return None
    return sum(price['close'] for price in prices[-period:]) / period  # Son 'period' kadar kapanış fiyatının ortalamasını al

# Stochastic Osilatör hesaplamak için kullanılan fonksiyon
def calculate_stochastic(prices, period=14, smooth_k=3, smooth_d=3):
    """Stochastic Osilatör (%K ve %D) hesaplar ve alım/satış sinyali üretir."""
    # Yeterli veri kontrolü
    if not prices or len(prices) < period + smooth_k + smooth_d - 1:
        return None, None, "Veri Yok"  # Yeterli veri yoksa hata döndür
    
    # %K değerlerini hesapla
    k_values = []
    for i in range(period - 1, len(prices)):
        sub_prices = prices[i - period + 1:i + 1]  # Son 'period' kadar veri
        highest_high = max(price['high'] for price in sub_prices)  # En yüksek fiyat
        lowest_low = min(price['low'] for price in sub_prices)  # En düşük fiyat
        current_close = prices[i]['close']  # Güncel kapanış fiyatı
        if highest_high == lowest_low:  # Bölme hatasını önlemek için
            k = 50  # Nötr bir değer
        else:
            k = 100 * (current_close - lowest_low) / (highest_high - lowest_low)  # %K formülü
        k_values.append(k)
    
    # Yumuşatılmış %K (slow %K) hesapla
    k_smooth_values = []
    for i in range(smooth_k - 1, len(k_values)):
        k_smooth = sum(k_values[i - smooth_k + 1:i + 1]) / smooth_k  # Son 'smooth_k' kadar ortalaması
        k_smooth_values.append(k_smooth)
    
    # %D (slow %D) hesapla
    d_smooth_values = []
    for i in range(smooth_d - 1, len(k_smooth_values)):
        d_smooth = sum(k_smooth_values[i - smooth_d + 1:i + 1]) / smooth_d  # Son 'smooth_d' kadar ortalaması
        d_smooth_values.append(d_smooth)
    
    # Son değerleri kontrol et
    if len(k_smooth_values) < 1 or len(d_smooth_values) < 1:
        return None, None, "Veri Yok"  # Yeterli veri yoksa hata döndür
    current_k = k_smooth_values[-1]  # Güncel %K
    current_d = d_smooth_values[-1]  # Güncel %D
    
    # Sinyal üret
    stoch_signal = "Nötr"  # Varsayılan sinyal
    if len(k_smooth_values) >= 2 and len(d_smooth_values) >= 2:  # Önceki değerler için kontrol
        prev_k = k_smooth_values[-2]  # Önceki %K
        prev_d = d_smooth_values[-2]  # Önceki %D
        if prev_k < prev_d and current_k > current_d and current_k < 20:  # Alım sinyali
            stoch_signal = "Alım"
        elif prev_k > prev_d and current_k < current_d and current_k > 80:  # Satış sinyali
            stoch_signal = "Satış"
    
    return round(current_k, 2), round(current_d, 2), stoch_signal  # Yuvarlanmış %K, %D ve sinyali döndür

# Yönsel Hareket Endeksi (+DI ve -DI) hesaplamak için kullanılan fonksiyon
def calculate_di(prices, period=14):
    """Belirtilen periyot için +DI ve -DI değerlerini hesaplar."""
    if not prices or len(prices) < period + 1:  # Yeterli veri yoksa None döndür
        return None, None
    plus_dms, minus_dms, trs = [], [], []  # Hareket ve gerçek aralık listeleri
    for i in range(1, len(prices)):
        high = prices[i]['high']  # Güncel yüksek
        low = prices[i]['low']  # Güncel düşük
        prev_high = prices[i-1]['high']  # Önceki yüksek
        prev_low = prices[i-1]['low']  # Önceki düşük
        prev_close = prices[i-1]['close']  # Önceki kapanış
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))  # Gerçek aralık (TR)
        plus_dm = high - prev_high if high - prev_high > prev_low - low else 0  # +DM
        minus_dm = prev_low - low if prev_low - low > high - prev_high else 0  # -DM
        trs.append(tr)
        plus_dms.append(plus_dm)
        minus_dms.append(minus_dm)
    if not trs:  # Veri yoksa None döndür
        return None, None
    atr = sum(trs[-period:]) / period  # Ortalama Gerçek Aralık (ATR)
    plus_di = 100 * (sum(plus_dms[-period:]) / period) / atr if atr else 0  # +DI
    minus_di = 100 * (sum(minus_dms[-period:]) / period) / atr if atr else 0  # -DI
    return round(plus_di, 2), round(minus_di, 2)  # Yuvarlanmış +DI ve -DI döndür

# Ortalama Yönsel Endeks (ADX) hesaplamak için kullanılan fonksiyon
def calculate_adx(prices, period=14):
    """Belirtilen periyot için ADX değerini hesaplar (trend gücü)."""
    if not prices or len(prices) < period + 1:  # Yeterli veri yoksa None döndür
        return None
    trs, plus_dms, minus_dms = [], [], []  # Hareket ve gerçek aralık listeleri
    for i in range(1, len(prices)):
        high = prices[i]['high']  # Güncel yüksek
        low = prices[i]['low']  # Güncel düşük
        prev_high = prices[i-1]['high']  # Önceki yüksek
        prev_low = prices[i-1]['low']  # Önceki düşük
        prev_close = prices[i-1]['close']  # Önceki kapanış
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))  # Gerçek aralık (TR)
        plus_dm = high - prev_high if high - prev_high > prev_low - low else 0  # +DM
        minus_dm = prev_low - low if prev_low - low > high - prev_high else 0  # -DM
        trs.append(tr)
        plus_dms.append(plus_dm)
        minus_dms.append(minus_dm)
    if not trs:  # Veri yoksa None döndür
        return None
    atr = sum(trs[-period:]) / period  # Ortalama Gerçek Aralık (ATR)
    plus_di = 100 * (sum(plus_dms[-period:]) / period) / atr if atr else 0  # +DI
    minus_di = 100 * (sum(minus_dms[-period:]) / period) / atr if atr else 0  # -DI
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if plus_di + minus_di else 0  # DX
    return round(dx, 2)  # Yuvarlanmış ADX döndür

# Göreceli Güç Endeksi (RSI) hesaplamak için kullanılan fonksiyon
def calculate_rsi(prices, period=14):
    """Belirtilen periyot için RSI değerini hesaplar (momentum göstergesi)."""
    if not prices or len(prices) < period + 1:  # Yeterli veri yoksa None döndür
        return None
    changes = [prices[i]['close'] - prices[i-1]['close'] for i in range(1, len(prices))]  # Fiyat değişimleri
    if len(changes) < period:  # Yeterli değişim yoksa None döndür
        return None
    gains = [chg if chg > 0 else 0 for chg in changes[-period:]]  # Kazançlar
    losses = [-chg if chg < 0 else 0 for chg in changes[-period:]]  # Kayıplar
    avg_gain = sum(gains) / period  # Ortalama kazanç
    avg_loss = sum(losses) / period  # Ortalama kayıp
    if avg_loss == 0:  # Kayıp yoksa özel durum
        rsi = 100 if avg_gain > 0 else 50  # Eğer kazanç varsa 100, yoksa 50
    else:
        rs = avg_gain / avg_loss  # Göreceli güç (RS)
        rsi = 100 - (100 / (1 + rs))  # RSI formülü
    return round(rsi, 2)  # Yuvarlanmış RSI döndür

# Tüm işlem çiftleri için analiz yapan ana fonksiyon
def trading_pairs(request):
    """Tüm işlem çiftleri için teknik analiz yapar ve sonuçları trading_pairs.html şablonuna render eder."""
    try:
        pairs = TradingPair.objects.all()  # Tüm işlem çiftlerini al
        current_prices = get_current_prices(pairs)  # Güncel fiyatları çek
        price_data = {}  # Analiz sonuçlarını saklamak için sözlük
        token = "5345035136:AAF9PZB78SvEm55M538OJtRirA33H1PaqUY"  # Telegram bot tokenı
        chat_id = "-1001423950701"  # Telegram chat ID'si
        
        for pair in pairs:  # Her bir işlem çifti için
            key = f"{pair.base_currency}/{pair.quote_currency}"  # Çift anahtarı (örneğin, BTC/USDT)
            historical_prices = get_historical_prices(pair.base_currency, pair.quote_currency)  # Geçmiş verileri al
            
            # SMA Hesaplamaları
            sma_50 = calculate_sma(historical_prices, 50)  # 50 günlük SMA
            sma_200 = calculate_sma(historical_prices, 200)  # 200 günlük SMA
            sma_50_rounded = round(sma_50, 2) if sma_50 else 'Veri Yok'  # Yuvarla veya hata mesajı
            sma_200_rounded = round(sma_200, 2) if sma_200 else 'Veri Yok'
            
            # SMA Sinyali
            signal = "Belirsiz"  # Varsayılan sinyal
            if sma_50 and sma_200:  # Eğer her iki SMA varsa
                if sma_50 > sma_200:
                    signal = "Golden Cross (Alım)"  # Alım sinyali
                elif sma_50 < sma_200:
                    signal = "Death Cross (Satış)"  # Satış sinyali
            
            # Stochastic Hesaplamaları
            stoch_k, stoch_d, stoch_signal = calculate_stochastic(historical_prices)  # Stochastic değerleri
            if stoch_k is None or stoch_d is None:  # Veri yoksa hata mesajı
                stoch_k = 'Veri Yok'
                stoch_d = 'Veri Yok'
                stoch_signal = 'Veri Yok'
            
            # ADX ve DI Hesaplamaları
            adx = calculate_adx(historical_prices)  # ADX hesapla
            plus_di, minus_di = calculate_di(historical_prices)  # +DI ve -DI hesapla
            adx_signal = "Zayıf Trend"  # Varsayılan ADX sinyali
            if adx and adx > 25:  # Eğer trend güçlü ise
                if plus_di > minus_di:
                    adx_signal = "Güçlü Yükseliş"  # Yükseliş trendi
                elif plus_di < minus_di:
                    adx_signal = "Güçlü Düşüş"  # Düşüş trendi
                else:
                    adx_signal = "Güçlü Trend (Yön Belirsiz)"  # Yön belirsiz
            
            # RSI Hesaplamaları
            rsi = calculate_rsi(historical_prices)  # RSI hesapla
            rsi_signal = "Nötr"  # Varsayılan RSI sinyali
            if rsi is not None:  # Eğer RSI varsa
                if rsi < 30:
                    rsi_signal = "Aşırı Satım (Alım)"  # Alım sinyali
                elif rsi > 70:
                    rsi_signal = "Aşırı Alım (Satış)"  # Satış sinyali
            
            # Güncel Fiyat
            current_price = current_prices.get(key, 'Bilinmeyen')  # Güncel fiyatı al
            if current_price == 'Bilinmeyen':  # Eğer API'den alınamadıysa
                current_price = float(historical_prices[-1]['close']) if historical_prices else 'Veri Yok'  # Son kapanış
            else:
                current_price = float(current_price)  # Float'a çevir
            
            # Fibonacci Seviyeleri ve İhtimaller
            if historical_prices:  # Geçmiş veri varsa
                highest_high = max(price['high'] for price in historical_prices)  # En yüksek fiyat
                lowest_low = min(price['low'] for price in historical_prices)  # En düşük fiyat
                price_range = highest_high - lowest_low  # Fiyat aralığı
                fibonacci_levels_raw = {  # Ham Fibonacci seviyeleri
                    '0%': lowest_low,
                    '23.6%': lowest_low + 0.236 * price_range,
                    '38.2%': lowest_low + 0.382 * price_range,
                    '50%': lowest_low + 0.5 * price_range,
                    '61.8%': lowest_low + 0.618 * price_range,
                    '100%': highest_high,
                }
                
                closest_level = None  # En yakın Fibonacci seviyesi
                min_diff = float('inf')  # Minimum fark
                turn_probability = 0  # Dönüş ihtimali
                rise_probability = 0  # Yükselme ihtimali
                fall_probability = 0  # Düşme ihtimali
                for level, value in fibonacci_levels_raw.items():
                    diff = abs(current_price - value)  # Fiyat farkı
                    if diff < min_diff:  # En yakın seviyeyi bul
                        min_diff = diff
                        closest_level = level
                        distance_factor = max(0, 1 - (diff / (price_range * 0.5)))  # Mesafe faktörü
                        turn_probability = 30 * distance_factor  # Temel dönüş ihtimali
                        rise_probability = 35  # Temel yükselme ihtimali
                        fall_probability = 35  # Temel düşme ihtimali
                        
                        # SMA sinyaline göre ihtimal ayarı
                        if signal == "Golden Cross (Alım)":
                            rise_probability += 15 * distance_factor
                            fall_probability -= 15 * distance_factor
                        elif signal == "Death Cross (Satış)":
                            fall_probability += 15 * distance_factor
                            rise_probability -= 15 * distance_factor
                        
                        # Stochastic sinyaline göre ihtimal ayarı
                        if stoch_signal == "Alım":
                            rise_probability += 10 * distance_factor
                            fall_probability -= 10 * distance_factor
                        elif stoch_signal == "Satış":
                            fall_probability += 10 * distance_factor
                            rise_probability -= 10 * distance_factor
                        
                        # ADX sinyaline göre ihtimal ayarı
                        if adx_signal == "Güçlü Yükseliş":
                            rise_probability += 10 * distance_factor
                        elif adx_signal == "Güçlü Düşüş":
                            fall_probability += 10 * distance_factor
                        
                        # RSI sinyaline göre ihtimal ayarı
                        if rsi is not None:
                            if rsi < 30:
                                rise_probability += 10 * distance_factor
                                fall_probability -= 10 * distance_factor
                            elif rsi > 70:
                                fall_probability += 10 * distance_factor
                                rise_probability -= 10 * distance_factor
                        
                        # Toplam ihtimali normalize et
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
                'fall_probability': fall_probability
            }
            
            # Telegram Bildirimi
            if rise_probability != 'Veri Yok' and rise_probability >= pair.notification_threshold:  # Eşik aşılırsa
                message = f"{key} için Yükselme İhtimali: %{rise_probability} (Güncel Fiyat: {current_price})"
                send_telegram_message(token, chat_id, message)  # Mesaj gönder
        
        # Şablona render et
        return render(request, 'trading_pairs.html', {'price_data': price_data})
    
    except Exception as e:  # Hata durumunda
        print(f"Hata oluştu: {e}")  # Hata mesajını yazdır
        return render(request, 'error.html', {'error': str(e)})  # Hata sayfasını render et

# Belirli bir işlem çifti için detaylı analiz yapan fonksiyon
def pair_detail(request, pair):
    """Belirli bir işlem çifti için teknik analiz yapar ve pair_detail.html şablonuna render eder."""
    try:
        timeframe = request.GET.get('timeframe', 'day')  # URL'den zaman dilimini al, yoksa 'day' kullan
        base, quote = pair.split('/')  # Çifti temel ve alıntı para birimlerine ayır
        
        # Zaman dilimine göre geçmiş fiyatları al
        historical_prices = get_historical_prices(base, quote, timeframe=timeframe)
        if not historical_prices:  # Veri yoksa hata döndür
            return render(request, 'error.html', {'error': f"{pair} için veri bulunamadı."})
        
        # Güncel fiyatı al
        current_price = get_current_prices([TradingPair(base_currency=base, quote_currency=quote)]).get(pair, 'Bilinmeyen')
        if current_price == 'Bilinmeyen':  # Eğer API'den alınamadıysa
            current_price = float(historical_prices[-1]['close']) if historical_prices else 'Veri Yok'  # Son kapanış
        else:
            current_price = float(current_price)  # Float'a çevir
        
        # Teknik göstergeleri hesapla
        sma_50 = calculate_sma(historical_prices, 50)  # 50 günlük SMA
        sma_200 = calculate_sma(historical_prices, 200)  # 200 günlük SMA
        sma_50_rounded = round(sma_50, 2) if sma_50 else 'Veri Yok'  # Yuvarla veya hata mesajı
        sma_200_rounded = round(sma_200, 2) if sma_200 else 'Veri Yok'
        
        stoch_k, stoch_d, stoch_signal = calculate_stochastic(historical_prices)  # Stochastic değerleri
        if stoch_k is None or stoch_d is None:  # Veri yoksa hata mesajı
            stoch_k = 'Veri Yok'
            stoch_d = 'Veri Yok'
            stoch_signal = 'Veri Yok'
        
        adx = calculate_adx(historical_prices)  # ADX hesapla
        rsi = calculate_rsi(historical_prices)  # RSI hesapla
        
        # 7 günlük fiyat değişimi
        price_change_7d = 'Veri Yok'
        if len(historical_prices) >= 7:  # Yeterli veri varsa
            price_change_7d = ((historical_prices[-1]['close'] - historical_prices[-7]['close']) / historical_prices[-7]['close']) * 100
            price_change_7d = round(price_change_7d, 2)  # Yüzde değişimi yuvarla
        
        # Fibonacci seviyeleri
        highest_high = max(price['high'] for price in historical_prices)  # En yüksek fiyat
        lowest_low = min(price['low'] for price in historical_prices)  # En düşük fiyat
        price_range = highest_high - lowest_low  # Fiyat aralığı
        fibonacci_levels_raw = {  # Ham Fibonacci seviyeleri
            '0%': lowest_low,
            '23.6%': lowest_low + 0.236 * price_range,
            '38.2%': lowest_low + 0.382 * price_range,
            '50%': lowest_low + 0.5 * price_range,
            '61.8%': lowest_low + 0.618 * price_range,
            '100%': highest_high,
        }
        
        fibonacci_levels = {}  # Sonuç sözlüğü
        closest_level = None  # En yakın seviye
        min_diff = float('inf')  # Minimum fark
        for level, value in fibonacci_levels_raw.items():
            diff = abs(current_price - value)  # Fiyat farkı
            if diff < min_diff:  # En yakın seviyeyi bul
                min_diff = diff
                closest_level = level
            fibonacci_levels[level] = {  # Seviye detayları
                'value': round(value, 2),  # Yuvarlanmış değer
                'turn_probability': 30,  # Örnek dönüş ihtimali
                'rise_probability': 35,  # Örnek yükselme ihtimali
                'fall_probability': 35  # Örnek düşme ihtimali
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
            'timeframe': timeframe  # Seçilen zaman dilimi
        }
        
        return render(request, 'pair_detail.html', context)  # Şablona render et
    
    except Exception as e:  # Hata durumunda
        print(f"Hata oluştu: {e}")  # Hata mesajını yazdır
        return render(request, 'error.html', {'error': str(e)})  # Hata sayfasını render et

# Güncel fiyatları JSON formatında döndüren fonksiyon
def get_prices_json(request):
    """Tüm işlem çiftlerinin güncel fiyatlarını JSON formatında döndürür (AJAX için)."""
    pairs = TradingPair.objects.all()  # Tüm işlem çiftlerini al
    prices = get_current_prices(pairs)  # Güncel fiyatları çek
    return JsonResponse(prices)  # JSON yanıtı döndür