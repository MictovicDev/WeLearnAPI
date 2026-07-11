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



class AvailabilitySerializer(serializers.ModelSerializer):
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = Availability
        fields = ['id', 'day_of_week', 'day_display', 'start_time', 'end_time', 'is_blocked']

    def validate(self, attrs):
        if attrs.get('start_time') and attrs.get('end_time'):
            if attrs['start_time'] >= attrs['end_time']:
                raise serializers.ValidationError('start_time must be before end_time.')
        return attrs



class PaymentInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayMentInfo
        fields = ['id', 'method', 'bank_name', 'account_number']
        read_only_fields = ['id']


class TutorProfileListSerializer(serializers.ModelSerializer):
    """Used for the public discovery list, kept lightweight."""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = TutorProfile
        fields = [
            'id', 'full_name', 'bio', 'subjects', 'session_status',
            'hourly_rate', 'average_rating', 'total_sessions'
        ]

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj):
        return obj.user.get_full_name()


class TutorProfileDetailSerializer(serializers.ModelSerializer):
    """Used for retrieve and for returning profile after create/update."""
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    payment_info = PaymentInfoSerializer(read_only=True)

    class Meta:
        model = TutorProfile
        fields = [
            'id', 'full_name', 'email', 'bio', 'subjects', 'session_status',
            'experience', 'education', 'payment_info',
            'hourly_rate', 'average_rating', 'total_sessions',
            'is_verified', 'verification_status',
        ]
        read_only_fields = ['is_verified', 'verification_status', 'average_rating', 'total_sessions']

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj):
        return obj.user.get_full_name()


class TutorProfileWriteSerializer(serializers.ModelSerializer):
    """Used for create_my_profile and my_profile PATCH."""
    payment_info = PaymentInfoSerializer(required=False)

    class Meta:
        model = TutorProfile
        fields = [
            'bio', 'subjects', 'session_status', 'experience', 'education',
            'payment_info', 'hourly_rate'
        ]

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
