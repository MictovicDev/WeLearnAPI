# wallets/serializers.py
from rest_framework import serializers


class WalletSummarySerializer(serializers.Serializer):
    available_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_clearance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_earned_lifetime = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()