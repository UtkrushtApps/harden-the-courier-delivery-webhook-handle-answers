# Solution Steps

1. Add a database-level uniqueness guarantee for webhook idempotency by changing `DeliveryEvent.external_event_id` to `unique=True` in `app/models.py`, then create a new migration file named `app/migrations/0002_deliveryevent_unique_external_event_id.py` with an `AlterField` operation.

2. Implement HMAC verification in `app/views.py`: read the raw request body from `request.body`, compute `hmac.new(settings.COURIER_WEBHOOK_SECRET.encode(), request.body, hashlib.sha256).hexdigest()`, read the `X-Courier-Signature` header, and compare with `hmac.compare_digest`. Return `False` when the header is missing or invalid.

3. In `CourierWebhookView.post`, keep signature verification as the very first guard so forged requests are rejected with `401 {"detail": "Invalid signature"}` before any database read or write occurs.

4. Move delivery processing into `transaction.atomic()` and fetch the delivery row with `select_for_update()` using the incoming `tracking_number`. If the delivery does not exist, return the existing 404 response.

5. Inside the transaction, implement idempotency by checking whether a `DeliveryEvent` with the same `external_event_id` already exists. If it does, return HTTP 200 with the existing success body and do not update the delivery or insert another event.

6. Still inside the transaction, enforce monotonic ordering by comparing the incoming `occurred_at` to `delivery.last_event_at`. If `last_event_at` exists and the incoming timestamp is older than or equal to it, return HTTP 200 and discard the event without changing delivery state.

7. Create the `DeliveryEvent` inside the atomic block before updating the delivery, and catch `IntegrityError` as a final race-safe fallback for duplicate `external_event_id` inserts. On that integrity error, return HTTP 200 without re-processing.

8. If the event is new and newer than the current delivery state, update `delivery.status` and `delivery.last_event_at`, save the row, and return the unchanged success payload `{"detail": "OK"}`.

9. Expand `app/tests.py` to cover the four missing scenarios: invalid signature returns 401 with no data changes, missing signature returns 401 with no data changes, duplicate webhook returns 200 twice but creates only one `DeliveryEvent`, and stale out-of-order webhook returns 200 without regressing `Delivery.status` or `last_event_at`.

10. Run migrations and verify everything with `python manage.py test app` so all five tests pass: the existing smoke test plus the four new behavior tests.

