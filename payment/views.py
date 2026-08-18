from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from tutors.permissions import IsTutor
from payment.connect_service import ConnectService
from payment.withdrawal_service import WithdrawalService
from bookings.models import Booking
from .services import PaymentService
from bookings.models import Booking
from payment.services import PaymentService
import logging
from django.conf import settings
from wallets.serializers import WithdrawalRequestSerializer


logger = logging.getLogger("stripe")

class PaymentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(
        detail=False,
        methods=["get"],
        url_path=r"initiate/(?P<booking_id>[^/.]+)/booking"
    )
    def initiate(self, request, booking_id=None):
        try:
            booking = Booking.objects.get(
                id=booking_id,
                student=request.user
            )
        except Booking.DoesNotExist:
            return Response(
                {"detail": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        payment = PaymentService().initiate_payment(booking)
        return Response(
            {
                "checkout_url": payment.checkout_url
            },
            status=status.HTTP_201_CREATED
        )

    @action(
            detail=False,
            methods=["get"],
            url_path=r"confirm/(?P<booking_id>[^/.]+)/"
        )
    def confirm(self, request, booking_id=None):
        try:
            booking = Booking.objects.get(
                id=booking_id,
                student=request.user
            )
            if booking.status == 'PAYMENT_CONFIRMED':
                return Response({"confirmed" : True},
                        status=status.HTTP_200_OK)
            else:
                return Response({"confirmed" : False},
                        status=status.HTTP_200_OK)
        except Booking.DoesNotExist:
            return Response(
                {"detail": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        event_id = request.headers.get("Stripe-Event-Id", "unknown")
        logger.info("Stripe webhook received. event_id=%s", event_id)

        try:
            PaymentService(gateway_name="stripe").handle_webhook_event(
                payload=request.body,
                headers=request.headers,
            )
            logger.info(request.body)

        except Exception:
            logger.exception(
                "Stripe webhook processing failed. event_id=%s", event_id
            )
            return Response(
                {"detail": "Webhook processing failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info("Stripe webhook processed successfully. event_id=%s", event_id)
        return Response(status=status.HTTP_200_OK)





# payment/views.py
class ConnectViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsTutor]

    @action(detail=False, methods=["get"], url_path="onboarding-link")
    def onboarding_link(self, request):
        tutor_profile = request.user.tutor_profile
        url = ConnectService().create_onboarding_link(
            tutor_profile,
            refresh_url=settings.STRIPE_CONNECT_REFRESH_URL,
            return_url=settings.STRIPE_CONNECT_RETURN_URL,
        )
        return Response({"onboarding_url": url})

    @action(detail=False, methods=["post"], url_path="withdraw")
    def withdraw(self, request):
        serializer = WithdrawalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        withdrawal = WithdrawalService().request_withdrawal(
            tutor_profile=request.user.tutor_profile,
            amount=serializer.validated_data["amount"],
        )
        return Response(
            {
                "id": withdrawal.id,
                "amount": withdrawal.amount,
                "status": withdrawal.status,
                "stripe_transfer_id": withdrawal.stripe_transfer_id,
            },
            status=status.HTTP_201_CREATED,
        )



