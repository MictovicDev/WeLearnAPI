# payments/services/payment_service.py
#
# Two flows live here:
#   1. Student pays for a booking -> destination charge that credits the
#      tutor's connected account directly, minus a platform fee.
#   2. Tutor withdraws their available balance -> a Stripe Payout on their
#      connected account.

from decimal import Decimal
from django.conf import settings
from .stripe_client import stripe
from ..models import Transaction

# e.g. 0.15 for a 15% platform cut. Keep as a setting so it's adjustable
# without a code change.
PLATFORM_FEE_PERCENT = Decimal(str(settings.STRIPE_APPLICATION_FEE_PERCENT))


def _to_cents(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value())


def create_booking_payment_intent(booking):
    """Call when a student is ready to pay for a session. Returns the
    client_secret the frontend needs to confirm payment with Stripe.js.

    Assumes `booking.tutor.tutor_profile` resolves to the TutorProfile and
    `booking.price` holds the session amount, adjust field names to match
    your Booking model.
    """
    tutor_profile = booking.tutor  # adjust attribute name if different
    stripe_account = tutor_profile.stripe_account  # TutorStripeAccount

    amount = Decimal(booking.price)
    fee_amount = (amount * PLATFORM_FEE_PERCENT).quantize(Decimal('0.01'))

    payment_intent = stripe.PaymentIntent.create(
        amount=_to_cents(amount),
        currency='usd',  # adjust to your currency
        transfer_data={'destination': stripe_account.stripe_account_id},
        application_fee_amount=_to_cents(fee_amount),
        metadata={'booking_id': str(booking.id), 'tutor_id': str(tutor_profile.id)},
    )

    Transaction.objects.create(
        tutor=tutor_profile,
        booking=booking,
        transaction_type=Transaction.TransactionType.EARNING,
        status=Transaction.Status.PENDING,
        amount=amount - fee_amount,
        description=f'Session with {getattr(booking, "student_name", booking.student)}',
        stripe_payment_intent_id=payment_intent.id,
    )
    return payment_intent.client_secret


def mark_earning_cleared(payment_intent_id):
    """Call from the payment_intent.succeeded webhook."""
    Transaction.objects.filter(
        stripe_payment_intent_id=payment_intent_id,
        transaction_type=Transaction.TransactionType.EARNING,
    ).update(status=Transaction.Status.CLEARED)


def mark_earning_failed(payment_intent_id):
    """Call from the payment_intent.payment_failed webhook."""
    Transaction.objects.filter(
        stripe_payment_intent_id=payment_intent_id,
        transaction_type=Transaction.TransactionType.EARNING,
    ).update(status=Transaction.Status.FAILED)


def request_payout(tutor_profile, amount: Decimal):
    """Tutor taps 'Withdraw Funds'. Pays out from their Stripe Connect
    balance to whatever external account (bank/debit card) they added
    during onboarding. Raises stripe.error.StripeError on failure, let
    the view catch and surface it."""
    stripe_account = tutor_profile.stripe_account

    payout = stripe.Payout.create(
        amount=_to_cents(amount),
        currency='usd',
        stripe_account=stripe_account.stripe_account_id,
    )

    Transaction.objects.create(
        tutor=tutor_profile,
        transaction_type=Transaction.TransactionType.PAYOUT,
        status=Transaction.Status.PENDING,
        amount=amount,
        description='Withdrawal to bank account',
        stripe_payout_id=payout.id,
    )
    return payout


def mark_payout_completed(payout_id):
    """Call from the payout.paid webhook."""
    Transaction.objects.filter(stripe_payout_id=payout_id).update(
        status=Transaction.Status.COMPLETED
    )


def mark_payout_failed(payout_id):
    """Call from the payout.failed webhook."""
    Transaction.objects.filter(stripe_payout_id=payout_id).update(
        status=Transaction.Status.FAILED
    )