from django.db import models
from django.conf import settings


class Booking(models.Model):
    class SessionType(models.TextChoices):
        ONLINE = 'online', 'Online'
        ONSITE = 'onsite', 'Onsite'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'
        CANCELLED = 'cancelled', 'Cancelled'
        COMPLETED = 'completed', 'Completed'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings_as_student'
    )
    tutor_profile = models.ForeignKey(
        'tutors.TutorProfile',
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    subject = models.ForeignKey(
        'tutors.Subject',
        on_delete=models.SET_NULL,
        null=True,
        related_name='bookings'
    )
    title = models.CharField(max_length=255)
    session_type = models.CharField(max_length=20, choices=SessionType.choices, blank=True)
    scheduled_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True, help_text='Student notes or special requests')
    tutor_response_note = models.TextField(blank=True, help_text='Tutor reason for decline/acceptance')
    session_link = models.URLField(blank=True, help_text='Online session link if applicable')
    location_address = models.TextField(blank=True, help_text='Onsite session address')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f'Booking #{self.pk} | {self.student.get_full_name()} '
            f'-> {self.tutor_profile.user.get_full_name()} | {self.scheduled_date}'
        )
