import hashlib
import hmac

from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Delivery, DeliveryEvent
from .serializers import WebhookPayloadSerializer


def _verify_signature(request) -> bool:
    """
    Verify the HMAC-SHA256 signature attached to the incoming webhook request.

    The courier partner signs the raw request body using the shared secret
    configured in settings.COURIER_WEBHOOK_SECRET and sends the resulting
    hex digest in the X-Courier-Signature header.

    Returns True if the signature is valid, False otherwise.
    """
    provided_signature = request.headers.get('X-Courier-Signature')
    if not provided_signature:
        return False

    expected_signature = hmac.new(
        settings.COURIER_WEBHOOK_SECRET.encode(),
        request.body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(provided_signature, expected_signature)


class CourierWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        if not _verify_signature(request):
            return Response(
                {'detail': 'Invalid signature'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = WebhookPayloadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        tracking_number = data['tracking_number']
        new_status = data['status']
        occurred_at = data['occurred_at']
        external_event_id = data['external_event_id']
        location = data.get('location', '')
        note = data.get('note', '')

        with transaction.atomic():
            try:
                delivery = Delivery.objects.select_for_update().get(
                    tracking_number=tracking_number,
                )
            except Delivery.DoesNotExist:
                return Response(
                    {'detail': 'Delivery not found.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if DeliveryEvent.objects.filter(external_event_id=external_event_id).exists():
                return Response({'detail': 'OK'}, status=status.HTTP_200_OK)

            if delivery.last_event_at is not None and occurred_at <= delivery.last_event_at:
                return Response({'detail': 'OK'}, status=status.HTTP_200_OK)

            try:
                DeliveryEvent.objects.create(
                    delivery=delivery,
                    external_event_id=external_event_id,
                    status=new_status,
                    occurred_at=occurred_at,
                    location=location,
                    note=note,
                )
            except IntegrityError:
                return Response({'detail': 'OK'}, status=status.HTTP_200_OK)

            delivery.status = new_status
            delivery.last_event_at = occurred_at
            delivery.save(update_fields=['status', 'last_event_at', 'updated_at'])

        return Response({'detail': 'OK'}, status=status.HTTP_200_OK)
