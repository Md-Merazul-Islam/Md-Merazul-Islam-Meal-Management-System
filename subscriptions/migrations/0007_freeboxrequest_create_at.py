
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0006_remove_box_country_remove_box_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='freeboxrequest',
            name='create_at',
            field=models.DateField(auto_now=True, null=True),
        ),
    ]
