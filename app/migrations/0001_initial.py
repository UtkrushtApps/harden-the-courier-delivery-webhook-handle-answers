from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Delivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tracking_number', models.CharField(max_length=64, unique=True)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('picked_up', 'Picked Up'),
                        ('in_transit', 'In Transit'),
                        ('out_for_delivery', 'Out for Delivery'),
                        ('delivered', 'Delivered'),
                        ('failed', 'Failed'),
                    ],
                    default='pending',
                    max_length=32,
                )),
                ('last_event_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'delivery_delivery'},
        ),
        migrations.CreateModel(
            name='DeliveryEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delivery', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='events',
                    to='app.delivery',
                )),
                ('external_event_id', models.CharField(max_length=128)),
                ('status', models.CharField(max_length=32)),
                ('occurred_at', models.DateTimeField()),
                ('location', models.CharField(blank=True, default='', max_length=255)),
                ('note', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'delivery_deliveryevent'},
        ),
    ]
