# payments/services/connect_service.py
#
# Handles Stripe Connect Express account creation and onboarding for tutors.

from django.conf import settings
from .stripe_client import stripe
from ..models import TutorStripeAccount


def get_or_create_account(tutor):
    """Returns the tutor's TutorStripeAccount, creating the Stripe Express
    account on first call."""
    account_record = TutorStripeAccount.objects.filter(tutor=tutor).first()
    if account_record:
        return account_record

    stripe_account = stripe.Account.create(
        type='express',
        country='NG',  # adjust to your primary market, or make this a param
        email=tutor.user.email,
        capabilities={
            'card_payments': {'requested': True},
            'transfers': {'requested': True},
        },
        business_type='individual',
    )
    account_record = TutorStripeAccount.objects.create(
        tutor=tutor,
        stripe_account_id=stripe_account.id,
        charges_enabled=stripe_account.charges_enabled,
        payouts_enabled=stripe_account.payouts_enabled,
        details_submitted=stripe_account.details_submitted,
    )
    return account_record


def create_onboarding_link(tutor):
    """Returns a one-time URL the tutor visits to complete Stripe onboarding
    (identity, bank details). Link expires after a few minutes, generate
    fresh each time the frontend asks for it."""
    account_record = get_or_create_account(tutor)
    account_link = stripe.AccountLink.create(
        account=account_record.stripe_account_id,
        refresh_url=settings.STRIPE_ONBOARDING_REFRESH_URL,
        return_url=settings.STRIPE_ONBOARDING_RETURN_URL,
        type='account_onboarding',
    )
    return account_link.url


def refresh_account_status(account_record):
    """Pulls latest charges_enabled/payouts_enabled/details_submitted from
    Stripe and syncs them locally. Call this from the return_url view and
    from the account.updated webhook."""
    stripe_account = stripe.Account.retrieve(account_record.stripe_account_id)
    account_record.charges_enabled = stripe_account.charges_enabled
    account_record.payouts_enabled = stripe_account.payouts_enabled
    account_record.details_submitted = stripe_account.details_submitted
    account_record.save(update_fields=['charges_enabled', 'payouts_enabled', 'details_submitted', 'updated_at'])
    return account_record