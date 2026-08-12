from django.apps import AppConfig
from django.dispatch import receiver
from payment.signals import payment_succeeded

class BookingsConfig(AppConfig):
    name = 'bookings'


@receiver(payment_succeeded)
def confirm_booking_on_payment(sender, booking, **kwargs):
    booking.status = booking.Status.PAYMENT_CONFIRMED
    booking.save(update_fields=["status"])