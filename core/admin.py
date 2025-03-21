from django.contrib import admin
from .models import TradingPair

@admin.register(TradingPair)
class TradingPairAdmin(admin.ModelAdmin):
    list_display = ('base_currency', 'quote_currency', 'notification_threshold', 'last_signal')
    fields = ('base_currency', 'quote_currency', 'notification_threshold', 'last_signal')        