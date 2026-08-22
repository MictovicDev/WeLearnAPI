# wallets/serialize
from rest_framework import serializers
from wallets.models import WalletTransaction, Withdrawal, Booking
from decimal import Decimal
from django.db import transaction

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


from django.db import transaction
from rest_framework import serializers


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    booking_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Withdrawal
        fields = [
            "id",
            "booking_id",
            "amount",
            "session",
            "account_name",
            "account_number",
            "bank_name",
        ]
        read_only_fields = ["id", "session"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Amount must be greater than zero."
            )
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        import uuid
        
        def generate_reference(prefix="REF"):
            return f"{prefix}_{uuid.uuid4().hex[:12].upper()}"

        booking_id = validated_data.pop("booking_id")
        amount = validated_data["amount"]

        with transaction.atomic():
            wallet = (
                user.wallet.__class__.objects
                .select_for_update()
                .get(pk=user.wallet.pk)
            )

            # Check booking
            try:
                booking = Booking.objects.get(id=booking_id)
            except Booking.DoesNotExist:
                raise serializers.ValidationError({
                    "booking_id": "Booking not found."
                })

            # Check wallet balance
            if wallet.withdrawable_balance < amount:
                raise serializers.ValidationError({
                    "amount": "Insufficient wallet balance."
                })
         
            # Deduct the money
            wallet.withdrawable_balance -= amount
            wallet.balance -= amount
            wallet.save(update_fields=["withdrawable_balance","balance"])
            booking.tutor_has_withdrawn = True
            booking.save(update_fields=["tutor_has_withdrawn"])
            new_transaction = WalletTransaction.objects.create(
                            wallet=wallet,
                            type="debit",
                            status="pending",
                            amount=amount,
                            balance_after=wallet.balance,
                            reference = generate_reference("WD"),
                            description=f"Withdrawal from {booking.id}"
            )
            withdrawal = Withdrawal.objects.create(
                session=booking,
                wallet=wallet,
                transaction=new_transaction,
                **validated_data
            )
            
            

        return withdrawal


class WithdrawalAdminSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="wallet.user.get_username", read_only=True)

    class Meta:
        model = Withdrawal
        fields = [
            "id", "user", "amount", "status", "payout_reference",
            "admin_note", "requested_at", "processed_at", "processed_by",
        ]
        read_only_fields = fields



