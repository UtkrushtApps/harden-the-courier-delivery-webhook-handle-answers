from django.db import models


class Delivery(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]

    tracking_number = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='pending')
    last_event_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'delivery_delivery'

    def __str__(self):
        return f'Delivery({self.tracking_number}, {self.status})'


class DeliveryEvent(models.Model):
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name='events',
    )
    external_event_id = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=32)
    occurred_at = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True, default='')
    note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'delivery_deliveryevent'

    def __str__(self):
        return f'DeliveryEvent({self.external_event_id}, {self.status})'
