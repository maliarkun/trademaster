# Generated by Django 4.2.20 on 2025-03-19 19:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='tradingpair',
            name='notification_threshold',
            field=models.IntegerField(default=51, help_text='Bildirim için yükselme ihtimali eşiği'),
        ),
    ]
