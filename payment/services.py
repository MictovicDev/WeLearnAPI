from django.db import transaction

from bookings.models import Booking
from payment.factory import PaymentGatewayFactory
from payment.interfaces import PaymentIntentRequest
from payment.models import Payment
from payment.signals import payment_succeeded
from rest_framework.exceptions import ValidationError
import logging
from services.email_service import notify_payment_success
from tutors.models import TutorProfile

logger = logging.getLogger("stripe")

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

        logger.info(
            "Webhook event parsed. type=%s reference=%s provider_reference=%s",
            event["type"],
            event["reference"],
            event["provider_reference"],
        )

        if event["type"] != "payment.succeeded":
            logger.info(
                "Ignoring non-payment-succeeded event. type=%s",
                event["type"],
            )
            return

        

        if not event["reference"]:
            logger.warning(
                "payment.succeeded event missing reference/booking_id. "
                "provider_reference=%s",
                event["provider_reference"],
            )
            return

        try:
            payment = (
                Payment.objects
                .select_for_update()
                .select_related("booking")
                .get(booking_id=event["reference"])
            )
        except Payment.DoesNotExist:
            logger.warning(
                "No Payment found for booking_id from webhook. "
                "booking_id=%s provider_reference=%s",
                event["reference"],
                event["provider_reference"],
            )
            return

        # Idempotency protection
        if payment.status == Payment.Status.SUCCEEDED:
            logger.info(
                "Payment already marked SUCCEEDED, skipping. "
                "payment_id=%s booking_id=%s",
                payment.id,
                event["reference"],
            )
            return

        booking = payment.booking

        # Lock wallet to prevent concurrent balance updates
        wallet = (
            booking.tutor_profile.user.wallet.__class__
            .objects
            .select_for_update()
            .get(pk=booking.tutor_profile.user.wallet.pk)
        )

        payment.status = Payment.Status.SUCCEEDED
        payment.provider_reference = event["provider_reference"]


        if event["type"] == "account.updated":
            TutorProfile.objects.filter(
                stripe_connect_account_id=event["provider_reference"]
            ).update(payouts_enabled=event["payouts_enabled"])
            logger.info(
                "Tutor payouts_enabled updated. account_id=%s payouts_enabled=%s",
                event["provider_reference"], event["payouts_enabled"],
            )
            return

        payment.save(
            update_fields=[
                "status",
                "provider_reference",
                "updated_at",
            ]
        )

        wallet.balance += payment.amount
        wallet.save(update_fields=["balance"])

        transaction.on_commit(
            lambda: payment_succeeded.send(
                sender=self.__class__,
                payment=payment,
                booking=booking,
            )
        )

        logger.info(
            "Payment marked SUCCEEDED and wallet credited. "
            "payment_id=%s booking_id=%s provider_reference=%s amount=%s",
            payment.id,
            booking.id,
            event["provider_reference"],
            payment.amount,
        )
