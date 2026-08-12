from rest_framework import serializers
from .models import Booking
from tutors.serializers import TutorProfileListSerializer, SubjectSerializer
from users.serializers import UserSerializer
from datetime import date, datetime
from decimal import Decimal
from tutors.models import Availability




class BookingCreateSerializer(serializers.ModelSerializer):
    availability_slot = serializers.PrimaryKeyRelatedField(
        queryset=Availability.objects.all(), write_only=True, required=True, help_text='ID of the availability slot to book')
    

    class Meta:
        model = Booking
        fields = ['tutor_profile', 'duration','availability_slot', 'subject', 'session_type', 'scheduled_date', 'notes']

    def validate(self, attrs):
        tutor_profile = attrs['tutor_profile']
        slot = attrs['availability_slot']
        print(slot)

        if slot.tutor.id != tutor_profile.id:
            raise serializers.ValidationError('This availability slot does not belong to the selected tutor.')

        if slot.is_booked:
            raise serializers.ValidationError('This slot has already been booked.')


        session_type = attrs.get('session_type')
        if session_type and tutor_profile.session_status not in ('online', 'onsite', 'both'):
            raise serializers.ValidationError(
                f"Tutor only supports {tutor_profile.session_status} sessions."
            )

        attrs['start_time'] = slot.start_time
        attrs['end_time'] = slot.end_time
        attrs['total_amount'] = self._compute_amount(tutor_profile, slot.start_time, slot.end_time)
        return attrs

    def create(self, validated_data):
        slot = validated_data.pop('availability_slot')
        booking = Booking.objects.create(availability_slot=slot, student=self.context['request'].user, **validated_data)
        slot.is_booked = True
        slot.save(update_fields=['is_booked'])
        return booking

    def _compute_amount(self, tutor_profile, start_time, end_time):
        # your existing rate calculation logic goes here
        pass

class MyBookingsSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = '__all__'





class BookingListSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    tutor_profile = TutorProfileListSerializer(read_only=True)
    subject = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    session_type_display = serializers.CharField(source='get_session_type_display', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'student', 'tutor_profile', 'subject', 'session_type',
            'session_type_display', 'scheduled_date', 'start_time', 'end_time',
            'status', 'status_display', "duration", 'notes', 'total_amount', 'created_at',
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
        fields = ['status', 'tutor_response_note']

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
