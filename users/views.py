from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse

from .serializers import (
    RegisterSerializer, UserSerializer, UserUpdateSerializer,
    CustomTokenObtainPairSerializer
)
from users.permissions import IsAdmin



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
        user = serializer.save()
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
