from django.dispatch import receiver

from .signals import payment_succeeded
from services.email_service import notify_payment_success


@receiver(payment_succeeded)
def payment_succeeded_handler(sender, payment, booking, **kwargs):
    notify_payment_success(booking, payment)
    