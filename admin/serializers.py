from rest_framework import serializers
from django.contrib.auth import get_user_model
from tutors.models import TutorProfile
from wallets.models import Withdrawal

User = get_user_model()


# ---------------------------------------------------------------- Tutors ---

class TutorAdminListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = TutorProfile
        fields = ['id', 'name', 'email', 'verification_status', 'subjects', 'total_sessions', 'average_rating']

    def get_name(self, obj):
        return obj.user.get_full_name()


class TutorAdminDetailSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    joined = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = TutorProfile
        fields = [
            'id', 'name', 'email', 'phone_number', 'location', 'joined', 'bio',
            'subjects', 'skills', 'verification_status', 'is_verified',
            'total_sessions', 'average_rating', 'total_reviews',
        ]

    def get_name(self, obj):
        return obj.user.get_full_name()


# --------------------------------------------------------------- Students --

class StudentAdminSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'email']

    def get_name(self, obj):
        return obj.get_full_name()


# ------------------------------------------------------------ Withdrawals --

class WithdrawalSessionSerializer(serializers.Serializer):
    """One row in the 'SESSION DETAILS' block."""
    id = serializers.IntegerField()
    student_name = serializers.SerializerMethodField()
    subject = serializers.CharField()
    scheduled_date = serializers.DateField()
    start_time = serializers.TimeField()
    session_type = serializers.CharField()

    def get_student_name(self, booking):
        return booking.student.get_full_name()


class WithdrawalAdminListSerializer(serializers.ModelSerializer):
    tutor_name = serializers.CharField(source='wallet.user.get_full_name', read_only=True)

    class Meta:
        model = Withdrawal
        fields = ['id', 'tutor_name', 'amount', 'status', 'requested_at']


class WithdrawalAdminDetailSerializer(serializers.ModelSerializer):
    tutor_name = serializers.CharField(source='wallet.user.get_full_name', read_only=True)
    sessions = serializers.SerializerMethodField()

    class Meta:
        model = Withdrawal
        fields = [
            'id', 'tutor_name', 'amount', 'status', 'admin_note',
            'account_name', 'bank_name', 'account_number',
            'payout_reference', 'requested_at', 'processed_at', 'sessions',
        ]

    def get_sessions(self, obj):
        # `sessions` (M2M) is the source of truth; `session` (single FK) looks
        # like a legacy field — fall back to it only if the M2M is empty.
        qs = obj.sessions.all() or ([obj.session] if obj.session_id else [])
        return WithdrawalSessionSerializer(qs, many=True).data


class WithdrawalActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default='')
    payout_reference = serializers.CharField(required=False, allow_blank=True, default='')


# ----------------------------------------------------------- Shared action -

class AdminActionSerializer(serializers.Serializer):
    """Used for every approve/reject action (tutors + withdrawals)."""
    note = serializers.CharField(required=False, allow_blank=True, default='')