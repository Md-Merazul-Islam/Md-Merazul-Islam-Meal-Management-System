# Generated by Django 5.1.7 on 2025-06-02 11:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('weekly_order_manage', '0005_alter_order_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='deliveryday',
            name='is_billed',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
