from django.dispatch import receiver

from .signals import payment_succeeded
from wallets.models import WalletTransaction
from services.email_service import notify_payment_success


@receiver(payment_succeeded)
def payment_succeeded_handler(sender, payment, booking, **kwargs):
    wallet = booking.tutor_profile.user.wallet

    WalletTransaction.objects.create(
        wallet=wallet,
        type="credit",
        status="completed",
        amount=payment.amount,
        reference=payment.reference,
        description= f"Payment from{booking.id}"
    )
    notify_payment_success(booking, payment)
    