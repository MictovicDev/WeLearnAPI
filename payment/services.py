from django.db import transaction

from bookings.models import Booking
from payment.factory import PaymentGatewayFactory
from payment.interfaces import PaymentIntentRequest
from payment.models import Payment
from payment.signals import payment_succeeded
from rest_framework.exceptions import ValidationError

class PaymentService:
    def __init__(self, gateway_name: str | None = None):
        self.gateway = PaymentGatewayFactory.get_gateway(gateway_name)

    def initiate_payment(self, booking: Booking) -> Payment:
        if booking.status == Booking.Status.PAYMENT_CONFIRMED:
            raise ValidationError("Booking has already been paid for")
        if booking.status == Booking.Status.COMPLETED:
            raise ValidationError("Booking completed.")
        if booking.status == Booking.Status.CANCELLED:
            raise ValidationError("Booking has been cancelled by Tutor.")
        if booking.status == Booking.Status.DECLINED:
            raise ValidationError("Booking has been declined by Tutor.")
        if booking.status == Booking.Status.PENDING:
            raise ValidationError("Booking is still pending, wait for approval, before payment")
        
        request = PaymentIntentRequest(
            amount=int(booking.total_amount * 100),
            reference=str(booking.id),
            currency='USD',
            customer_email=booking.student.email,
            metadata={"booking_id": str(booking.id)},
        )
        result = self.gateway.create_payment(request)

        payment, _ = Payment.objects.update_or_create(
            booking=booking,
            defaults={
                "amount": request.amount,
                "currency": request.currency,
                "provider_reference": result.provider_reference,
                "status": Payment.Status.PENDING,
            },
        )
        payment.checkout_url = result.checkout_url  # not persisted, just returned to caller
        return payment

    @transaction.atomic
    def handle_webhook_event(self, payload: bytes, headers: dict):
        event = self.gateway.parse_webhook_event(payload, headers)
        if event["type"] != "payment.succeeded":
            return

        try:
            payment = Payment.objects.select_for_update().select_related("booking").get(
                booking_id=event["reference"]
            )
        except Payment.DoesNotExist:
            return

        if payment.status == Payment.Status.SUCCEEDED:
            return  # already processed, do nothing further

        payment.status = Payment.Status.SUCCEEDED
        payment.provider_reference = event["provider_reference"]
        payment.save(update_fields=["status", "provider_reference", "updated_at"])

        payment_succeeded.send(sender=self.__class__, booking=payment.booking)