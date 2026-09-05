from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse
from bookings.serializers import BookingListSerializer
from .serializers import (
    RegisterSerializer, UserSerializer, UserUpdateSerializer,
    CustomTokenObtainPairSerializer
)
from users.permissions import IsAdmin
from services.email_service import notify_verification_email
from .models import EmailVerificationToken
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

from .models import PasswordResetToken
from .serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer


User = get_user_model()


@extend_schema(tags=['Auth'])
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        summary='Login',
        description='Authenticate with email and password. Returns JWT access and refresh tokens alongside the user object.',
        responses={200: CustomTokenObtainPairSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(tags=['Auth'])
class CustomTokenRefreshView(TokenRefreshView):
    @extend_schema(
        summary='Refresh access token',
        description='Exchange a valid refresh token for a new access token.',
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema_view(
    register=extend_schema(
        summary='Register a new user',
        description='Create a student or tutor account. Admin accounts cannot be self-registered.',
        request=RegisterSerializer,
        responses={201: UserSerializer},
        tags=['Auth'],
    ),
    me=extend_schema(
        summary='Get or update current user profile',
        description='GET returns the authenticated user. PATCH updates name or profile image.',
        tags=['Users'],
    ),
    logout=extend_schema(
        summary='Logout',
        description='Blacklist the provided refresh token to invalidate the session.',
        tags=['Auth'],
    ),
)
class UserViewSet(viewsets.GenericViewSet):
    queryset = User.objects.all()

    def get_permissions(self):
        if self.action == 'register':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'register':
            return RegisterSerializer
        if self.action in ['me'] and self.request.method in ['PATCH']:
            return UserUpdateSerializer
        return UserSerializer

    @action(methods=['POST'], detail=False, url_path='register')
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(is_active=False)
        token = EmailVerificationToken.objects.create(user=user)
        notify_verification_email(user, verification_token=token.key)
        out = UserSerializer(user, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(methods=['GET', 'PATCH'], detail=False, url_path='me')
    def me(self, request):
        if request.method == 'GET':
            return Response(UserSerializer(request.user, context={'request': request}).data)
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user, context={'request': request}).data)


    @action(methods=['GET'], detail=False, url_path='bookings')
    def bookings(self, request):
        booking= request.user.bookings_as_student.all()
        return Response(BookingListSerializer(booking, many=True).data)

    @action(methods=['POST'], detail=False, url_path='logout')
    def logout(self, request):
        try:
            token = RefreshToken(request.data.get('refresh'))
            token.blacklist()
            return Response({'detail': 'Logged out successfully.'})
        except Exception:
            return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)



@extend_schema(tags=['Admin'])
@extend_schema_view(
    list=extend_schema(summary='List all users', description='Admin only. Returns all registered users.'),
    retrieve=extend_schema(summary='Retrieve a user', description='Admin only.'),
    partial_update=extend_schema(summary='Update a user', description='Admin only. Update user fields.'),
    destroy=extend_schema(summary='Deactivate a user', description='Admin only. Soft-deletes by setting is_active=False.'),
)
class AdminUserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    search_fields = ['email', 'first_name', 'last_name']
    filterset_fields = ['role', 'is_active']

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])


# accounts/views.py
class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token_key = request.data.get("token")
        try:
            token = EmailVerificationToken.objects.get(key=token_key)
        except EmailVerificationToken.DoesNotExist:
            return Response({"detail": "Invalid token"}, status=400)

        if not token.is_valid():
            return Response({"detail": "Token expired"}, status=400)

        user = token.user
        user.is_active = True
        user.save(update_fields=["is_active"])
        token.delete()  # one-time use
        return Response({"detail": "Email verified"}, status=200)





class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = User.objects.filter(email=email, is_active=True).first()
        if user:
            token = PasswordResetToken.objects.create(user=user)
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token.key}"
            send_mail(
                subject='Reset your password',
                message=f'Click the link to reset your password: {reset_url}. This link expires in 1 hour.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

        # Always return 200, don't reveal whether the email exists
        return Response(
            {'detail': 'If an account with that email exists, a reset link has been sent.'},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_key = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            token = PasswordResetToken.objects.select_related('user').get(key=token_key)
        except PasswordResetToken.DoesNotExist:
            return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

        if not token.is_valid():
            return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

        user = token.user
        user.set_password(new_password)
        user.save(update_fields=['password'])

        token.used = True
        token.save(update_fields=['used'])

        # Invalidate any other outstanding tokens for this user
        PasswordResetToken.objects.filter(user=user, used=False).exclude(pk=token.pk).update(used=True)

        return Response({'detail': 'Password has been reset successfully.'}, status=status.HTTP_200_OK)
