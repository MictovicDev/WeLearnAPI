from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Booking
from .serializers import (
    BookingCreateSerializer,
    BookingListSerializer,
    BookingDetailSerializer,
    BookingStatusUpdateSerializer,
    BookingCancelSerializer,
    BookingCompleteSerializer,
)
from users.permissions import IsStudent, IsAdmin, IsBookingParticipant
from tutors.permissions import IsTutor


@extend_schema(tags=['Bookings'])
@extend_schema_view(
    list=extend_schema(
        summary='List my bookings',
        description=(
            'Returns bookings for the current user. '
            'Students see their own bookings. Tutors see bookings on their profile. '
            'Admins see all bookings. Filter by status.'
        ),
    ),
    retrieve=extend_schema(
        summary='Get booking details',
        description='Full booking detail including session link, address, and tutor response.',
    ),
    create=extend_schema(
        summary='Create a booking',
        description=(
            'Student only. Book a session with a verified tutor. '
            'Validates session type against tutor teaching mode and computes total amount from hourly rate.'
        ),
        request=BookingCreateSerializer,
        responses={201: BookingDetailSerializer},
    ),
    respond=extend_schema(
        summary='Accept or decline a booking',
        description='Tutor only. Accept or decline a pending booking. Optionally add a response note and session link.',
        request=BookingStatusUpdateSerializer,
        responses={200: BookingDetailSerializer},
    ),
    cancel=extend_schema(
        summary='Cancel a booking',
        description='Student or tutor. Cancel a pending or accepted booking. Optionally provide a reason.',
        request=BookingCancelSerializer,
        responses={200: BookingDetailSerializer},
    ),
    complete=extend_schema(
        summary='Mark session as completed',
        description='Tutor only. Mark an accepted booking as completed after the session has taken place.',
        request=BookingCompleteSerializer,
        responses={200: BookingDetailSerializer},
    ),
)
class BookingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'session_type', 'scheduled_date']
    ordering_fields = ['scheduled_date', 'created_at']
    ordering = ['-scheduled_date']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Booking.objects.none()
        user = self.request.user
        if user.role == 'admin':
            return Booking.objects.all().select_related('student', 'tutor_profile__user', 'subject')
        if user.role == 'tutor':
            return Booking.objects.filter(tutor_profile__user=user).select_related('student', 'tutor_profile__user', 'subject')
        return Booking.objects.filter(student=user).select_related('student', 'tutor_profile__user', 'subject')

    def get_serializer_class(self):
        if self.action == 'create':
            return BookingCreateSerializer
        if self.action == 'retrieve':
            return BookingDetailSerializer
        if self.action == 'respond':
            return BookingStatusUpdateSerializer
        if self.action == 'cancel':
            return BookingCancelSerializer
        return BookingListSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsStudent()]
        if self.action == 'respond':
            return [IsAuthenticated(), IsTutor()]
        if self.action == 'complete':
            return [IsAuthenticated(), IsTutor()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = BookingCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(BookingDetailSerializer(booking, context={'request': request}).data, status=201)

    @action(methods=['PATCH'], detail=True, url_path='respond')
    def respond(self, request, pk=None):
        booking = self.get_object()
        if booking.tutor_profile.user != request.user:
            return Response({'detail': 'Not your booking.'}, status=403)
        if booking.status != Booking.Status.PENDING:
            return Response({'detail': 'Only pending bookings can be responded to.'}, status=400)
        serializer = BookingStatusUpdateSerializer(booking, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(BookingDetailSerializer(booking, context={'request': request}).data)

    @action(methods=['PATCH'], detail=True, url_path='cancel')
    def cancel(self, request, pk=None):
        booking = self.get_object()
        user = request.user
        is_participant = booking.student == user or booking.tutor_profile.user == user
        if not is_participant and user.role != 'admin':
            return Response({'detail': 'Not a participant in this booking.'}, status=403)
        if booking.status not in [Booking.Status.PENDING, Booking.Status.ACCEPTED]:
            return Response({'detail': 'Only pending or accepted bookings can be cancelled.'}, status=400)
        serializer = BookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get('reason', '')
        booking.status = Booking.Status.CANCELLED
        booking.tutor_response_note = reason
        booking.save(update_fields=['status', 'tutor_response_note'])
        return Response(BookingDetailSerializer(booking, context={'request': request}).data)

    @action(methods=['PATCH'], detail=True, url_path='complete')
    def complete(self, request, pk=None):
        booking = self.get_object()
        if booking.tutor_profile.user != request.user:
            return Response({'detail': 'Not your booking.'}, status=403)
        if booking.status != Booking.Status.ACCEPTED:
            return Response({'detail': 'Only accepted bookings can be marked complete.'}, status=400)
        booking.status = Booking.Status.COMPLETED
        booking.save(update_fields=['status'])
        # Increment tutor session count
        profile = booking.tutor_profile
        profile.total_sessions += 1
        profile.save(update_fields=['total_sessions'])
        return Response(BookingDetailSerializer(booking, context={'request': request}).data)
