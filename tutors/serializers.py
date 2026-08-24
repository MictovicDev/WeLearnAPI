from rest_framework import serializers
from .models import Subject, TutorProfile, TutorCertification, TutorVerificationDocument, Availability
from users.serializers import UserSerializer
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import TutorProfile, PayMentInfo


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'description']


class TutorCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorCertification
        fields = ['id', 'title', 'document', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class TutorVerificationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorVerificationDocument
        fields = ['id', 'document_type', 'document', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class TutorVerificationActionSerializer(serializers.Serializer):    
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class PaymentInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayMentInfo
        fields = ['id', 'method', 'bank_name', 'account_number']
        read_only_fields = ['id']


class AvailabilityListSerializer(serializers.ListSerializer):
    def validate(self, data):
        seen = set()
        for item in data:
            key = (item['day_of_week'], item['start_time'])
            if key in seen:
                raise serializers.ValidationError(
                    f"Duplicate slot for day {item['day_of_week']} at {item['start_time']} in payload."
                )
            seen.add(key)
        return data


class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = ['id', 'day_of_week', 'start_time', 'end_time', 'is_booked']
        list_serializer_class = AvailabilityListSerializer

    def validate(self, attrs):
        start = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end = attrs.get('end_time', getattr(self.instance, 'end_time', None))
        if start and end and start >= end:
            raise serializers.ValidationError('end_time must be after start_time.')
        return attrs

class TutorProfileDetailSerializer(serializers.ModelSerializer):
    """Used for retrieve and for returning profile after create/update."""
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    payment_info = PaymentInfoSerializer(read_only=True)
    availability_slots = AvailabilitySerializer(many=True)
    bookings = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = TutorProfile
        fields = [
            'id', 'full_name', 'email', 'bio', 'subjects', 'session_status',
            'experience', 'education', 'payment_info',
            'hourly_rate', 'average_rating', 'total_sessions',
            'is_verified', 'verification_status', 'location',
            'profile_image',
            'banner',
            'language',
            'phone_number', 
            'professional_title',
            'skills',
            'language',
            "availability_slots"
        ]
        read_only_fields = ['is_verified', 'verification_status', 'average_rating', 'total_sessions']

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj):
        return obj.user.get_full_name()

    def get_bookings(self, obj):
        from bookings.serializers import BookingListSerializer
        bookings = obj.bookings.all()
        return BookingListSerializer(bookings, many=True).data

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_profile_image(self, obj):
        if not obj.profile_image:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(obj.profile_image.url)

        from django.conf import settings
        return f"{settings.SITE_URL}{obj.profile_image.url}"


class TutorProfileListSerializer(serializers.ModelSerializer):
    """Used for the public discovery list, kept lightweight."""

    full_name = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = TutorProfile
        fields = "__all__"

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj):
        return obj.user.get_full_name()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_profile_image(self, obj):
        if not obj.profile_image:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(obj.profile_image.url)

        from django.conf import settings
        return f"{settings.SITE_URL}{obj.profile_image.url}"



class TutorProfileWriteSerializer(serializers.ModelSerializer):
    """Used for create_my_profile and my_profile PATCH."""
    payment_info = PaymentInfoSerializer(required=False)

    class Meta:
        model = TutorProfile
        exclude = ['user']

    def create(self, validated_data):
        payment_data = validated_data.pop('payment_info', None)
        profile = TutorProfile.objects.create(**validated_data)
        if payment_data:
            payment_obj = PayMentInfo.objects.create(user=profile.user, **payment_data)
            profile.payment_info = payment_obj
            profile.save(update_fields=['payment_info'])
        return profile

    def update(self, instance, validated_data):
        payment_data = validated_data.pop('payment_info', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if payment_data is not None:
            if instance.payment_info:
                for attr, value in payment_data.items():
                    setattr(instance.payment_info, attr, value)
                instance.payment_info.save()
            else:
                payment_obj = PayMentInfo.objects.create(user=instance.user, **payment_data)
                instance.payment_info = payment_obj
                instance.save(update_fields=['payment_info'])

        return instance
