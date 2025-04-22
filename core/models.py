from django.db import models
from django.contrib.auth.models import User

class TimeFrame(models.Model):
    name = models.CharField(max_length=10, unique=True, verbose_name="Zaman Dilimi Kodu")
    description = models.CharField(max_length=50, blank=True, verbose_name="Açıklama")

    def __str__(self):
        return self.name

class TradingPair(models.Model):
    base_currency = models.CharField(max_length=10, verbose_name="Temel Para Birimi")
    quote_currency = models.CharField(max_length=10, verbose_name="Karşıt Para Birimi")
    notification_threshold = models.IntegerField(default=51, help_text="Threshold for notification probability")
    time_frames = models.ManyToManyField(TimeFrame, related_name='trading_pairs', verbose_name="Seçili Zaman Dilimleri",blank=True)

    def __str__(self):
        return f"{self.base_currency}/{self.quote_currency}"

    class Meta:
        unique_together = ('base_currency', 'quote_currency')

class UserPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='preferences')
    trading_pair = models.ForeignKey(TradingPair, on_delete=models.CASCADE)
    time_frame = models.ForeignKey(TimeFrame, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - {self.trading_pair} - {self.time_frame.name}"

class Signal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='signals', null=True)
    trading_pair = models.ForeignKey(TradingPair, on_delete=models.CASCADE, related_name='signals')
    indicator = models.CharField(max_length=50, verbose_name="İndikatör")
    signal = models.CharField(max_length=10, verbose_name="Sinyal")
    price = models.DecimalField(max_digits=20, decimal_places=10, verbose_name="Fiyat")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Zamanı")
    time_frame = models.ForeignKey(TimeFrame, on_delete=models.CASCADE, verbose_name="Zaman Dilimi")

    def __str__(self):
        return f"{self.trading_pair} - {self.indicator} - {self.signal}"

class NotificationSettings(models.Model):
    telegram_enabled = models.BooleanField(default=True, verbose_name="Telegram Bildirimleri Aktif")
    test_mode = models.BooleanField(default=False, verbose_name="Test Modu")

    def __str__(self):
        return "Bildirim Ayarları"