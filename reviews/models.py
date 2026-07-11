from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings


class Review(models.Model):
    booking = models.OneToOneField(
        'bookings.Booking',
        on_delete=models.CASCADE,
        related_name='review'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews_given'
    )
    tutor_profile = models.ForeignKey(
        'tutors.TutorProfile',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Review by {self.student.get_full_name()} for {self.tutor_profile.user.get_full_name()} ({self.rating}/5)'
