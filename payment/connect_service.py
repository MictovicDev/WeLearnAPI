# payment/connect_service.py
import stripe
from django.conf import settings
import logging

logger = logging.getLogger("stripe")


class ConnectService:
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_connected_account(self, tutor_profile):
        account = stripe.Account.create(
            type="express",
            email=tutor_profile.user.email,
            capabilities={"transfers": {"requested": True}},
        )
        tutor_profile.stripe_connect_account_id = account.id
        tutor_profile.save(update_fields=["stripe_connect_account_id"])
        logger.info(
            "Stripe connected account created. tutor_profile_id=%s account_id=%s",
            tutor_profile.id, account.id,
        )
        return account

    def create_onboarding_link(self, tutor_profile, refresh_url, return_url):
        if not tutor_profile.stripe_connect_account_id:
            self.create_connected_account(tutor_profile)

        link = stripe.AccountLink.create(
            account=tutor_profile.stripe_connect_account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
        )
        return link.url