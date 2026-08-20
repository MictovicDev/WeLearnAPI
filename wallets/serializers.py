# wallets/serialize
from rest_framework import serializers
from wallets.models import WalletTransaction, Withdrawal, Booking
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


# serializers.py
class CompletedSessionSerializer(serializers.ModelSerializer):
    class Meta:
            model = Booking
            fields = '__all__'



class WalletSummarySerializer(serializers.Serializer):
    available_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    withdrawable_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_earned_lifetime = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    completed_sessions = CompletedSessionSerializer(
        many=True,
        required=False,
        default=[]
    )


# payment/serializers.py
class WithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdrawal
        fields = ["id", "amount", "status", "stripe_transfer_id", "created_at"]


# serializers.py
from rest_framework import serializers
from .models import Withdrawal


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    """User-facing — they just submit an amount."""
    class Meta:
        model = Withdrawal
        fields = ["id", "amount", "session", "account_name","account_number", "bank_name"]
        read_only_fields = ["id", "status", "requested_at"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
    

    def validate_session(self, value):
        pass


    def create(self, validated_data):
        wallet = self.context["request"].user.wallet
        id = validated_data["id"]
        try:
            booking = Booking.objects.get(id=int(id))
        except Booking.DoesNotExist:
            raise serializers.ValidationError("Booking Not Found", 404)
        
        amount = validated_data["amount"]
        account_number = validated_data["account_number"]
        account_name = validated_data["account_name"]
        bank_name = validated_data["bank_name"]

        return Withdrawal.request(
                booking=booking,
                account_name=account_name,
                account_number=account_number,
                bank_name=bank_name, 
                wallet=wallet,
                amount=amount)


class WithdrawalAdminSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="wallet.user.get_username", read_only=True)

    class Meta:
        model = Withdrawal
        fields = [
            "id", "user", "amount", "status", "payout_reference",
            "admin_note", "requested_at", "processed_at", "processed_by",
        ]
        read_only_fields = fields



