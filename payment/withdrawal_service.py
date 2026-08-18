# payment/withdrawal_service.py
import stripe
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError
from wallets.models import Withdrawal
import logging

logger = logging.getLogger("stripe")


class WithdrawalService:
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    @transaction.atomic
    def request_withdrawal(self, tutor_profile, amount: Decimal) -> Withdrawal:
        if not tutor_profile.payouts_enabled:
            raise ValidationError("Tutor has not completed payout onboarding.")

        wallet = (
            tutor_profile.user.wallet.__class__
            .objects.select_for_update()
            .get(pk=tutor_profile.user.wallet.pk)
        )
        if wallet.balance < amount:
            raise ValidationError("Insufficient wallet balance.")

        transfer = stripe.Transfer.create(
            amount=int(amount * 100),
            currency="usd",
            destination=tutor_profile.stripe_connect_account_id,
            metadata={"tutor_profile_id": str(tutor_profile.id)},
        )

        wallet.balance -= amount
        wallet.save(update_fields=["balance"])

        withdrawal = Withdrawal.objects.create(
            tutor_profile=tutor_profile,
            amount=amount,
            stripe_transfer_id=transfer.id,
            status=Withdrawal.Status.PROCESSING,
        )
        logger.info(
            "Withdrawal transfer created. tutor_profile_id=%s amount=%s transfer_id=%s",
            tutor_profile.id, amount, transfer.id,
        )
        return withdrawal