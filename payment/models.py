# Add this to your models.py (or a new payments/models.py app)
# Adjust the TutorProfile import path to match your project structure.

from django.db import models
from django.core.validators import MinValueValidator
from tutors.models import TutorProfile  # adjust import path


class PayoutMethod(models.Model):
    class MethodType(models.TextChoices):
        BANK = 'bank', 'Bank Account'
        PAYPAL = 'paypal', 'PayPal'

    tutor = models.ForeignKey(
        TutorProfile, related_name='payout_methods', on_delete=models.CASCADE
    )
    method_type = models.CharField(max_length=20, choices=MethodType.choices)
    display_name = models.CharField(max_length=100)  # e.g. "Chase Bank •••• 4821"
    account_identifier = models.CharField(max_length=255)  # last4 or paypal email
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def save(self, *args, **kwargs):
        # keep only one default per tutor
        if self.is_default:
            PayoutMethod.objects.filter(tutor=self.tutor).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.display_name} ({self.tutor})'


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        EARNING = 'earning', 'Earning'
        PAYOUT = 'payout', 'Payout'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CLEARED = 'cleared', 'Cleared'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    tutor = models.ForeignKey(
        TutorProfile, related_name='transactions', on_delete=models.CASCADE
    )
    # adjust 'bookings.Booking' to your actual app_label.ModelName
    booking = models.ForeignKey(
        'bookings.Booking', related_name='transactions',
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    payout_method = models.ForeignKey(
        PayoutMethod, related_name='transactions',
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_transfer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_payout_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.transaction_type} - {self.amount} ({self.tutor})'

 
 
class TutorStripeAccount(models.Model):
    """One row per tutor. Wraps their Stripe Connect Express account."""
    tutor = models.OneToOneField(
        TutorProfile, related_name='stripe_account', on_delete=models.CASCADE
    )
    stripe_account_id = models.CharField(max_length=255, unique=True)
    charges_enabled = models.BooleanField(default=False)
    payouts_enabled = models.BooleanField(default=False)
    details_submitted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    @property
    def onboarding_complete(self):
        return self.charges_enabled and self.payouts_enabled and self.details_submitted
 
    def __str__(self):
        return f'{self.tutor} - {self.stripe_account_id}'



from django.conf import settings
from django.db import models


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    booking = models.OneToOneField("bookings.Booking", on_delete=models.CASCADE, related_name="payment")
    gateway = models.CharField(max_length=20, default="stripe")
    provider_reference = models.CharField(max_length=255, blank=True)
    amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=10, default="usd")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)