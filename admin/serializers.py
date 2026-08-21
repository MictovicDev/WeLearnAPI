from rest_framework import serializers
from django.contrib.auth import get_user_model
from tutors.models import TutorProfile
from wallets.models import Withdrawal
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class AdminRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "password",
        ]

    def validate_email(self, value):
        value = value.lower().strip()

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        return value

    def create(self, validated_data):
        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            **validated_data,
        )

        user.is_staff = True
        user.is_active = True
        user.is_superuser = False

        user.save(
            update_fields=[
                "is_staff",
                "is_active",
                "is_superuser",
            ]
        )

        return user




class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"]
        password = attrs["password"]

        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=password,
        )

        if not user:
            raise serializers.ValidationError(
                {"detail": "Invalid email or password."}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "This account is inactive."}
            )

        if not user.is_staff:
            raise serializers.ValidationError(
                {"detail": "You do not have permission to access the admin panel."}
            )

        refresh = RefreshToken.for_user(user)

        return {
            "user": user,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


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