# wallets/serialize
from rest_framework import serializers
from wallets.models import WalletTransaction, Withdrawal
from decimal import Decimal

class WalletTransactionSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="description")
    subtitle = serializers.SerializerMethodField()
    signed_amount = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = WalletTransaction
        fields = ["id", "type", "title", "subtitle", "signed_amount", "status_label", "created_at"]

    def get_subtitle(self, obj):
        return obj.metadata.get("subtitle") or obj.metadata.get("destination", "")

    def get_signed_amount(self, obj):
        sign = "+" if obj.type == WalletTransaction.Type.CREDIT else "-"
        return f"{sign}${obj.amount:.2f}"

    def get_status_label(self, obj):
        if obj.status == WalletTransaction.Status.PENDING:
            return "Pending"
        if obj.type == WalletTransaction.Type.CREDIT:
            return "Cleared"
        return "Completed"


class WalletSummarySerializer(serializers.Serializer):
    available_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_clearance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_earned_lifetime = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()


# payment/serializers.py
class WithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdrawal
        fields = ["id", "amount", "status", "stripe_transfer_id", "created_at"]


# payment/serializers.py
class WithdrawalRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))