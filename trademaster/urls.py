from django.contrib import admin
from django.urls import path, re_path  # re_path eklemeyi unutmayın
from core import views  

urlpatterns = [
    path('admin/', admin.site.urls),
    path('prices/', views.trading_pairs, name='trading_pairs'),
    path('prices/json/', views.get_prices_json, name='get_prices_json'),
    re_path(r'^pair/(?P<pair>[\w\/-]+)/$', views.pair_detail, name='pair_detail'),
]