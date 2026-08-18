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
from google_auth_oauthlib.flow import Flow
from django.conf import settings
from users.permissions import IsStudent, IsAdmin, IsBookingParticipant
from tutors.permissions import IsTutor
from services.email_service import notify_booking_created, notify_booking_status
import logging
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from .services import get_or_create_user_from_google, verify_google_id_token
from bookings.models import GoogleOAuthToken
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import uuid
from datetime import datetime

logger = logging.getLogger('tutor_platform')


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
            return Booking.objects.all().select_related('student', 'tutor_profile__user')
        if user.role == 'tutor':
            print(True)
            print(user)
            print(Booking.objects.filter(tutor_profile__user=user))
            return Booking.objects.filter(tutor_profile__user=user)
        return Booking.objects.filter(student=user).select_related('student', 'tutor_profile__user')

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
            print(IsStudent())
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
        notify_booking_created(booking)
        return Response(BookingDetailSerializer(booking, context={'request': request}).data, status=201)

    @action(methods=['PATCH'], detail=True, url_path='respond')
    def respond(self, request, pk=None):
        try:
            booking = Booking.objects.get(id=pk)
        except Booking.DoesNotExist:
            return Response({'detail': 'Booking not found.'}, status=404)

        if booking.tutor_profile.user != request.user:
            return Response({'detail': 'Not your booking.'}, status=403)
        if booking.status != Booking.Status.PENDING:
            return Response({'detail': 'Only pending bookings can be responded to.'}, status=400)

        serializer = BookingStatusUpdateSerializer(booking, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data.get('status')

        if new_status == Booking.Status.ACCEPTED:
            if booking.availability_slot:
                booking.availability_slot.is_booked = True
                booking.availability_slot.save(update_fields=['is_booked'])

            if booking.session_type == Booking.SessionType.ONLINE:
                self._create_calendar_event(booking)

        serializer.save()
        notify_booking_status(booking, new_status)
        return Response(
            {"detail": f"Booking {booking.status.lower()} successfully."},
            status=status.HTTP_200_OK,
        )

    def _create_calendar_event(self, booking):
        try:
            google_token = GoogleOAuthToken.objects.first()
        except GoogleOAuthToken.DoesNotExist:
            return

        if not google_token:
            return

        credentials = Credentials(
            token=google_token.access_token,
            refresh_token=google_token.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=SCOPES,
        )

        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())

                google_token.access_token = credentials.token
                google_token.expires_at = credentials.expiry

                google_token.save(
                    update_fields=[
                        "access_token",
                        "expires_at",
                    ]
                )

            except Exception as exc:
                logger.exception(
                    "Failed to refresh Google Calendar token: %s",
                    exc,
                )
                return

        service = build(
            "calendar",
            "v3",
            credentials=credentials,
        )

        start_date = datetime.combine(
            booking.scheduled_date,
            booking.start_time,
        )

        end_date = datetime.combine(
            booking.scheduled_date,
            booking.end_time,
        )
        print(start_date)
        print(end_date)

        body = {
            "summary": booking.title or f"Tutoring session: {booking.subject}",
            "description": booking.notes or "",
            "location": booking.location_address or "",

            "start": {
                "dateTime": start_date.isoformat(),
                "timeZone": "Africa/Lagos",
            },

            "end": {
                "dateTime": end_date.isoformat(),
                "timeZone": "Africa/Lagos",
            },

            "conferenceData": {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {
                        "type": "hangoutsMeet",
                    },
                },
            },
        }

        google_event = (
            service.events()
            .insert(
                calendarId="primary",
                body=body,
                conferenceDataVersion=1,
            )
            .execute()
        )

        booking.session_link = google_event.get("hangoutLink", "")
        booking.google_event_id = google_event["id"]

        booking.save(
            update_fields=[
                "session_link",
                "google_event_id",
            ]
        )

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
        booking.status = Booking.Status.DECLINED
        booking.tutor_response_note = reason
        booking.save(update_fields=['status', 'tutor_response_note'])
        notify_booking_status(booking, status="declined")
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





SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
]



from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from google_auth_oauthlib.flow import Flow
from django.contrib.auth import get_user_model

User = get_user_model()
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from rest_framework.permissions import IsAuthenticated

class GoogleCalendarConnectView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
        )

        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )

        request.session["google_oauth_state"] = state
        request.session["google_code_verifier"] = flow.code_verifier

        return HttpResponseRedirect(authorization_url)


class GoogleCalendarCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        state = request.session.get("google_oauth_state")
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            state=state,
        )

        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI

        state = request.session.get("google_oauth_state")
        code_verifier = request.session.get("google_code_verifier")

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            state=state,
        )

        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        flow.code_verifier = code_verifier

        flow.fetch_token(
            authorization_response=request.build_absolute_uri()
        )
        credentials = flow.credentials
        GoogleOAuthToken.objects.update_or_create(
            defaults={
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "expires_at": credentials.expiry,
            },
        )

        return Response(
            {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "expiry": credentials.expiry,
            }
        )