from django.db import models
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from django.core.exceptions import ValidationError


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
    session_link = models.URLField(blank=True, help_text='Online session link if applicable')
    location_address = models.TextField(blank=True, help_text='Onsite session address')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    duration = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def calculate_amount(self):
        """
        Compute total_amount in USD from duration (minutes) and the tutor's
        hourly rate. Returns None if the inputs aren't available yet.
        """
        if not self.duration or not self.tutor_profile_id:
            return None

        hourly_rate = self.tutor_profile.hourly_rate
        if hourly_rate is None:
            return None

        hours = Decimal(self.duration) / Decimal(60)
        amount = (Decimal(hourly_rate) * hours).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        return amount

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
        self.total_amount = self.calculate_amount()
        self.currency = self.currency or 'USD'
        super().save(*args, **kwargs)

    class Meta:
            ordering = ['-created_at']

    def __str__(self):
        return (
            f'Booking #{self.pk} | {self.student.get_full_name()} '
            f'-> {self.tutor_profile.user.get_full_name()} | {self.scheduled_date}'
        )
