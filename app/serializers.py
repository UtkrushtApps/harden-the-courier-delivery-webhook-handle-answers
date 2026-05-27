from rest_framework import serializers


class WebhookPayloadSerializer(serializers.Serializer):
    tracking_number = serializers.CharField(max_length=64)
    status = serializers.CharField(max_length=32)
    occurred_at = serializers.DateTimeField()
    external_event_id = serializers.CharField(max_length=128)
    location = serializers.CharField(max_length=255, required=False, default='')
    note = serializers.CharField(required=False, default='', allow_blank=True)
