# wallets/views.py
from decimal import Decimal

from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from wallets.models import Wallet, WalletTransaction
from wallets.serializers import WalletSummarySerializer, WalletTransactionSerializer


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
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        qs = WalletTransaction.objects.filter(wallet=wallet)

        filter_param = request.query_params.get("filter", "all")
        if filter_param == "earnings":
            qs = qs.filter(type=WalletTransaction.Type.CREDIT)
        elif filter_param == "payouts":
            qs = qs.filter(type=WalletTransaction.Type.DEBIT)

        serializer = WalletTransactionSerializer(qs, many=True)
        return Response(serializer.data)