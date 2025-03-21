# Generated by Django 4.2.20 on 2025-03-21 00:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_tradingpair_notification_threshold'),
    ]

    operations = [
        migrations.AddField(
            model_name='tradingpair',
            name='last_signal',
            field=models.CharField(blank=True, help_text="Son gönderilen sinyal: 'yükseliş' veya 'düşüş'", max_length=10, null=True),
        ),
    ]
