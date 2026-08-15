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
from bookings.serializers import MyBookingsSerializer
import logging
from django.db.models import Sum, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from payment.models import Transaction, PayoutMethod
from payment.serializers import (
    TransactionSerializer,
    PayoutMethodSerializer,
    WalletSummarySerializer,
    DashboardStatsSerializer,
    PerformanceChartPointSerializer,
)
import json

logger = logging.getLogger('tutor_platform')

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

    @action(methods=['GET'], detail=False, url_path='my-bookings')
    def bookings(self, request):
        profile = request.user.tutor_profile
        bookings = profile.bookings.all()
        return Response(MyBookingsSerializer(bookings, many=True).data)

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


    @action(methods=['GET', 'PATCH'], detail=False, url_path='my-profile')
    def my_profile(self, request):
        try:
            profile = request.user.tutor_profile
        except TutorProfile.DoesNotExist:
            return Response({'detail': 'Profile not found. Create one first.'}, status=404)

        if request.method == 'GET':
            return Response(TutorProfileDetailSerializer(profile, context={'request': request}).data)
        logger.info(request.data)
        data = request.data.copy()  # Make a mutable copy of the request data
        availability_data = data.pop('availability', None) if hasattr(request.data, 'pop') else None
        payment_info_raw = data.get('payment_info')
        if isinstance(payment_info_raw, str):
            try:
                data['payment_info'] = json.loads(payment_info_raw)
            except json.JSONDecodeError:
                return Response({'payment_info': ['Invalid JSON.']}, status=400)


        serializer = TutorProfileWriteSerializer(profile, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)

        availability_serializer = None
        if availability_data is not None:
            availability_serializer = AvailabilitySerializer(data=availability_data, many=True)
            availability_serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()
            if availability_serializer is not None:
                profile.availability_slots.all().delete()
                slots = [
                    Availability(tutor=profile, **item)
                    for item in availability_serializer.validated_data
                ]
                Availability.objects.bulk_create(slots)

        return Response(TutorProfileDetailSerializer(profile, context={'request': request}).data)


    @action(methods=['GET'], detail=False, url_path='my-profile/dashboard-stats')
    def dashboard_stats(self, request):
        profile = request.user.tutor_profile
        now = timezone.now()
        week_start = now - timedelta(days=7)
    
        # adjust field/status names below to match your actual Booking model
        upcoming_sessions = profile.bookings.filter(
            status='confirmed', scheduled_date__gte=now,
        ).count()
    
        pending_requests = profile.bookings.filter(status='pending').count()
    
        weekly_earnings = profile.transactions.filter(
            transaction_type=Transaction.TransactionType.EARNING,
            created_at__gte=week_start,
        ).aggregate(total=Sum('amount'))['total'] or 0
    
        data = {
            'upcoming_sessions': upcoming_sessions,
            'pending_requests': pending_requests,
            'weekly_earnings': weekly_earnings,
            'average_rating': profile.average_rating or 0,
        }
        return Response(DashboardStatsSerializer(data).data)
    
    
    @action(methods=['GET'], detail=False, url_path='my-profile/wallet')
    def wallet_summary(self, request):
        profile = request.user.tutor_profile
        totals = profile.transactions.aggregate(
            cleared=Sum('amount', filter=Q(
                status=Transaction.Status.CLEARED,
                transaction_type=Transaction.TransactionType.EARNING,
            )),
            pending=Sum('amount', filter=Q(
                status=Transaction.Status.PENDING,
                transaction_type=Transaction.TransactionType.EARNING,
            )),
            payouts=Sum('amount', filter=Q(
                transaction_type=Transaction.TransactionType.PAYOUT,
                status=Transaction.Status.COMPLETED,
            )),
            lifetime_earnings=Sum('amount', filter=Q(
                transaction_type=Transaction.TransactionType.EARNING,
            )),
        )
        cleared = totals['cleared'] or 0
        payouts = totals['payouts'] or 0
    
        data = {
            'available_balance': cleared - payouts,
            'pending_clearance': totals['pending'] or 0,
            'total_earned_lifetime': totals['lifetime_earnings'] or 0,
        }
        return Response(WalletSummarySerializer(data).data)
    
    
    @action(methods=['GET'], detail=False, url_path='my-profile/transactions')
    def transactions(self, request):
        profile = request.user.tutor_profile
        tx_type = request.query_params.get('type')  # 'earnings' or 'payouts'
    
        qs = profile.transactions.all()
        if tx_type == 'earnings':
            qs = qs.filter(transaction_type=Transaction.TransactionType.EARNING)
        elif tx_type == 'payouts':
            qs = qs.filter(transaction_type=Transaction.TransactionType.PAYOUT)
    
        page = self.paginate_queryset(qs)
        serializer = TransactionSerializer(page if page is not None else qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
    
    
    @action(methods=['GET', 'POST'], detail=False, url_path='my-profile/payout-methods')
    def payout_methods(self, request):
        profile = request.user.tutor_profile
        if request.method == 'GET':
            methods = profile.payout_methods.all()
            return Response(PayoutMethodSerializer(methods, many=True).data)
    
        serializer = PayoutMethodSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tutor=profile)
        return Response(serializer.data, status=201)
    
    
    @action(methods=['GET'], detail=False, url_path='my-profile/performance-chart')
    def performance_chart(self, request):
        """Revenue grouped by day, defaults to the last 7 days.
        Pass ?days=30 for a longer window."""
        profile = request.user.tutor_profile
        days = int(request.query_params.get('days', 7))
        start_date = (timezone.now() - timedelta(days=days - 1)).date()
    
        earnings = (
            profile.transactions.filter(
                transaction_type=Transaction.TransactionType.EARNING,
                created_at__date__gte=start_date,
            )
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(revenue=Sum('amount'))
        )
        revenue_by_date = {row['day']: row['revenue'] for row in earnings}
    
        results = []
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            results.append({
                'day': current_date.strftime('%a'),
                'date': current_date,
                'revenue': revenue_by_date.get(current_date, 0),
            })
        return Response(PerformanceChartPointSerializer(results, many=True).data)
 




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
