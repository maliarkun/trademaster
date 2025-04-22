from django.urls import path
from . import views

urlpatterns = [
    path('indicators/bollinger-bands/', views.bollinger_bands_page, name='bollinger_bands_page'),
]