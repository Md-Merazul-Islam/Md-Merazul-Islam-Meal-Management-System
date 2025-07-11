# Generated by Django 5.1.7 on 2025-04-21 11:44

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('areas', '0002_deliverymanarea_review'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='deliverymanarea',
            name='delivery_man_name',
        ),
        migrations.RemoveField(
            model_name='deliverymanarea',
            name='phone_number',
        ),
        migrations.RemoveField(
            model_name='deliverymanarea',
            name='photo',
        ),
        migrations.AddField(
            model_name='deliverymanarea',
            name='delivery_man',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
