# payments/services/stripe_client.py
#
# Central place that configures the stripe SDK. Every other service
# module imports `stripe` from here rather than importing the package
# directly, so there's one spot to change if the API version changes.

import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = '2024-06-20'  # pin a version, bump deliberately

__all__ = ['stripe']