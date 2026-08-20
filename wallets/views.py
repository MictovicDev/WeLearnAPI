# wallets/views.py
from decimal import Decimal

from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from wallets.models import Wallet, Withdrawal, WalletTransaction
from wallets.serializers import WalletSummarySerializer, WalletTransactionSerializer, WithdrawalSerializer




class WalletViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        pending_clearance = WalletTransaction.objects.filter(
            wallet=wallet,
            type=WalletTransaction.Type.CREDIT,
            status=WalletTransaction.Status.PENDING,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        total_earned_lifetime = WalletTransaction.objects.filter(
            wallet=wallet,
            type=WalletTransaction.Type.CREDIT,
            status=WalletTransaction.Status.COMPLETED,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        data = {
            "available_balance": wallet.balance,
            "pending_clearance": pending_clearance,
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
            withdrawal = serializer.save()
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(withdrawal).data, status=status.HTTP_201_CREATED)


class AdminWithdrawalViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin dashboard queue.
    GET  /admin/withdrawals/                 → list all (optionally ?status=pending)
    GET  /admin/withdrawals/{id}/             → retrieve
    POST /admin/withdrawals/{id}/approve/     → approve
    POST /admin/withdrawals/{id}/reject/      → reject (requires "reason")
    POST /admin/withdrawals/{id}/mark_paid/   → mark as paid out
    """
    serializer_class = WithdrawalAdminSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Withdrawal.objects.select_related("wallet__user").all()

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        withdrawal = self.get_object()
        try:
            withdrawal.approve(
                admin_user=request.user,
                payout_reference=request.data.get("payout_reference"),
                note=request.data.get("note"),
            )
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(withdrawal).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        withdrawal = self.get_object()
        reason = request.data.get("reason", "")
        if not reason:
            return Response({"detail": "A rejection reason is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            withdrawal.reject(admin_user=request.user, reason=reason)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(withdrawal).data)

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        withdrawal = self.get_object()
        try:
            withdrawal.mark_paid(payout_reference=request.data.get("payout_reference"))
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(withdrawal).data)