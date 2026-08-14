from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from users.views import UserViewSet, AdminUserViewSet, CustomTokenObtainPairView, CustomTokenRefreshView
from tutors.views import SubjectViewSet, TutorProfileViewSet, AvailabilityViewSet
from bookings.views import BookingViewSet
from reviews.views import ReviewViewSet
from chat.views import ChatThreadViewSet
from payment.views import PaymentViewSet



router = DefaultRouter()

# Auth / Users
router.register(r'users', UserViewSet, basename='users')
router.register(r'admin/users', AdminUserViewSet, basename='admin-users')
# Tutors
router.register(r'subjects', SubjectViewSet, basename='subjects')
router.register(r'tutors', TutorProfileViewSet, basename='tutors')

router.register(r'tutors/my/availability', AvailabilityViewSet, basename='availability')

# Bookings
router.register(r'bookings', BookingViewSet, basename='bookings')

# Reviews
router.register(r'reviews', ReviewViewSet, basename='reviews')

router.register('payment', PaymentViewSet, basename='payment')

# Messaging
router.register(r'chat', ChatThreadViewSet, basename='chats')

urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT auth
    path('api/v1/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),

    # Stripe webhook, kept outside the router since it's a plain view with
    # its own auth handling, not a DRF viewset action.
    path('api/v1/webhooks/', include('payment.urls')),

    # All routed viewsets
    path('api/v1/', include(router.urls)),
    # path('api/v1/chat/', include('chat.urls')),

    # Schema & docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)