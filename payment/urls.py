# payments/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, StripeWebhookView

router = DefaultRouter()
router.register('payment', PaymentViewSet, basename='payments')


urlpatterns = [
    path('stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
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