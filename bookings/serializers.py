from rest_framework import serializers
from .models import Booking
from tutors.serializers import TutorProfileListSerializer, SubjectSerializer
from users.serializers import UserSerializer


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            'id', 'tutor_profile', 'subject', 'session_type',
            'scheduled_date', 'start_time', 'end_time', 'notes',
            'location_address',
        ]

    def validate(self, attrs):
        if attrs.get('start_time') and attrs.get('end_time'):
            if attrs['start_time'] >= attrs['end_time']:
                raise serializers.ValidationError('start_time must be before end_time.')
        tutor_profile = attrs.get('tutor_profile')
        session_type = attrs.get('session_type')
        if tutor_profile and session_type:
            mode = tutor_profile.teaching_mode
            if session_type == Booking.SessionType.ONLINE and mode == 'onsite':
                raise serializers.ValidationError('This tutor only offers onsite sessions.')
            if session_type == Booking.SessionType.ONSITE and mode == 'online':
                raise serializers.ValidationError('This tutor only offers online sessions.')
        return attrs

    def create(self, validated_data):
        student = self.context['request'].user
        tutor = validated_data['tutor_profile']
        # Compute amount based on duration and hourly rate
        start = validated_data['start_time']
        end = validated_data['end_time']
        duration_hours = (end.hour * 60 + end.minute - start.hour * 60 - start.minute) / 60
        validated_data['total_amount'] = tutor.hourly_rate * duration_hours
        validated_data['student'] = student
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
