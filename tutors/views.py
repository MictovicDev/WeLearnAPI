from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from django.db import transaction
from .models import Subject, TutorProfile, TutorCertification, TutorVerificationDocument, Availability
from .serializers import (
    SubjectSerializer,
    TutorProfileListSerializer,
    TutorProfileDetailSerializer,
    TutorProfileWriteSerializer,
    TutorCertificationSerializer,
    TutorVerificationDocumentSerializer,
    AvailabilitySerializer,
    TutorVerificationActionSerializer
)
from .filters import TutorProfileFilter
from .permissions import IsTutor, IsTutorOwner
from users.permissions import IsAdmin


@extend_schema(tags=['Tutors'])
@extend_schema_view(
    list=extend_schema(
        summary='List subjects',
        description='Returns all available subjects that tutors can teach.',
    ),
    create=extend_schema(
        summary='Create a subject',
        description='Admin only. Add a new teaching subject to the platform.',
    ),
)
class SubjectViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        return [IsAuthenticated(), IsAdmin()]


@extend_schema(tags=['Tutors'])
@extend_schema_view(
    list=extend_schema(
        summary='Discover tutors',
        description=(
            'Public endpoint. Returns all verified tutors. '
            'Filter by subject, price range, rating, teaching mode, location, and experience. '
            'Search by name. Order by hourly_rate, average_rating, or total_sessions.'
        ),
        parameters=[
            OpenApiParameter('subject', description='Filter by subject ID(s)', many=True),
            OpenApiParameter('min_rate', description='Minimum hourly rate'),
            OpenApiParameter('max_rate', description='Maximum hourly rate'),
            OpenApiParameter('min_rating', description='Minimum average rating (1-5)'),
            OpenApiParameter('teaching_mode', description='online | onsite | both'),
            OpenApiParameter('location', description='City or area (partial match)'),
            OpenApiParameter('search', description='Search by tutor name'),
            OpenApiParameter('ordering', description='Sort: hourly_rate, -hourly_rate, average_rating, -average_rating'),
        ],
    ),
    retrieve=extend_schema(
        summary='Get tutor profile',
        description='Public. Full profile including certifications, subjects, and availability slots.',
    ),
    create_my_profile=extend_schema(
        summary='Create my tutor profile',
        description='Tutor only. Creates the authenticated tutor\'s professional profile and submits for admin verification.',
        request=TutorProfileWriteSerializer,
        responses={201: TutorProfileDetailSerializer},
    ),
    my_profile=extend_schema(
        summary='Get or update my tutor profile',
        description='Tutor only. GET returns own profile. PATCH updates bio, subjects, rate, mode, etc.',
    ),
    upload_verification=extend_schema(
        summary='Upload verification document',
        description='Tutor only. Submit identity or qualification documents for admin review.',
        request=TutorVerificationDocumentSerializer,
        responses={201: TutorVerificationDocumentSerializer},
    ),
    upload_certification=extend_schema(
        summary='Upload certification',
        description='Tutor only. Attach optional certificates (degree, diploma, etc.) to profile.',
        request=TutorCertificationSerializer,
        responses={201: TutorCertificationSerializer},
    ),
    verify=extend_schema(
        summary='Approve or reject a tutor',
        description='Admin only. Set verification status to approved or rejected.',
        request=TutorVerificationActionSerializer,
        responses={200: TutorProfileDetailSerializer},
    ),
    availability_bulk=extend_schema(
    summary='Replace all availability slots',
    description=(
        'Tutor only. Replaces the tutor\'s entire availability schedule in one request. '
        'Existing slots not present in the payload are deleted, all submitted slots are recreated.'
    ),
    request=AvailabilitySerializer(many=True),
    responses={200: AvailabilitySerializer(many=True)},
),
)
class TutorProfileViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = TutorProfile.objects.filter(is_verified=True).select_related('user')
    filterset_class = TutorProfileFilter
    search_fields = ['user__first_name', 'user__last_name', 'bio']
    ordering_fields = ['hourly_rate', 'average_rating', 'total_sessions', 'years_of_experience']
    ordering = ['-average_rating']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TutorProfileDetailSerializer
        if self.action in ['create_my_profile', 'my_profile'] and self.request.method in ['POST', 'PATCH']:
            return TutorProfileWriteSerializer
        return TutorProfileListSerializer

    def get_permissions(self):
        public_actions = ['list', 'retrieve']
        tutor_actions = [
            'create_my_profile', 'my_profile', 'upload_verification',
            'upload_certification', 'availability', 'availability_detail',
            'availability_bulk',
        ]
        admin_actions = ['verify']
        if self.action in public_actions:
            return [AllowAny()]
        if self.action in tutor_actions:
            return [IsAuthenticated(), IsTutor()]
        if self.action in admin_actions:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    @action(methods=['POST'], detail=False, url_path='my-profile/create')
    def create_my_profile(self, request):
        if hasattr(request.user, 'tutor_profile'):
            return Response({'detail': 'Profile already exists. Use PATCH to update.'}, status=400)
        serializer = TutorProfileWriteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        profile = serializer.save(user=request.user)
        return Response(TutorProfileDetailSerializer(profile, context={'request': request}).data, status=201)

    @action(methods=['GET', 'PATCH'], detail=False, url_path='my-profile')
    def my_profile(self, request):
        try:
            profile = request.user.tutor_profile
        except TutorProfile.DoesNotExist:
            return Response({'detail': 'Profile not found. Create one first.'}, status=404)
        if request.method == 'GET':
            return Response(TutorProfileDetailSerializer(profile, context={'request': request}).data)
        serializer = TutorProfileWriteSerializer(profile, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TutorProfileDetailSerializer(profile, context={'request': request}).data)

    @action(methods=['POST'], detail=False, url_path='my-profile/upload-verification')
    def upload_verification(self, request):
        profile = request.user.tutor_profile
        serializer = TutorVerificationDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tutor=profile)
        return Response(serializer.data, status=201)

    @action(methods=['POST'], detail=False, url_path='my-profile/upload-certification')
    def upload_certification(self, request):
        profile = request.user.tutor_profile
        serializer = TutorCertificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tutor=profile)
        return Response(serializer.data, status=201)

    @action(methods=['POST'], detail=True, url_path='verify')
    def verify(self, request, pk=None):
        # Admin sees all profiles, not just verified
        profile = TutorProfile.objects.get(pk=pk)
        serializer = TutorVerificationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_value = serializer.validated_data['action']
        if action_value == 'approve':
            profile.verification_status = TutorProfile.VerificationStatus.APPROVED
            profile.is_verified = True
        else:
            profile.verification_status = TutorProfile.VerificationStatus.REJECTED
            profile.is_verified = False
        profile.save(update_fields=['verification_status', 'is_verified'])
        return Response(TutorProfileDetailSerializer(profile, context={'request': request}).data)


    @action(methods=['GET', 'POST'], detail=False, url_path='my-profile/availability')
    def availability(self, request):
        profile = request.user.tutor_profile
        if request.method == 'GET':
            slots = profile.availability_slots.all()
            return Response(AvailabilitySerializer(slots, many=True).data)
        serializer = AvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tutor=profile)
        return Response(serializer.data, status=201)

    @action(methods=['PATCH', 'DELETE'], detail=False, url_path='my-profile/availability/(?P<slot_id>[^/.]+)')
    def availability_detail(self, request, slot_id=None):
        profile = request.user.tutor_profile
        try:
            slot = profile.availability_slots.get(pk=slot_id)
        except Availability.DoesNotExist:
            return Response({'detail': 'Availability slot not found.'}, status=404)

        if request.method == 'DELETE':
            slot.delete()
            return Response(status=204)

        serializer = AvailabilitySerializer(slot, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(methods=['PUT'], detail=False, url_path='my-profile/availability/bulk')
    def availability_bulk(self, request):
        profile = request.user.tutor_profile
        serializer = AvailabilitySerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            profile.availability_slots.all().delete()
            slots = [
                Availability(tutor=profile, **item)
                for item in serializer.validated_data
            ]
            Availability.objects.bulk_create(slots)

        return Response(
            AvailabilitySerializer(profile.availability_slots.all(), many=True).data,
            status=200,
        )


@extend_schema(tags=['Tutors'])
@extend_schema_view(
    list=extend_schema(
        summary='List my availability slots',
        description='Tutor only. Returns all weekly availability slots for the authenticated tutor.',
    ),
    create=extend_schema(
        summary='Add availability slot',
        description='Tutor only. Add a new day/time slot to weekly availability.',
    ),
    update=extend_schema(
        summary='Update availability slot',
        description='Tutor only. Update time or blocked status of a slot.',
    ),
    destroy=extend_schema(
        summary='Delete availability slot',
        description='Tutor only. Remove a time slot from weekly availability.',
    ),
)
class AvailabilityViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AvailabilitySerializer
    permission_classes = [IsAuthenticated, IsTutor]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Availability.objects.none()
        return Availability.objects.filter(tutor=self.request.user.tutor_profile)

    def perform_create(self, serializer):
        serializer.save(tutor=self.request.user.tutor_profile)
