# wallets/views.py
from decimal import Decimal

from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from wallets.models import Wallet, Withdrawal, WalletTransaction
from wallets.serializers import WalletSummarySerializer, WalletTransactionSerializer, WithdrawalSerializer, CompletedSessionSerializer




class WalletViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        withdrawable_amount = Booking.objects.filter(
            tutor_profile__user=request.user,
            status=Booking.Status.COMPLETED,
            tutor_completed=True,
            student_acknowledged=True,
        ).aggregate(
            total=Sum("total_amount")
        )["total"] or Decimal("0.00")

        total_earned_lifetime = WalletTransaction.objects.filter(
            wallet=wallet,
            type=WalletTransaction.Type.CREDIT,
            status=WalletTransaction.Status.COMPLETED,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        data = {
            "available_balance": wallet.balance,
            "withdrawable_balance": withdrawable_amount,
            "total_earned_lifetime": total_earned_lifetime,
            "currency": wallet.currency,
        }
        serializer = WalletSummarySerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def transactions(self, request):
        filter_param = request.query_params.get("filter", "all")

        if filter_param == "payouts":
            withdrawals = Withdrawal.objects.filter(
                tutor_profile=request.user.tutor_profile
            ).order_by("-created_at")
            serializer = WithdrawalSerializer(withdrawals, many=True)
            return Response(serializer.data)

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        qs = WalletTransaction.objects.filter(wallet=wallet)

        if filter_param == "earnings":
            qs = qs.filter(type=WalletTransaction.Type.CREDIT)
        # "all" still shows raw WalletTransaction rows (credits + any remaining debit rows)

        serializer = WalletTransactionSerializer(qs, many=True)
        return Response(serializer.data)




from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from bookings.models import Booking  # adjust import path to your app


class CompletedSessionsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class CompletedSessionListView(generics.ListAPIView):
    """
    GET /wallet/completed-sessions/
    Sessions where both tutor and student have confirmed completion.
    """
    serializer_class = CompletedSessionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CompletedSessionsPagination

    def get_queryset(self):
        return Booking.objects.filter(
            tutor_profile__user=self.request.user,
            status=Booking.Status.COMPLETED,
            tutor_completed=True,
            student_acknowledged=True,
        ).order_by("-id")


from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError

from .models import Withdrawal
from .serializers import WithdrawalRequestSerializer, WithdrawalAdminSerializer


class WithdrawalViewSet(viewsets.GenericViewSet, viewsets.mixins.CreateModelMixin, viewsets.mixins.ListModelMixin, viewsets.mixins.RetrieveModelMixin):
    """
    User-facing wallet withdrawals.
    POST /withdrawals/        → request a withdrawal
    GET  /withdrawals/        → list my withdrawals
    GET  /withdrawals/{id}/   → retrieve one of mine
    """
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Withdrawal.objects.filter(wallet__user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(
                    user=request.user
                )

                amount = serializer.validated_data["amount"]

                if amount > wallet.withdrawable_balance:
                    raise ValidationError(
                        "Insufficient withdrawable balance."
                    )

                # Deduct immediately
                wallet.withdrawable_balance -= amount
                wallet.save(update_fields=["withdrawable_balance"])

                # Create withdrawal
                withdrawal = serializer.save(wallet=wallet)

        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            self.get_serializer(withdrawal).data,
            status=status.HTTP_201_CREATED
        )

