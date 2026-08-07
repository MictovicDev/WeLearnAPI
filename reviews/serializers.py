from rest_framework import serializers
from .models import Review
from users.serializers import UserSerializer


class ReviewCreateSerializer(serializers.ModelSerializer):
    stars = serializers.IntegerField(min_value=1, max_value=5, write_only=True)

    class Meta:
        model = Review
        fields = ['id', 'booking', 'stars', 'rating', 'comment']
        read_only_fields = ['id', 'rating']

    def validate(self, attrs):
        attrs['rating'] = attrs.pop('stars')
        return attrs

    def validate_booking(self, booking):
        student = self.context['request'].user
        if booking.student != student:
            raise serializers.ValidationError('You can only review your own bookings.')
        if booking.status != 'completed':
            raise serializers.ValidationError('You can only review completed sessions.')
        if hasattr(booking, 'review'):
            raise serializers.ValidationError('This session has already been reviewed.')
        return booking

    def create(self, validated_data):
        booking = validated_data['booking']
        validated_data['student'] = self.context['request'].user
        validated_data['tutor_profile'] = booking.tutor_profile
        review = super().create(validated_data)
        self._update_tutor_rating(booking.tutor_profile)
        return review

    def _update_tutor_rating(self, tutor_profile):
        from django.db.models import Avg
        agg = tutor_profile.reviews.aggregate(avg=Avg('rating'))
        tutor_profile.average_rating = agg['avg'] or 0
        tutor_profile.total_reviews = tutor_profile.reviews.count()
        tutor_profile.save(update_fields=['average_rating', 'total_reviews'])


class ReviewSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'student', 'booking', 'tutor_profile', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'student', 'tutor_profile', 'created_at']
