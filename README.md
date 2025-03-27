# TradeMaster

TradeMaster, kripto para piyasalarında işlem çiftlerini analiz eden ve alım-satım sinyalleri sunan bir web uygulamasıdır. Bir yatırım aracı <b>değildir.</b>

Özellikler
- Güncel Veriler: Kripto para çiftleri için gerçek zamanlı fiyat ve analiz verileri.
- Teknik Göstergeler: SMA, RSI, Stochastic, ADX, ATR, VWAP ve Ichimoku Bulutu gibi araçlar.
- Fibonacci Seviyeleri: Destek ve direnç noktalarını bulmak için Fibonacci retracement.
- Sinyaller: Göstergelere göre alım, satım veya bekleme önerileri.
- Grafikler: Fiyat hareketlerini ve seviyeleri görselleştirme.

Kurulum

Gereksinimler
- Python 3.8 veya üstü
- Django 4.0 veya üstü
- Git

Adımlar
1. Projeyi İndirin:
   ```
   git clone https://github.com/maliarkun/trademaster.git
   cd trademaster
   ```
2. Sanal Ortam Hazırlayın:
   - Sanal ortamı oluştur:
     ```
     python -m venv venv
     ```
   - Sanal ortamı aktive et:
     - Linux/Mac için:
       ```
       source venv/bin/activate
       ```
     - Windows için:
       ```
       venv\Scripts\activate
       ```
   Not: Terminalde (venv) yazısını görüyorsanız, sanal ortam aktif olmuştur.

3. Paketleri Yükleyin:
   ```
   pip install -r requirements.txt
   ```
4. Veritabanını Ayarlayın:
   ```
   python manage.py migrate
   ```
5. Uygulamayı Çalıştırın:
   ```
   python manage.py runserver
   ```
6. Tarayıcıda Açın:
   - http://127.0.0.1:8000/ adresine gidin.

Kullanım
- Ana Sayfa: İşlem çiftlerini listeleyin ve birini seçin.
- Detay Sayfası: Seçtiğiniz çifte ait göstergeleri, Fibonacci seviyelerini ve sinyalleri görün.
- Zaman Dilimi: Analizi saatlik, günlük veya haftalık olarak ayarlayın.

Katkıda Bulunma
Projeyi geliştirmek isterseniz:
- Depoyu forklayın.
- Yeni bir branch açın:
  git checkout -b yenilik
- Değişikliklerinizi kaydedin:
  git commit -m 'Değişiklik yapıldı'
- Push edin:
  git push origin yenilik
- Pull Request oluşturun.

Lisans
Bu proje MIT Lisansı ile lisanslanmıştır.
