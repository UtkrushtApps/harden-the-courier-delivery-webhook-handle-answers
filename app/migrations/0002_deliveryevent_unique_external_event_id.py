from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deliveryevent',
            name='external_event_id',
            field=models.CharField(max_length=128, unique=True),
        ),
    ]
