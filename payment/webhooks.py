# payments/webhooks.py
#
# Public endpoint Stripe calls directly, not authenticated the normal way.
# Signature verification is what proves the request actually came from Stripe.

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .services.stripe_client import stripe
from .services.connect_service import refresh_account_status
from .services.payment_service import (
    mark_earning_cleared,
    mark_earning_failed,
    mark_payout_completed,
    mark_payout_failed,
)
from .models import TutorStripeAccount

import logging

logger = logging.getLogger('payments')


@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        logger.warning('Invalid Stripe webhook signature')
        return Response(status=400)

    event_type = event['type']
    data = event['data']['object']

    if event_type == 'payment_intent.succeeded':
        mark_earning_cleared(data['id'])

    elif event_type == 'payment_intent.payment_failed':
        mark_earning_failed(data['id'])

    elif event_type == 'payout.paid':
        mark_payout_completed(data['id'])

    elif event_type == 'payout.failed':
        mark_payout_failed(data['id'])

    elif event_type == 'account.updated':
        account_record = TutorStripeAccount.objects.filter(
            stripe_account_id=data['id']
        ).first()
        if account_record:
            refresh_account_status(account_record)

    else:
        logger.info('Unhandled Stripe event type: %s', event_type)

    return Response(status=200)