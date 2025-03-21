from django.contrib import admin
from django.urls import path, re_path  # re_path eklemeyi unutmayın
from core import views  # views modülünü core'dan alıyoruz

urlpatterns = [
    # Admin paneli için URL
    path('admin/', admin.site.urls),
    
    # Ana sayfa: Tüm işlem çiftlerinin listesi ve analizleri
    path('prices/', views.trading_pairs, name='trading_pairs'),
    
    # AJAX ile güncel fiyatları almak için JSON endpoint
    path('prices/json/', views.get_prices_json, name='get_prices_json'),
    
    # Belirli bir işlem çifti için detaylı analiz sayfası
    # Örnek: /pair/BTC/USDT/ gibi URL'ler için
    re_path(r'^pair/(?P<pair>[\w\/-]+)/$', views.pair_detail, name='pair_detail'),
]