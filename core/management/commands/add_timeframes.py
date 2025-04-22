from django.core.management.base import BaseCommand
from core.models import TimeFrame

class Command(BaseCommand):
    help = 'Önceden tanımlı zaman dilimlerini veritabanına ekler'

    def handle(self, *args, **kwargs):
        timeframes = [
            {'name': '15m', 'description': '15 dakika'},
            {'name': '1h', 'description': '1 saat'},
            {'name': '4h', 'description': '4 saat'},
            {'name': '1d', 'description': '1 gün'},
            {'name': '1w', 'description': '1 hafta'},
            {'name': '1M', 'description': '1 ay'},
        ]

        for tf in timeframes:
            TimeFrame.objects.get_or_create(name=tf['name'], defaults={'description': tf['description']})

        self.stdout.write(self.style.SUCCESS('Zaman dilimleri başarıyla eklendi!'))