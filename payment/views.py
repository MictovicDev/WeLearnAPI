from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from bookings.models import Booking
from .services import PaymentService
from bookings.models import Booking
from payment.services import PaymentService


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
        print('Entered')
        PaymentService(gateway_name="stripe").handle_webhook_event(
            payload=request.body,
            headers=request.headers,
        )
        return Response(status=status.HTTP_200_OK)