import stripe
from django.conf import settings
from payment.interfaces import PaymentGatewayInterface, PaymentIntentRequest, PaymentResult
from django.core.exceptions import ValidationError
import logging


logger = logging.getLogger("stripe")


class StripeGateway(PaymentGatewayInterface):
    """Adapts the Stripe SDK to our internal PaymentGatewayInterface."""

    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_payment(self, request: PaymentIntentRequest) -> PaymentResult:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": request.currency,
                    "unit_amount": request.amount,
                    "product_data": {"name": f"Tutoring session - {request.reference}"},
                },
                "quantity": 1,
            }],
            customer_email=request.customer_email,
            metadata={"reference": request.reference, **request.metadata},
            success_url=settings.PAYMENT_SUCCESS_URL,
            cancel_url=settings.PAYMENT_CANCEL_URL,
        )
        return PaymentResult(
            success=True,
            provider_reference=session.id,
            checkout_url=session.url,
            raw_response=session,
        )

    def verify_payment(self, provider_reference: str) -> PaymentResult:
        session = stripe.checkout.Session.retrieve(provider_reference)
        return PaymentResult(
            success=session.payment_status == "paid",
            provider_reference=session.id,
            raw_response=session,
        )

    def parse_webhook_event(self, payload: bytes, headers: dict) -> dict:
        try:
            event = stripe.Webhook.construct_event(
                payload,
                headers.get("Stripe-Signature"),
                settings.STRIPE_WEBHOOK_SECRET,
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            logger.warning("Stripe webhook signature verification failed.")
            raise

        obj = event["data"]["object"]

        try:
            provider_reference = obj["id"]
        except (KeyError, TypeError):
            provider_reference = None
            logger.warning(
                "Stripe event object missing 'id'. event_type=%s", event.get("type")
            )

        try:
            reference = obj["metadata"]["reference"]
        except (KeyError, TypeError):
            reference = None
            logger.warning(
                "Stripe event object missing metadata.reference. event_type=%s provider_reference=%s",
                event.get("type"), provider_reference,
            )

        if event["type"] == "checkout.session.completed":
            return {
                "type": "payment.succeeded",
                "reference": reference,
                "provider_reference": provider_reference,
            }

        return {
            "type": "payment.other",
            "reference": reference,
            "provider_reference": provider_reference,
        }