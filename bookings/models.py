from django.db import models
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from django.core.exceptions import ValidationError
import uuid
from users.models import User

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
        PAYMENT_CONFIRMED = 'payment_confirmed', 'Payment Confirmed'

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
    subject = models.CharField(max_length=100, help_text='Subject for the tutoring session', blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True, help_text='Optional title for the session')
    session_type = models.CharField(max_length=20, choices=SessionType.choices, blank=True)
    scheduled_date = models.DateField(auto_now_add=True, null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    availability_slot = models.ForeignKey(
        'tutors.Availability',
        on_delete=models.SET_NULL,
        related_name='bookings',
        null=True, blank=True
    )
    end_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True, help_text='Student notes or special requests')
    tutor_response_note = models.TextField(blank=True, help_text='Tutor reason for decline/acceptance')
    session_link = models.URLField(blank=True, null=True)
    google_event_id = models.CharField(max_length=255, blank=True, null=True)
    location_address = models.TextField(blank=True, help_text='Onsite session address')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    duration = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']


    def clean(self):
        super().clean()
        if self.availability_slot_id and self.duration:
            slot = self.availability_slot
            slot_start = datetime.combine(datetime.today(), slot.start_time)
            slot_end = datetime.combine(datetime.today(), slot.end_time)
            slot_minutes = (slot_end - slot_start).total_seconds() / 60

            if self.duration > slot_minutes:
                raise ValidationError(
                    {'duration': 'Booking duration exceeds the selected availability slot.'}
                )

    def save(self, *args, **kwargs):
        self.clean()
        self.currency = self.currency or 'USD'
        super().save(*args, **kwargs)

    def get_tutor_fullname(self):
        name = self.tutor_profile.user.first_name + self.tutor_profile.user.last_name
        return name

    class Meta:
            ordering = ['-created_at']

    def __str__(self):
        return (
            f'Booking #{self.pk} | {self.student.get_full_name()} '
            f'-> {self.tutor_profile.user.get_full_name()} | {self.scheduled_date}'
        )
    
class GoogleOAuthToken(models.Model):
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()


class TimeStampedModel(models.Model):
    """Abstract base giving every model a UUID pk plus created/updated timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class SocialAccount(TimeStampedModel):
    """
    Links a User to a third-party identity provider. One User can hold
    several of these (e.g. password + Google), which is why this is a
    separate table rather than a provider field on User itself.
    """

    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="social_accounts")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    # the provider's stable subject identifier (Google's `sub` claim) -
    # never the email, since emails can be reassigned by the provider
    provider_uid = models.CharField(max_length=255)

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["provider", "provider_uid"], name="unique_provider_account"),
        ]

    def __str__(self):
        return f"{self.get_provider_display()} account for {self.user}"