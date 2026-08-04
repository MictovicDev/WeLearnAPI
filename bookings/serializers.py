from rest_framework import serializers
from .models import Booking
from tutors.serializers import TutorProfileListSerializer, SubjectSerializer
from users.serializers import UserSerializer
from datetime import date, datetime
from decimal import Decimal




class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['tutor_profile', 'subject', 'session_type', 'scheduled_date', 'start_time', 'end_time', 'notes']

    def validate(self, attrs):
        tutor_profile = attrs['tutor_profile']
        scheduled_date = attrs['scheduled_date']
        start_time = attrs['start_time']
        end_time = attrs['end_time']

        if start_time >= end_time:
            raise serializers.ValidationError('end_time must be after start_time.')

        day_of_week = scheduled_date.weekday()  # Monday=0, matches Availability.DayOfWeek

        slot = tutor_profile.availability_slots.filter(
            day_of_week=day_of_week,
            is_blocked=False,
            start_time__lte=start_time,
            end_time__gte=end_time,
        ).first()

        if not slot:
            raise serializers.ValidationError(
                'Tutor is not available at the requested day and time.'
            )

        session_type = attrs.get('session_type')
        if session_type and tutor_profile.teaching_mode not in ('both', session_type):
            raise serializers.ValidationError(
                f"Tutor only supports {tutor_profile.teaching_mode} sessions."
            )

        attrs['total_amount'] = self._compute_amount(tutor_profile, start_time, end_time)
        return attrs

    def _compute_amount(self, tutor_profile, start_time, end_time):
        duration_hours = (
            datetime.combine(date.min, end_time) - datetime.combine(date.min, start_time)
        ).total_seconds() / 3600
        return round(tutor_profile.hourly_rate * Decimal(str(duration_hours)), 2)

    def create(self, validated_data):
        validated_data['student'] = self.context['request'].user
        return super().create(validated_data)







class BookingListSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    tutor_profile = TutorProfileListSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    session_type_display = serializers.CharField(source='get_session_type_display', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'student', 'tutor_profile', 'subject', 'session_type',
            'session_type_display', 'scheduled_date', 'start_time', 'end_time',
            'status', 'status_display', 'notes', 'total_amount', 'created_at',
        ]


class BookingDetailSerializer(BookingListSerializer):
    class Meta(BookingListSerializer.Meta):
        fields = BookingListSerializer.Meta.fields + [
            'tutor_response_note', 'session_link', 'location_address', 'updated_at',
        ]


class BookingStatusUpdateSerializer(serializers.ModelSerializer):
    """Tutor uses this to accept/decline a booking."""
    class Meta:
        model = Booking
        fields = ['status', 'tutor_response_note', 'session_link']

    def validate_status(self, value):
        allowed = [Booking.Status.ACCEPTED, Booking.Status.DECLINED]
        if value not in allowed:
            raise serializers.ValidationError('Tutors can only accept or decline bookings.')
        return value


class BookingCompleteSerializer(serializers.ModelSerializer):
    """Tutor marks session as completed."""
    class Meta:
        model = Booking
        fields = ['status']

    def validate_status(self, value):
        if value != Booking.Status.COMPLETED:
            raise serializers.ValidationError('Status must be completed.')
        return value


class BookingCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
