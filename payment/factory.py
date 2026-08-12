from django.conf import settings
from payment.gateways.stripes_gateway import StripeGateway
from payment.interfaces import PaymentGatewayInterface

_GATEWAYS = {
    "stripe": StripeGateway,
    # "paystack": PaystackGateway,   # add later, nothing else changes
}


class PaymentGatewayFactory:
    @staticmethod
    def get_gateway(name: str | None = None) -> PaymentGatewayInterface:
        name = name or settings.DEFAULT_PAYMENT_GATEWAY
        gateway_cls = _GATEWAYS.get(name)
        if not gateway_cls:
            raise ValueError(f"Unsupported payment gateway: {name}")
        return gateway_cls()