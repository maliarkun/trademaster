from django.contrib import admin
from .models import TradingPair, Signal, TimeFrame  # TimeFrame modelini ekledik
from .models import NotificationSettings

admin.site.register(NotificationSettings)

@admin.register(TradingPair)
class TradingPairAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'notification_threshold')

@admin.register(Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = ('trading_pair', 'signal', 'timestamp')

@admin.register(TimeFrame)
class TimeFrameAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

