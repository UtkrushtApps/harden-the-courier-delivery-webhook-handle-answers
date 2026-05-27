from django.urls import path

from .views import CourierWebhookView

urlpatterns = [
    path('webhooks/courier/status/', CourierWebhookView.as_view(), name='courier-webhook'),
]
