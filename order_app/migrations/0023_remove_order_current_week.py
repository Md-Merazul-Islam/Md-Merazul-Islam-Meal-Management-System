# Generated by Django 5.1.7 on 2025-05-31 09:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('order_app', '0022_order_current_week'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='current_week',
        ),
    ]
