from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PaymentResult:
    success: bool
    provider_reference: str
    checkout_url: str | None = None
    raw_response: dict | None = None


@dataclass
class PaymentIntentRequest:
    amount: int  # smallest currency unit (e.g. kobo/cents)
    currency: str
    reference: str  # your internal booking/payment reference
    customer_email: str
    metadata: dict


class PaymentGatewayInterface(ABC):
    """Every payment provider (Stripe, Paystack, Flutterwave...) implements this."""

    @abstractmethod
    def create_payment(self, request: PaymentIntentRequest) -> PaymentResult:
        ...

    @abstractmethod
    def verify_payment(self, provider_reference: str) -> PaymentResult:
        ...

    @abstractmethod
    def parse_webhook_event(self, payload: bytes, headers: dict) -> dict:
        """Validate signature and return a normalized event dict:
        {"type": "payment.succeeded" | "payment.failed", "reference": ..., "raw": ...}
        """
        ...