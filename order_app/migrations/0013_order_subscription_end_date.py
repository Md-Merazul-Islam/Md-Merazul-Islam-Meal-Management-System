# Generated by Django 5.1.7 on 2025-05-27 08:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order_app', '0012_order_subscription_duration_deliveryproduct_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='subscription_end_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
