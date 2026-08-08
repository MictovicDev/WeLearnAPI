# payments/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentsViewSet
from .webhooks import stripe_webhook

router = DefaultRouter()
router.register('', PaymentsViewSet, basename='payments')

urlpatterns = [
    path('webhook/', stripe_webhook, name='stripe-webhook'),  # keep outside the router, no auth
    path('', include(router.urls)),
]

# Resulting endpoints (with the include below mounted at /api/payments/):
#   POST /api/payments/onboard/
#   GET  /api/payments/onboard/status/
#   POST /api/payments/checkout/
#   POST /api/payments/withdraw/
#   POST /api/payments/webhook/
#
# In your project's root urls.py:
# path('api/payments/', include('payments.urls')),