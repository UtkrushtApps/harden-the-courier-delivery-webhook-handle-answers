import hashlib
import hmac
import json
from datetime import datetime, timezone

from django.test import TestCase

from .models import Delivery, DeliveryEvent

WEBHOOK_SECRET = 'supersecretkey123'
WEBHOOK_URL = '/api/webhooks/courier/status/'


def make_signature(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(
        secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()


def post_webhook(
    client,
    payload: dict,
    secret: str = WEBHOOK_SECRET,
    omit_signature: bool = False,
    bad_signature: bool = False,
):
    body = json.dumps(payload).encode()
    headers = {'content_type': 'application/json'}
    if omit_signature:
        pass
    elif bad_signature:
        headers['HTTP_X_COURIER_SIGNATURE'] = 'invalidsignaturevalue'
    else:
        headers['HTTP_X_COURIER_SIGNATURE'] = make_signature(body, secret)
    return client.post(WEBHOOK_URL, data=body, **headers)


class CourierWebhookSmokeTest(TestCase):
    """One passing baseline test — the happy path with a valid signed request."""

    def setUp(self):
        self.delivery = Delivery.objects.create(
            tracking_number='TRACK-001',
            status='pending',
        )

    def test_valid_webhook_updates_delivery_status(self):
        payload = {
            'tracking_number': 'TRACK-001',
            'status': 'picked_up',
            'occurred_at': '2024-06-01T10:00:00Z',
            'external_event_id': 'evt-smoke-001',
            'location': 'Warehouse A',
        }
        response = post_webhook(self.client, payload)
        self.assertEqual(response.status_code, 200)
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, 'picked_up')
        self.assertEqual(DeliveryEvent.objects.filter(delivery=self.delivery).count(), 1)


class CourierWebhookSignatureTest(TestCase):
    """
    Tests for HMAC signature verification.
    """

    def setUp(self):
        self.delivery = Delivery.objects.create(
            tracking_number='TRACK-SIG',
            status='pending',
        )
        self.payload = {
            'tracking_number': 'TRACK-SIG',
            'status': 'picked_up',
            'occurred_at': '2024-06-01T10:00:00Z',
            'external_event_id': 'evt-sig-001',
        }

    def test_invalid_signature_returns_401(self):
        response = post_webhook(self.client, self.payload, bad_signature=True)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {'detail': 'Invalid signature'})

        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, 'pending')
        self.assertIsNone(self.delivery.last_event_at)
        self.assertEqual(DeliveryEvent.objects.count(), 0)

    def test_missing_signature_returns_401(self):
        response = post_webhook(self.client, self.payload, omit_signature=True)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {'detail': 'Invalid signature'})

        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, 'pending')
        self.assertIsNone(self.delivery.last_event_at)
        self.assertEqual(DeliveryEvent.objects.count(), 0)


class CourierWebhookIdempotencyTest(TestCase):
    """
    Tests for duplicate event handling.
    """

    def setUp(self):
        self.delivery = Delivery.objects.create(
            tracking_number='TRACK-IDEM',
            status='pending',
        )
        self.payload = {
            'tracking_number': 'TRACK-IDEM',
            'status': 'in_transit',
            'occurred_at': '2024-06-01T12:00:00Z',
            'external_event_id': 'evt-idem-001',
        }

    def test_duplicate_event_does_not_create_second_row(self):
        first_response = post_webhook(self.client, self.payload)
        second_response = post_webhook(self.client, self.payload)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(first_response.json(), {'detail': 'OK'})
        self.assertEqual(second_response.json(), {'detail': 'OK'})

        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, 'in_transit')
        self.assertEqual(DeliveryEvent.objects.filter(external_event_id='evt-idem-001').count(), 1)
        self.assertEqual(DeliveryEvent.objects.filter(delivery=self.delivery).count(), 1)


class CourierWebhookStateTransitionTest(TestCase):
    """
    Tests for monotonic state transition enforcement.
    """

    def setUp(self):
        self.delivery = Delivery.objects.create(
            tracking_number='TRACK-STALE',
            status='delivered',
            last_event_at=datetime(2024, 6, 1, 16, 0, 0, tzinfo=timezone.utc),
        )

    def test_stale_event_does_not_regress_delivery_status(self):
        payload = {
            'tracking_number': 'TRACK-STALE',
            'status': 'picked_up',
            'occurred_at': '2024-06-01T15:00:00Z',
            'external_event_id': 'evt-stale-001',
            'location': 'Old scan point',
        }

        response = post_webhook(self.client, payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'detail': 'OK'})

        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, 'delivered')
        self.assertEqual(
            self.delivery.last_event_at,
            datetime(2024, 6, 1, 16, 0, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(DeliveryEvent.objects.count(), 0)
