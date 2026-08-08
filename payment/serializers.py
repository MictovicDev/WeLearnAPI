# Add this to your serializers.py

from rest_framework import serializers
from .models import Transaction, PayoutMethod


class PayoutMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutMethod
        fields = ['id', 'method_type', 'display_name', 'account_identifier', 'is_default', 'created_at']
        read_only_fields = ['id', 'created_at']


class TransactionSerializer(serializers.ModelSerializer):
    # safe lookup, works even when booking is null
    booking_subject = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_type', 'status', 'amount',
            'description', 'booking', 'booking_subject', 'created_at',
        ]
        read_only_fields = fields

    def get_booking_subject(self, obj):
        if obj.booking_id and hasattr(obj.booking, 'subject'):
            return getattr(obj.booking.subject, 'name', None)
        return None


class WalletSummarySerializer(serializers.Serializer):
    available_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_clearance = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_earned_lifetime = serializers.DecimalField(max_digits=10, decimal_places=2)


class DashboardStatsSerializer(serializers.Serializer):
    upcoming_sessions = serializers.IntegerField()
    pending_requests = serializers.IntegerField()
    weekly_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)


class PerformanceChartPointSerializer(serializers.Serializer):
    day = serializers.CharField()      # e.g. "Mon"
    date = serializers.DateField()
    revenue = serializers.DecimalField(max_digits=10, decimal_places=2)