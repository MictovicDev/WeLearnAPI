from django.db import models
from django.conf import settings



class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
    


class PayMentInfo(models.Model):
    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        PAYPAL = 'paypal', 'PayPal'
        STRIPE = 'stripe', 'Stripe'
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_info',
        blank=True, null=True
    )
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f'{self.method} - {self.bank_name or "N/A"}'


class TutorProfile(models.Model):
    class TeachingMode(models.TextChoices):
        ONLINE = 'online', 'Online'
        ONSITE = 'onsite', 'Onsite'
        BOTH = 'both', 'Both'

    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'


    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tutor_profile'
    )
    bio = models.TextField()
    banner = models.ImageField(upload_to='tutor_banners/', blank=True, null=True)
    stripe_connect_account_id = models.CharField(max_length=255, blank=True, null=True)
    payouts_enabled = models.BooleanField(default=False)
    profile_image = models.ImageField(upload_to='tutor_profiles/', blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, help_text='City or area for onsite sessions')
    language = models.CharField(max_length=50, blank=True, help_text='Primary language of instruction')
    phone_number = models.CharField(max_length=20, blank=True, help_text='Contact number for students')
    professional_title = models.CharField(max_length=100, blank=True, help_text='e.g. Math Tutor, Physics Instructor')
    skills = models.JSONField(blank=True, null=True, help_text='List of skills or expertise areas')
    subjects = models.JSONField(blank=True, null=True, help_text='List of all Subjects')
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text='Hourly rate in USD')
    session_status = models.CharField(
        max_length=20, choices=TeachingMode.choices, default=TeachingMode.ONLINE
    )
    location = models.CharField(max_length=255, blank=True, help_text='City or area for onsite sessions')
    experience = models.JSONField(blank=True, null=True, help_text='List of experience entries')
    education = models.JSONField(blank=True, null=True, help_text='List of education entries')
    payment_info = models.OneToOneField(
        PayMentInfo,  on_delete=models.SET_NULL, null=True, blank=True, related_name='tutor_profile'
    )
    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.PENDING
    )
    is_verified = models.BooleanField(default=False)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.PositiveIntegerField(default=0)
    total_sessions = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-average_rating', '-total_sessions']

    def __str__(self):
        return f'TutorProfile({self.user.get_full_name()})'


class TutorCertification(models.Model):
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='certifications')
    title = models.CharField(max_length=255)
    document = models.FileField(upload_to='certifications/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.title} - {self.tutor.user.get_full_name()}'


class TutorVerificationDocument(models.Model):
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='verification_documents')
    document_type = models.CharField(max_length=100, help_text='e.g. National ID, Passport, Degree')
    document = models.FileField(upload_to='verification_docs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.document_type} - {self.tutor.user.get_full_name()}'


class Availability(models.Model):
    class DayOfWeek(models.TextChoices):
        MONDAY = 'Monday', 'Monday'
        TUESDAY = 'Tuesday', 'Tuesday'
        WEDNESDAY = 'Wednesday', 'Wednesday'
        THURSDAY = 'Thursday', 'Thursday'
        FRIDAY = 'Friday', 'Friday'
        SATURDAY = 'Saturday', 'Saturday'
        SUNDAY = 'Sunday', 'Sunday'

    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='availability_slots')
    day_of_week = models.CharField(max_length=9, choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_booked = models.BooleanField(default=False, help_text='Block this slot as unavailable')

    class Meta:
        ordering = ['day_of_week', 'start_time']
        unique_together = ['tutor', 'day_of_week', 'start_time']

    def __str__(self):
        return f'{self.tutor.user.get_full_name()} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}'
    


