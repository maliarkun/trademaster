from django.db import models

# Create your models here.

from django.db import models

class TradingPair(models.Model):
    base_currency = models.CharField(max_length=10)
    quote_currency = models.CharField(max_length=10)
    notification_threshold = models.IntegerField(default=51, help_text="Bildirim için yükselme ihtimali eşiği")

    def __str__(self):
        return f"{self.base_currency}/{self.quote_currency}"    