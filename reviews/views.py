from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Review
from .serializers import ReviewCreateSerializer, ReviewSerializer
from users.permissions import IsStudent


@extend_schema(tags=['Reviews'])
@extend_schema_view(
    list=extend_schema(
        summary='List reviews for a tutor',
        description='Public. Returns all reviews for a given tutor profile. Pass ?tutor_profile=<id> to filter.',
    ),
    create=extend_schema(
        summary='Submit a review',
        description=(
            'Student only. Submit a rating and comment for a completed session. '
            'Each booking can only be reviewed once. Automatically recalculates tutor average rating.'
        ),
        request=ReviewCreateSerializer,
        responses={201: ReviewSerializer},
    ),
)
class ReviewViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    filterset_fields = ['tutor_profile', 'rating']
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']

    def get_queryset(self):
        return Review.objects.all().select_related('student', 'tutor_profile__user', 'booking')

    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer

    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        return [IsAuthenticated(), IsStudent()]
