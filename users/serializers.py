from django.contrib.auth import get_user_model
from rest_framework import serializers, permissions
from drf_spectacular.utils import extend_schema_field
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'password', 'password_confirm']
        extra_kwargs = {
            'role': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        if attrs.get('role') == User.Role.ADMIN:
            raise serializers.ValidationError({'role': 'Cannot self-register as admin.'})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        if user.role == User.Role.TUTOR:
            from tutors.models import TutorProfile
            TutorProfile.objects.create(user=user)
        return user


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'profile_image', 'is_active', 'date_joined',
        ]
        read_only_fields = ['id', 'email', 'role', 'is_active', 'date_joined']

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj):
        return obj.get_full_name()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_profile_image(self, obj):
        profile_image = None

        # Prefer tutor profile image if the user has a tutor profile
        if hasattr(obj, "tutor_profile") and obj.tutor_profile:
            profile_image = obj.tutor_profile.profile_image

        # Fall back to user's profile image
        if not profile_image:
            profile_image = obj.profile_image

        if not profile_image:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(profile_image.url)

        from django.conf import settings
        return f"{settings.SITE_URL}{profile_image.url}"


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'profile_image']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user, context=self.context).data
        return data


class IsTutor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_tutor




class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return User.objects.normalize_email(value)


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value