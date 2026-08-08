# payments/views.py

from decimal import Decimal
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import stripe as stripe_errors  # for catching stripe.error.StripeError

from .services.connect_service import create_onboarding_link, get_or_create_account, refresh_account_status
from .services.payment_service import create_booking_payment_intent, request_payout
from bookings.models import Booking  # adjust import path


class PaymentsViewSet(viewsets.GenericViewSet):
    """Groups all Stripe-facing endpoints: tutor onboarding, student
    checkout, and tutor withdrawals. No model queryset backs this directly,
    each action reaches into the service layer instead."""
    permission_classes = [IsAuthenticated]

    @action(methods=['POST'], detail=False, url_path='onboard')
    def onboard(self, request):
        """Returns a fresh Stripe onboarding URL for the current tutor."""
        profile = request.user.tutor_profile
        url = create_onboarding_link(profile)
        return Response({'onboarding_url': url})

    @action(methods=['GET'], detail=False, url_path='onboard/status')
    def onboard_status(self, request):
        """Current onboarding status, refreshed from Stripe."""
        profile = request.user.tutor_profile
        account_record = get_or_create_account(profile)
        account_record = refresh_account_status(account_record)
        return Response({
            'charges_enabled': account_record.charges_enabled,
            'payouts_enabled': account_record.payouts_enabled,
            'details_submitted': account_record.details_submitted,
            'onboarding_complete': account_record.onboarding_complete,
        })

    @action(methods=['POST'], detail=False, url_path='checkout')
    def checkout(self, request):
        """POST {"booking_id": 123} -> {"client_secret": "..."}
        Called by the student right before showing the Stripe payment element."""
        booking_id = request.data.get('booking_id')
        try:
            booking = Booking.objects.get(pk=booking_id, student=request.user)
        except Booking.DoesNotExist:
            return Response({'detail': 'Booking not found.'}, status=404)

        client_secret = create_booking_payment_intent(booking)
        return Response({'client_secret': client_secret})

    @action(methods=['POST'], detail=False, url_path='withdraw')
    def withdraw(self, request):
        """POST {"amount": "250.00"} -> triggers a Stripe payout for the tutor.
        Validate against your wallet_summary's available_balance before calling
        this, both client-side and here, to avoid overdrawing."""
        profile = request.user.tutor_profile
        amount = Decimal(str(request.data.get('amount', '0')))
        if amount <= 0:
            return Response({'detail': 'Amount must be positive.'}, status=400)

        try:
            payout = request_payout(profile, amount)
        except stripe_errors.error.StripeError as exc:
            return Response({'detail': str(exc)}, status=400)

        return Response({'payout_id': payout.id, 'status': payout.status})