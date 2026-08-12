# wallets/views.py
from decimal import Decimal

from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from wallets.models import Wallet, WalletTransaction
from wallets.serializers import WalletSummarySerializer


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